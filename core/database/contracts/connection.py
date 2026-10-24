"""
core/database/contracts/connection.py
=====================================
Interface for Database Connection Drivers.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Tuple, Callable
from core.database.contracts.grammar import GrammarInterface, SchemaGrammarInterface


class ConnectionInterface(ABC):
    """Abstract interface for database connection drivers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Connection configuration name (e.g. 'mysql', 'sqlite', 'pgsql')."""
        pass

    @property
    @abstractmethod
    def driver(self) -> str:
        """Database driver type name (e.g. 'mysql', 'sqlite', 'postgresql')."""
        pass

    @property
    @abstractmethod
    def grammar(self) -> GrammarInterface:
        """The query grammar compiler for this connection."""
        pass

    @property
    @abstractmethod
    def schema_grammar(self) -> SchemaGrammarInterface:
        """The schema / DDL grammar compiler for this connection."""
        pass

    @abstractmethod
    def connection(self) -> Any:
        """Get the active underlying connection instance for the current thread."""
        pass

    @abstractmethod
    def cursor(self, as_dict: bool = True) -> Any:
        """Create a new cursor on the active connection."""
        pass

    @abstractmethod
    def execute(self, sql: str, params: tuple = (), as_dict: bool = True) -> Any:
        """Execute a SQL query."""
        pass

    @abstractmethod
    def execute_many(self, sql: str, params_list: List[tuple], batch_size: int = 1000) -> int:
        """Execute a batch query."""
        pass

    @abstractmethod
    def begin_transaction(self) -> None:
        """Begin a new database transaction."""
        pass

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the current transaction."""
        pass

    @abstractmethod
    def in_transaction(self) -> bool:
        """Check if currently inside an active transaction."""
        pass

    @abstractmethod
    def transaction_level(self) -> int:
        """Get the transaction nesting level."""
        pass

    @abstractmethod
    def last_insert_id(self, cursor: Any = None) -> int:
        """Retrieve the last inserted record ID."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close or release the connection for the current thread."""
        pass

    @abstractmethod
    def close_all(self) -> None:
        """Close all connections across pools on application shutdown."""
        pass
