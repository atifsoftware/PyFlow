"""
core/database/grammar/sqlite_grammar.py
=======================================
SQLite SQL query grammar compiler.
"""

from core.database.grammar.base_grammar import BaseGrammar


class SqliteGrammar(BaseGrammar):
    """SQLite specific query compiler with ANSI double-quotes and ? placeholders."""

    placeholder: str = "?"

    def wrap_value(self, value: str) -> str:
        """Wrap identifier in SQLite double-quotes."""
        if value == "*":
            return value
        escaped = value.replace('"', '""')
        return f'"{escaped}"'

    def compile_where_date(self, column: str, operator: str) -> str:
        return f"date({column}) {operator} {self.placeholder}"

    def compile_where_date_func(self, column: str, function: str, operator: str) -> str:
        formats = {
            "YEAR": "%Y",
            "MONTH": "%m",
            "DAY": "%d",
        }
        fmt = formats.get(function.upper(), "%Y")
        return f"strftime('{fmt}', {column}) {operator} {self.placeholder}"
