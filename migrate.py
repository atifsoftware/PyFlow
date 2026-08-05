"""
migrate.py
==========
Migration স্ক্রিপ্ট - সব টেবিল তৈরি করে (.env অনুযায়ী SQLite, MySQL অথবা PostgreSQL)।

চালানোর নিয়ম:
    python migrate.py              # সব টেবিল তৈরি / আপডেট করা
    python migrate.py --fresh      # সব টেবিল ড্রপ করে নতুনভাবে তৈরি করা (সাবধান!)
    python migrate.py --status     # কোন টেবিল আছে সেটা দেখানো
    python migrate.py rollback     # শেষ batch rollback করা
    python migrate.py rollback --step=3  # ৩টি migration পেছানো
"""

import sys
import os


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config.config import get_config
from core.database import Database


# ─────────────────────────────────────────────────────────────── SQLite Schema
SQLITE_MIGRATIONS = [
    ("users", """
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL UNIQUE,
            password    TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'user',
            created_at  TEXT,
            updated_at  TEXT
        )
    """),
    ("settings", """
        CREATE TABLE IF NOT EXISTS settings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT NOT NULL UNIQUE,
            value       TEXT,
            created_at  TEXT,
            updated_at  TEXT
        )
    """),
    ("activity_logs", """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NULL,
            action      TEXT NOT NULL,
            description TEXT,
            ip_address  TEXT,
            user_agent  TEXT,
            created_at  TEXT
        )
    """),
    ("api_keys", """
        CREATE TABLE IF NOT EXISTS api_keys (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            name         TEXT NOT NULL,
            key          TEXT NOT NULL UNIQUE,
            last_used_at TEXT,
            created_at   TEXT,
            updated_at   TEXT
        )
    """),
    ("jobs", """
        CREATE TABLE IF NOT EXISTS jobs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            queue        TEXT NOT NULL,
            payload      TEXT NOT NULL,
            attempts     INTEGER NOT NULL DEFAULT 0,
            reserved_at  INTEGER NULL,
            available_at INTEGER NOT NULL,
            created_at   INTEGER NOT NULL
        )
    """),
]

