"""
app/models/permission_model.py
===============================
RBAC সিস্টেমের Permission মডেল।

টেবিল: permissions (id, name, display_name, group, created_at, updated_at)
নামকরণ convention: "resource.action" যেমন "users.delete", "posts.edit"
"""
from core.model import Model


class Permission(Model):
    table = "permissions"
    fillable = ["name", "display_name", "group"]

    @classmethod
    def seed_defaults(cls):
        """সব default permission তৈরি করে"""
        defaults = [
            # User management
            {"name": "users.view",   "display_name": "ব্যবহারকারী দেখা",   "group": "users"},
            {"name": "users.create", "display_name": "ব্যবহারকারী যোগ",    "group": "users"},
            {"name": "users.edit",   "display_name": "ব্যবহারকারী সম্পাদনা", "group": "users"},
            {"name": "users.delete", "display_name": "ব্যবহারকারী মুছে দেওয়া", "group": "users"},
            # Settings
            {"name": "settings.view", "display_name": "সেটিংস দেখা",    "group": "settings"},
            {"name": "settings.edit", "display_name": "সেটিংস পরিবর্তন", "group": "settings"},
            # Logs
            {"name": "logs.view",   "display_name": "লগ দেখা",    "group": "logs"},
            {"name": "logs.delete", "display_name": "লগ মুছে দেওয়া", "group": "logs"},
            # Jobs / Queue
            {"name": "jobs.view",   "display_name": "জব দেখা",   "group": "jobs"},
            {"name": "jobs.delete", "display_name": "জব মুছে দেওয়া", "group": "jobs"},
            # API Keys
            {"name": "api_keys.view",   "display_name": "API কী দেখা",    "group": "api_keys"},
            {"name": "api_keys.create", "display_name": "API কী তৈরি",    "group": "api_keys"},
            {"name": "api_keys.delete", "display_name": "API কী মুছে দেওয়া", "group": "api_keys"},
        ]
        for p in defaults:
            existing = cls.find_by("name", p["name"])
            if not existing:
                cls.create(p)
