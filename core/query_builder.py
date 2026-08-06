"""
core/query_builder.py
======================
Laravel/PHP Eloquent স্টাইলের ফ্লুয়েন্ট Query Builder। ইউজার ইনপুট কখনোই
সরাসরি SQL স্ট্রিং-এর ভেতরে বসে না — সবকিছু placeholder (? বা %s) আর bound
parameter দিয়ে পাঠানো হয় Database.execute()-এ। এটাই SQL Injection ঠেকানোর
মূল প্রতিরক্ষা।

কলাম/টেবিলের নাম (identifier) হোয়াইটলিস্ট রেজেক্স দিয়ে ভ্যালিডেট করা হয়,
কারণ identifier bind করা যায় না (placeholder শুধু ভ্যালুর জন্য কাজ করে)।

Driver-aware quoting:
  - MySQL:           `table`, `column`  (backtick)
  - PostgreSQL:      "table", "column"  (double-quote)
  - SQLite:          "table", "column"  (double-quote)
"""

import re
from core.database import Database, QueryError

# Identifier validation — backtick অথবা double-quote অথবা সাদা সব গ্রাহ্য
_IDENTIFIER_RE = re.compile(
    r'^[`"]?[a-zA-Z_][a-zA-Z0-9_]*[`"]?(\.[`"]?[a-zA-Z_][a-zA-Z0-9_]*[`"]?)?$'
)


def _safe_identifier(name: str) -> str:
    """
    টেবিল/কলামের নাম ভ্যালিডেট করে driver-অনুযায়ী quote যোগ করে।

    - MySQL:      `column`   (ব্যাকটিক)
    - PostgreSQL: "column"   (ডাবল-কোট)
    - SQLite:     "column"   (ডাবল-কোট)
    """
    if name == "*":
        return name

    base = name.split(" ")[0]  # "users u" এর মতো alias হলে base অংশ চেক করে
    # Quote সরিয়ে raw name validate করা
    raw_base = base.strip("`\"\'")
    raw_re   = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$')
    if not raw_re.match(raw_base):
        raise QueryError(f"অবৈধ কলাম/টেবিল নাম: {name!r}")

    # Driver অনুযায়ী quote character
    q = "`" if Database.driver == "mysql" else '"'

    parts  = raw_base.split(".")
    quoted = ".".join(f"{q}{p}{q}" for p in parts)

    if " " in name:
        alias = name.split(" ", 1)[1]
        return f"{quoted} {alias}"
    return quoted


