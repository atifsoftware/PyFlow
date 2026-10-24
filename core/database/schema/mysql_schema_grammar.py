"""
core/database/schema/mysql_schema_grammar.py
============================================
MySQL Schema / DDL Grammar Compiler.
"""

from core.database.schema.base_schema_grammar import BaseSchemaGrammar


class MySqlSchemaGrammar(BaseSchemaGrammar):
    """MySQL specific schema grammar with backtick quoting."""

    def wrap_table(self, table: str) -> str:
        return f'`{table.replace("`", "``")}`'

    def wrap(self, value: str) -> str:
        return f'`{value.replace("`", "``")}`'
