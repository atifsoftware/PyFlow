"""
core/database/drivers/postgres_connection.py
============================================
PostgreSQL connection driver with thread-safe pooling for PyFlow.
"""

import time
import logging
import threading
from queue import Queue, Empty
from typing import Any, List, Optional

from core.database.drivers.base_connection import BaseConnection, QueryError, Profiler
from core.database.grammar.postgres_grammar import PostgresGrammar
from core.database.schema.postgres_schema_grammar import PostgresSchemaGrammar

logger = logging.getLogger("PyFlow.db")


class PostgresConnection(BaseConnection):
    """PostgreSQL connection driver with connection pooling."""

    def __init__(self, name: str = "pgsql", config: dict = None):
        cfg = config or {}
        grammar = PostgresGrammar()
        schema_grammar = PostgresSchemaGrammar()
        super().__init__(name, cfg, grammar, schema_grammar)

        self._pool_size = int(cfg.get("pool_size", cfg.get("DB_POOL_SIZE", 5)))
        self._pool: Queue = Queue(maxsize=self._pool_size)
        self._lock = threading.Lock()
        self._created = 0

    @property
    def driver(self) -> str:
        return "postgresql"

    def _create_raw_connection(self):
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as exc:
            raise QueryError(
                "PostgreSQL ব্যবহার করতে 'pip install psycopg2-binary' করুন, "
                "অথবা .env-এ DB_DRIVER=sqlite দিয়ে রাখুন"
            ) from exc

        host = self._config.get("host", self._config.get("DB_HOST", "127.0.0.1"))
        port = int(self._config.get("port", self._config.get("DB_PORT", 5432)))
        user = self._config.get("user", self._config.get("DB_USER", "postgres"))
        password = self._config.get("password", self._config.get("DB_PASSWORD", ""))
        dbname = self._config.get("database", self._config.get("DB_NAME", ""))
        schema = self._config.get("schema", self._config.get("DB_SCHEMA", "public"))

        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=10,
            options=f"-c search_path={schema}",
        )
        conn.autocommit = False
        return conn

    def _is_alive(self, conn) -> bool:
        if conn is None:
            return False
        try:
            if hasattr(conn, "closed") and conn.closed != 0:
                return False
            _ = conn.isolation_level
            return True
        except Exception:
            return False

    def connection(self):
        """Get or acquire connection for active thread."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            try:
                conn = self._pool.get_nowait()
                if not self._is_alive(conn):
                    conn = self._create_raw_connection()
            except Empty:
                with self._lock:
                    if self._created < self._pool_size:
                        conn = self._create_raw_connection()
                        self._created += 1
                    else:
                        try:
                            conn = self._pool.get(timeout=5.0)
                            if not self._is_alive(conn):
                                conn = self._create_raw_connection()
                        except Empty:
                            raise QueryError(f"PostgreSQL connection pool exhausted (size={self._pool_size}).")
            self._local.conn = conn

        return self._local.conn

    def cursor(self, as_dict: bool = True):
        conn = self.connection()
        try:
            import psycopg2.extras
            if as_dict:
                return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            return conn.cursor()
        except Exception:
            return conn.cursor()

    def execute(self, sql: str, params: tuple = (), as_dict: bool = True) -> Any:
        conn = self.connection()
        cur = self.cursor(as_dict=as_dict)
        start = time.monotonic()
        try:
            cur.execute(sql, params)
            elapsed = (time.monotonic() - start) * 1000
            Profiler.log_query(sql, params, elapsed, connection=self._name)

            sql_upper = sql.strip().upper()
            if sql_upper.startswith(("SELECT", "EXPLAIN")):
                return cur.fetchall()
            elif sql_upper.startswith("INSERT"):
                affected = cur.rowcount if cur.rowcount > 0 else 1
                # If RETURNING was used, fetch the inserted id directly
                if "RETURNING" in sql_upper:
                    try:
                        row = cur.fetchone()
                        if row:
                            inserted_id = dict(row).get("id") if isinstance(row, dict) else row[0]
                            return {"id": inserted_id, "affected": affected}
                    except Exception:
                        pass
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
        cur = cursor or self.cursor(as_dict=False)
        should_close = cursor is None
        try:
            cur.execute("SELECT LASTVAL()")
            row = cur.fetchone()
            val = row[0] if row else 0
            return int(val) if val else 0
        except Exception:
            return 0
        finally:
            if should_close:
                try:
                    cur.close()
                except Exception:
                    pass

    def close(self):
        """Release active connection back to pool."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            conn = self._local.conn
            self._local.conn = None
            try:
                self._pool.put_nowait(conn)
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

    def close_all(self):
        self.close()
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
