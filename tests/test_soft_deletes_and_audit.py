"""
tests/test_soft_deletes_and_audit.py
====================================
Unit tests for Soft Deletes, Dirty State Tracking, save(), and Audit Trail.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.database import Database
from core.model import Model
from core.audit import AuditTrail, AuditLog


class Product(Model):
    table = "test_products"
    fillable = ["name", "price", "stock", "deleted_at", "created_at", "updated_at"]
    soft_deletes = True
    audit_trail = True


class TestSoftDeletesAndAudit(PyFlowTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        conn = Database.connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                deleted_at TEXT NULL,
                created_at TEXT NULL,
                updated_at TEXT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auditable_type TEXT NOT NULL,
                auditable_id TEXT NOT NULL,
                event TEXT NOT NULL,
                old_values TEXT,
                new_values TEXT,
                user_id INTEGER NULL,
                ip_address TEXT,
                user_agent TEXT,
                url TEXT,
                created_at TEXT
            )
        """)
        conn.commit()

    def setUp(self):
        super().setUp()
        Database.connection().execute("DELETE FROM test_products")
        Database.connection().execute("DELETE FROM audit_logs")
        Database.connection().commit()
        AuditTrail.clear_context()

    def test_soft_delete_and_query_scopes(self):
        # Create 2 products
        p1 = Product.create({"name": "Laptop", "price": 1200.0, "stock": 10})
        p2 = Product.create({"name": "Mouse", "price": 25.0, "stock": 50})

        self.assertFalse(p1.trashed())
        self.assertFalse(p2.trashed())

        # All products should be returned
        all_active = Product.all()
        self.assertEqual(len(all_active), 2)

        # Soft delete p1
        p1.delete()
        self.assertTrue(p1.trashed())

        # Standard query / all() should only return active products (excluding p1)
        active_after = Product.all()
        self.assertEqual(len(active_after), 1)
        self.assertEqual(active_after[0].name, "Mouse")

        # with_trashed should return both
        with_t = Product.with_trashed().get()
        self.assertEqual(len(with_t), 2)

        # only_trashed should return only p1
        only_t = Product.only_trashed().get()
        self.assertEqual(len(only_t), 1)
        self.assertEqual(only_t[0]["name"], "Laptop")

        # Restore p1
        p1.restore()
        self.assertFalse(p1.trashed())

        restored_all = Product.all()
        self.assertEqual(len(restored_all), 2)

    def test_force_delete(self):
        p = Product.create({"name": "Keyboard", "price": 45.0, "stock": 20})
        p.force_delete()

        # Should not exist even in with_trashed
        all_records = Product.with_trashed().get()
        self.assertEqual(len(all_records), 0)

    def test_dirty_state_tracking_and_save(self):
        p = Product.create({"name": "Monitor", "price": 300.0, "stock": 15})

        self.assertFalse(p.is_dirty())
        self.assertFalse(p.is_dirty("price"))

        # Modify attribute
        p.price = 350.0
        self.assertTrue(p.is_dirty())
        self.assertTrue(p.is_dirty("price"))
        self.assertFalse(p.is_dirty("name"))
        self.assertEqual(p.get_original("price"), 300.0)
        self.assertEqual(p.get_dirty(), {"price": 350.0})

        # Save model
        p.save()
        self.assertFalse(p.is_dirty())

        # Verify persisted in database
        fresh = Product.find(p.id)
        self.assertEqual(fresh.price, 350.0)

    def test_audit_trail_captures_events(self):
        AuditTrail.set_context(user_id=42, ip_address="192.168.1.100", url="/admin/products")

        # Create
        prod = Product.create({"name": "Printer", "price": 200.0, "stock": 5})

        logs = prod.audit_logs()
        self.assertGreaterEqual(len(logs), 1)
        create_log = [l for l in logs if l.event == "created"][0]
        self.assertEqual(create_log.auditable_type, "Product")
        self.assertEqual(create_log.auditable_id, str(prod.id))
        self.assertEqual(create_log.user_id, 42)
        self.assertEqual(create_log.ip_address, "192.168.1.100")
        self.assertEqual(create_log.url, "/admin/products")

        # Update
        prod.stock = 8
        prod.save()

        logs = prod.audit_logs()
        update_log = [l for l in logs if l.event == "updated"][0]
        self.assertEqual(update_log.diff()["stock"], (5, 8))

        # Soft delete
        prod.delete()
        logs = prod.audit_logs()
        delete_log = [l for l in logs if l.event == "soft_deleted"][0]
        self.assertIsNotNone(delete_log)

        # Restore
        prod.restore()
        logs = prod.audit_logs()
        restore_log = [l for l in logs if l.event == "restored"][0]
        self.assertIsNotNone(restore_log)


if __name__ == "__main__":
    unittest.main()
