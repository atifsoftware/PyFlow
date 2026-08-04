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
