"""
core/database/contracts/grammar.py
==================================
Interfaces for Query Grammar and Schema Grammar compilers.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Tuple, Dict, Optional


class GrammarInterface(ABC):
    """Abstract interface for SQL query compilers."""

    @abstractmethod
    def wrap_table(self, table: str) -> str:
        """Wrap a table name in keyword escape quotes (e.g. `table` or "table")."""
        pass

    @abstractmethod
    def wrap(self, value: str) -> str:
        """Wrap a column or identifier in keyword escape quotes."""
        pass

    @abstractmethod
    def compile_select(self, query: Any) -> str:
        """Compile a SELECT query."""
        pass

    @abstractmethod
    def compile_insert(self, query: Any, values: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """Compile an INSERT statement with parameters."""
        pass

    @abstractmethod
    def compile_update(self, query: Any, values: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """Compile an UPDATE statement with parameters."""
        pass

    @abstractmethod
    def compile_delete(self, query: Any) -> Tuple[str, List[Any]]:
        """Compile a DELETE statement with parameters."""
        pass


class SchemaGrammarInterface(ABC):
    """Abstract interface for DDL / Schema compilers."""

    @abstractmethod
    def wrap_table(self, table: str) -> str:
        pass

    @abstractmethod
    def wrap(self, value: str) -> str:
        pass

    @abstractmethod
    def compile_drop(self, table: str) -> str:
        pass

    @abstractmethod
    def compile_drop_if_exists(self, table: str) -> str:
        pass
