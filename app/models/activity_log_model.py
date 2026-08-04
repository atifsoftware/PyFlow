"""
app/models/activity_log_model.py
==================================
সিস্টেমের ব্যবহারকারীদের কার্যকলাপের রেকর্ড (Audit Trail) রাখার মডেল।
"""

import time
from core.model import Model


class ActivityLog(Model):
    table = "activity_logs"
    timestamps = False  # manual created_at
    fillable = ["user_id", "action", "description", "ip_address", "user_agent", "created_at"]

    @classmethod
    def log(cls, request, action: str, description: str = "", user_id=None):
        """স্বয়ংক্রিয়ভাবে রিকোয়েস্ট থেকে মেটাডেটা সংগ্রহ করে অ্যাক্টিভিটি লগ সংরক্ষণ করে"""
        ip = request.ip() if hasattr(request, "ip") else "0.0.0.0"
        user_agent = request.header("User-Agent", "Unknown") if hasattr(request, "header") else "Unknown"
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        return cls.create({
            "user_id": user_id,
            "action": action,
            "description": description,
            "ip_address": ip,
            "user_agent": user_agent[:255] if user_agent else "Unknown",
            "created_at": now
        })
