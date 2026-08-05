"""
tests/test_model.py
====================
Model base class-এর unit tests।
CRUD, fillable protection, timestamps, relations।
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.model import Model, _default_fk


# ─── Test Model ──────────────────────────────────────────────────────────────

class Post(Model):
    table = "posts"
    fillable = ["user_id", "title", "body"]
    timestamps = True


class ProtectedModel(Model):
    table = "users"
    fillable = ["name", "email", "password", "role"]


class ModelTest(PyFlowTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # posts টেবিল তৈরি করা
        from core.database import Database
        Database.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL,
                body TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        Database.connection().commit()

    def test_create_returns_instance(self):
        user = ProtectedModel.create({
            "name": "Test User", "email": "test@model.com",
            "password": "hashed", "role": "user"
        })
        self.assertIsNotNone(user)
        self.assertIsInstance(user, ProtectedModel)
        self.assertEqual(user.name, "Test User")
        self.assertEqual(user.email, "test@model.com")

    def test_find_by_primary_key(self):
        user = ProtectedModel.create({
            "name": "FindMe", "email": "findme@model.com",
            "password": "x", "role": "user"
        })
        found = ProtectedModel.find(user.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.email, "findme@model.com")

    def test_find_returns_none_for_missing(self):
        result = ProtectedModel.find(999999)
        self.assertIsNone(result)

    def test_find_by_column(self):
        ProtectedModel.create({
            "name": "ByEmail", "email": "byemail@model.com",
            "password": "x", "role": "user"
        })
        found = ProtectedModel.find_by("email", "byemail@model.com")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "ByEmail")

    def test_update_modifies_attributes(self):
        user = ProtectedModel.create({
            "name": "Before", "email": "before@model.com",
            "password": "x", "role": "user"
        })
        user.update({"name": "After"})
        self.assertEqual(user.name, "After")
        # DB থেকেও verify করা
        fresh = ProtectedModel.find(user.id)
        self.assertEqual(fresh.name, "After")

    def test_delete_removes_record(self):
        user = ProtectedModel.create({
            "name": "Delete Me", "email": "deleteme@model.com",
            "password": "x", "role": "user"
        })
        uid = user.id
        user.delete()
        self.assertIsNone(ProtectedModel.find(uid))

    def test_timestamps_are_set_on_create(self):
        user = ProtectedModel.create({
            "name": "Ts User", "email": "ts@model.com",
            "password": "x", "role": "user"
        })
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)

    def test_fillable_protects_non_fillable_fields(self):
        # fillable-তে নেই এমন field pass করলে সেটা DB-তে যাবে না
        user = ProtectedModel.create({
            "name": "Protected",
            "email": "prot@model.com",
            "password": "x",
            "role": "user",
            "admin_override": "HACKED",  # fillable-তে নেই
        })
        # admin_override DB-তে যায়নি তাই None হবে
        self.assertIsNone(user.admin_override)

    def test_to_dict_excludes_hidden(self):
        from app.models.user_model import User
        user = User.create({
            "name": "Hidden", "email": "hidden@model.com",
            "password": "secret_hash", "role": "user"
        })
        d = user.to_dict()
        self.assertNotIn("password", d)

    def test_all_returns_list(self):
        ProtectedModel.create({"name": "A1", "email": "a1@model.com", "password": "x", "role": "user"})
        ProtectedModel.create({"name": "A2", "email": "a2@model.com", "password": "x", "role": "user"})
        all_users = ProtectedModel.all()
        self.assertIsInstance(all_users, list)
        self.assertGreaterEqual(len(all_users), 2)

    def test_where_chaining(self):
        ProtectedModel.create({"name": "Active", "email": "active@model.com", "password": "x", "role": "admin"})
        admins = ProtectedModel.where("role", "admin").get()
        self.assertGreater(len(admins), 0)
        for row in admins:
            self.assertEqual(row.get("role") if isinstance(row, dict) else row, "admin")

    def test_default_fk_helper(self):
        self.assertEqual(_default_fk("users"), "user_id")
        self.assertEqual(_default_fk("posts"), "post_id")
        self.assertEqual(_default_fk("activity_logs"), "activity_log_id")

    def test_attribute_access_via_getattr(self):
        user = ProtectedModel.create({
            "name": "AttrTest", "email": "attr@model.com",
            "password": "x", "role": "user"
        })
        self.assertEqual(user.name, "AttrTest")
        self.assertIsNone(user.nonexistent_field)

    def test_eager_relations_loaded_on_instance(self):
        """_set_relation ও _loaded_relations চেক করা"""
        from app.models.user_model import User
        user = User.create({
            "name": "EagerTest", "email": "eager@model.com",
            "password": "x", "role": "user"
        })
        # manually set relation
        user._set_relation("logs", [{"action": "login"}])
        self.assertIn("logs", user._loaded_relations)
        self.assertEqual(user.logs[0]["action"], "login")


if __name__ == "__main__":
    import unittest
    unittest.main()
