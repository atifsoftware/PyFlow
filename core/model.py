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
    connection = None    # নির্দিষ্ট ডাটাবেজ কানেকশন নাম (যেমন 'mysql', 'pgsql', 'sqlite')
    primary_key = "id"
    fillable = []       # mass-assignment-এ কোন কলামগুলো allow করা হবে
    hidden = []          # to_dict()-এ কোন কলাম বাদ যাবে (যেমন password)
    timestamps = True    # created_at/updated_at অটো-ম্যানেজ করবে কিনা
    soft_deletes = False # Soft delete (deleted_at) সক্রিয় করবে কিনা
    deleted_at_column = "deleted_at" # Soft delete timestamp column
    audit_trail = False  # স্বয়ংক্রিয় অডিট লগিং সক্রিয় করবে কিনা
    audit_exclude = ["password", "remember_token"] # অডিটে বাদ দেওয়ার মতো সংবেদনশীল ফিল্ড
    eager_relations = {} # with_() এর জন্য relation definitions

    @classmethod
    def get_connection(cls):
        """মডেলের জন্য নির্দিষ্ট করা ডাটাবেজ কানেকশন রিটার্ন করে"""
        from core.database import Database
        return Database.connection(cls.connection) if cls.connection else Database.connection()

    def __init__(self, attributes: dict = None):
        self._attributes = dict(attributes) if attributes else {}
        self._original = dict(self._attributes)  # Dirty state tracking
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

    # ─────────────────────────────────────── State & Dirty Tracking ──────────

    def is_dirty(self, attribute: str = None) -> bool:
        """কোনো অ্যাট্রিবিউট বা মডেল পরিবর্তিত হয়েছে কিনা চেক করে"""
        if attribute:
            return self._attributes.get(attribute) != self._original.get(attribute)
        all_keys = set(self._attributes.keys()) | set(self._original.keys())
        return any(self._attributes.get(k) != self._original.get(k) for k in all_keys)

    def get_dirty(self) -> dict:
        """পরিবর্তিত ফিল্ডগুলোর নতুন ভ্যালুর ডিকশনারি রিটার্ন করে"""
        dirty = {}
        for k, v in self._attributes.items():
            if k not in self._original or v != self._original[k]:
                dirty[k] = v
        return dirty

    def get_original(self, attribute: str = None):
        """ডাটাবেজ থেকে লোড হওয়ার সময়ের আসল মান রিটার্ন করে"""
        if attribute:
            return self._original.get(attribute)
        return dict(self._original)

    def sync_original(self):
        """বর্তমান অ্যাট্রিবিউটগুলোকে মূল মান হিসেবে সিঙ্ক করে"""
        self._original = dict(self._attributes)
        return self

    # ─────────────────────────────────────── Query API ──────────────────────

    @classmethod
    def query(cls) -> QueryBuilder:
        if not cls.table:
            raise ValueError(f"{cls.__name__} ক্লাসে 'table' সেট করা নেই")
        builder = QueryBuilder(cls.table, connection=cls.get_connection())
        builder.set_model(cls)
        if cls.soft_deletes:
            builder.without_trashed(cls.deleted_at_column)
        return builder

    @classmethod
    def with_trashed(cls) -> QueryBuilder:
        """Soft-deleted সহ সব রেকর্ড নিয়ে আসে"""
        return cls.query().with_trashed()

    @classmethod
    def only_trashed(cls) -> QueryBuilder:
        """শুধুমাত্র soft-deleted রেকর্ড নিয়ে আসে"""
        return cls.query().only_trashed(cls.deleted_at_column)

    @classmethod
    def without_trashed(cls) -> QueryBuilder:
        """শুধুমাত্র সক্রিয় (নন-ডিলিটেড) রেকর্ড নিয়ে আসে"""
        return cls.query().without_trashed(cls.deleted_at_column)

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
        instance.sync_original()
        if hasattr(cls, "on_created"):
            cls.on_created(instance)
        Event.fire(f"{cls.table}.created", instance)
        if getattr(cls, "audit_trail", False):
            try:
                from core.audit import AuditTrail
                AuditTrail.log(
                    auditable=instance,
                    event="created",
                    old_values={},
                    new_values=instance.to_dict(),
                )
            except Exception:
                pass
        return instance

    def save(self):
        """
        Active Record save() — নতুন মডেল হলে insert করে, বিদ্যমান হলে শুধু dirty ফিল্ড update করে।
        """
        import time
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        pk_value = self._attributes.get(self.primary_key)

        if pk_value is not None:
            # Existing model update
            dirty = self.get_dirty()
            if not dirty:
                return self
            filtered = self._filter_fillable(dirty)
            if self.timestamps:
                filtered["updated_at"] = now
                self._attributes["updated_at"] = now
            if hasattr(self.__class__, "on_updating"):
                self.__class__.on_updating(self, filtered)
            Event.fire(f"{self.__class__.table}.updating", self, filtered)
            old_values = {k: self._original.get(k) for k in filtered if k in self._original}
            self.__class__.query().with_trashed().where(self.primary_key, pk_value).update(filtered)
            self._attributes.update(filtered)
            self.sync_original()
            if hasattr(self.__class__, "on_updated"):
                self.__class__.on_updated(self)
            Event.fire(f"{self.__class__.table}.updated", self)
            if getattr(self.__class__, "audit_trail", False):
                try:
                    from core.audit import AuditTrail
                    AuditTrail.log(
                        auditable=self,
                        event="updated",
                        old_values=old_values,
                        new_values=filtered,
                    )
                except Exception:
                    pass
            return self
        else:
            # New model insert
            filtered = self._filter_fillable(self._attributes)
            if self.timestamps:
                filtered.setdefault("created_at", now)
                filtered.setdefault("updated_at", now)
            if hasattr(self.__class__, "on_creating"):
                self.__class__.on_creating(filtered)
            Event.fire(f"{self.__class__.table}.creating", filtered)
            new_id = self.__class__.query().insert(filtered)
            self._attributes[self.primary_key] = new_id
            self._attributes.update(filtered)
            self.sync_original()
            if hasattr(self.__class__, "on_created"):
                self.__class__.on_created(self)
            Event.fire(f"{self.__class__.table}.created", self)
            if getattr(self.__class__, "audit_trail", False):
                try:
                    from core.audit import AuditTrail
                    AuditTrail.log(
                        auditable=self,
                        event="created",
                        old_values={},
                        new_values=self.to_dict(),
                    )
                except Exception:
                    pass
            return self

    def update(self, data: dict):
        import time
        filtered = self._filter_fillable(data)
        if self.timestamps:
            filtered["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self.__class__, "on_updating"):
            self.__class__.on_updating(self, filtered)
        Event.fire(f"{self.__class__.table}.updating", self, filtered)
        pk_value = self._attributes.get(self.primary_key)
        old_values = {k: self._attributes.get(k) for k in filtered}
        self.__class__.query().with_trashed().where(self.primary_key, pk_value).update(filtered)
        self._attributes.update(filtered)
        self.sync_original()
        if hasattr(self.__class__, "on_updated"):
            self.__class__.on_updated(self)
        Event.fire(f"{self.__class__.table}.updated", self)
        if getattr(self.__class__, "audit_trail", False):
            try:
                from core.audit import AuditTrail
                AuditTrail.log(
                    auditable=self,
                    event="updated",
                    old_values=old_values,
                    new_values=filtered,
                )
            except Exception:
                pass
        return self

    def delete(self, force: bool = False):
        """
        রেকর্ড ডিলিট করে। soft_deletes সক্রিয় থাকলে এবং force=False হলে soft delete করে।
        """
        if hasattr(self.__class__, "on_deleting"):
            self.__class__.on_deleting(self)
        Event.fire(f"{self.__class__.table}.deleting", self)
        pk_value = self._attributes.get(self.primary_key)

        if self.soft_deletes and not force:
            import time
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            old_deleted_at = self._attributes.get(self.deleted_at_column)
            self._attributes[self.deleted_at_column] = now
            update_data = {self.deleted_at_column: now}
            if self.timestamps:
                now_up = time.strftime("%Y-%m-%d %H:%M:%S")
                update_data["updated_at"] = now_up
                self._attributes["updated_at"] = now_up
            result = self.__class__.query().with_trashed().where(self.primary_key, pk_value).update(update_data)
            self.sync_original()
            if hasattr(self.__class__, "on_soft_deleted"):
                self.__class__.on_soft_deleted(self)
            Event.fire(f"{self.__class__.table}.soft_deleted", self)
            Event.fire(f"{self.__class__.table}.deleted", self)
            if getattr(self.__class__, "audit_trail", False):
                try:
                    from core.audit import AuditTrail
                    AuditTrail.log(
                        auditable=self,
                        event="soft_deleted",
                        old_values={self.deleted_at_column: old_deleted_at},
                        new_values={self.deleted_at_column: now},
                    )
                except Exception:
                    pass
            return result
        else:
            old_attrs = dict(self._attributes)
            result = self.__class__.query().with_trashed().where(self.primary_key, pk_value).delete()
            if hasattr(self.__class__, "on_deleted"):
                self.__class__.on_deleted(self)
            Event.fire(f"{self.__class__.table}.deleted", self)
            if getattr(self.__class__, "audit_trail", False):
                try:
                    from core.audit import AuditTrail
                    AuditTrail.log(
                        auditable=self,
                        event="force_deleted" if self.soft_deletes else "deleted",
                        old_values=old_attrs,
                        new_values={},
                    )
                except Exception:
                    pass
            return result

    def force_delete(self):
        """সরাসরি ডাটাবেজ থেকে ফিজিক্যালি ডিলিট করে"""
        return self.delete(force=True)

    def restore(self):
        """Soft-deleted রেকর্ড রিস্টোর করে (deleted_at = None)"""
        if not self.soft_deletes:
            raise ValueError(f"{self.__class__.__name__} ক্লাসে soft_deletes সক্রিয় নেই")
        if hasattr(self.__class__, "on_restoring"):
            self.__class__.on_restoring(self)
        Event.fire(f"{self.__class__.table}.restoring", self)
        pk_value = self._attributes.get(self.primary_key)
        old_deleted_at = self._attributes.get(self.deleted_at_column)
        self._attributes[self.deleted_at_column] = None
        update_data = {self.deleted_at_column: None}
        if self.timestamps:
            import time
            now_up = time.strftime("%Y-%m-%d %H:%M:%S")
            update_data["updated_at"] = now_up
            self._attributes["updated_at"] = now_up
        result = self.__class__.query().with_trashed().where(self.primary_key, pk_value).update(update_data)
        self.sync_original()
        if hasattr(self.__class__, "on_restored"):
            self.__class__.on_restored(self)
        Event.fire(f"{self.__class__.table}.restored", self)
        if getattr(self.__class__, "audit_trail", False):
            try:
                from core.audit import AuditTrail
                AuditTrail.log(
                    auditable=self,
                    event="restored",
                    old_values={self.deleted_at_column: old_deleted_at},
                    new_values={self.deleted_at_column: None},
                )
            except Exception:
                pass
        return result

    def trashed(self) -> bool:
        """রেকর্ডটি soft-deleted কিনা চেক করে"""
        return bool(self._attributes.get(self.deleted_at_column))

    def audit_logs(self):
        """এই রেকর্ডের সমস্ত অডিট হিস্টোরি রিটার্ন করে"""
        try:
            from core.audit import AuditLog
            pk_val = str(self._attributes.get(self.primary_key, ""))
            rows = AuditLog.where("auditable_type", self.__class__.__name__).where("auditable_id", pk_val).order_by("id", "DESC").get()
            return [AuditLog(r) if isinstance(r, dict) else r for r in rows]
        except Exception:
            return []

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
        return EagerQueryProxy(cls, list(relation_names))

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
        """শুধু fillable কলামগুলো pass করে — mass-assignment protection।
        FIX: fillable সেট না থাকলে আগে নীরবে {} রিটার্ন করতো, যা empty row insert করতো।
             এখন: fillable = [] হলে সব data pass করে (open model), কিন্তু warning লগ করে।
             নিরাপদ থাকতে চাইলে Model subclass-এ fillable সেট করুন।
        """
        if not cls.fillable:
            import logging
            logging.getLogger("pyflow").warning(
                f"[MODEL] '{cls.__name__}' ক্লাসে 'fillable' সেট করা নেই — সব কলাম pass হচ্ছে। "
                "Mass-assignment protection নিষ্ক্রিয়। নিরাপত্তার জন্য fillable তালিকা সেট করুন।"
            )
            return dict(data)  # সব data pass করা (open model behavior)
        return {k: v for k, v in data.items() if k in cls.fillable}


# ─────────────────────────── Module Helpers ───────────────────────────────

def _default_fk(table_name: str) -> str:
    """Table name থেকে default foreign key তৈরি করা: users → user_id
    FIX: আগের rstrip('s') logic ভুল ছিল — 'status' → 'statu_id', 'news' → 'new_id'।
         এখন শুধু সাধারণ plural শেষ (-ies → y, -es → নিয়ম, -s → বাদ) handle করা হয়।
    """
    t = table_name.lower()
    # অনিয়মিত শব্দ whitelist
    _irregular = {
        "people": "person", "men": "man", "women": "woman",
        "children": "child", "teeth": "tooth", "feet": "foot",
    }
    if t in _irregular:
        return f"{_irregular[t]}_id"

    # সাধারণ pluralization বিপরীত করা
    if t.endswith("ies") and len(t) > 3:
        base = t[:-3] + "y"    # categories → category
    elif t.endswith("ses") or t.endswith("xes") or t.endswith("zes") or t.endswith("ches") or t.endswith("shes"):
        base = t[:-2]           # boxes → box, classes → class
    elif t.endswith("s") and not t.endswith("ss") and len(t) > 2:
        base = t[:-1]           # users → user (কিন্তু 'status', 'address' → যেমন আছে)
    else:
        base = t               # 'news', 'status' → নিজেই foreign key base

    return f"{base}_id"


# ─────────────────────────── Eager Query Proxy ────────────────────────────

class EagerQueryProxy:
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

    def with_trashed(self):
        self._qb = self._qb.with_trashed()
        return self

    def only_trashed(self, *args, **kwargs):
        self._qb = self._qb.only_trashed(*args, **kwargs)
        return self

    def without_trashed(self, *args, **kwargs):
        self._qb = self._qb.without_trashed(*args, **kwargs)
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
