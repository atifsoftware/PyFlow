"""
core/database/drivers/base_connection.py
========================================
Base connection driver implementation for PyFlow.
Handles threading-local state, transactions, SAVEPOINTs, and hooks.
"""

import time
import logging
import threading
import functools
from contextlib import contextmanager
from typing import Any, List, Dict, Optional, Tuple, Callable

from core.database.contracts.connection import ConnectionInterface
from core.database.contracts.grammar import GrammarInterface, SchemaGrammarInterface

logger = logging.getLogger("PyFlow.db")


class QueryError(Exception):
    pass


class TransactionError(Exception):
    pass


class Profiler:
    """Thread-safe Profiler tracking query execution times, logs, and memory."""
    _local = threading.local()

    @classmethod
    def start_request(cls, method: str, path: str):
        cls._local.start_time = time.monotonic()
        cls._local.queries = []
        cls._local.logs = []

    @classmethod
    def log_query(cls, sql: str, params: tuple, duration_ms: float, connection: str = "default"):
        if not hasattr(cls._local, "queries"):
            cls._local.queries = []
        cls._local.queries.append({
            "connection": connection,
            "sql": sql,
            "params": params,
            "duration": duration_ms,
        })

    @classmethod
    def log_message(cls, level: str, message: str):
        if not hasattr(cls._local, "logs"):
            cls._local.logs = []
        cls._local.logs.append({
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        })

    @classmethod
    def get_data(cls) -> dict:
        if not hasattr(cls._local, "start_time"):
            return {"duration": 0, "queries": [], "logs": []}
        duration = (time.monotonic() - cls._local.start_time) * 1000
        return {
            "duration": duration,
            "queries": getattr(cls._local, "queries", []),
            "logs": getattr(cls._local, "logs", []),
        }


