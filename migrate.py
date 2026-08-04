"""
migrate.py
==========
Migration স্ক্রিপ্ট - সব টেবিল তৈরি করে (SQLite অথবা MySQL, .env অনুযায়ী)।

চালানোর নিয়ম:
    python migrate.py             # সব টেবিল তৈরি / আপডেট করা
    python migrate.py --fresh     # সব টেবিল ড্রপ করে নতুনভাবে তৈরি করা (সাবধান!)
    python migrate.py --status    # কোন টেবিল আছে সেটা দেখানো
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
]


def _ensure_mysql_database(config: dict):
    """
    MySQL-এ database না থাকলে তৈরি করে।
    PHP-এ CREATE DATABASE ম্যানুয়ালি করতে হয়, এখানে অটো।
    """
    try:
        import pymysql
        db_name = config.get("DB_NAME", "pymvc_db")
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


def _drop_all_tables(config: dict, driver: str):
    """--fresh ফ্ল্যাগ দিলে সব টেবিল ড্রপ করে"""
    migrations = MYSQL_MIGRATIONS if driver == "mysql" else SQLITE_MIGRATIONS
    conn = Database.connection()
    cursor = conn.cursor()

    if driver == "mysql":
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    for table_name, _ in reversed(migrations):
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
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

    os.makedirs("storage", exist_ok=True)
    os.makedirs("storage/logs", exist_ok=True)

    # MySQL হলে database আগে তৈরি করা
    if driver == "mysql":
        print("🔌 MySQL-এ সংযুক্ত হচ্ছে...")
        _ensure_mysql_database(config)

    Database.init(config)

    if status:
        _show_status(config, driver)
        Database.close()
        return

    if fresh:
        print("\n⚠️  --fresh: সব টেবিল মুছে নতুনভাবে তৈরি হবে!")
        confirm = input("   নিশ্চিত? (yes লিখুন): ").strip()
        if confirm.lower() != "yes":
            print("   বাতিল করা হয়েছে।")
            return
        _drop_all_tables(config, driver)

    migrations = MYSQL_MIGRATIONS if driver == "mysql" else SQLITE_MIGRATIONS

    print(f"\n🚀 Migration শুরু ({driver.upper()})...")
    conn = Database.connection()
    cursor = conn.cursor()

    for table_name, sql in migrations:
        cursor.execute(sql.strip())
        print(f"  ✅ '{table_name}' টেবিল তৈরি/যাচাই হয়েছে")

    conn.commit()
    Database.close()

    print(f"\n🎉 Migration সম্পন্ন! Database: {config['DB_NAME']}")


if __name__ == "__main__":
    main()
