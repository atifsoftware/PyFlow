"""
core/database.py
=================
PHP-এর PDO-র মতো একটা শক্তিশালী Database wrapper।
MySQL, PostgreSQL এবং SQLite — তিনটি driver সাপোর্ট করে।

.env-এ driver বেছে নিন:
    DB_DRIVER=mysql          # MySQL 5.7+ / MariaDB
    DB_DRIVER=postgresql     # PostgreSQL 13+
    DB_DRIVER=sqlite         # SQLite (development/testing)

PDO-স্টাইল বৈশিষ্ট্য (v4 — Multi-driver):
  - Prepared Statements (bound parameters) — SQL Injection সম্ভব না
  - কানেকশন পুলিং (MySQL + PostgreSQL)
  - Transaction context manager (with Database.transaction())
  - Nested transactions — SAVEPOINT sp_2, sp_3...
  - Named savepoint API (with Database.savepoint("name"))
  - @atomic decorator — function-level transaction
  - on_commit / on_rollback hooks — email-safe notifications
  - Auto-commit in QueryBuilder outside transactions
  - Driver-aware identifier quoting (backtick vs double-quote)
  - utf8mb4 / UTF-8 — বাংলা ও ইমোজি সম্পূর্ণ সাপোর্ট
  - Auto-reconnect — connection drop হলে নিজেই reconnect করে

Atomic Transaction ব্যবহার:
    # Context Manager
    with Database.transaction():
        Order.create(data)
        OrderItem.create(item_data)          # দুটোই commit বা rollback

    # Decorator
    @atomic
    def post_journal(entries):
        for entry in entries:
            JournalLine.create(entry)

    # on_commit hook (email-safe)
    with Database.transaction():
        order = Order.create(data)
        Database.on_commit(lambda: Mailer.send("confirm", email))

    # Named savepoint (partial rollback)
    with Database.transaction():
        journal = Journal.create(header)
        with Database.savepoint("line_1"):
            JournalLine.create(line)         # শুধু এটা rollback হতে পারে
"""

import os
import sqlite3
import threading
import logging
import time
import functools
from queue import Queue, Empty

logger = logging.getLogger("PyFlow.db")


class QueryError(Exception):
    pass


class TransactionError(Exception):
    """Transaction-সংক্রান্ত error — unbalanced, locked period ইত্যাদি"""
    pass


# ─────────────────────────────── Profiler ────────────────────────────────────

class Profiler:
    """
    Thread-safe Profiler:
    রিকোয়েস্টের এক্সিকিউশন টাইম, ডেটাবেস কুয়েরি এবং লগ ট্র্যাক করে।
    """
    _local = threading.local()

    @classmethod
    def start_request(cls, method: str, path: str):
        cls._local.start_time = time.monotonic()
        cls._local.queries = []
        cls._local.logs = []

    @classmethod
    def log_query(cls, sql: str, params: tuple, duration_ms: float):
        if not hasattr(cls._local, "queries"):
            cls._local.queries = []
        cls._local.queries.append({
            "sql":      sql,
            "params":   params,
            "duration": duration_ms,
        })

    @classmethod
    def log_message(cls, level: str, message: str):
        if not hasattr(cls._local, "logs"):
            cls._local.logs = []
        cls._local.logs.append({
            "time":    time.strftime("%H:%M:%S"),
            "level":   level,
            "message": message,
        })

    @classmethod
    def get_data(cls) -> dict:
        if not hasattr(cls._local, "start_time"):
            return {"duration": 0, "queries": [], "logs": []}
        duration = (time.monotonic() - cls._local.start_time) * 1000
        return {
            "duration": duration,
            "queries":  getattr(cls._local, "queries", []),
            "logs":     getattr(cls._local, "logs", []),
        }


# ─────────────────────────────── Connection Pool ─────────────────────────────

