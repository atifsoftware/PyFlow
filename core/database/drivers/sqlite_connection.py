"""
core/database/drivers/sqlite_connection.py
==========================================
SQLite connection driver for PyFlow.
"""

import os
import sqlite3
import time
import logging
from typing import Any, List, Optional
from core.database.drivers.base_connection import BaseConnection, QueryError, Profiler
from core.database.grammar.sqlite_grammar import SqliteGrammar
from core.database.schema.sqlite_schema_grammar import SqliteSchemaGrammar

logger = logging.getLogger("PyFlow.db")


class SqliteConnection(BaseConnection):
    """Thread-local SQLite connection driver."""

    def __init__(self, name: str = "sqlite", config: dict = None):
        cfg = config or {}
        grammar = SqliteGrammar()
        schema_grammar = SqliteSchemaGrammar()
        super().__init__(name, cfg, grammar, schema_grammar)
        self._db_path = cfg.get("database", cfg.get("DB_NAME", "storage/database.sqlite"))

    @property
    def driver(self) -> str:
        return "sqlite"

    def connection(self) -> sqlite3.Connection:
        """Get or initialize thread-local sqlite3 connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            if self._db_path != ":memory:":
                db_dir = os.path.dirname(self._db_path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)

            conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                timeout=float(self._config.get("timeout", 10.0)),
            )
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._local.conn = conn

        return self._local.conn

    def cursor(self, as_dict: bool = True):
        conn = self.connection()
        cur = conn.cursor()
        if as_dict:
            cur.row_factory = sqlite3.Row
        else:
            cur.row_factory = None
        return cur

    def execute(self, sql: str, params: tuple = (), as_dict: bool = True) -> Any:
        conn = self.connection()
        cur = self.cursor(as_dict=as_dict)
        start = time.monotonic()
        try:
            cur.execute(sql, params)
            elapsed = (time.monotonic() - start) * 1000
            Profiler.log_query(sql, params, elapsed, connection=self._name)

            sql_upper = sql.strip().upper()
            if sql_upper.startswith(("SELECT", "PRAGMA", "EXPLAIN")):
                if as_dict and cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = []
                    for row in cur.fetchall():
                        rows.append(dict(zip(columns, row)))
                    return rows
                return cur.fetchall()
            elif sql_upper.startswith("INSERT"):
                affected = cur.rowcount if cur.rowcount > 0 else 1
                last_id = self.last_insert_id(cur)
                if last_id:
                    return {"id": last_id, "affected": affected}
                return {"affected": affected}
            else:
                return cur.rowcount if cur.rowcount >= 0 else 0
        except Exception as exc:
            if not self.in_transaction():
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error("[%s] Query ব্যর্থ: %s | params=%s | error=%s", self._name, sql, params, exc)
            raise QueryError(f"Query ব্যর্থ হয়েছে: {exc}\nSQL: {sql}") from exc
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def execute_many(self, sql: str, params_list: List[tuple], batch_size: int = 1000) -> int:
        if not params_list:
            return 0
        conn = self.connection()
        cur = self.cursor(as_dict=False)
        total_rows = 0
        try:
            for i in range(0, len(params_list), batch_size):
                batch = params_list[i:i + batch_size]
                cur.executemany(sql, batch)
                total_rows += cur.rowcount if cur.rowcount > 0 else len(batch)
            if not self.in_transaction():
                self.commit()
            return total_rows
        except Exception as exc:
            if not self.in_transaction():
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error("[%s] Batch query ব্যর্থ: %s", self._name, exc)
            raise QueryError(f"Batch query ব্যর্থ: {exc}") from exc
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def last_insert_id(self, cursor: Any = None) -> int:
        if cursor is not None and hasattr(cursor, "lastrowid") and cursor.lastrowid:
            return int(cursor.lastrowid)
        cur = self.cursor(as_dict=False)
        try:
            cur.execute("SELECT last_insert_rowid()")
            row = cur.fetchone()
            return int(row[0]) if row and row[0] else 0
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def close(self):
        """Close connection for current thread."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    def close_all(self):
        self.close()
