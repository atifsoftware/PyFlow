"""
tests/test_session.py
======================
Unit tests for the File-based Session and cross-platform FileLock.
"""

import unittest
import os
import shutil
import time
import threading
from core.session import Session, FileLock


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.test_dir = "storage/test_sessions"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            try:
                shutil.rmtree(self.test_dir)
            except OSError:
                pass

    def test_basic_session_read_write(self):
        # 1. Create session
        sess = Session(storage_dir=self.test_dir)
        sess_id = sess.session_id
        sess.set("username", "rifat")
        sess.set("role", "admin")

        # 2. Reload session
        sess2 = Session(storage_dir=self.test_dir, session_id=sess_id)
        self.assertEqual(sess2.get("username"), "rifat")
        self.assertEqual(sess2.get("role"), "admin")

    def test_session_flash(self):
        sess = Session(storage_dir=self.test_dir)
        sess.flash("message", "Success!")

        # Reload
        sess2 = Session(storage_dir=self.test_dir, session_id=sess.session_id)
        self.assertEqual(sess2.get_flash("message"), "Success!")

        # Second reload - flash should be gone
        sess3 = Session(storage_dir=self.test_dir, session_id=sess.session_id)
        self.assertIsNone(sess3.get_flash("message"))

    def test_file_lock_mutual_exclusion(self):
        lock_path = os.path.join(self.test_dir, "test.lock")
        lock1 = FileLock(lock_path)
        lock2 = FileLock(lock_path, timeout=0.2)

        # Acquire lock 1
        self.assertTrue(lock1.acquire())

        # Try to acquire lock 2 (should fail because of timeout)
        self.assertFalse(lock2.acquire())

        # Release lock 1
        lock1.release()

        # Try to acquire lock 2 again (should succeed now)
        self.assertTrue(lock2.acquire())
        lock2.release()


if __name__ == "__main__":
    unittest.main()