class ConnectionPool:
    """
    Thread-safe MySQL কানেকশন পুল।
    PHP-এর PDO persistent connection-এর মতো কাজ করে।
    প্রতিটা request শেষে connection pool-এ ফেরত যায়, বন্ধ হয় না।
    """

    def __init__(self, factory, pool_size: int = 5):
        self._factory    = factory
        self._pool: Queue = Queue(maxsize=pool_size)
        self._pool_size  = pool_size
        self._lock       = threading.Lock()
        self._created    = 0

        initial = min(2, pool_size)
        for _ in range(initial):
            conn = self._factory()
            self._pool.put(conn)
            self._created += 1

    def acquire(self, timeout: float = 5.0):
        """Pool থেকে একটা connection নেওয়া। খালি না থাকলে নতুন বানায়।"""
        try:
            conn = self._pool.get_nowait()
            try:
                conn.ping(reconnect=True)
            except Exception:
                conn = self._factory()
            return conn
        except Empty:
            pass

        with self._lock:
            if self._created < self._pool_size:
                conn = self._factory()
                self._created += 1
                return conn

        try:
            conn = self._pool.get(timeout=timeout)
            try:
                conn.ping(reconnect=True)
            except Exception:
                conn = self._factory()
            return conn
        except Empty:
            raise QueryError(
                f"Database connection pool exhausted (size={self._pool_size}). "
                "DB_POOL_SIZE বাড়িয়ে দেখুন।"
            )

    def release(self, conn):
        """Connection pool-এ ফেরত দেওয়া (বন্ধ করা না)"""
        try:
            self._pool.put_nowait(conn)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

    def close_all(self):
        """সব connection বন্ধ করা (graceful shutdown)"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass


# ─────────────────────────────── Database ────────────────────────────────────

class Database:
    """
    Singleton connection manager।
    - MySQL: কানেকশন পুল ব্যবহার করে (প্রতি থ্রেডে আলাদা)
    - SQLite: থ্রেড-লোকাল connection (ডেভেলপমেন্ট/ছোট প্রজেক্ট)

    ব্যবহার:
        Database.init(config)          # App শুরুতে একবার
        Database.execute(sql, params)  # Query চালানো
        Database.close()               # Request শেষে connection ফেরত দেওয়া
    """

    _config: dict        = None
    _local               = threading.local()
    _pool: ConnectionPool = None
    driver: str          = "sqlite"

    # ──────────────────────────── Init ───────────────────────────────────────

    @classmethod
    def init(cls, config: dict):
        cls._config = config
        cls.driver  = config.get("DB_DRIVER", "sqlite").lower()

        if cls.driver not in ("mysql", "postgresql", "sqlite"):
            raise QueryError(
                f"অজানা DB_DRIVER: '{cls.driver}'। "
                "সঠিক মান: mysql, postgresql, sqlite"
            )

        if cls.driver == "mysql":
            pool_size  = int(config.get("DB_POOL_SIZE", 5))
            cls._pool  = ConnectionPool(cls._create_mysql_connection, pool_size)
            logger.info(
                "MySQL connection pool তৈরি হয়েছে (size=%d, host=%s, db=%s)",
                pool_size, config.get("DB_HOST"), config.get("DB_NAME"),
            )

        elif cls.driver == "postgresql":
            pool_size = int(config.get("DB_POOL_SIZE", 5))
            cls._pool = ConnectionPool(cls._create_postgresql_connection, pool_size)
            logger.info(
                "PostgreSQL connection pool তৈরি হয়েছে (size=%d, host=%s, db=%s)",
                pool_size, config.get("DB_HOST"), config.get("DB_NAME"),
            )

    @classmethod
    def _create_mysql_connection(cls):
        """নতুন MySQL connection তৈরি করা"""
        try:
            import pymysql
            import pymysql.cursors
        except ImportError as exc:
            raise QueryError(
                "MySQL ব্যবহার করতে 'pip install pymysql' করুন, "
                "অথবা .env-এ DB_DRIVER=sqlite দিয়ে রাখুন"
            ) from exc

        config = Database._config
        conn   = pymysql.connect(
            host         = config.get("DB_HOST", "127.0.0.1"),
            port         = int(config.get("DB_PORT", 3306)),
            user         = config.get("DB_USER", "root"),
            password     = config.get("DB_PASSWORD", ""),
            database     = config.get("DB_NAME", ""),
            charset      = "utf8mb4",
            collation    = "utf8mb4_unicode_ci",
            cursorclass  = pymysql.cursors.DictCursor,
            autocommit   = False,
            connect_timeout = 10,
            read_timeout    = 30,
            write_timeout   = 30,
        )
        cursor = conn.cursor()
        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("SET time_zone = %s", (config.get("DB_TIMEZONE", "+06:00"),))
        conn.commit()
        return conn

    @classmethod
    def _create_postgresql_connection(cls):
        """নতুন PostgreSQL connection তৈরি করা (psycopg2)"""
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError as exc:
            raise QueryError(
                "PostgreSQL ব্যবহার করতে 'pip install psycopg2-binary' করুন, "
                "অথবা .env-এ DB_DRIVER=sqlite দিয়ে রাখুন"
            ) from exc

        config = Database._config
        conn = psycopg2.connect(
            host     = config.get("DB_HOST",     "127.0.0.1"),
            port     = int(config.get("DB_PORT", 5432)),
            user     = config.get("DB_USER",     "postgres"),
            password = config.get("DB_PASSWORD", ""),
            dbname   = config.get("DB_NAME",     ""),
            connect_timeout = 10,
            options  = f"-c search_path={config.get('DB_SCHEMA', 'public')}",
        )
        conn.autocommit = False
        # psycopg2 cursor — DictCursor দিয়ে dict-like row
        conn._cursor_factory = psycopg2.extras.RealDictCursor
        logger.debug("PostgreSQL connection তৈরি হয়েছে")
        return conn

    @classmethod
    def _create_sqlite_connection(cls):
        if cls._config is None:
            raise QueryError("Database.init(config) কল না করে connection নেওয়া যাবে না")
        db_path = cls._config.get("DB_NAME", "storage/database.sqlite")
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    # ──────────────────────────── Connection ─────────────────────────────────

    @classmethod
    def connection(cls):
        """
        বর্তমান থ্রেডের connection রিটার্ন করে।
        - MySQL / PostgreSQL: pool থেকে নেওয়া হয়
        - SQLite: thread-local connection
        """
        if Database.driver in ("mysql", "postgresql"):
            if not hasattr(Database._local, "conn") or Database._local.conn is None:
                Database._local.conn = Database._pool.acquire()
            return Database._local.conn
        else:  # sqlite
            if not hasattr(Database._local, "conn") or Database._local.conn is None:
                Database._local.conn = Database._create_sqlite_connection()
            return Database._local.conn

    @classmethod
    def cursor(cls):
        """
        Driver-aware cursor রিটার্ন করে।
        PostgreSQL-এ RealDictCursor ব্যবহার করে dict-like rows পাওয়া যায়।
        """
        conn = cls.connection()
        if cls.driver == "postgresql":
            try:
                import psycopg2.extras
                return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            except Exception:
                return conn.cursor()
        return conn.cursor()

    @classmethod
    def placeholder(cls) -> str:
        """
        Driver-aware parameter placeholder.
        - MySQL:      %s  (pymysql)
        - PostgreSQL: %s  (psycopg2 — একই!)
        - SQLite:     ?   (sqlite3)
        """
        return "?" if cls.driver == "sqlite" else "%s"

    @classmethod
    def quote_identifier(cls, name: str) -> str:
        """
        Driver-aware identifier quoting.
        - MySQL:              `table_name`  (backtick)
        - PostgreSQL/SQLite:  "table_name"  (double-quote)

        এটা সরাসরি ব্যবহার করবেন না — query_builder._safe_identifier() ব্যবহার করুন।
        """
        if cls.driver == "mysql":
            return f"`{name}`"
        return f'"{name}"'

    # ──────────────────────────── Execute ────────────────────────────────────

    @classmethod
    def execute(cls, sql: str, params: tuple = ()):
        """
        যেকোনো SQL চালায়। params সবসময় tuple/list হিসেবে দিতে হবে।
        কখনো sql-এর ভেতর f-string দিয়ে ভ্যালু বসাবেন না — SQL Injection ঝুঁকি।

        সব driver-এ একই API:
            Database.execute("SELECT * FROM users WHERE id = %s", (1,))  # MySQL/PostgreSQL
            Database.execute("SELECT * FROM users WHERE id = ?",  (1,))  # SQLite
            # query_builder ব্যবহার করলে placeholder স্বয়ংক্রিয়
        """
        conn   = cls.connection()
        cur    = cls.cursor()  # driver-aware cursor
        start  = time.monotonic()
        try:
            cur.execute(sql, params)
            elapsed = (time.monotonic() - start) * 1000
            Profiler.log_query(sql, params, elapsed)
            if elapsed > 200:
                logger.warning("Slow query (%.0fms): %s", elapsed, sql[:120])
            return cur
        except Exception as exc:
            # Transaction-এর বাইরে থাকলে অটো rollback
            if not cls.in_transaction():
                conn.rollback()
            logger.error("Query ব্যর্থ: %s | params=%s | error=%s", sql, params, exc)
            raise QueryError(f"Query ব্যর্থ হয়েছে: {exc}\nSQL: {sql}") from exc

    @classmethod
    def execute_many(cls, sql: str, params_list: list) -> int:
        """একাধিক row একসাথে INSERT করার জন্য (batch insert)।"""
        conn = cls.connection()
        cur  = cls.cursor()
        try:
            cur.executemany(sql, params_list)
            if not cls.in_transaction():
                cls.commit()
            return cur.rowcount
        except Exception as exc:
            if not cls.in_transaction():
                conn.rollback()
            raise QueryError(f"Batch query ব্যর্থ: {exc}") from exc

    # ──────────────────────────── Commit / Rollback ──────────────────────────

    @classmethod
    def commit(cls):
        """সরাসরি commit — সাধারণত transaction context manager ব্যবহার করুন।"""
        cls.connection().commit()

    @classmethod
    def rollback(cls):
        """সরাসরি rollback — সাধারণত transaction context manager ব্যবহার করুন।"""
        cls.connection().rollback()

    @classmethod
    def in_transaction(cls) -> bool:
        """বর্তমান thread কোনো transaction-এর ভেতরে আছে কিনা"""
        return (
            hasattr(cls._local, "transaction_level")
            and cls._local.transaction_level > 0
        )

    @classmethod
    def transaction_level(cls) -> int:
        """Nesting depth: 0 = বাইরে, 1 = outer, 2 = nested, ..."""
        return getattr(cls._local, "transaction_level", 0)

    @classmethod
    def last_insert_id(cls, cursor) -> int:
        return cursor.lastrowid

    # ──────────────────────────── Hooks ──────────────────────────────────────

    @classmethod
    def on_commit(cls, callback):
        """
        Transaction সফলভাবে commit হলে callback চালাবে।
        ব্যবহার: email/notification পাঠানো যেগুলো rollback-এ যাওয়া উচিত না।

        with Database.transaction():
            order = Order.create(data)
            Database.on_commit(lambda: Mailer.send_order_confirmation(order))
        """
        if not hasattr(cls._local, "commit_hooks"):
            cls._local.commit_hooks = []
        cls._local.commit_hooks.append(callback)

    @classmethod
    def on_rollback(cls, callback):
        """
        Transaction rollback হলে callback চালাবে।
        ব্যবহার: error logging, compensation actions।

        with Database.transaction():
            StockOut.create(data)
            Database.on_rollback(lambda: logger.error("Stock deduction failed!"))
        """
        if not hasattr(cls._local, "rollback_hooks"):
            cls._local.rollback_hooks = []
        cls._local.rollback_hooks.append(callback)

    @classmethod
    def _fire_commit_hooks(cls):
        """Commit hooks চালানো ও clear করা"""
        hooks = getattr(cls._local, "commit_hooks", [])
        cls._local.commit_hooks = []
        for hook in hooks:
            try:
                hook()
            except Exception as e:
                logger.warning("on_commit hook ব্যর্থ হয়েছে: %s", e)

    @classmethod
    def _fire_rollback_hooks(cls):
        """Rollback hooks চালানো ও clear করা"""
        hooks = getattr(cls._local, "rollback_hooks", [])
        cls._local.rollback_hooks  = []
        cls._local.commit_hooks    = []   # commit hooks বাতিল
        for hook in hooks:
            try:
                hook()
            except Exception as e:
                logger.warning("on_rollback hook ব্যর্থ হয়েছে: %s", e)

    # ──────────────────────────── Connection close ───────────────────────────

    @classmethod
    def close(cls):
        """
        Request শেষে connection পরিচালনা:
        - MySQL/PostgreSQL: pool-এ ফেরত দেওয়া (পুনরায় ব্যবহারযোগ্য)
        - SQLite: সত্যিই বন্ধ করা
        """
        if hasattr(cls._local, "conn") and cls._local.conn:
            if cls.driver in ("mysql", "postgresql") and cls._pool:
                cls._pool.release(cls._local.conn)
            else:
                cls._local.conn.close()
            cls._local.conn = None

    @classmethod
    def get_status(cls) -> dict:
        """Connection pool-এর বর্তমান অবস্থা (debug/monitoring)"""
        if cls.driver in ("mysql", "postgresql") and cls._pool:
            return {
                "driver":    cls.driver,
                "pool_size": cls._pool._pool_size,
                "available": cls._pool._pool.qsize(),
                "created":   cls._pool._created,
            }
        return {"driver": cls.driver}

    # ─────────────────────────── Transaction Context Manager ─────────────────

    class transaction:
        """
        Atomic Transaction context manager।

        সাধারণ ব্যবহার:
            with Database.transaction():
                Order.create(order_data)
                for item in items:
                    OrderItem.create(item)
            # সব ঠিক → commit, যেকোনো error → rollback

        Nested ব্যবহার:
            with Database.transaction():           # level 1 → COMMIT/ROLLBACK
                journal = Journal.create(...)
                with Database.transaction():       # level 2 → SAVEPOINT sp_2
                    JournalLine.create(...)        # শুধু এটা আলাদাভাবে rollback হতে পারে

        on_commit / on_rollback hooks:
            with Database.transaction():
                order = Order.create(data)
                Database.on_commit(lambda: send_email(order))
                Database.on_rollback(lambda: log_failure(order))
        """

        def __enter__(self):
            conn = Database.connection()
            if not hasattr(Database._local, "transaction_level"):
                Database._local.transaction_level = 0

            Database._local.transaction_level += 1
            level = Database._local.transaction_level

            if level > 1:
                # Nested → SAVEPOINT
                sp_name = f"sp_{level}"
                conn.cursor().execute(f"SAVEPOINT {sp_name}")
                logger.debug("SAVEPOINT %s তৈরি হয়েছে", sp_name)
            else:
                logger.debug("Transaction শুরু হয়েছে (level 1)")

            return conn

        def __exit__(self, exc_type, exc_val, exc_tb):
            if not hasattr(Database._local, "transaction_level"):
                Database._local.transaction_level = 1

            level = Database._local.transaction_level
            conn  = Database.connection()

            if exc_type is not None:
                # ── Error → Rollback ──────────────────────────────────────
                if level > 1:
                    sp_name = f"sp_{level}"
                    try:
                        conn.cursor().execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                        conn.cursor().execute(f"RELEASE SAVEPOINT {sp_name}")
                    except Exception as sp_err:
                        logger.error("SAVEPOINT rollback ব্যর্থ: %s", sp_err)
                else:
                    Database.rollback()
                    Database._fire_rollback_hooks()
                    logger.debug("Transaction rollback হয়েছে")

                Database._local.transaction_level = max(0, level - 1)
                return False  # ✅ exception সবসময় propagate করো

            else:
                # ── Success → Commit ──────────────────────────────────────
                if level > 1:
                    sp_name = f"sp_{level}"
                    try:
                        conn.cursor().execute(f"RELEASE SAVEPOINT {sp_name}")
                    except Exception:
                        pass
                else:
                    Database.commit()
                    Database._fire_commit_hooks()
                    logger.debug("Transaction commit হয়েছে")

                Database._local.transaction_level = max(0, level - 1)
                return False  # ✅ exception কখনো suppress করো না


# ─────────────────────────── Named Savepoint ─────────────────────────────────

class _SavepointContext:
    """
    Named savepoint context manager — partial rollback-এর জন্য।

    ব্যবহার:
        with Database.transaction():
            journal = Journal.create(header)

            for i, entry in enumerate(entries):
                with Database.savepoint(f"entry_{i}"):
                    JournalLine.create(entry)
                    Account.update_balance(entry)
                # শুধু এই entry fail করলে rollback, journal ও বাকি entries টিকে থাকে

    Database.savepoint("name") দিয়ে call করুন।
    """

    def __init__(self, name: str):
        # নিরাপদ identifier নিশ্চিত করা
        safe_name  = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
        self._name = f"sp_named_{safe_name}"

    def __enter__(self):
        if not Database.in_transaction():
            raise TransactionError(
                "Database.savepoint() শুধুমাত্র Database.transaction() block-এর ভেতরে ব্যবহার করুন"
            )
        conn = Database.connection()
        conn.cursor().execute(f"SAVEPOINT {self._name}")
        logger.debug("Named SAVEPOINT '%s' তৈরি হয়েছে", self._name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        conn   = Database.connection()
        cursor = conn.cursor()
        if exc_type is not None:
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {self._name}")
                cursor.execute(f"RELEASE SAVEPOINT {self._name}")
            except Exception as e:
                logger.error("Named SAVEPOINT rollback ব্যর্থ ('%s'): %s", self._name, e)
            logger.debug("Named SAVEPOINT '%s' rollback হয়েছে", self._name)
        else:
            try:
                cursor.execute(f"RELEASE SAVEPOINT {self._name}")
            except Exception:
                pass
            logger.debug("Named SAVEPOINT '%s' release হয়েছে", self._name)
        return False  # exception সবসময় propagate


# savepoint() কে Database-এর classmethod হিসেবে accessible করা
Database.savepoint = _SavepointContext


# ─────────────────────────── @atomic Decorator ───────────────────────────────

def atomic(func):
    """
    Function-কে একটি atomic transaction-এ wrap করে।
    error হলে auto rollback, সফল হলে auto commit।

    ব্যবহার:
        @atomic
        def post_journal(entries: list):
            total_d = sum(e["debit"]  for e in entries)
            total_c = sum(e["credit"] for e in entries)
            if total_d != total_c:
                raise TransactionError("Journal unbalanced!")
            journal = Journal.create({...})
            for e in entries:
                JournalLine.create({**e, "journal_id": journal.id})

        @atomic
        def transfer_stock(from_id, to_id, qty):
            StockOut.create({"warehouse_id": from_id, "qty": qty})
            StockIn.create({"warehouse_id": to_id,   "qty": qty})

    Nested @atomic functions-ও সঠিকভাবে কাজ করে (SAVEPOINT ব্যবহার করে)।
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with Database.transaction():
            return func(*args, **kwargs)
    return wrapper
