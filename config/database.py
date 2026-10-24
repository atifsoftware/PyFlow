"""
config/database.py
==================
Multi-Database Engine Configuration for PyFlow.
Supports simultaneous active connections across SQLite, MySQL, and PostgreSQL.
"""

import os


def get_database_config() -> dict:
    """
    Returns the multi-database configuration schema.
    Compatible with Laravel config/database.php structure.
    """
    default_connection = os.getenv("DB_CONNECTION", os.getenv("DB_DRIVER", "sqlite")).lower()

    return {
        "default": default_connection,

        "connections": {
            # ──────────────── SQLite Connection ────────────────
            "sqlite": {
                "driver": "sqlite",
                "database": os.getenv("DB_SQLITE_PATH", os.getenv("DB_NAME", "storage/database.sqlite")),
                "timeout": 10.0,
            },

            # ──────────────── MySQL Connection ─────────────────
            "mysql": {
                "driver": "mysql",
                "host": os.getenv("DB_HOST", "127.0.0.1"),
                "port": int(os.getenv("DB_PORT", 3306)),
                "database": os.getenv("DB_NAME", "pyflow_db"),
                "user": os.getenv("DB_USER", "root"),
                "password": os.getenv("DB_PASSWORD", ""),
                "pool_size": int(os.getenv("DB_POOL_SIZE", 5)),
                "timezone": os.getenv("DB_TIMEZONE", "+06:00"),
            },

            # ──────────────── PostgreSQL Connection ────────────
            "pgsql": {
                "driver": "postgresql",
                "host": os.getenv("PG_HOST", os.getenv("DB_HOST", "127.0.0.1")),
                "port": int(os.getenv("PG_PORT", 5432)),
                "database": os.getenv("PG_NAME", os.getenv("DB_NAME", "pyflow_db")),
                "user": os.getenv("PG_USER", "postgres"),
                "password": os.getenv("PG_PASSWORD", os.getenv("DB_PASSWORD", "")),
                "schema": os.getenv("DB_SCHEMA", "public"),
                "pool_size": int(os.getenv("DB_POOL_SIZE", 5)),
            },

            "postgresql": {
                "driver": "postgresql",
                "host": os.getenv("PG_HOST", os.getenv("DB_HOST", "127.0.0.1")),
                "port": int(os.getenv("PG_PORT", 5432)),
                "database": os.getenv("PG_NAME", os.getenv("DB_NAME", "pyflow_db")),
                "user": os.getenv("PG_USER", "postgres"),
                "password": os.getenv("PG_PASSWORD", os.getenv("DB_PASSWORD", "")),
                "schema": os.getenv("DB_SCHEMA", "public"),
                "pool_size": int(os.getenv("DB_POOL_SIZE", 5)),
            },
        },
    }