class QueryBuilder:
    def __init__(self, table: str):
        self.table = _safe_identifier(table)
        self._select = ["*"]
        self._wheres = []       # list of (fragment, params)
        self._joins = []
        self._order = []
        self._group = []
        self._havings = []      # list of (fragment, value)
        self._limit = None
        self._offset = None
        self._params = []
        self._cache_ttl = None  # None = no cache; int = cache TTL seconds

    # ---------------------------------------------------------------- SELECT
    def select(self, *columns):
        self._select = [_safe_identifier(c) for c in columns] if columns else ["*"]
        return self

    def join(self, table, first, operator, second, kind="INNER"):
        table = _safe_identifier(table)
        first = _safe_identifier(first)
        second = _safe_identifier(second)
        if operator not in ("=", "!=", ">", "<", ">=", "<="):
            raise QueryError("অবৈধ join operator")
        self._joins.append(f"{kind} JOIN {table} ON {first} {operator} {second}")
        return self

    def left_join(self, table, first, operator, second):
        return self.join(table, first, operator, second, kind="LEFT")

    # ----------------------------------------------------------------- WHERE
    def where(self, column, operator, value=None):
        """where('age', '>', 18)  অথবা  where('active', True) -> '=' ধরে নেবে"""
        if value is None:
            value = operator
            operator = "="
        column = _safe_identifier(column)
        if operator.upper() not in ("=", "!=", "<>", ">", "<", ">=", "<=", "LIKE", "NOT LIKE"):
            raise QueryError("অবৈধ where operator")
        ph = Database.placeholder()
        self._wheres.append((f"{column} {operator} {ph}", "AND"))
        self._params.append(value)
        return self

    def or_where(self, column, operator, value=None):
        if value is None:
            value = operator
            operator = "="
        column = _safe_identifier(column)
        ph = Database.placeholder()
        self._wheres.append((f"{column} {operator} {ph}", "OR"))
        self._params.append(value)
        return self

    def where_group(self, callback, joiner="AND"):
        """
        Grouped WHERE clauses — e.g. WHERE a AND (b OR c)
        callback-এ একটি নতুন QueryBuilder instance পাস করা হয় যার wheres-কে parenthesis-এ wrap করা হয়।
        """
        sub_qb = QueryBuilder(self.table)
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
        column = _safe_identifier(column)
        if not values:
            self._wheres.append(("1 = 0", "AND"))  # খালি list হলে কোনো রেজাল্ট না
            return self
        ph = Database.placeholder()
        placeholders = ", ".join([ph] * len(values))
        self._wheres.append((f"{column} IN ({placeholders})", "AND"))
        self._params.extend(values)
        return self

    def where_like(self, column, pattern):
        column = _safe_identifier(column)
        ph = Database.placeholder()
        self._wheres.append((f"{column} LIKE {ph}", "AND"))
        self._params.append(pattern)
        return self

    def where_null(self, column):
        column = _safe_identifier(column)
        self._wheres.append((f"{column} IS NULL", "AND"))
        return self

    def where_not_null(self, column):
        column = _safe_identifier(column)
        self._wheres.append((f"{column} IS NOT NULL", "AND"))
        return self

    def where_between(self, column, start, end):
        """WHERE column BETWEEN start AND end — তারিখ বা সংখ্যার range ফিল্টারে উপকারী"""
        column = _safe_identifier(column)
        ph = Database.placeholder()
        self._wheres.append((f"{column} BETWEEN {ph} AND {ph}", "AND"))
        self._params.extend([start, end])
        return self

    def where_not_in(self, column, values):
        """WHERE column NOT IN (...)"""
        column = _safe_identifier(column)
        if not values:
            return self  # খালি list হলে কোনো ফিল্টার লাগবে না
        ph = Database.placeholder()
        placeholders = ", ".join([ph] * len(values))
        self._wheres.append((f"{column} NOT IN ({placeholders})", "AND"))
        self._params.extend(values)
        return self

    # --------------------------------------------------------- ORDER / LIMIT
    def order_by(self, column, direction="ASC"):
        column = _safe_identifier(column)
        direction = "DESC" if str(direction).upper() == "DESC" else "ASC"
        self._order.append(f"{column} {direction}")
        return self

    def group_by(self, *columns):
        self._group.extend(_safe_identifier(c) for c in columns)
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

            # Count total matching query before modifying limit/offset
            total = self.count()

            self._limit = per_page
            self._offset = (page - 1) * per_page
            rows = self.get()

            from core.pagination import Paginator
            return Paginator(rows, total, per_page, page, request.path, request.query)
        else:
            page = max(1, int(request_or_page))
            self._limit = per_page
            self._offset = (page - 1) * per_page
            return self

    def having(self, column, operator, value):
        """GROUP BY-এর পরে ফিল্টার করার জন্য HAVING clause — aggregate ফাংশনে ব্যবহার করুন"""
        column = _safe_identifier(column)
        if operator.upper() not in ("=", "!=", "<>", ">", "<", ">=", "<="):
            raise QueryError("অবৈধ having operator")
        ph = Database.placeholder()
        self._havings.append((f"{column} {operator} {ph}", value))
        return self

    def having_raw(self, fragment: str, operator: str, value=None):
        """
        কাস্টম HAVING expression — যেমন having_raw('COUNT(*)', '>', 5)
        
        ⚠️ সতর্কবার্তা: কাস্টম এক্সপ্রেশনে ভ্যারিয়েবল বাইন্ড করতে value প্যারামিটারটি ব্যবহার করুন।
        কখনোই having_raw("COUNT(*) > " + input_val) এভাবে লজিক লিখবেন না।
        """
        if value is None:
            value = operator
            operator = ""
        
        ph = Database.placeholder() if operator else ""
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

    def to_sql(self):
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
        """
        Query result caching সক্রিয় করে।
        পরবর্তী .get() call-এ result Cache-এ রাখা হবে।

        ব্যবহার:
            users = User.where("active", 1).cache(seconds=300).get()
        """
        self._cache_ttl = seconds
        return self

    def get(self):
        """সব রো রিটার্ন করে (list of dict)। cache() চেইন করলে cached result দেয়।"""
        sql, params = self.to_sql()

        if self._cache_ttl is not None:
            # Cache key namespace with table version tag
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
                cursor = Database.execute(sql, params)
                rows = [dict(r) for r in cursor.fetchall()]
                Cache.put(cache_key, rows, ttl=self._cache_ttl)
                return rows
            except Exception:
                pass  # cache ব্যর্থ হলে normally execute করা

        cursor = Database.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


    def first(self):
        self._limit = 1
        rows = self.get()
        return rows[0] if rows else None

    def count(self):
        """ফিক্স: মূল QueryBuilder-এর _select না বদলে আলাদা কপি দিয়ে COUNT করে"""
        import copy
        count_qb = copy.copy(self)
        count_qb._select = ["COUNT(*) as cnt"]
        count_qb._order = []
        count_qb._limit = None
        count_qb._offset = None
        sql, params = count_qb.to_sql()
        cursor = Database.execute(sql, params)
        row = cursor.fetchone()
        return dict(row)["cnt"] if row else 0

    def exists(self) -> bool:
        return self.count() > 0

    # --------------------------------------------------------- WRITE OPS
    def _invalidate_cache(self):
        """টেবিলের রাইট অপারেশন হলে ক্যাশ ইনভ্যালিডেট করে"""
        try:
            from core.cache import Cache
            Cache.increment(f"table_version:{self.table}")
        except Exception:
            pass

    def insert(self, data: dict) -> int:
        self._invalidate_cache()
        columns = [_safe_identifier(c) for c in data.keys()]
        ph = Database.placeholder()
        placeholders = ", ".join([ph] * len(columns))
        sql = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders})"
        cursor = Database.execute(sql, tuple(data.values()))
        if not Database.in_transaction():
            Database.commit()
        return Database.last_insert_id(cursor)

    def update(self, data: dict) -> int:
        self._invalidate_cache()
        columns = [_safe_identifier(c) for c in data.keys()]
        ph = Database.placeholder()
        set_clause = ", ".join([f"{c} = {ph}" for c in columns])
        sql = f"UPDATE {self.table} SET {set_clause}"
        sql += self._build_where_clause()
        if not self._wheres:
            raise QueryError(
                "নিরাপত্তার কারণে WHERE ছাড়া UPDATE চালানো নিষেধ। "
                "সব রো আপডেট করতে চাইলে .update_all() ব্যবহার করুন।"
            )
        params = tuple(data.values()) + tuple(self._params)
        cursor = Database.execute(sql, params)
        if not Database.in_transaction():
            Database.commit()
        return cursor.rowcount

    def update_all(self, data: dict) -> int:
        """সব রো আপডেট করে (সতর্কতা: বিপজ্জনক হতে পারে!)"""
        self._invalidate_cache()
        columns = [_safe_identifier(c) for c in data.keys()]
        ph = Database.placeholder()
        set_clause = ", ".join([f"{c} = {ph}" for c in columns])
        sql = f"UPDATE {self.table} SET {set_clause}"
        if self._wheres:
            sql += self._build_where_clause()
        params = tuple(data.values()) + tuple(self._params)
        cursor = Database.execute(sql, params)
        if not Database.in_transaction():
            Database.commit()
        return cursor.rowcount

    def delete(self) -> int:
        self._invalidate_cache()
        sql = f"DELETE FROM {self.table}"
        sql += self._build_where_clause()
        if not self._wheres:
            raise QueryError(
                "নিরাপত্তার কারণে WHERE ছাড়া DELETE চালানো নিষেধ। "
                "সব রো ডিলিট করতে চাইলে .delete_all() ব্যবহার করুন।"
            )
        cursor = Database.execute(sql, tuple(self._params))
        if not Database.in_transaction():
            Database.commit()
        return cursor.rowcount

    def delete_all(self) -> int:
        """সব রো ডিলিট করে (সতর্কতা: বিপজ্জনক হতে পারে!)"""
        self._invalidate_cache()
        sql = f"DELETE FROM {self.table}"
        if self._wheres:
            sql += self._build_where_clause()
        cursor = Database.execute(sql, tuple(self._params))
        if not Database.in_transaction():
            Database.commit()
        return cursor.rowcount

    @staticmethod
    def raw(sql: str, params: tuple = ()):
        """
        একদম কাস্টম query চালানোর জন্য - কিন্তু params সবসময় bound রাখতে হবে।
        কখনো raw(f"... {user_input}") এভাবে লিখবেন না।
        """
        cursor = Database.execute(sql, params)
        if sql.strip().upper().startswith("SELECT"):
            return [dict(r) for r in cursor.fetchall()]
        Database.commit()
        return cursor.rowcount
