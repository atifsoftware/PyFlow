"""
tests/test_routing.py
======================
Router — route matching, named routes, prefix groups।
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.router import Router


def _dummy_handler(request, session):
    return None


class RouterTest(PyFlowTestCase):

    def _make_router(self):
        r = Router()
        r.get("/",           _dummy_handler, name="home")
        r.get("/about",      _dummy_handler, name="about")
        r.post("/login",     _dummy_handler, name="login")
        r.get("/users",      _dummy_handler, name="users.index")
        r.get("/users/{id:int}", _dummy_handler, name="users.show")
        r.delete("/users/{id:int}", _dummy_handler, name="users.destroy")
        r.get("/posts/{slug}", _dummy_handler, name="posts.show")
        return r

    def test_get_route_matches(self):
        r = self._make_router()
        route, params = r.resolve("GET", "/")
        self.assertIsNotNone(route)
        self.assertNotEqual(route, "METHOD_NOT_ALLOWED")

    def test_post_route_matches(self):
        r = self._make_router()
        route, params = r.resolve("POST", "/login")
        self.assertIsNotNone(route)
        self.assertNotEqual(route, "METHOD_NOT_ALLOWED")

    def test_unknown_route_returns_none(self):
        r = self._make_router()
        route, params = r.resolve("GET", "/nonexistent")
        self.assertIsNone(route)

    def test_method_not_allowed(self):
        r = self._make_router()
        from core.router import MethodNotAllowedError
        with self.assertRaises(MethodNotAllowedError):
            r.resolve("DELETE", "/about")

    def test_int_param_extracted(self):
        r = self._make_router()
        route, params = r.resolve("GET", "/users/42")
        self.assertIsNotNone(route)
        self.assertEqual(params.get("id"), 42)  # int not string

    def test_string_param_extracted(self):
        r = self._make_router()
        route, params = r.resolve("GET", "/posts/hello-world")
        self.assertIsNotNone(route)
        self.assertEqual(params.get("slug"), "hello-world")

    def test_delete_method_matches(self):
        r = self._make_router()
        route, params = r.resolve("DELETE", "/users/5")
        self.assertIsNotNone(route)
        self.assertEqual(params.get("id"), 5)

    def test_named_route_url(self):
        r = self._make_router()
        url = r.url_for("home")
        self.assertEqual(url, "/")

    def test_named_route_with_param(self):
        r = self._make_router()
        url = r.url_for("users.show", id=7)
        self.assertIn("7", url)

    def test_prefix_group(self):
        r = Router()
        with r.group(prefix="/api/v1"):
            r.get("/users", _dummy_handler, name="api.users")
        route, params = r.resolve("GET", "/api/v1/users")
        self.assertIsNotNone(route)

    def test_nested_prefix(self):
        r = Router()
        with r.group(prefix="/api"):
            with r.group(prefix="/v2"):
                r.get("/health", _dummy_handler, name="api.v2.health")
        route, _ = r.resolve("GET", "/api/v2/health")
        self.assertIsNotNone(route)

    def test_root_path_exact_match(self):
        r = self._make_router()
        route, params = r.resolve("GET", "/")
        self.assertIsNotNone(route)
        # /about-এ যাওয়া উচিত না
        route2, _ = r.resolve("GET", "/about")
        self.assertIsNotNone(route2)
        self.assertNotEqual(route, route2)


if __name__ == "__main__":
    import unittest
    unittest.main()
