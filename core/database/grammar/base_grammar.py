"""
core/database/grammar/base_grammar.py
=====================================
Base SQL query grammar compiler for PyFlow.
Decouples query state from SQL dialect syntax compilation.
"""

import re
import json
from typing import Any, List, Tuple, Dict, Optional
from core.database.contracts.grammar import GrammarInterface

_RAW_BASE_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$')
_ALIAS_RE = re.compile(r'^(?:as\s+)?[a-zA-Z_][a-zA-Z0-9_]*$', re.IGNORECASE)


class BaseGrammar(GrammarInterface):
    """
    Abstract base grammar for compiling SQL queries.
    Provides standard ANSI SQL compilation logic with hook methods for dialect differences.
    """

    placeholder: str = "?"

    def wrap_table(self, table: str) -> str:
        """Wrap table name in identifier escape characters."""
        return self.wrap(table)

    def wrap_value(self, value: str) -> str:
        """Wrap single segment in quotes (default double-quotes)."""
        if value == "*":
            return value
        escaped = value.replace('"', '""')
        return f'"{escaped}"'

    def wrap(self, name: str) -> str:
        """
        Safely validate and quote identifiers (columns, tables, aliases).
        Supports:
          - '*'
          - 'column'
          - 'table.column'
          - 'table alias'
          - 'column as alias'
        """
        if not name or name == "*":
            return "*"

        name = str(name).strip()
        if name == "*":
            return name

        base = name.split(" ")[0]
        raw_base = base.strip("`\"'")
        if not _RAW_BASE_RE.match(raw_base):
            from core.database.manager import QueryError
            raise QueryError(f"অবৈধ কলাম/টেবিল নাম: {name!r}")

        parts = raw_base.split(".")
        quoted = ".".join(self.wrap_value(p) for p in parts)

        if " " in name:
            alias = name.split(" ", 1)[1].strip()
            if not _ALIAS_RE.match(alias):
                from core.database.manager import QueryError
                raise QueryError(f"অবৈধ alias: {alias!r}")

            alias_parts = re.split(r'\s+', alias)
            if len(alias_parts) == 2 and alias_parts[0].upper() == "AS":
                return f"{quoted} AS {self.wrap_value(alias_parts[1])}"
            else:
                return f"{quoted} {self.wrap_value(alias)}"

        return quoted

    # ---------------------------------------------------------------- SELECT
    def compile_select(self, query: Any) -> str:
        """Compile a full SELECT statement from QueryBuilder components."""
        components = [
            self.compile_columns(query),
            self.compile_from(query),
            self.compile_joins(query),
            self.compile_wheres(query),
            self.compile_groups(query),
            self.compile_havings(query),
            self.compile_orders(query),
            self.compile_limit(query),
            self.compile_offset(query),
        ]
        return " ".join(part for part in components if part).strip()

    def compile_columns(self, query: Any) -> str:
        selects = getattr(query, "_select", ["*"])
        if not selects:
            selects = ["*"]
        quoted_cols = [self.wrap(col) if col != "*" else "*" for col in selects]
        return f"SELECT {', '.join(quoted_cols)}"

    def compile_from(self, query: Any) -> str:
        return f"FROM {self.wrap_table(getattr(query, 'raw_table', query.table))}"

    def compile_joins(self, query: Any) -> str:
        joins = getattr(query, "_joins", [])
        return " ".join(joins) if joins else ""

    def compile_wheres(self, query: Any) -> str:
        wheres = getattr(query, "_wheres", [])
        if not wheres:
            return ""
        
        # In PyFlow, _wheres can be list of (fragment, params) tuples or dicts
        sql_parts = []
        for item in wheres:
            if isinstance(item, tuple):
                fragment, _ = item
                sql_parts.append(fragment)
            elif isinstance(item, dict):
                sql_parts.append(self.compile_where_item(item))
            elif isinstance(item, str):
                sql_parts.append(item)

        if not sql_parts:
            return ""

        clause = " AND ".join(sql_parts)
        return f"WHERE {clause}"

    def compile_where_item(self, where: dict) -> str:
        """Compile structured WHERE dict."""
        col = self.wrap(where["column"])
        op = str(where.get("operator", "=")).upper()
        
        if op in ("IS NULL", "IS NOT NULL"):
            return f"{col} {op}"
        if op in ("IN", "NOT IN"):
            vals = where.get("value", [])
            placeholders = ", ".join([self.placeholder] * len(vals))
            return f"{col} {op} ({placeholders})"
        if op in ("BETWEEN", "NOT BETWEEN"):
            return f"{col} {op} {self.placeholder} AND {self.placeholder}"
        if op == "DATE":
            return self.compile_where_date(col, where.get("sql_operator", "="))
        if op == "DATE_FUNC":
            return self.compile_where_date_func(col, where.get("function", "YEAR"), where.get("sql_operator", "="))
        if op == "JSON_CONTAINS":
            return self.compile_where_json_contains(col)
        
        return f"{col} {op} {self.placeholder}"

    def compile_where_date(self, column: str, operator: str) -> str:
        return f"DATE({column}) {operator} {self.placeholder}"

    def compile_where_date_func(self, column: str, function: str, operator: str) -> str:
        return f"{function}({column}) {operator} {self.placeholder}"

    def compile_where_json_contains(self, column: str) -> str:
        return f"JSON_CONTAINS({column}, {self.placeholder}, {self.placeholder})"

    def compile_groups(self, query: Any) -> str:
        groups = getattr(query, "_group", [])
        if not groups:
            return ""
        return f"GROUP BY {', '.join(self.wrap(c) for c in groups)}"

    def compile_havings(self, query: Any) -> str:
        havings = getattr(query, "_havings", [])
        if not havings:
            return ""
        clauses = []
        for item in havings:
            if isinstance(item, tuple):
                clauses.append(item[0])
            else:
                clauses.append(str(item))
        return f"HAVING {' AND '.join(clauses)}" if clauses else ""

    def compile_orders(self, query: Any) -> str:
        orders = getattr(query, "_order", [])
        if not orders:
            return ""
        return f"ORDER BY {', '.join(orders)}"

    def compile_limit(self, query: Any) -> str:
        limit = getattr(query, "_limit", None)
        return f"LIMIT {int(limit)}" if limit is not None else ""

    def compile_offset(self, query: Any) -> str:
        offset = getattr(query, "_offset", None)
        return f"OFFSET {int(offset)}" if offset is not None else ""

    # --------------------------------------------------------- WRITE OPS
    def compile_insert(self, query: Any, values: Dict[str, Any]) -> Tuple[str, List[Any]]:
        table = self.wrap_table(getattr(query, "raw_table", query.table))
        columns = [self.wrap(col) for col in values.keys()]
        placeholders = [self.placeholder] * len(columns)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        params = list(values.values())
        return sql, params

    def compile_update(self, query: Any, values: Dict[str, Any]) -> Tuple[str, List[Any]]:
        table = self.wrap_table(getattr(query, "raw_table", query.table))
        set_parts = [f"{self.wrap(col)} = {self.placeholder}" for col in values.keys()]
        sql = f"UPDATE {table} SET {', '.join(set_parts)}"
        where_clause = self.compile_wheres(query)
        if where_clause:
            sql += f" {where_clause}"
        
        # Params: values for SET followed by parameters for WHERE
        params = list(values.values()) + list(getattr(query, "_params", []))
        return sql, params

    def compile_delete(self, query: Any) -> Tuple[str, List[Any]]:
        table = self.wrap_table(getattr(query, "raw_table", query.table))
        sql = f"DELETE FROM {table}"
        where_clause = self.compile_wheres(query)
        if where_clause:
            sql += f" {where_clause}"
        params = list(getattr(query, "_params", []))
        return sql, params
