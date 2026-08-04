"""
app/models/setting_model.py
============================
Setting মডেল - সিস্টেম সেটিংস কি-ভ্যালু জোড়া স্টোর করার জন্য।
"""

import json
from core.model import Model


class Setting(Model):
    table = "settings"
    fillable = ["key", "value"]

    # Cache locally to avoid multiple queries in single request
    _cache = {}

    @classmethod
    def get(cls, key: str, default=None):
        """ডাটাবেস থেকে একটি নির্দিষ্ট সেটিংস ভ্যালু রিট্রিভ করে"""
        if key in cls._cache:
            return cls._cache[key]

        row = cls.find_by("key", key)
        if row:
            val = row._attributes.get("value")
            # Try to parse JSON if it looks like a dictionary/list string
            if isinstance(val, str):
                try:
                    if (val.startswith("{") and val.endswith("}")) or (val.startswith("[") and val.endswith("]")):
                        val = json.loads(val)
                except Exception:
                    pass
            cls._cache[key] = val
            return val

        return default

    @classmethod
    def set(cls, key: str, value) -> bool:
        """ডাটাবেসে সেটিংস ভ্যালু আপডেট বা ইনসার্ট করে"""
        if isinstance(value, (dict, list)):
            db_value = json.dumps(value)
        else:
            db_value = str(value) if value is not None else ""

        # Update cache
        cls._cache[key] = value

        row = cls.find_by("key", key)
        if row:
            row.update({"value": db_value})
        else:
            cls.create({"key": key, "value": db_value})
        return True