# ─────────────────────────────────────────────────────────────── MySQL Schema
# utf8mb4 charset: বাংলা, আরবি, ইমোজি সব সাপোর্ট করে
# InnoDB engine: Foreign Key, Transaction সাপোর্ট দেয়
MYSQL_MIGRATIONS = [
    ("users", """
        CREATE TABLE IF NOT EXISTS users (
            id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(100)  NOT NULL,
            email       VARCHAR(150)  NOT NULL UNIQUE,
            password    VARCHAR(255)  NOT NULL,
            role        VARCHAR(20)   NOT NULL DEFAULT 'user',
            created_at  DATETIME      NULL,
            updated_at  DATETIME      NULL,
            INDEX idx_email (email),
            INDEX idx_role  (role)
        ) ENGINE=InnoDB
          DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci
          COMMENT='ব্যবহারকারীর তথ্য'
    """),
    ("settings", """
        CREATE TABLE IF NOT EXISTS settings (
            id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            `key`       VARCHAR(100) NOT NULL UNIQUE,
            `value`     TEXT         NULL,
            created_at  DATETIME     NULL,
            updated_at  DATETIME     NULL,
            INDEX idx_key (`key`)
        ) ENGINE=InnoDB
          DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci
    """),
    ("activity_logs", """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id     INT UNSIGNED NULL,
            action      VARCHAR(100) NOT NULL,
            description TEXT         NULL,
            ip_address  VARCHAR(45)  NULL,
            user_agent  VARCHAR(255) NULL,
            created_at  DATETIME     NULL,
            INDEX idx_user_id (user_id),
            INDEX idx_action (action)
        ) ENGINE=InnoDB
          DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci
    """),
    ("api_keys", """
        CREATE TABLE IF NOT EXISTS api_keys (
            id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id      INT UNSIGNED NOT NULL,
            name         VARCHAR(100) NOT NULL,
            `key`        VARCHAR(64)  NOT NULL UNIQUE,
            last_used_at DATETIME     NULL,
            created_at   DATETIME     NULL,
            updated_at   DATETIME     NULL,
            INDEX idx_user_id (user_id),
            INDEX idx_key (`key`)
        ) ENGINE=InnoDB
          DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci
    """),
    ("jobs", """
        CREATE TABLE IF NOT EXISTS jobs (
            id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            queue        VARCHAR(100) NOT NULL,
            payload      LONGTEXT     NOT NULL,
            attempts     TINYINT UNSIGNED NOT NULL DEFAULT 0,
            reserved_at  INT UNSIGNED NULL,
            available_at INT UNSIGNED NOT NULL,
            created_at   INT UNSIGNED NOT NULL,
            INDEX idx_queue_reserved_available (queue, reserved_at, available_at)
        ) ENGINE=InnoDB
          DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci
    """),
    ("roles", """
        CREATE TABLE IF NOT EXISTS `roles` (
            id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            name         VARCHAR(100) NOT NULL UNIQUE,
            display_name VARCHAR(150),
            created_at   DATETIME,
            updated_at   DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """),
    ("permissions", """
        CREATE TABLE IF NOT EXISTS `permissions` (
            id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            name         VARCHAR(150) NOT NULL UNIQUE COMMENT 'e.g. users.delete',
            display_name VARCHAR(200),
            `group`      VARCHAR(100),
            created_at   DATETIME,
            updated_at   DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """),
    ("role_permission", """
        CREATE TABLE IF NOT EXISTS `role_permission` (
            role_id       INT UNSIGNED NOT NULL,
            permission_id INT UNSIGNED NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id)       REFERENCES roles(id)       ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """),
]

# ───────────────────────────────────────────────────── PostgreSQL Schema
# SERIAL = auto-increment, TEXT = unlimited string, TIMESTAMPTZ = timezone-aware
POSTGRESQL_MIGRATIONS = [
    ("users", """
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL          PRIMARY KEY,
            name        VARCHAR(100)    NOT NULL,
            email       VARCHAR(150)    NOT NULL UNIQUE,
            password    VARCHAR(255)    NOT NULL,
            role        VARCHAR(20)     NOT NULL DEFAULT 'user',
            created_at  TIMESTAMPTZ     NULL,
            updated_at  TIMESTAMPTZ     NULL
        )
    """),
    ("settings", """
        CREATE TABLE IF NOT EXISTS settings (
            id          SERIAL          PRIMARY KEY,
            key         VARCHAR(100)    NOT NULL UNIQUE,
            value       TEXT            NULL,
            created_at  TIMESTAMPTZ     NULL,
            updated_at  TIMESTAMPTZ     NULL
        )
    """),
    ("activity_logs", """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id          SERIAL          PRIMARY KEY,
            user_id     INTEGER         NULL,
            action      VARCHAR(100)    NOT NULL,
            description TEXT            NULL,
            ip_address  VARCHAR(45)     NULL,
            user_agent  VARCHAR(255)    NULL,
            created_at  TIMESTAMPTZ     NULL
        )
    """),
    ("api_keys", """
        CREATE TABLE IF NOT EXISTS api_keys (
            id           SERIAL          PRIMARY KEY,
            user_id      INTEGER         NOT NULL,
            name         VARCHAR(100)    NOT NULL,
            key          VARCHAR(64)     NOT NULL UNIQUE,
            last_used_at TIMESTAMPTZ     NULL,
            created_at   TIMESTAMPTZ     NULL,
            updated_at   TIMESTAMPTZ     NULL
        )
    """),
    ("jobs", """
        CREATE TABLE IF NOT EXISTS jobs (
            id           SERIAL          PRIMARY KEY,
            queue        VARCHAR(100)    NOT NULL,
            payload      TEXT            NOT NULL,
            attempts     SMALLINT        NOT NULL DEFAULT 0,
            reserved_at  BIGINT          NULL,
            available_at BIGINT          NOT NULL,
            created_at   BIGINT          NOT NULL
        )
    """),
    ("roles", """
        CREATE TABLE IF NOT EXISTS roles (
            id           SERIAL          PRIMARY KEY,
            name         VARCHAR(100)    NOT NULL UNIQUE,
            display_name VARCHAR(150),
            created_at   TIMESTAMPTZ,
            updated_at   TIMESTAMPTZ
        )
    """),
    ("permissions", """
        CREATE TABLE IF NOT EXISTS permissions (
            id           SERIAL          PRIMARY KEY,
            name         VARCHAR(150)    NOT NULL UNIQUE,
            display_name VARCHAR(200),
            "group"      VARCHAR(100),
            created_at   TIMESTAMPTZ,
            updated_at   TIMESTAMPTZ
        )
    """),
    ("role_permission", """
        CREATE TABLE IF NOT EXISTS role_permission (
            role_id       INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        )
    """),
]

