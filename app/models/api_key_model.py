"""
app/models/api_key_model.py
============================
FastAPI এপিআই অথেন্টিকেশনের জন্য API Key জেনারেট ও চেক করার মডেল।
"""

import hashlib
import secrets
import time
from core.model import Model


class ApiKey(Model):
    table = "api_keys"
    fillable = ["user_id", "name", "key", "last_used_at", "rate_limit"]

    # Rate limit tiers (requests per hour)
    TIER_FREE = 100
    TIER_PRO = 10000
    TIER_UNLIMITED = 0  # 0 = no limit

    @classmethod
    def generate(cls, user_id: int, name: str, rate_limit: int = None):
        """নতুন একটি API Key তৈরি করে এবং ডাটাবেসে সেভ করে। (প্লেইনটেক্সট কি, মডেল অবজেক্ট) রিটার্ন করে"""
        if rate_limit is None:
            rate_limit = cls.TIER_FREE
        token = "pm_sk_" + secrets.token_hex(24)  # pm_sk_ + 48 hex chars = 54 chars total
        hashed = hashlib.sha256(token.encode("utf-8")).hexdigest()

        key_instance = cls.create({"user_id": user_id, "name": name, "key": hashed, "rate_limit": rate_limit})
        return token, key_instance


    @classmethod
    def authenticate(cls, token: str):
        """টোকেন হ্যাশ করে ডাটাবেস থেকে মেলাবে। মিললে User অবজেক্ট রিটার্ন করবে, নতুবা None"""
        if not token or not token.startswith("pm_sk_"):
            return None

        hashed = hashlib.sha256(token.encode("utf-8")).hexdigest()
        api_key = cls.find_by("key", hashed)

        if api_key:
            # Update last_used_at timestamp
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            api_key.update({"last_used_at": now})

            # Fetch corresponding User model
            from app.models.user_model import User

            return User.find(api_key.user_id)

        return None
