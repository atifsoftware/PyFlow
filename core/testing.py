"""
core/testing.py
================
PyFlow Unit Test Framework।
Python stdlib unittest-এর উপর ভিত্তি করে তৈরি।
In-memory SQLite database দিয়ে দ্রুত, isolated test চালায়।

ব্যবহার:
    from core.testing import PyFlowTestCase

    class UserModelTest(PyFlowTestCase):
        def test_user_creation(self):
            user = User.create({"name": "Test", "email": "t@t.com", "password": "x"})
            self.assertIsNotNone(user)
            self.assertEqual(user.name, "Test")

    class ValidatorTest(PyFlowTestCase):
        def test_required_rule(self):
            response = self.post("/register", data={})
            self.assert_status(response, 422)
"""

import unittest
import sys
import os

# Project root সেট করা
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class PyFlowTestCase(unittest.TestCase):
    """
    PyFlow Test Base Class। প্রতিটি test method-এর আগে-পরে
    in-memory SQLite database তৈরি ও মুছে দেওয়া হয়।
    """

    @classmethod
    def setUpClass(cls):
        """Test class-এ একবার Database init করা"""
        from core.database import Database
        cls._test_config = {
            "DB_DRIVER": "sqlite",
            "DB_NAME": ":memory:",
            "DB_POOL_SIZE": "1",
        }
        Database.init(cls._test_config)
        cls._run_test_migrations()

    @classmethod
    def tearDownClass(cls):
        """Test class শেষে Database বন্ধ করা"""
        from core.database import Database
        Database.close()

    @classmethod
    def _run_test_migrations(cls):
        """In-memory SQLite-তে basic tables তৈরি করা"""
        from core.database import Database
        conn = Database.connection()
        cursor = conn.cursor()

        tables_sql = [
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT,
                updated_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                created_at TEXT,
                updated_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                action TEXT,
                description TEXT,
                ip_address TEXT,
                created_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                queue TEXT NOT NULL,
                payload TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                reserved_at INTEGER,
                available_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT,
                created_at TEXT,
                updated_at TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                display_name TEXT,
                grp TEXT,
                created_at TEXT,
                updated_at TEXT
            )""",
        ]
        for sql in tables_sql:
            try:
                cursor.execute(sql)
            except Exception:
                pass
        conn.commit()

    def setUp(self):
        """প্রতিটি test-এর আগে data cleanup করা"""
        from core.database import Database
        conn = Database.connection()
        cursor = conn.cursor()
        # সব table থেকে data মুছে দেওয়া (না হলে tests একে অপরকে affect করে)
        for table in ["users", "settings", "activity_logs", "jobs", "roles", "permissions"]:
            try:
                cursor.execute(f"DELETE FROM {table}")
            except Exception:
                pass
        conn.commit()

        # Event listeners reset করা (test isolation)
        try:
            from core.event import Event
            Event.flush()
        except Exception:
            pass

    # ─── Custom Assertions ─────────────────────────────────────────────────

    def assert_status(self, response, expected_status: int):
        """HTTP Response-এর status code চেক করে"""
        actual = getattr(response, "status_code", None)
        self.assertEqual(
            actual, expected_status,
            f"Expected HTTP {expected_status}, got {actual}"
        )

    def assert_redirect(self, response, expected_url: str = None):
        """Response redirect কিনা চেক করে"""
        actual_status = getattr(response, "status_code", 0)
        self.assertIn(actual_status, (301, 302, 303, 307, 308),
                      f"Expected redirect, got HTTP {actual_status}")
        if expected_url:
            location = getattr(response, "headers", {}).get("Location", "")
            self.assertIn(expected_url, location,
                          f"Expected redirect to '{expected_url}', got '{location}'")

    def assert_json_response(self, response, key: str, value=None):
        """JSON response-এ নির্দিষ্ট key এবং value আছে কিনা চেক করে"""
        import json
        try:
            body = b"".join(response.wsgi_body())
            data = json.loads(body.decode("utf-8"))
        except Exception as exc:
            self.fail(f"Response JSON parse করা যায়নি: {exc}")

        self.assertIn(key, data, f"JSON response-এ '{key}' key পাওয়া যায়নি")
        if value is not None:
            self.assertEqual(data[key], value,
                             f"JSON key '{key}': expected {value!r}, got {data[key]!r}")
        return data

    def assert_in_db(self, table: str, conditions: dict):
        """Database-এ নির্দিষ্ট row আছে কিনা চেক করে"""
        from core.database import Database
        ph = Database.placeholder()
        where = " AND ".join(f"{k} = {ph}" for k in conditions)
        values = list(conditions.values())
        cursor = Database.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}", values)
        row = cursor.fetchone()
        row = dict(row) if not isinstance(row, dict) else row
        count = row.get("cnt", 0)
        self.assertGreater(count, 0,
                           f"DB table '{table}' থেকে {conditions} মেলানো row পাওয়া যায়নি")

    def assert_not_in_db(self, table: str, conditions: dict):
        """Database-এ নির্দিষ্ট row নেই কিনা চেক করে"""
        from core.database import Database
        ph = Database.placeholder()
        where = " AND ".join(f"{k} = {ph}" for k in conditions)
        values = list(conditions.values())
        cursor = Database.execute(f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}", values)
        row = cursor.fetchone()
        row = dict(row) if not isinstance(row, dict) else row
        count = row.get("cnt", 0)
        self.assertEqual(count, 0,
                         f"DB table '{table}'-এ {conditions} মেলানো row পাওয়া গেছে (থাকার কথা নয়)")