class BaseConnection(ConnectionInterface):
    """
    Abstract base connection driver providing thread-safe transactions,
    SAVEPOINTs, commit/rollback hooks, and profiler diagnostics.
    """

    def __init__(self, name: str, config: dict, grammar: GrammarInterface, schema_grammar: SchemaGrammarInterface):
        self._name = name
        self._config = config
        self._grammar = grammar
        self._schema_grammar = schema_grammar
        self._local = threading.local()

    @property
    def name(self) -> str:
        return self._name

    @property
    def grammar(self) -> GrammarInterface:
        return self._grammar

    @property
    def schema_grammar(self) -> SchemaGrammarInterface:
        return self._schema_grammar

    @property
    def placeholder(self) -> str:
        return getattr(self._grammar, "placeholder", "?")

    # ------------------------------------------------------------- Transactions
    def begin_transaction(self):
        """Start a transaction or establish a nested SAVEPOINT."""
        level = self.transaction_level()
        conn = self.connection()

        if level == 0:
            self._local.commit_hooks = [[]]
            self._local.rollback_hooks = [[]]
            self._local.savepoints = []
            if hasattr(conn, "autocommit"):
                conn.autocommit = False
            elif self.driver == "sqlite":
                conn.execute("BEGIN IMMEDIATE")
            self._local.transaction_level = 1
            logger.debug("[%s] Transaction শুরু হয়েছে (level=1)", self._name)
        else:
            sp_name = f"sp_{level + 1}"
            self._local.savepoints.append(sp_name)
            self._local.commit_hooks.append([])
            self._local.rollback_hooks.append([])
            self.execute_raw(f"SAVEPOINT {sp_name}")
            self._local.transaction_level = level + 1
            logger.debug("[%s] Nested savepoint তৈরি হয়েছে: %s (level=%d)", self._name, sp_name, level + 1)

    def commit(self):
        """Commit transaction or release savepoint."""
        level = self.transaction_level()
        if level <= 0:
            return

        conn = self.connection()

        if level == 1:
            try:
                conn.commit()
                logger.debug("[%s] Transaction commit সম্পন্ন (level=1)", self._name)
            except Exception as exc:
                self.rollback()
                raise TransactionError(f"Commit ব্যর্থ হয়েছে: {exc}") from exc
            finally:
                hooks = self._local.commit_hooks.pop() if getattr(self._local, "commit_hooks", None) else []
                self._local.transaction_level = 0
                self._local.savepoints = []
                self._run_hooks(hooks, "commit")
        else:
            sp_name = self._local.savepoints.pop()
            try:
                self.execute_raw(f"RELEASE SAVEPOINT {sp_name}")
                logger.debug("[%s] Savepoint released: %s", self._name, sp_name)
            except Exception:
                pass
            hooks = self._local.commit_hooks.pop() if getattr(self._local, "commit_hooks", None) else []
            self._local.transaction_level = level - 1
            if self._local.commit_hooks:
                self._local.commit_hooks[-1].extend(hooks)

    def rollback(self):
        """Rollback transaction or rollback to savepoint."""
        level = self.transaction_level()
        if level <= 0:
            return

        conn = self.connection()

        if level == 1:
            try:
                conn.rollback()
                logger.debug("[%s] Transaction rollback সম্পন্ন (level=1)", self._name)
            except Exception as exc:
                logger.error("[%s] Rollback ব্যর্থ: %s", self._name, exc)
            finally:
                hooks = self._local.rollback_hooks.pop() if getattr(self._local, "rollback_hooks", None) else []
                self._local.transaction_level = 0
                self._local.savepoints = []
                self._run_hooks(hooks, "rollback")
        else:
            sp_name = self._local.savepoints.pop()
            try:
                self.execute_raw(f"ROLLBACK TO SAVEPOINT {sp_name}")
                self.execute_raw(f"RELEASE SAVEPOINT {sp_name}")
                logger.debug("[%s] Rolled back to savepoint: %s", self._name, sp_name)
            except Exception as exc:
                logger.error("[%s] Savepoint rollback ব্যর্থ: %s", self._name, exc)
            if getattr(self._local, "commit_hooks", None):
                self._local.commit_hooks.pop()  # Discard inner commit hooks
            hooks = self._local.rollback_hooks.pop() if getattr(self._local, "rollback_hooks", None) else []
            self._local.transaction_level = level - 1
            self._run_hooks(hooks, "rollback")

    def in_transaction(self) -> bool:
        return self.transaction_level() > 0

    def transaction_level(self) -> int:
        return getattr(self._local, "transaction_level", 0)

    @contextmanager
    def transaction(self, attempts: int = 1):
        """
        Atomic transaction context manager.
        Usage:
            with conn.transaction():
                conn.execute(...)
        """
        last_exc = None
        for attempt in range(1, attempts + 1):
            self.begin_transaction()
            try:
                yield self
                self.commit()
                return
            except Exception as exc:
                self.rollback()
                last_exc = exc
                if attempt < attempts:
                    time.sleep(0.05 * (2 ** (attempt - 1)))
                    continue
                raise last_exc

    @contextmanager
    def savepoint(self, name: Optional[str] = None):
        """
        Named savepoint context manager.
        Usage:
            with conn.savepoint("line_1"):
                ...
        """
        if not self.in_transaction():
            raise TransactionError("Savepoint শুধুমাত্র সক্রিয় transaction-এর ভেতরে ব্যবহার করা যায়")

        sp_name = name or f"custom_sp_{len(getattr(self._local, 'savepoints', [])) + 1}"
        self.execute_raw(f"SAVEPOINT {sp_name}")
        self._local.commit_hooks.append([])
        self._local.rollback_hooks.append([])

        try:
            yield sp_name
            try:
                self.execute_raw(f"RELEASE SAVEPOINT {sp_name}")
            except Exception:
                pass
            hooks = self._local.commit_hooks.pop()
            if self._local.commit_hooks:
                self._local.commit_hooks[-1].extend(hooks)
        except Exception:
            try:
                self.execute_raw(f"ROLLBACK TO SAVEPOINT {sp_name}")
                self.execute_raw(f"RELEASE SAVEPOINT {sp_name}")
            except Exception:
                pass
            hooks = self._local.rollback_hooks.pop()
            self._run_hooks(hooks, "rollback")
            raise

    def atomic(self, fn: Callable):
        """Decorator for function-level atomic transactions."""
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with self.transaction():
                return fn(*args, **kwargs)
        return wrapper

    def on_commit(self, callback: Callable):
        """Register hook callback to execute upon successful transaction commit."""
        if not hasattr(self._local, "commit_hooks") or not self._local.commit_hooks:
            self._local.commit_hooks = [[]]
        self._local.commit_hooks[-1].append(callback)

    def on_rollback(self, callback: Callable):
        """Register hook callback to execute upon transaction rollback."""
        if not hasattr(self._local, "rollback_hooks") or not self._local.rollback_hooks:
            self._local.rollback_hooks = [[]]
        self._local.rollback_hooks[-1].append(callback)

    def _run_hooks(self, hooks: list, hook_type: str):
        for hook in hooks:
            try:
                hook()
            except Exception as exc:
                logger.error("[%s] %s hook ব্যর্থ: %s", self._name, hook_type, exc)

    def execute_raw(self, sql: str):
        """Execute unparameterized raw command (e.g. SAVEPOINT)."""
        cur = self.cursor(as_dict=False)
        try:
            cur.execute(sql)
        finally:
            try:
                cur.close()
            except Exception:
                pass
