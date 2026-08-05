"""
app/models/user_model.py
=========================
User মডেল - উদাহরণস্বরূপ auth সিস্টেমের জন্য।
"""

from core.model import Model
from core.security import Hash


class User(Model):
    table = "users"
    fillable = ["name", "email", "password", "role"]
    hidden = ["password"]  # to_dict() করলে পাসওয়ার্ড হ্যাশ কখনো বাইরে যাবে না

    @classmethod
    def create_with_password(cls, name, email, plain_password, role="user"):
        hashed = Hash.make(plain_password)
        return cls.create({
            "name": name,
            "email": email,
            "password": hashed,
            "role": role,
        })

    def check_password(self, plain_password) -> bool:
        return Hash.check(plain_password, self._attributes.get("password", ""))

    def get_role(self):
        """User-এর Role অবজেক্ট রিটার্ন করে"""
        from app.models.role_model import Role
        role_name = self._attributes.get("role", "user")
        return Role.find_by("name", role_name)

    def has_role(self, role_name: str) -> bool:
        """User নির্দিষ্ট role-এ আছে কিনা"""
        return self._attributes.get("role") == role_name

    def has_permission(self, permission_name: str) -> bool:
        """
        User-এর নির্দিষ্ট permission আছে কিনা।
        admin সব permission পায়, অন্যরা role অনুযায়ী।
        """
        if self._attributes.get("role") == "admin":
            return True  # admin সবকিছু করতে পারে
        role_obj = self.get_role()
        if not role_obj:
            return False
        return role_obj.has_permission(permission_name)


