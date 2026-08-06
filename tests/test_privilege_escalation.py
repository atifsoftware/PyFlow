"""
tests/test_privilege_escalation.py
==================================
Tests for Broken Access Control and Privilege Escalation prevention.
"""

import unittest
from core.response import Response
from core.middleware import admin_middleware, api_admin_middleware


class DummyRequest:
    def __init__(self, role="user"):
        self.user_role = role


class DummySession:
    def __init__(self, role="user"):
        self.data = {"role": role, "user_id": 1}

    def get(self, key, default=None):
        return self.data.get(key, default)


class PrivilegeEscalationTest(unittest.TestCase):
    def test_admin_middleware_allows_admin(self):
        session = DummySession(role="admin")
        request = DummyRequest()
        result = admin_middleware(request, session)
        self.assertIsNone(result, "Admin user should not be blocked")

    def test_admin_middleware_blocks_user(self):
        session = DummySession(role="user")
        request = DummyRequest()
        result = admin_middleware(request, session)
        self.assertIsNotNone(result, "Normal user must be blocked")
        self.assertEqual(result.status_code, 403)

    def test_api_admin_middleware_allows_admin(self):
        request = DummyRequest(role="admin")
        result = api_admin_middleware(request, None)
        self.assertIsNone(result, "API Admin should not be blocked")

    def test_api_admin_middleware_blocks_user(self):
        request = DummyRequest(role="user")
        result = api_admin_middleware(request, None)
        self.assertIsNotNone(result, "API normal user must be blocked")
        self.assertEqual(result.status_code, 403)


if __name__ == "__main__":
    unittest.main()
