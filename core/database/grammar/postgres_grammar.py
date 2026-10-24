"""
core/database/grammar/postgres_grammar.py
=========================================
PostgreSQL SQL query grammar compiler.
"""

from typing import Any, Dict, List, Tuple
from core.database.grammar.base_grammar import BaseGrammar


class PostgresGrammar(BaseGrammar):
    """PostgreSQL specific query compiler with ANSI double-quotes and %s placeholders."""

    placeholder: str = "%s"

    def wrap_value(self, value: str) -> str:
        """Wrap identifier in ANSI SQL double-quotes."""
        if value == "*":
            return value
        escaped = value.replace('"', '""')
        return f'"{escaped}"'

    def compile_where_date(self, column: str, operator: str) -> str:
        return f"{column}::date {operator} {self.placeholder}"

    def compile_where_date_func(self, column: str, function: str, operator: str) -> str:
        func = function.upper()
        return f"EXTRACT({func} FROM {column}) {operator} {self.placeholder}"

    def compile_where_json_contains(self, column: str) -> str:
        return f"{column}::jsonb @> {self.placeholder}::jsonb"

    def compile_insert(self, query: Any, values: Dict[str, Any], returning: str = "id") -> Tuple[str, List[Any]]:
        sql, params = super().compile_insert(query, values)
        if returning:
            sql += f" RETURNING {self.wrap(returning)}"
        return sql, params
