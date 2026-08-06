"""
core/model.py
==============
Active-Record স্টাইলের বেস Model। প্রতিটা app/models/*.py এই ক্লাস থেকে
ইনহেরিট করবে এবং `table` নাম সেট করবে। সব DB অ্যাক্সেস QueryBuilder-এর
মধ্য দিয়ে যায়, তাই bound parameter ছাড়া কোনো raw SQL string তৈরি হয় না।

Eager Loading (N+1 সমাধান):
    User.with_("posts").get()           # hasMany — মাত্র 2 queries
    User.with_("posts", "role").get()   # 3 queries total
    Post.with_("user").get()            # belongsTo — 2 queries

eager_relations dict define করুন Model-এ:
    class User(Model):
        table = "users"
        eager_relations = {
            "logs": {"type": "has_many", "model": ActivityLog, "foreign_key": "user_id"},
        }
"""

from core.query_builder import QueryBuilder
from core.event import Event


class Model:
    table = None
    primary_key = "id"
    fillable = []       # mass-assignment-এ কোন কলামগুলো allow করা হবে
    hidden = []          # to_dict()-এ কোন কলাম বাদ যাবে (যেমন password)
    timestamps = True    # created_at/updated_at অটো-ম্যানেজ করবে কিনা
    eager_relations = {} # with_() এর জন্য relation definitions

    def __init__(self, attributes: dict = None):
        self._attributes = attributes or {}
        self._loaded_relations = {}  # eager loaded relations cache

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        # eager loaded relation চেক করা আগে
        if name in self.__dict__.get("_loaded_relations", {}):
            return self._loaded_relations[name]
        return self._attributes.get(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._attributes[name] = value

    def to_dict(self) -> dict:
        data = {k: v for k, v in self._attributes.items() if k not in self.hidden}
        # eager loaded relations-ও include করা
        for rel_name, rel_val in self._loaded_relations.items():
            if isinstance(rel_val, list):
                data[rel_name] = [r.to_dict() if isinstance(r, Model) else r for r in rel_val]
            elif isinstance(rel_val, Model):
                data[rel_name] = rel_val.to_dict()
            else:
                data[rel_name] = rel_val
        return data

    # ─────────────────────────────────────── Query API ──────────────────────

    @classmethod
    def query(cls) -> QueryBuilder:
        if not cls.table:
            raise ValueError(f"{cls.__name__} ক্লাসে 'table' সেট করা নেই")
        return QueryBuilder(cls.table)

    @classmethod
    def all(cls):
        rows = cls.query().get()
        return [cls(row) for row in rows]

    @classmethod
    def find(cls, id_value):
        row = cls.query().where(cls.primary_key, id_value).first()
        return cls(row) if row else None

    @classmethod
    def find_by(cls, column, value):
        row = cls.query().where(column, value).first()
        return cls(row) if row else None

    @classmethod
    def where(cls, column, operator, value=None) -> QueryBuilder:
        return cls.query().where(column, operator, value)

    @classmethod
    def create(cls, data: dict):
        import time
        filtered = cls._filter_fillable(data)
        if cls.timestamps:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            filtered.setdefault("created_at", now)
            filtered.setdefault("updated_at", now)
        if hasattr(cls, "on_creating"):
            cls.on_creating(filtered)
        Event.fire(f"{cls.table}.creating", filtered)
        new_id = cls.query().insert(filtered)
        instance = cls({**filtered, cls.primary_key: new_id})
        if hasattr(cls, "on_created"):
            cls.on_created(instance)
        Event.fire(f"{cls.table}.created", instance)
        return instance

    def update(self, data: dict):
        import time
        filtered = self._filter_fillable(data)
        if self.timestamps:
            filtered["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self.__class__, "on_updating"):
            self.__class__.on_updating(self, filtered)
        Event.fire(f"{self.__class__.table}.updating", self, filtered)
        pk_value = self._attributes.get(self.primary_key)
        self.__class__.query().where(self.primary_key, pk_value).update(filtered)
        self._attributes.update(filtered)
        if hasattr(self.__class__, "on_updated"):
            self.__class__.on_updated(self)
        Event.fire(f"{self.__class__.table}.updated", self)
        return self

    def delete(self):
        if hasattr(self.__class__, "on_deleting"):
            self.__class__.on_deleting(self)
        Event.fire(f"{self.__class__.table}.deleting", self)
        pk_value = self._attributes.get(self.primary_key)
        result = self.__class__.query().where(self.primary_key, pk_value).delete()
        if hasattr(self.__class__, "on_deleted"):
            self.__class__.on_deleted(self)
        Event.fire(f"{self.__class__.table}.deleted", self)
        return result

    # ─────────────────────────── Eager Loading (N+1 সমাধান) ──────────────────

    @classmethod
    def with_(cls, *relation_names):
        """
        Eager loading — N+1 query সমস্যা সমাধান করে।
        প্রতিটি relation-এর জন্য একটি batch IN() query চালায়।

        ব্যবহার:
            users = User.with_("logs").get()
            users = User.with_("logs", "role").get()

        Model-এ eager_relations dict define করতে হবে:
            eager_relations = {
                "logs": {"type": "has_many", "model": ActivityLog, "foreign_key": "user_id"},
            }
        """
        return _EagerQueryProxy(cls, list(relation_names))

    def _set_relation(self, name: str, value):
        """Eager loaded relation সেট করা"""
        self._loaded_relations[name] = value

    # ─────────────────────────────────────── Relationships ──────────────────

    def has_many(self, related_class, foreign_key=None, local_key="id"):
        """
        One-to-Many Relationship।
        eager loaded হলে cache থেকে দেয়, নইলে QueryBuilder রিটার্ন করে।
        """
        rel_name = related_class.table
        if rel_name in self._loaded_relations:
            return self._loaded_relations[rel_name]
        fk = foreign_key or _default_fk(self.table)
        pk_val = self._attributes.get(local_key)
        return related_class.where(fk, pk_val)

    def belongs_to(self, related_class, foreign_key=None, owner_key="id"):
        """Inverse Relationship — সরাসরি related Model অথবা None রিটার্ন করে"""
        rel_name = related_class.table
        if rel_name in self._loaded_relations:
            return self._loaded_relations[rel_name]
        fk = foreign_key or _default_fk(related_class.table)
        fk_val = self._attributes.get(fk)
        if fk_val is None:
            return None
        return related_class.find_by(owner_key, fk_val)

    def has_one(self, related_class, foreign_key=None, local_key="id"):
        """One-to-One Relationship — একটি Model অথবা None রিটার্ন করে"""
        rel_name = related_class.table
        if rel_name in self._loaded_relations:
            return self._loaded_relations[rel_name]
        fk = foreign_key or _default_fk(self.table)
        pk_val = self._attributes.get(local_key)
        return related_class.where(fk, pk_val).first()

    # ─────────────────────────────────────── Internals ──────────────────────

    @classmethod
    def _filter_fillable(cls, data: dict) -> dict:
        """শুধু fillable কলামগুলো pass করে — mass-assignment protection"""
        if not cls.fillable:
            return {}
        return {k: v for k, v in data.items() if k in cls.fillable}


# ─────────────────────────── Module Helpers ───────────────────────────────

def _default_fk(table_name: str) -> str:
    """Table name থেকে default foreign key তৈরি করা: users → user_id"""
    base = table_name.rstrip("s") if table_name.endswith("s") else table_name
    return f"{base}_id"


# ─────────────────────────── Eager Query Proxy ────────────────────────────

class _EagerQueryProxy:
    """
    User.with_("posts").get() এই chain handle করে।
    .get() কল হলে main query চালায়, তারপর relations batch IN() query দিয়ে load করে।
    """

    def __init__(self, model_cls, relation_names: list):
        self._cls = model_cls
        self._relations = relation_names
        self._qb = model_cls.query()

    def where(self, *args, **kwargs):
        self._qb = self._qb.where(*args, **kwargs)
        return self

    def order_by(self, *args, **kwargs):
        self._qb = self._qb.order_by(*args, **kwargs)
        return self

    def limit(self, n):
        self._qb = self._qb.limit(n)
        return self

    def offset(self, n):
        self._qb = self._qb.offset(n)
        return self

    def get(self):
        """Main query চালায়, তারপর সব relations batch load করে"""
        rows = self._qb.get()
        instances = [self._cls(row) for row in rows]
        if not instances:
            return instances

        for rel_name in self._relations:
            self._load_relation(instances, rel_name)

        return instances

    def first(self):
        results = self.limit(1).get()
        return results[0] if results else None

    def _load_relation(self, instances: list, rel_name: str):
        """eager_relations dict থেকে relation definition নিয়ে batch load করে"""
        eager_map = getattr(self._cls, "eager_relations", {})
        rel_def = eager_map.get(rel_name)
        if not rel_def:
            return

        rel_type   = rel_def.get("type", "has_many")
        related_cls = rel_def["model"]
        fk         = rel_def.get("foreign_key")
        local_key  = rel_def.get("local_key", "id")
        owner_key  = rel_def.get("owner_key", "id")

        if rel_type == "has_many":
            self._eager_has_many(instances, rel_name, related_cls, fk, local_key)
        elif rel_type == "has_one":
            self._eager_has_one(instances, rel_name, related_cls, fk, local_key)
        elif rel_type == "belongs_to":
            self._eager_belongs_to(instances, rel_name, related_cls, fk, owner_key)

    def _eager_has_many(self, instances, rel_name, related_cls, fk, local_key):
        """hasMany batch: IN() query — O(1) instead of O(N)"""
        if fk is None:
            fk = _default_fk(self._cls.table)

        pk_values = list({
            inst._attributes.get(local_key)
            for inst in instances
            if inst._attributes.get(local_key) is not None
        })
        if not pk_values:
            for inst in instances:
                inst._set_relation(rel_name, [])
            return

        from core.database import Database
        ph = Database.placeholder()
        safe_fk = Database.quote_identifier(fk)
        safe_table = Database.quote_identifier(related_cls.table)

        related_rows = []
        chunk_size = 500
        for i in range(0, len(pk_values), chunk_size):
            chunk = pk_values[i:i+chunk_size]
            placeholders = ", ".join([ph] * len(chunk))
            sql = f"SELECT * FROM {safe_table} WHERE {safe_fk} IN ({placeholders})"
            cursor = Database.execute(sql, tuple(chunk))
            related_rows.extend(cursor.fetchall())

        grouped: dict = {}
        for row in related_rows:
            row = dict(row) if not isinstance(row, dict) else row
            key = row.get(fk)
            grouped.setdefault(key, []).append(related_cls(row))

        for inst in instances:
            pk_val = inst._attributes.get(local_key)
            inst._set_relation(rel_name, grouped.get(pk_val, []))

    def _eager_has_one(self, instances, rel_name, related_cls, fk, local_key):
        """hasOne batch: IN() query"""
        if fk is None:
            fk = _default_fk(self._cls.table)

        pk_values = list({
            inst._attributes.get(local_key)
            for inst in instances
            if inst._attributes.get(local_key) is not None
        })
        if not pk_values:
            for inst in instances:
                inst._set_relation(rel_name, None)
            return

        from core.database import Database
        ph = Database.placeholder()
        safe_fk = Database.quote_identifier(fk)
        safe_table = Database.quote_identifier(related_cls.table)

        related_rows = []
        chunk_size = 500
        for i in range(0, len(pk_values), chunk_size):
            chunk = pk_values[i:i+chunk_size]
            placeholders = ", ".join([ph] * len(chunk))
            sql = f"SELECT * FROM {safe_table} WHERE {safe_fk} IN ({placeholders})"
            cursor = Database.execute(sql, tuple(chunk))
            related_rows.extend(cursor.fetchall())

        grouped: dict = {}
        for row in related_rows:
            row = dict(row) if not isinstance(row, dict) else row
            key = row.get(fk)
            if key not in grouped:
                grouped[key] = related_cls(row)

        for inst in instances:
            pk_val = inst._attributes.get(local_key)
            inst._set_relation(rel_name, grouped.get(pk_val))

    def _eager_belongs_to(self, instances, rel_name, related_cls, fk, owner_key):
        """belongsTo batch: IN() query"""
        if fk is None:
            fk = _default_fk(related_cls.table)

        fk_values = list({
            inst._attributes.get(fk)
            for inst in instances
            if inst._attributes.get(fk) is not None
        })
        if not fk_values:
            for inst in instances:
                inst._set_relation(rel_name, None)
            return

        from core.database import Database
        ph = Database.placeholder()
        safe_ok = Database.quote_identifier(owner_key)
        safe_table = Database.quote_identifier(related_cls.table)

        related_rows = []
        chunk_size = 500
        for i in range(0, len(fk_values), chunk_size):
            chunk = fk_values[i:i+chunk_size]
            placeholders = ", ".join([ph] * len(chunk))
            sql = f"SELECT * FROM {safe_table} WHERE {safe_ok} IN ({placeholders})"
            cursor = Database.execute(sql, tuple(chunk))
            related_rows.extend(cursor.fetchall())

        keyed: dict = {}
        for row in related_rows:
            row = dict(row) if not isinstance(row, dict) else row
            keyed[row.get(owner_key)] = related_cls(row)

        for inst in instances:
            fk_val = inst._attributes.get(fk)
            inst._set_relation(rel_name, keyed.get(fk_val))
