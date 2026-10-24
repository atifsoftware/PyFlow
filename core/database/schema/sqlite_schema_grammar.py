"""
core/database/schema/sqlite_schema_grammar.py
=============================================
SQLite Schema / DDL Grammar Compiler.
"""

from core.database.schema.base_schema_grammar import BaseSchemaGrammar


class SqliteSchemaGrammar(BaseSchemaGrammar):
    """SQLite specific schema grammar with double quotes."""

    def wrap_table(self, table: str) -> str:
        escaped = table.replace('"', '""')
        return f'"{escaped}"'

    def wrap(self, value: str) -> str:
        escaped = value.replace('"', '""')
        return f'"{escaped}"'
