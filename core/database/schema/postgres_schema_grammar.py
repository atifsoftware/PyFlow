"""
core/database/schema/postgres_schema_grammar.py
===============================================
PostgreSQL Schema / DDL Grammar Compiler.
"""

from core.database.schema.base_schema_grammar import BaseSchemaGrammar


class PostgresSchemaGrammar(BaseSchemaGrammar):
    """PostgreSQL specific schema grammar with double quotes."""

    def wrap_table(self, table: str) -> str:
        escaped = table.replace('"', '""')
        return f'"{escaped}"'

    def wrap(self, value: str) -> str:
        escaped = value.replace('"', '""')
        return f'"{escaped}"'
