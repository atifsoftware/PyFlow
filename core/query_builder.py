"""
core/query_builder.py
======================
Laravel/PHP Eloquent-styled Fluent Query Builder with Multi-Database and Grammar Architecture.
Decouples query state from SQL dialect compilation via Connection Grammars.
Supports simultaneous querying against SQLite, MySQL, and PostgreSQL.
"""

import re
from typing import Any, List, Dict, Optional, Tuple, Union
from core.database import Database, QueryError

# Compile identifier regexes at module level for optimal performance
_RAW_BASE_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$')
_ALIAS_RE = re.compile(r'^(?:as\s+)?[a-zA-Z_][a-zA-Z0-9_]*$', re.IGNORECASE)


def _safe_identifier(name: str, grammar=None) -> str:
    """
    Validate table/column name and quote according to connection grammar.
    """
    if name == "*":
        return name
    if grammar is not None:
        return grammar.wrap(name)
    return Database.connection().grammar.wrap(name)


class QueryBuilder:
    """
    Fluent Query Builder bound to a specific database connection and grammar.
    """

    def __init__(self, table: str, connection=None):
        from core.database.drivers.base_connection import BaseConnection
        if isinstance(connection, BaseConnection):
            self._connection = connection
        elif connection is not None:
            self._connection = Database.connection(connection)
        else:
            self._connection = Database.connection()

        self.grammar = self._connection.grammar
        self.raw_table = table
        self.table = self.grammar.wrap_table(table)
        self._select = ["*"]
        self._wheres = []       # list of (fragment, joiner)
        self._joins = []
        self._order = []
        self._group = []
        self._havings = []      # list of (fragment, value)
        self._limit = None
        self._offset = None
        self._params = []
        self._cache_ttl = None  # None = no cache; int = cache TTL seconds
        self._model = None

    @property
    def connection(self):
        return self._connection

    def set_model(self, model_class):
        self._model = model_class
        return self

    # ---------------------------------------------------------------- SELECT
    def select(self, *columns):
        self._select = [self.grammar.wrap(c) for c in columns] if columns else ["*"]
        return self

    def join(self, table, first, operator, second, kind="INNER"):
        table = self.grammar.wrap_table(table)
        first = self.grammar.wrap(first)
        second = self.grammar.wrap(second)
        if operator not in ("=", "!=", ">", "<", ">=", "<="):
            raise QueryError("অবৈধ join operator")
        self._joins.append(f"{kind} JOIN {table} ON {first} {operator} {second}")
        return self

    def left_join(self, table, first, operator, second):
        return self.join(table, first, operator, second, kind="LEFT")

    # ----------------------------------------------------------------- WHERE
    def where(self, column, operator, value=None):
        """where('age', '>', 18) অথবা where('active', True) -> '=' ধরে নেবে"""
        if value is None:
            value = operator
            operator = "="
        col = self.grammar.wrap(column)
        if operator.upper() not in ("=", "!=", "<>", ">", "<", ">=", "<=", "LIKE", "NOT LIKE"):
            raise QueryError("অবৈধ where operator")
        ph = self._connection.placeholder
        self._wheres.append((f"{col} {operator} {ph}", "AND"))
        self._params.append(value)
        return self

    def or_where(self, column, operator, value=None):
        if value is None:
            value = operator
            operator = "="
        col = self.grammar.wrap(column)
        ph = self._connection.placeholder
        self._wheres.append((f"{col} {operator} {ph}", "OR"))
        self._params.append(value)
        return self

    def where_group(self, callback, joiner="AND"):
        """
        Grouped WHERE clauses — e.g. WHERE a AND (b OR c)
        """
        sub_qb = QueryBuilder(self.raw_table, connection=self._connection)
        callback(sub_qb)
        if sub_qb._wheres:
            parts = []
            for i, (fragment, j) in enumerate(sub_qb._wheres):
                if i == 0:
                    parts.append(fragment)
                else:
                    parts.append(f"{j} {fragment}")
            sub_sql = " ".join(parts)
            self._wheres.append((f"({sub_sql})", joiner))
            self._params.extend(sub_qb._params)
        return self

    def where_in(self, column, values):
        col = self.grammar.wrap(column)
        if not values:
            self._wheres.append(("1 = 0", "AND"))
            return self
        ph = self._connection.placeholder
        placeholders = ", ".join([ph] * len(values))
        self._wheres.append((f"{col} IN ({placeholders})", "AND"))
        self._params.extend(values)
        return self

    def where_like(self, column, pattern):
        col = self.grammar.wrap(column)
        ph = self._connection.placeholder
        self._wheres.append((f"{col} LIKE {ph}", "AND"))
        self._params.append(pattern)
        return self

    def where_null(self, column):
        col = self.grammar.wrap(column)
        self._wheres.append((f"{col} IS NULL", "AND"))
        return self

    def where_not_null(self, column):
        col = self.grammar.wrap(column)
        self._wheres.append((f"{col} IS NOT NULL", "AND"))
        return self

    def where_between(self, column, start, end):
        """WHERE column BETWEEN start AND end"""
        col = self.grammar.wrap(column)
        ph = self._connection.placeholder
        self._wheres.append((f"{col} BETWEEN {ph} AND {ph}", "AND"))
        self._params.extend([start, end])
        return self

    def where_not_in(self, column, values):
        """WHERE column NOT IN (...)"""
        col = self.grammar.wrap(column)
        if not values:
            return self
        ph = self._connection.placeholder
        placeholders = ", ".join([ph] * len(values))
        self._wheres.append((f"{col} NOT IN ({placeholders})", "AND"))
        self._params.extend(values)
        return self

    # --------------------------------------------------------- ORDER / LIMIT
    def order_by(self, column, direction="ASC"):
        col = self.grammar.wrap(column)
        direction = "DESC" if str(direction).upper() == "DESC" else "ASC"
        self._order.append(f"{col} {direction}")
        return self

    def group_by(self, *columns):
        self._group.extend(self.grammar.wrap(c) for c in columns)
        return self

    def limit(self, n: int):
        self._limit = int(n)
        return self

    def offset(self, n: int):
        self._offset = int(n)
        return self

    def paginate(self, request_or_page, per_page: int = 15):
        from core.request import Request
        if isinstance(request_or_page, Request):
            request = request_or_page
            try:
                page = int(request.input("page", 1))
            except (ValueError, TypeError):
                page = 1
            page = max(1, page)

            clone = self.clone()
            total = clone.count()

            clone._limit = per_page
            clone._offset = (page - 1) * per_page
            rows = clone.get()

            from core.pagination import Paginator
            return Paginator(rows, total, per_page, page, request.path, request.query)
        else:
            page = max(1, int(request_or_page))
            clone = self.clone()
            clone._limit = per_page
            clone._offset = (page - 1) * per_page
            return clone

    def having(self, column, operator, value):
        col = self.grammar.wrap(column)
        if operator.upper() not in ("=", "!=", "<>", ">", "<", ">=", "<="):
            raise QueryError("অবৈধ having operator")
        ph = self._connection.placeholder
        self._havings.append((f"{col} {operator} {ph}", value))
        return self

    def having_raw(self, fragment: str, operator: str, value=None):
        if value is None:
            value = operator
            operator = ""
        ph = self._connection.placeholder if operator else ""
        expr = f"{fragment} {operator} {ph}".strip()
        self._havings.append((expr, value))
        return self

    # ------------------------------------------------------------ BUILD SQL
    def _build_where_clause(self):
        if not self._wheres:
            return ""
        parts = []
        for i, (fragment, joiner) in enumerate(self._wheres):
            if i == 0:
                parts.append(fragment)
            else:
                parts.append(f"{joiner} {fragment}")
        return " WHERE " + " ".join(parts)

    def _build_having_clause(self):
        if not self._havings:
            return "", ()
        parts = []
        vals = []
        for fragment, value in self._havings:
            parts.append(fragment)
            vals.append(value)
        return " HAVING " + " AND ".join(parts), tuple(vals)

    def to_sql(self) -> Tuple[str, tuple]:
        sql = f"SELECT {', '.join(self._select)} FROM {self.table}"
        if self._joins:
            sql += " " + " ".join(self._joins)
        sql += self._build_where_clause()
        if self._group:
            sql += " GROUP BY " + ", ".join(self._group)
        having_clause, having_params = self._build_having_clause()
        sql += having_clause
        if self._order:
            sql += " ORDER BY " + ", ".join(self._order)
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"
        return sql, tuple(self._params) + having_params

    # ------------------------------------------------------------- EXECUTE
    def cache(self, seconds: int = 60):
        self._cache_ttl = seconds
        return self

    def get(self):
        """Execute and fetch all records."""
        sql, params = self.to_sql()

        if self._cache_ttl is not None:
            try:
                from core.cache import Cache
                version = str(Cache.get(f"table_version:{self.table}", "1"))
            except Exception:
                version = "1"

            import hashlib, json
            try:
                key_source = sql + "|" + json.dumps(params, default=str, sort_keys=True)
            except Exception:
                key_source = sql + "|" + str(params)

            cache_key = f"qb:table:{self.table}:v{version}:" + hashlib.md5(key_source.encode("utf-8")).hexdigest()

            try:
                from core.cache import Cache
                cached = Cache.get(cache_key)
                if cached is not None:
                    return cached
                rows = self._connection.execute(sql, params)
                Cache.put(cache_key, rows, ttl=self._cache_ttl)
                return rows
            except Exception:
                pass

        rows = self._connection.execute(sql, params)
        return rows

    def first(self):
        self._limit = 1
        rows = self.get()
        return rows[0] if rows else None

    def count(self):
        count_qb = self.clone()
        count_qb._select = ["COUNT(*) as cnt"]
        count_qb._order = []
        count_qb._limit = None
        count_qb._offset = None
        sql, params = count_qb.to_sql()
        rows = self._connection.execute(sql, params)
        if rows and len(rows) > 0:
            return rows[0].get("cnt", 0)
        return 0

    def exists(self) -> bool:
        return self.count() > 0

    # --------------------------------------------------------- WRITE OPS
    def _invalidate_cache(self):
        try:
            from core.cache import Cache
            Cache.increment(f"table_version:{self.table}")
        except Exception:
            pass

    def insert(self, data: dict):
        """
        Insert record into table. Returns primary key ID if available, or affected dict.
        """
        self._invalidate_cache()
        columns = [self.grammar.wrap(c) for c in data.keys()]
        ph = self._connection.placeholder
        placeholders = ", ".join([ph] * len(columns))
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"

        if self._connection.driver == "postgresql":
            sql += ' RETURNING "id"'
            result = self._connection.execute(sql, tuple(data.values()))
            if not self._connection.in_transaction():
                self._connection.commit()
            if isinstance(result, dict) and "id" in result and result["id"] is not None:
                return result["id"]
            return result
        else:
            result = self._connection.execute(sql, tuple(data.values()))
            if not self._connection.in_transaction():
                self._connection.commit()
            if isinstance(result, dict) and "id" in result and result["id"] is not None:
                return result["id"]
            return result

    def update(self, data: dict) -> int:
        if not data:
            return 0
        self._invalidate_cache()
        columns = [self.grammar.wrap(c) for c in data.keys()]
        ph = self._connection.placeholder
        set_clause = ", ".join([f"{c} = {ph}" for c in columns])
        sql = f"UPDATE {self.table} SET {set_clause}"
        sql += self._build_where_clause()
        if not self._wheres:
            raise QueryError(
                "নিরাপত্তার কারণে WHERE ছাড়া UPDATE চালানো নিষেধ। "
                "সব রো আপডেট করতে চাইলে .update_all() ব্যবহার করুন।"
            )
        params = tuple(data.values()) + tuple(self._params)
        cursor = self._connection.execute(sql, params)
        if not self._connection.in_transaction():
            self._connection.commit()
        return cursor if isinstance(cursor, int) else getattr(cursor, "rowcount", 0)

    def update_all(self, data: dict) -> int:
        if not data:
            return 0
        self._invalidate_cache()
        columns = [self.grammar.wrap(c) for c in data.keys()]
        ph = self._connection.placeholder
        set_clause = ", ".join([f"{c} = {ph}" for c in columns])
        sql = f"UPDATE {self.table} SET {set_clause}"
        if self._wheres:
            sql += self._build_where_clause()
        params = tuple(data.values()) + tuple(self._params)
        cursor = self._connection.execute(sql, params)
        if not self._connection.in_transaction():
            self._connection.commit()
        return cursor if isinstance(cursor, int) else getattr(cursor, "rowcount", 0)

    def delete(self) -> int:
        self._invalidate_cache()
        sql = f"DELETE FROM {self.table}"
        sql += self._build_where_clause()
        if not self._wheres:
            raise QueryError(
                "নিরাপত্তার কারণে WHERE ছাড়া DELETE চালানো নিষেধ। "
                "সব রো ডিলিট করতে চাইলে .delete_all() ব্যবহার করুন।"
            )
        cursor = self._connection.execute(sql, tuple(self._params))
        if not self._connection.in_transaction():
            self._connection.commit()
        return cursor if isinstance(cursor, int) else getattr(cursor, "rowcount", 0)

    def delete_all(self) -> int:
        self._invalidate_cache()
        sql = f"DELETE FROM {self.table}"
        if self._wheres:
            sql += self._build_where_clause()
        cursor = self._connection.execute(sql, tuple(self._params))
        if not self._connection.in_transaction():
            self._connection.commit()
        return cursor if isinstance(cursor, int) else getattr(cursor, "rowcount", 0)

    def clone(self):
        new_qb = QueryBuilder(self.raw_table, connection=self._connection)
        new_qb._select = list(self._select)
        new_qb._wheres = list(self._wheres)
        new_qb._joins = list(self._joins)
        new_qb._order = list(self._order)
        new_qb._group = list(self._group)
        new_qb._havings = list(self._havings)
        new_qb._limit = self._limit
        new_qb._offset = self._offset
        new_qb._params = list(self._params)
        new_qb._cache_ttl = self._cache_ttl
        new_qb._model = self._model
        return new_qb