# SQLite-তেও RBAC tables যোগ করা
SQLITE_MIGRATIONS = list(SQLITE_MIGRATIONS) + [
    ("roles", """
        CREATE TABLE IF NOT EXISTS roles (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            display_name TEXT,
            created_at   TEXT,
            updated_at   TEXT
        )
    """),
    ("permissions", """
        CREATE TABLE IF NOT EXISTS permissions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            display_name TEXT,
            'group'      TEXT,
            created_at   TEXT,
            updated_at   TEXT
        )
    """),
    ("role_permission", """
        CREATE TABLE IF NOT EXISTS role_permission (
            role_id       INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY (role_id, permission_id)
        )
    """),
]


def _get_migrations(driver: str) -> list:
    """ড্রাইভার অনুযায়ী সঠিক migration list দেয়"""
    if driver == "mysql":
        return MYSQL_MIGRATIONS
    elif driver == "postgresql":
        return POSTGRESQL_MIGRATIONS
    return SQLITE_MIGRATIONS


def _rollback(config: dict, driver: str, step: int = 1):
    """শেষ batch(গুলো) rollback করে"""
    conn   = Database.connection()
    cursor = conn.cursor()

    # migrations_log টেবিল না থাকলে তৈরি করা
    if driver == "mysql":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `migrations_log` (
                id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                batch      INT UNSIGNED NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                ran_at     DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    elif driver == "postgresql":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations_log (
                id         SERIAL PRIMARY KEY,
                batch      INTEGER NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                ran_at     TIMESTAMPTZ NOT NULL
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch INTEGER NOT NULL,
                table_name TEXT NOT NULL,
                ran_at TEXT NOT NULL
            )
        """)
    conn.commit()

    # সর্বশেষ batch নম্বর বের করা
    cursor.execute("SELECT MAX(batch) as mb FROM migrations_log")
    row = cursor.fetchone()
    if not row:
        print("কোনো migration log নেই।")
        return
    row = dict(row) if not isinstance(row, dict) else row
    max_batch = row.get("mb") or 0
    if max_batch == 0:
        print("Rollback করার মতো কোনো migration পাওয়া যায়নি।")
        return

    rollback_from = max_batch
    rollback_to = max(1, max_batch - step + 1)

    # Rollback করার table list বের করা
    ph = Database.placeholder()
    cursor.execute(
        f"SELECT table_name FROM migrations_log WHERE batch BETWEEN {ph} AND {ph} ORDER BY id DESC",
        (rollback_to, rollback_from)
    )
    tables_to_rollback = [
        (dict(r) if not isinstance(r, dict) else r).get("table_name") for r in cursor.fetchall()
    ]

    if driver == "mysql":
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    for table in tables_to_rollback:
        if driver == "mysql":
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
        elif driver == "postgresql":
            cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        else:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  🗑️  '{table}' টেবিল rollback হয়েছে")

    if driver == "mysql":
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    # log মুছে দেওয়া
    cursor.execute(
        f"DELETE FROM migrations_log WHERE batch BETWEEN {ph} AND {ph}",
        (rollback_to, rollback_from)
    )
    conn.commit()
    print(f"\n✅ {len(tables_to_rollback)}টি migration rollback সম্পন্ন (batch {rollback_to}→{rollback_from})")


def _log_migration(conn, driver: str, table_name: str, batch: int):
    """Migration run হওয়ার পরে log করা"""
    import time
    cursor = conn.cursor()
    if driver == "mysql":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `migrations_log` (
                id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                batch INT UNSIGNED NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                ran_at DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    elif driver == "postgresql":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations_log (
                id         SERIAL PRIMARY KEY,
                batch      INTEGER NOT NULL,
                table_name VARCHAR(100) NOT NULL,
                ran_at     TIMESTAMPTZ NOT NULL
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch INTEGER NOT NULL,
                table_name TEXT NOT NULL,
                ran_at TEXT NOT NULL
            )
        """)
    ran_at = time.strftime("%Y-%m-%d %H:%M:%S")
    ph = Database.placeholder()
    cursor.execute(
        f"INSERT INTO migrations_log (batch, table_name, ran_at) VALUES ({ph}, {ph}, {ph})",
        (batch, table_name, ran_at)
    )


