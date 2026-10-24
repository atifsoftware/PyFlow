"""
core/database/drivers/mysql_connection.py
=========================================
MySQL connection driver with thread-safe connection pooling for PyFlow.
"""

import time
import logging
import threading
from queue import Queue, Empty
from typing import Any, List, Optional

from core.database.drivers.base_connection import BaseConnection, QueryError, Profiler
from core.database.grammar.mysql_grammar import MySqlGrammar
from core.database.schema.mysql_schema_grammar import MySqlSchemaGrammar

logger = logging.getLogger("PyFlow.db")


class MySqlConnection(BaseConnection):
    """MySQL connection driver with connection pooling."""

    def __init__(self, name: str = "mysql", config: dict = None):
        cfg = config or {}
        grammar = MySqlGrammar()
        schema_grammar = MySqlSchemaGrammar()
        super().__init__(name, cfg, grammar, schema_grammar)

        self._pool_size = int(cfg.get("pool_size", cfg.get("DB_POOL_SIZE", 5)))
        self._pool: Queue = Queue(maxsize=self._pool_size)
        self._lock = threading.Lock()
        self._created = 0
        self._initialized = False

    @property
    def driver(self) -> str:
        return "mysql"

    def _create_raw_connection(self):
        try:
            import MySQLdb
            import MySQLdb.cursors
        except ImportError:
            try:
                import pymysql
                pymysql.install_as_MySQLdb()
                import MySQLdb
                import MySQLdb.cursors
            except ImportError as exc:
                raise QueryError(
                    "MySQL ব্যবহার করতে 'pip install mysqlclient' অথবা 'pip install pymysql' করুন, "
                    "অথবা .env-এ DB_DRIVER=sqlite দিয়ে রাখুন"
                ) from exc

        host = self._config.get("host", self._config.get("DB_HOST", "127.0.0.1"))
        port = int(self._config.get("port", self._config.get("DB_PORT", 3306)))
        user = self._config.get("user", self._config.get("DB_USER", "root"))
        passwd = self._config.get("password", self._config.get("DB_PASSWORD", ""))
        db = self._config.get("database", self._config.get("DB_NAME", ""))
        tz = self._config.get("timezone", self._config.get("DB_TIMEZONE", "+06:00"))

        conn = MySQLdb.connect(
            host=host,
            port=port,
            user=user,
            passwd=passwd,
            db=db,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
        )
        cur = conn.cursor()
        cur.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.execute("SET time_zone = %s", (tz,))
        cur.close()
        conn.commit()
        return conn

    def _is_alive(self, conn) -> bool:
        if conn is None:
            return False
        try:
            if hasattr(conn, "ping"):
                try:
                    conn.ping(reconnect=True)
                except TypeError:
                    conn.ping()
                return True
            return True
        except Exception:
            return False

    def connection(self):
        """Get or acquire connection for active thread."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            # Try to get from pool
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
                            conn = self._pool.get(timeout=2.0)
                            if not self._is_alive(conn):
                                conn = self._create_raw_connection()
                        except Empty:
                            max_overflow = max(15, self._pool_size * 3)
                            if self._created < max_overflow:
                                conn = self._create_raw_connection()
                                self._created += 1
                                logger.warning("[%s] Pool busy. Created overflow connection (%d/%d).", self._name, self._created, max_overflow)
                            else:
                                raise QueryError(f"MySQL connection pool exhausted (size={self._pool_size}, max_overflow={max_overflow}).")
            self._local.conn = conn

        return self._local.conn

    def cursor(self, as_dict: bool = True):
        conn = self.connection()
        if not as_dict:
            return conn.cursor()
        cursor_cls = None
        try:
            import MySQLdb.cursors
            cursor_cls = getattr(MySQLdb.cursors, "DictCursor", None)
        except Exception:
            pass
        if not cursor_cls:
            try:
                import pymysql.cursors
                cursor_cls = pymysql.cursors.DictCursor
            except Exception:
                pass

        if cursor_cls:
            try:
                return conn.cursor(cursor=cursor_cls)
            except (TypeError, ValueError):
                try:
                    return conn.cursor(cursorclass=cursor_cls)
                except Exception:
                    pass
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
            if sql_upper.startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
                return list(cur.fetchall())
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
            cur.execute("SELECT LAST_INSERT_ID()")
            row = cur.fetchone()
            return int(row[0]) if row and row[0] else 0
        finally:
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
                with self._lock:
                    self._created = max(0, self._created - 1)
                try:
                    conn.close()
                except Exception:
                    pass

    def close_all(self):
        """Close all pooled connections."""
        self.close()
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
