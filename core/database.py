"""
core/database.py
=================
PHP-এর PDO-র মতো একটা শক্তিশালী Database wrapper।
MySQL (pymysql) অথবা SQLite দুটোই সাপোর্ট করে।

PDO-স্টাইল বৈশিষ্ট্য (v2 — MySQL সম্পূর্ণ সাপোর্ট):
  - Prepared Statements (bound parameters) — SQL Injection সম্ভব না
  - কানেকশন পুলিং (MySQL) — প্রতিটা request-এ নতুন connect/disconnect এড়ানো
  - Transaction context manager (with Database.transaction())
  - utf8mb4 charset — বাংলা ও ইমোজি সম্পূর্ণ সাপোর্ট
  - Auto-reconnect — connection drop হলে নিজেই reconnect করে
  - DB_POOL_SIZE .env দিয়ে কনফিগারযোগ্য
  - Strict mode এবং time_zone সেট করার সুবিধা
"""

import sqlite3
import threading
import logging
import time
from queue import Queue, Empty

logger = logging.getLogger("PyFlow.db")


class QueryError(Exception):
    pass


class Profiler:
    """
    Thread-safe Profiler:
    রিকোয়েস্টের এক্সিকিউশন টাইম, ডেটাবেস কুয়েরি এবং লগ ট্র্যাক করে।
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
            "sql": sql,
            "params": params,
            "duration": duration_ms
        })

    @classmethod
    def log_message(cls, level: str, message: str):
        if not hasattr(cls._local, "logs"):
            cls._local.logs = []
        cls._local.logs.append({
            "time": time.strftime("%H:%M:%S"),
            "level": level,
            "message": message
        })

    @classmethod
    def get_data(cls) -> dict:
        if not hasattr(cls._local, "start_time"):
            return {
                "duration": 0,
                "queries": [],
                "logs": []
            }
        duration = (time.monotonic() - cls._local.start_time) * 1000
        return {
            "duration": duration,
            "queries": getattr(cls._local, "queries", []),
            "logs": getattr(cls._local, "logs", [])
        }


class ConnectionPool:
    """
    Thread-safe MySQL কানেকশন পুল।
    PHP-এর PDO persistent connection-এর মতো কাজ করে।
    প্রতিটা request শেষে connection pool-এ ফেরত যায়, বন্ধ হয় না।
    """
    def __init__(self, factory, pool_size: int = 5):
        self._factory = factory
        self._pool: Queue = Queue(maxsize=pool_size)
        self._pool_size = pool_size
        self._lock = threading.Lock()
        self._created = 0

        # শুরুতে কিছু connection তৈরি করে রাখা (eager initialization)
        initial = min(2, pool_size)
        for _ in range(initial):
            conn = self._factory()
            self._pool.put(conn)
            self._created += 1

    def acquire(self, timeout: float = 5.0):
        """Pool থেকে একটা connection নেওয়া। খালি না থাকলে নতুন বানায়।"""
        try:
            conn = self._pool.get_nowait()
            # পুরনো connection জীবিত আছে কিনা ping দিয়ে চেক করা (auto-reconnect)
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

        # pool পূর্ণ হলে একটু অপেক্ষা করে আবার চেষ্টা
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
            # pool পূর্ণ হলে connection বন্ধ করে দেওয়া
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


# -----------------------------------------------------------------------
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

    _config: dict = None
    _local = threading.local()
    _pool: ConnectionPool = None
    driver: str = "sqlite"

    @classmethod
    def init(cls, config: dict):
        cls._config = config
        cls.driver = config.get("DB_DRIVER", "sqlite").lower()

        if cls.driver == "mysql":
            pool_size = int(config.get("DB_POOL_SIZE", 5))
            cls._pool = ConnectionPool(cls._create_mysql_connection, pool_size)
            logger.info(
                "MySQL connection pool তৈরি হয়েছে (size=%d, host=%s, db=%s)",
                pool_size,
                config.get("DB_HOST"),
                config.get("DB_NAME"),
            )

    @classmethod
    def _create_mysql_connection(cls):
        """নতুন MySQL connection তৈরি করা — PHP PDO-র new PDO(...) এর মতো"""
        try:
            import pymysql
            import pymysql.cursors
        except ImportError as exc:
            raise QueryError(
                "MySQL ব্যবহার করতে 'pip install pymysql' করুন, "
                "অথবা .env-এ DB_DRIVER=sqlite দিয়ে রাখুন"
            ) from exc

        config = Database._config
        conn = pymysql.connect(
            host=config.get("DB_HOST", "127.0.0.1"),
            port=int(config.get("DB_PORT", 3306)),
            user=config.get("DB_USER", "root"),
            password=config.get("DB_PASSWORD", ""),
            database=config.get("DB_NAME", ""),
            charset="utf8mb4",                          # বাংলা + ইমোজি সাপোর্ট
            collation="utf8mb4_unicode_ci",
            cursorclass=pymysql.cursors.DictCursor,     # সব row dict হিসেবে আসবে
            autocommit=False,                           # explicit commit দরকার হবে
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
        )
        # সংযোগ হাবার পরে charset নিশ্চিত করা
        cursor = conn.cursor()
        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("SET time_zone = %s", (config.get("DB_TIMEZONE", "+06:00"),))
        conn.commit()
        return conn

    @classmethod
    def connection(cls):
        """
        বর্তমান থ্রেডের connection রিটার্ন করে।
        MySQL: pool থেকে নেওয়া; SQLite: thread-local।
        """
        if Database.driver == "mysql":
            # প্রতি থ্রেডে আলাদা pool connection রাখা হয়
            if not hasattr(Database._local, "conn") or Database._local.conn is None:
                Database._local.conn = Database._pool.acquire()
            return Database._local.conn
        else:
            # SQLite: thread-local new connection
            if not hasattr(Database._local, "conn") or Database._local.conn is None:
                Database._local.conn = Database._create_sqlite_connection()
            return Database._local.conn

    @classmethod
    def _create_sqlite_connection(cls):
        if cls._config is None:
            raise QueryError("Database.init(config) কল না করে connection নেওয়া যাবে না")
        db_path = cls._config.get("DB_NAME", "storage/database.sqlite")
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")       # পারফরম্যান্স বাড়ায়
        return conn

    @classmethod
    def placeholder(cls) -> str:
        """MySQL আর SQLite-এর placeholder আলাদা (%s vs ?)"""
        return "%s" if cls.driver == "mysql" else "?"

    @classmethod
    def execute(cls, sql: str, params: tuple = ()):
        """
        যেকোনো SQL চালায়। params সবসময় tuple/list হিসেবে দিতে হবে।
        কখনো sql-এর ভেতর f-string দিয়ে ভ্যালু বসাবেন না — এটাই SQL Injection
        প্রতিরোধের মূল নিয়ম (PHP PDO-র bindParam-এর equivalent)।
        """
        conn = cls.connection()
        cursor = conn.cursor()
        start = time.monotonic()
        try:
            cursor.execute(sql, params)
            elapsed = (time.monotonic() - start) * 1000
            
            # প্রফাইলারে কুয়েরি রেকর্ড করা
            Profiler.log_query(sql, params, elapsed)
            
            if elapsed > 200:
                logger.warning("Slow query (%.0fms): %s", elapsed, sql[:120])
            return cursor
        except Exception as exc:
            if not cls.in_transaction():
                conn.rollback()
            logger.error("Query ব্যর্থ: %s | params=%s | error=%s", sql, params, exc)
            raise QueryError(f"Query ব্যর্থ হয়েছে: {exc}\nSQL: {sql}") from exc

    @classmethod
    def execute_many(cls, sql: str, params_list: list) -> int:
        """
        একাধিক row একসাথে INSERT করার জন্য (batch insert)।
        PHP PDO-র executemany()-র মতো।
        """
        conn = cls.connection()
        cursor = conn.cursor()
        try:
            cursor.executemany(sql, params_list)
            if not cls.in_transaction():
                cls.commit()
            return cursor.rowcount
        except Exception as exc:
            if not cls.in_transaction():
                conn.rollback()
            raise QueryError(f"Batch query ব্যর্থ: {exc}") from exc

    @classmethod
    def commit(cls):
        cls.connection().commit()

    @classmethod
    def rollback(cls):
        cls.connection().rollback()

    @classmethod
    def in_transaction(cls) -> bool:
        return hasattr(cls._local, "transaction_level") and cls._local.transaction_level > 0

    @classmethod
    def last_insert_id(cls, cursor) -> int:
        return cursor.lastrowid

    @classmethod
    def close(cls):
        """
        Request শেষে connection পরিচালনা:
        - MySQL: pool-এ ফেরত দেওয়া (পুনরায় ব্যবহারযোগ্য)
        - SQLite: সত্যিই বন্ধ করা
        """
        if hasattr(cls._local, "conn") and cls._local.conn:
            if cls.driver == "mysql" and cls._pool:
                cls._pool.release(cls._local.conn)
            else:
                cls._local.conn.close()
            cls._local.conn = None

    @classmethod
    def get_status(cls) -> dict:
        """Connection pool-এর বর্তমান অবস্থা (debug/monitoring-এর জন্য)"""
        if cls.driver == "mysql" and cls._pool:
            return {
                "driver": "mysql",
                "pool_size": cls._pool._pool_size,
                "available": cls._pool._pool.qsize(),
                "created": cls._pool._created,
            }
        return {"driver": "sqlite"}

    # ----------------------------------------------------------------
    # Transaction context manager — PHP PDO beginTransaction()-এর মতো
    # ----------------------------------------------------------------
    class transaction:
        """
        with Database.transaction():
            Model.create({...})
            OtherModel.create({...})
        Exception হলে অটো rollback, না হলে অটো commit।
        নেস্টেড ট্রানজেকশনের ক্ষেত্রে SQL SAVEPOINT ব্যবহার করা হয়।
        """
        def __enter__(self):
            conn = Database.connection()
            if not hasattr(Database._local, "transaction_level"):
                Database._local.transaction_level = 0
            
            Database._local.transaction_level += 1
            level = Database._local.transaction_level
            
            if level > 1:
                cursor = conn.cursor()
                cursor.execute(f"SAVEPOINT sp_{level}")
            
            return conn

        def __exit__(self, exc_type, exc_val, exc_tb):
            if not hasattr(Database._local, "transaction_level"):
                Database._local.transaction_level = 1
                
            level = Database._local.transaction_level
            conn = Database.connection()
            
            if exc_type is not None:
                if level > 1:
                    cursor = conn.cursor()
                    cursor.execute(f"ROLLBACK TO SAVEPOINT sp_{level}")
                    cursor.execute(f"RELEASE SAVEPOINT sp_{level}")
                else:
                    Database.rollback()
                
                Database._local.transaction_level = max(0, level - 1)
                return False  # Outer transaction context is notified

            else:
                if level > 1:
                    cursor = conn.cursor()
                    try:
                        cursor.execute(f"RELEASE SAVEPOINT sp_{level}")
                    except Exception:
                        pass
                else:
                    Database.commit()
                
                Database._local.transaction_level = max(0, level - 1)
                return True


import os  # noqa: E402 — Database._create_sqlite_connection-এ দরকার