def _ensure_mysql_database(config: dict):
    """
    MySQL-এ database না থাকলে তৈরি করে।
    """
    try:
        import pymysql
        db_name = config.get("DB_NAME", "pyflow_db")
        conn = pymysql.connect(
            host=config.get("DB_HOST", "127.0.0.1"),
            port=int(config.get("DB_PORT", 3306)),
            user=config.get("DB_USER", "root"),
            password=config.get("DB_PASSWORD", ""),
            charset="utf8mb4",
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        conn.close()
        print(f"  ✅ Database '{db_name}' নিশ্চিত হয়েছে (MySQL)")
    except Exception as exc:
        print(f"  ⚠️  Database তৈরিতে সমস্যা: {exc}")
        raise


def _ensure_postgresql_database(config: dict):
    """
    PostgreSQL-এ database না থাকলে তৈরি করে।
    সতর্ক: PostgreSQL-এ CREATE DATABASE transaction-এর ভেতরে পড়ে না।
    """
    try:
        import psycopg2
        db_name = config.get("DB_NAME", "pyflow_db")
        # postgres ডিফোল্ট database-এ connect করে নতুন database তৈরি করা
        conn = psycopg2.connect(
            host     = config.get("DB_HOST", "127.0.0.1"),
            port     = int(config.get("DB_PORT", 5432)),
            user     = config.get("DB_USER", "postgres"),
            password = config.get("DB_PASSWORD", ""),
            dbname   = "postgres",  # সবসময় আছে এই database
        )
        conn.autocommit = True  # CREATE DATABASE transaction-এ হয় না
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        if not cursor.fetchone():
            cursor.execute(f'CREATE DATABASE "{db_name}" ENCODING = \'UTF8\'')
            print(f"  ✅ PostgreSQL database '{db_name}' তৈরি হয়েছে")
        else:
            print(f"  ✅ PostgreSQL database '{db_name}' ইতিমধ্যে আছে")
        conn.close()
    except Exception as exc:
        print(f"  ⚠️  PostgreSQL database নিশ্চিত করতে সমস্যা: {exc}")
        raise


def _drop_all_tables(config: dict, driver: str):
    """--fresh ফ্ল্যাগ দিলে সব টেবিল ড্রপ করে"""
    migrations = _get_migrations(driver)
    conn       = Database.connection()
    cursor     = conn.cursor()

    if driver == "mysql":
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    elif driver == "postgresql":
        pass  # PostgreSQL-এ CASCADE ব্যবহার করবো

    for table_name, _ in reversed(migrations):
        if driver == "mysql":
            cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        elif driver == "postgresql":
            cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
        else:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        print(f"  🗑️  '{table_name}' টেবিল ড্রপ করা হয়েছে")

    if driver == "mysql":
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    conn.commit()


def _show_status(config: dict, driver: str):
    """কোন কোন টেবিল আছে দেখানো"""
    conn = Database.connection()
    cursor = conn.cursor()

    if driver == "mysql":
        db_name = config.get("DB_NAME")
        cursor.execute(
            "SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH "
            "FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = %s",
            (db_name,)
        )
        rows = cursor.fetchall()
        print(f"\n📋 MySQL Database: {db_name}")
        print(f"{'টেবিল নাম':<25} {'আনুমানিক রো':<15} {'ডেটা সাইজ'}")
        print("-" * 55)
        for row in rows:
            row = dict(row) if not isinstance(row, dict) else row
            name = row.get("TABLE_NAME", "")
            rows_count = row.get("TABLE_ROWS", 0)
            size = row.get("DATA_LENGTH", 0)
            print(f"{name:<25} {rows_count:<15} {size} bytes")
    else:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        rows = cursor.fetchall()
        print(f"\n📋 SQLite: {config.get('DB_NAME')}")
        for row in rows:
            print(f"  - {dict(row).get('name', row[0])}")


def main():
    config = get_config()
    driver = config.get("DB_DRIVER", "sqlite")
    fresh = "--fresh" in sys.argv
    status = "--status" in sys.argv
    rollback = "rollback" in sys.argv

    # --step=N পার্স করা
    step = 1
    for arg in sys.argv:
        if arg.startswith("--step="):
            try:
                step = int(arg.split("=")[1])
            except (ValueError, IndexError):
                pass

    os.makedirs("storage", exist_ok=True)
    os.makedirs("storage/logs", exist_ok=True)

    # Driver অনুযায়ী database আগে তৈরি করা
    if driver == "mysql":
        print("🔌 MySQL-এ সংযুক্ত হচ্ছে...")
        _ensure_mysql_database(config)
    elif driver == "postgresql":
        print("🔌 PostgreSQL-এ সংযুক্ত হচ্ছে...")
        _ensure_postgresql_database(config)

    Database.init(config)

    if status:
        _show_status(config, driver)
        Database.close()
        return

    if rollback:
        print(f"\n⏪ {step}টি Migration Rollback হচ্ছে...")
        _rollback(config, driver, step)
        Database.close()
        return

    if fresh:
        print("\n⚠️  --fresh: সব টেবিল মুছে নতুনভাবে তৈরি হবে!")
        confirm = input("   নিশ্চিত? (yes লিখুন): ").strip()
        if confirm.lower() != "yes":
            print("   বাতিল করা হয়েছে।")
            return
        _drop_all_tables(config, driver)

    migrations = _get_migrations(driver)

    print(f"\n🚀 Migration শুরু ({driver.upper()})...")
    conn = Database.connection()
    cursor = conn.cursor()

    # বর্তমান batch নম্বর বের করা
    try:
        cursor.execute("SELECT MAX(batch) as mb FROM migrations_log")
        row = cursor.fetchone()
        row = dict(row) if row and not isinstance(row, dict) else (row or {})
        current_batch = int(row.get("mb") or 0) + 1
    except Exception:
        current_batch = 1

    for table_name, sql in migrations:
        cursor.execute(sql.strip())
        print(f"  ✅ '{table_name}' টেবিল তৈরি/যাচাই হয়েছে")
        try:
            _log_migration(conn, driver, table_name, current_batch)
        except Exception:
            pass  # log failure migration-কে থামাবে না

    conn.commit()
    Database.close()

    print(f"\n🎉 Migration সম্পন্ন! Database: {config['DB_NAME']}")


if __name__ == "__main__":
    main()

