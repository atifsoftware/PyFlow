"""
tests/test_maintenance_mode.py
==============================
Unit tests for PyFlow Maintenance Mode (down / up) and Secret Bypass.
"""

import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.application import Application
from core.router import Router
from core.response import Response


class TestMaintenanceMode(PyFlowTestCase):

    def setUp(self):
        super().setUp()
        self.router = Router()
        self.router.get("/dashboard", lambda req, sess: Response("Welcome to Dashboard"))
        self.app = Application(self.router, {"APP_DEBUG": False})

        self.storage_framework = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "storage", "framework"
        )
        os.makedirs(self.storage_framework, exist_ok=True)
        self.down_file = os.path.join(self.storage_framework, "down.json")
        if os.path.exists(self.down_file):
            os.remove(self.down_file)

    def tearDown(self):
        super().tearDown()
        if os.path.exists(self.down_file):
            os.remove(self.down_file)

    def make_environ(self, path="/dashboard", query="", cookie="", accept="text/html"):
        return {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "HTTP_COOKIE": cookie,
            "HTTP_ACCEPT": accept,
            "wsgi.input": sys.modules["io"].BytesIO(b""),
        }

    def test_normal_operation_when_not_down(self):
        env = self.make_environ()
        resp = self.app._handle_request(env)
        self.assertEqual(resp.status_code, 200)

    def test_maintenance_mode_returns_503(self):
        with open(self.down_file, "w", encoding="utf-8") as f:
            json.dump({"secret": "admin_pass_123", "message": "Upgrading ERP database."}, f)

        # Normal user gets 503
        env = self.make_environ()
        resp = self.app._handle_request(env)
        self.assertEqual(resp.status_code, 503)
        body = resp.body.decode("utf-8") if isinstance(resp.body, bytes) else resp.body
        self.assertIn("Upgrading ERP database", body)

        # JSON client gets 503 JSON
        json_env = self.make_environ(accept="application/json")
        json_resp = self.app._handle_request(json_env)
        self.assertEqual(json_resp.status_code, 503)
        json_body = json.loads(json_resp.body.decode("utf-8") if isinstance(json_resp.body, bytes) else json_resp.body)
        self.assertTrue(json_body.get("maintenance"))

    def test_maintenance_mode_secret_bypass(self):
        with open(self.down_file, "w", encoding="utf-8") as f:
            json.dump({"secret": "admin_pass_123", "message": "Upgrading ERP database."}, f)

        # Admin with query secret bypasses 503
        bypass_env = self.make_environ(query="secret=admin_pass_123")
        resp = self.app._handle_request(bypass_env)
        self.assertEqual(resp.status_code, 200)

        # Admin with cookie bypasses 503
        cookie_env = self.make_environ(cookie="pyflow_maintenance=admin_pass_123")
        cookie_resp = self.app._handle_request(cookie_env)
        self.assertEqual(cookie_resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
