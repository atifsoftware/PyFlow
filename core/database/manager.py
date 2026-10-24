"""
core/database/manager.py
========================
Multi-Database Connection Manager for PyFlow.
Manages connections, registries, and connection pooling across SQLite, MySQL, and PostgreSQL.
"""

import os
import logging
from typing import Dict, Any, Optional

from core.database.contracts.connection import ConnectionInterface
from core.database.drivers.base_connection import BaseConnection, QueryError, TransactionError, Profiler
from core.database.drivers.sqlite_connection import SqliteConnection
from core.database.drivers.mysql_connection import MySqlConnection
from core.database.drivers.postgres_connection import PostgresConnection

logger = logging.getLogger("PyFlow.db")


class DatabaseManager:
    """
    Central Multi-Database Manager.
    Allows accessing multiple connections simultaneously via connection('name').
    """

    def __init__(self, config: Optional[dict] = None):
        self._config: dict = {}
        self._connections: Dict[str, BaseConnection] = {}
        self._default: str = "sqlite"
        if config:
            self.init(config)

    def init(self, config: dict):
        """Initialize configurations and setup connections map."""
        self._config = config
        
        # Check if structured connections dictionary is provided
        if "connections" in config and isinstance(config["connections"], dict):
            self._default = config.get("default", config.get("DB_DRIVER", "sqlite")).lower()
        else:
            # Flattened legacy config adapter
            driver = config.get("DB_DRIVER", "sqlite").lower()
            self._default = driver
            self._config = {
                "default": driver,
                "connections": {
                    driver: config,
                    "sqlite": {
                        "driver": "sqlite",
                        "database": config.get("DB_NAME", "storage/database.sqlite") if driver == "sqlite" else "storage/database.sqlite",
                        "timeout": 10.0,
                    },
                    "mysql": {
                        "driver": "mysql",
                        "host": config.get("DB_HOST", "127.0.0.1"),
                        "port": int(config.get("DB_PORT", 3306)),
                        "user": config.get("DB_USER", "root"),
                        "password": config.get("DB_PASSWORD", ""),
                        "database": config.get("DB_NAME", ""),
                        "pool_size": int(config.get("DB_POOL_SIZE", 5)),
                        "timezone": config.get("DB_TIMEZONE", "+06:00"),
                    },
                    "pgsql": {
                        "driver": "postgresql",
                        "host": config.get("DB_HOST", "127.0.0.1"),
                        "port": int(config.get("DB_PORT", 5432)),
                        "user": config.get("DB_USER", "postgres"),
                        "password": config.get("DB_PASSWORD", ""),
                        "database": config.get("DB_NAME", ""),
                        "schema": config.get("DB_SCHEMA", "public"),
                        "pool_size": int(config.get("DB_POOL_SIZE", 5)),
                    },
                    "postgresql": {
                        "driver": "postgresql",
                        "host": config.get("DB_HOST", "127.0.0.1"),
                        "port": int(config.get("DB_PORT", 5432)),
                        "user": config.get("DB_USER", "postgres"),
                        "password": config.get("DB_PASSWORD", ""),
                        "database": config.get("DB_NAME", ""),
                        "schema": config.get("DB_SCHEMA", "public"),
                        "pool_size": int(config.get("DB_POOL_SIZE", 5)),
                    }
                }
            }

    @property
    def default_driver(self) -> str:
        if not self._config:
            try:
                from config.config import get_config
                self.init(get_config())
            except Exception:
                pass
        return self._default

    def connection(self, name: Optional[str] = None) -> BaseConnection:
        """
        Get a specific database connection driver instance.
        If name is None, returns the active default connection.
        """
        if not self._config:
            try:
                from config.config import get_config
                self.init(get_config())
            except Exception:
                pass

        conn_name = (name or self._default).lower()
        if conn_name in ("postgres", "pgsql"):
            conn_name = "pgsql" if "pgsql" in self._config.get("connections", {}) else "postgresql"

        if conn_name not in self._connections:
            self._connections[conn_name] = self._make_connection(conn_name)

        return self._connections[conn_name]

    def _make_connection(self, name: str) -> BaseConnection:
        """Instantiate driver based on configuration."""
        conns = self._config.get("connections", {})
        conn_cfg = conns.get(name, {})
        driver = conn_cfg.get("driver", name).lower()

        if driver in ("sqlite",):
            conn = SqliteConnection(name=name, config=conn_cfg)
            logger.info("SQLite connection initialized: '%s'", name)
            return conn

        elif driver in ("mysql", "mariadb"):
            conn = MySqlConnection(name=name, config=conn_cfg)
            logger.info("MySQL connection initialized: '%s' (host=%s, db=%s)", name, conn_cfg.get("host"), conn_cfg.get("database"))
            return conn

        elif driver in ("pgsql", "postgres", "postgresql"):
            conn = PostgresConnection(name=name, config=conn_cfg)
            logger.info("PostgreSQL connection initialized: '%s' (host=%s, db=%s)", name, conn_cfg.get("host"), conn_cfg.get("database"))
            return conn

        raise QueryError(f"অজানা ডাটাবেজ ড্রাইভার: '{driver}' (connection: '{name}')")

    def purge(self, name: Optional[str] = None):
        """Close and remove connection from active cache."""
        if name:
            if name in self._connections:
                self._connections[name].close_all()
                del self._connections[name]
        else:
            for conn in self._connections.values():
                conn.close_all()
            self._connections.clear()

    def close(self):
        """Close thread connections across all drivers."""
        for conn in self._connections.values():
            conn.close()

    def close_all(self):
        """Shutdown and close all connection pools."""
        for conn in self._connections.values():
            conn.close_all()

    def table(self, table: str, connection: Optional[str] = None):
        """Shortcut to start a QueryBuilder on a specific connection."""
        from core.query_builder import QueryBuilder
        conn = self.connection(connection)
        return QueryBuilder(table, connection=conn)

    # ------------------------------------------------ Dynamic Delegation
    def __getattr__(self, name: str) -> Any:
        """Delegate any unknown method to the default connection."""
        default_conn = self.connection()
        return getattr(default_conn, name)
