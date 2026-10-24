"""
core/database/__init__.py
=========================
PyFlow Database Facade and Multi-Database Engine.
Provides simultaneous connection management, Query Grammars, and Transaction Controls.
"""

from typing import Optional, Any, Callable, List

from core.database.manager import DatabaseManager
from core.database.drivers.base_connection import QueryError, TransactionError, Profiler
from core.database.drivers.base_connection import BaseConnection
from core.database.grammar.base_grammar import BaseGrammar
from core.database.grammar.mysql_grammar import MySqlGrammar
from core.database.grammar.postgres_grammar import PostgresGrammar
from core.database.grammar.sqlite_grammar import SqliteGrammar


class DatabaseMeta(type):
    """Metaclass allowing dynamic class properties like Database.driver."""

    @property
    def driver(cls) -> str:
        return cls.connection().driver


class Database(metaclass=DatabaseMeta):
    """
    Database Facade for PyFlow Multi-Database Engine.
    Supports simultaneous connections across SQLite, MySQL, and PostgreSQL.
    """

    _manager: DatabaseManager = DatabaseManager()

    @classmethod
    def init(cls, config: dict):
        """Initialize all configured database connections."""
        cls._manager.init(config)

    @classmethod
    def manager(cls) -> DatabaseManager:
        return cls._manager

    @classmethod
    def connection(cls, name: Optional[str] = None) -> BaseConnection:
        """Get a specific database connection instance or default if name is None."""
        return cls._manager.connection(name)

    @classmethod
    def table(cls, table: str, connection: Optional[str] = None):
        """Start a QueryBuilder instance bound to a specific connection."""
        return cls._manager.table(table, connection)

    @classmethod
    def cursor(cls, as_dict: bool = True):
        return cls.connection().cursor(as_dict=as_dict)

    @classmethod
    def execute(cls, sql: str, params: tuple = (), use_dict_cursor: bool = True) -> Any:
        return cls.connection().execute(sql, params, as_dict=use_dict_cursor)

    @classmethod
    def execute_many(cls, sql: str, params_list: List[tuple], batch_size: int = 1000) -> int:
        return cls.connection().execute_many(sql, params_list, batch_size=batch_size)

    @classmethod
    def commit(cls):
        cls.connection().commit()

    @classmethod
    def rollback(cls):
        cls.connection().rollback()

    @classmethod
    def in_transaction(cls) -> bool:
        return cls.connection().in_transaction()

    @classmethod
    def transaction_level(cls) -> int:
        return cls.connection().transaction_level()

    @classmethod
    def transaction(cls, attempts: int = 1):
        """Transaction context manager for default connection."""
        return cls.connection().transaction(attempts=attempts)

    @classmethod
    def savepoint(cls, name: Optional[str] = None):
        """Named savepoint context manager for default connection."""
        return cls.connection().savepoint(name=name)

    @classmethod
    def atomic(cls, fn: Callable):
        """Function decorator for atomic transactions."""
        return cls.connection().atomic(fn)

    @classmethod
    def on_commit(cls, callback: Callable):
        cls.connection().on_commit(callback)

    @classmethod
    def on_rollback(cls, callback: Callable):
        cls.connection().on_rollback(callback)

    @classmethod
    def last_insert_id(cls, cursor: Any = None) -> int:
        return cls.connection().last_insert_id(cursor=cursor)

    @classmethod
    def placeholder(cls) -> str:
        return cls.connection().placeholder

    @classmethod
    def quote_identifier(cls, name: str) -> str:
        return cls.connection().grammar.wrap(name)

    @classmethod
    def close(cls):
        """Release connections for current thread."""
        cls._manager.close()

    @classmethod
    def close_all(cls):
        """Close all connection pools across all drivers."""
        cls._manager.close_all()


def atomic(fn: Optional[Callable] = None, connection: Optional[str] = None):
    """
    Function decorator for atomic transactions.
    Usage:
        @atomic
        def post_order(): ...

        @atomic(connection="mysql")
        def post_mysql_order(): ...
    """
    if fn is not None and callable(fn):
        return Database.connection(connection).atomic(fn)

    def decorator(func):
        return Database.connection(connection).atomic(func)
    return decorator


class _SavepointContext:
    """Context manager wrapper for SAVEPOINT."""
    def __init__(self, name: Optional[str] = None, connection: Optional[str] = None):
        self.name = name
        self.connection = connection
        self._ctx = None

    def __enter__(self):
        conn = Database.connection(self.connection)
        self._ctx = conn.savepoint(self.name)
        return self._ctx.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._ctx:
            return self._ctx.__exit__(exc_type, exc_val, exc_tb)
        return False


__all__ = [
    "Database",
    "DatabaseManager",
    "QueryError",
    "TransactionError",
    "Profiler",
    "BaseGrammar",
    "MySqlGrammar",
    "PostgresGrammar",
    "SqliteGrammar",
    "atomic",
    "_SavepointContext",
]
