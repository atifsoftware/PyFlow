"""
app/models/role_model.py
=========================
RBAC সিস্টেমের Role মডেল।

টেবিল: roles (id, name, display_name, created_at, updated_at)
"""
from core.model import Model


class Role(Model):
    table = "roles"
    fillable = ["name", "display_name"]

    def permissions(self):
        """এই Role-এর সব Permission রিটার্ন করে"""
        from app.models.permission_model import Permission
        from core.database import Database
        conn = Database.connection()
        cursor = conn.cursor()
        placeholder = Database.placeholder()
        cursor.execute(
            f"SELECT p.* FROM permissions p "
            f"INNER JOIN role_permission rp ON p.id = rp.permission_id "
            f"WHERE rp.role_id = {placeholder}",
            (self.id,)
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            perm = Permission.__new__(Permission)
            perm._attributes = dict(row) if not isinstance(row, dict) else row
            result.append(perm)
        return result

    def has_permission(self, permission_name: str) -> bool:
        """এই Role-এ নির্দিষ্ট permission আছে কিনা"""
        for perm in self.permissions():
            if perm.name == permission_name:
                return True
        return False

    @classmethod
    def seed_defaults(cls):
        """Default role তৈরি করে (admin, moderator, user)"""
        defaults = [
            {"name": "admin", "display_name": "Administrator"},
            {"name": "moderator", "display_name": "Moderator"},
            {"name": "user", "display_name": "User"},
        ]
        for r in defaults:
            existing = cls.find_by("name", r["name"])
            if not existing:
                cls.create(r)
