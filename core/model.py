"""
core/model.py
==============
Active-Record স্টাইলের বেস Model। প্রতিটা app/models/*.py এই ক্লাস থেকে
ইনহেরিট করবে এবং `table` নাম সেট করবে। সব DB অ্যাক্সেস QueryBuilder-এর
মধ্য দিয়ে যায়, তাই bound parameter ছাড়া কোনো raw SQL string তৈরি হয় না।
"""

from core.query_builder import QueryBuilder


class Model:
    table = None
    primary_key = "id"
    fillable = []          # mass-assignment-এ কোন কলামগুলো allow করা হবে
    hidden = []             # to_dict()-এ কোন কলাম বাদ যাবে (যেমন password)
    timestamps = True       # created_at/updated_at অটো-ম্যানেজ করবে কিনা

    def __init__(self, attributes: dict = None):
        self._attributes = attributes or {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._attributes.get(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._attributes[name] = value

    def to_dict(self) -> dict:
        return {k: v for k, v in self._attributes.items() if k not in self.hidden}

    # ------------------------------------------------------------- query API
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
        new_id = cls.query().insert(filtered)
        return cls.find(new_id)

    def update(self, data: dict):
        import time
        filtered = self._filter_fillable(data)
        if self.timestamps:
            filtered["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        pk_value = self._attributes.get(self.primary_key)
        self.__class__.query().where(self.primary_key, pk_value).update(filtered)
        self._attributes.update(filtered)
        return self

    def delete(self):
        pk_value = self._attributes.get(self.primary_key)
        return self.__class__.query().where(self.primary_key, pk_value).delete()

    # --------------------------------------------------------- Relationships
    def has_many(self, related_class, foreign_key=None, local_key="id"):
        """
        One-to-Many Relationship (যেমন: user.sales())
        QueryBuilder রিটার্ন করে, যাতে চাইলে আরও চেইন করা যায়: user.sales().where('amount', '>', 100).get()
        """
        fk = foreign_key or f"{self.table[:-1] if self.table.endswith('s') else self.table}_id"
        pk_val = self._attributes.get(local_key)
        return related_class.where(fk, pk_val)

    def belongs_to(self, related_class, foreign_key=None, owner_key="id"):
        """
        Inverse Relationship (যেমন: sale.user())
        সরাসরি রিলেটেড মডেল অবজেক্ট রিটার্ন করে অথবা None
        """
        fk = foreign_key or f"{related_class.table[:-1] if related_class.table.endswith('s') else related_class.table}_id"
        fk_val = self._attributes.get(fk)
        if fk_val is None:
            return None
        return related_class.find_by(owner_key, fk_val)

    def has_one(self, related_class, foreign_key=None, local_key="id"):
        """
        One-to-One Relationship (যেমন: user.profile())
        সরাসরি একটি মডেল অবজেক্ট বা None রিটার্ন করে
        """
        fk = foreign_key or f"{self.table[:-1] if self.table.endswith('s') else self.table}_id"
        pk_val = self._attributes.get(local_key)
        return related_class.where(fk, pk_val).first()

    @classmethod
    def _filter_fillable(cls, data: dict) -> dict:
        """
        mass-assignment vulnerability ঠেকানোর জন্য - শুধু fillable লিস্টে থাকা
        কলামই DB-তে যাবে। খালি fillable = [] মানে সব ব্লক (ইচ্ছাকৃতভাবে করবেন
        নাহলে ভুলে সব কলাম fillable হয়ে যাবে না)।
        """
        if not cls.fillable:
            return dict(data)
        return {k: v for k, v in data.items() if k in cls.fillable}
