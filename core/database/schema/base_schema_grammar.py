"""
core/database/schema/base_schema_grammar.py
===========================================
Base Schema / DDL Grammar Compiler.
"""

from core.database.contracts.grammar import SchemaGrammarInterface


class BaseSchemaGrammar(SchemaGrammarInterface):
    """Abstract base schema grammar for DDL statements."""

    def wrap_table(self, table: str) -> str:
        return f'"{table}"'

    def wrap(self, value: str) -> str:
        return f'"{value}"'

    def compile_drop(self, table: str) -> str:
        return f"DROP TABLE {self.wrap_table(table)}"

    def compile_drop_if_exists(self, table: str) -> str:
        return f"DROP TABLE IF EXISTS {self.wrap_table(table)}"
