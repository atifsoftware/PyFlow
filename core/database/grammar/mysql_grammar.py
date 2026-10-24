"""
core/database/grammar/mysql_grammar.py
======================================
MySQL SQL query grammar compiler.
"""

from typing import Any
from core.database.grammar.base_grammar import BaseGrammar


class MySqlGrammar(BaseGrammar):
    """MySQL specific query compiler with backtick escaping and %s placeholders."""

    placeholder: str = "%s"

    def wrap_value(self, value: str) -> str:
        """Wrap identifier in MySQL backticks."""
        if value == "*":
            return value
        return f'`{value.replace("`", "``")}`'

    def compile_where_date(self, column: str, operator: str) -> str:
        return f"DATE({column}) {operator} {self.placeholder}"

    def compile_where_date_func(self, column: str, function: str, operator: str) -> str:
        return f"{function.upper()}({column}) {operator} {self.placeholder}"

    def compile_where_json_contains(self, column: str) -> str:
        return f"JSON_CONTAINS({column}, {self.placeholder}, {self.placeholder})"
