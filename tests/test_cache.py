"""
tests/test_cache.py
====================
Cache সিস্টেমের unit tests।
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.cache import Cache


class CacheTest(PyFlowTestCase):

    def setUp(self):
        super().setUp()
        Cache.flush()  # প্রতিটি test-এর আগে cache পরিষ্কার করা

    def test_put_and_get(self):
        Cache.put("test_key", "hello_world", ttl=60)
        result = Cache.get("test_key")
        self.assertEqual(result, "hello_world")

    def test_get_default_when_missing(self):
        result = Cache.get("nonexistent_key", default="fallback")
        self.assertEqual(result, "fallback")

    def test_get_returns_none_when_missing_and_no_default(self):
        result = Cache.get("nonexistent_key")
        self.assertIsNone(result)

    def test_forget(self):
        Cache.put("forget_me", "value", ttl=60)
        Cache.forget("forget_me")
        result = Cache.get("forget_me")
        self.assertIsNone(result)

    def test_has(self):
        Cache.put("existing", 42, ttl=60)
        self.assertTrue(Cache.has("existing"))
        self.assertFalse(Cache.has("not_existing"))

    def test_remember_creates_when_missing(self):
        counter = [0]
        def compute():
            counter[0] += 1
            return "computed_value"

        result = Cache.remember("comp_key", 60, compute)
        self.assertEqual(result, "computed_value")
        self.assertEqual(counter[0], 1)

    def test_remember_uses_cache_on_second_call(self):
        counter = [0]
        def compute():
            counter[0] += 1
            return "computed_value"

        Cache.remember("comp_key2", 60, compute)
        Cache.remember("comp_key2", 60, compute)
        # compute() একবারই ডাকা উচিত
        self.assertEqual(counter[0], 1)

    def test_put_dict_value(self):
        Cache.put("dict_key", {"name": "PyFlow", "version": 2}, ttl=60)
        result = Cache.get("dict_key")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "PyFlow")

    def test_put_list_value(self):
        Cache.put("list_key", [1, 2, 3], ttl=60)
        result = Cache.get("list_key")
        self.assertEqual(result, [1, 2, 3])

    def test_increment(self):
        Cache.increment("counter", by=5)
        Cache.increment("counter", by=3)
        result = Cache.get("counter")
        self.assertEqual(result, 8)

    def test_pull_removes_after_read(self):
        Cache.put("pull_key", "value", ttl=60)
        result = Cache.pull("pull_key")
        self.assertEqual(result, "value")
        self.assertIsNone(Cache.get("pull_key"))

    def test_flush_clears_all(self):
        Cache.put("k1", "v1", ttl=60)
        Cache.put("k2", "v2", ttl=60)
        count = Cache.flush()
        self.assertGreaterEqual(count, 2)
        self.assertIsNone(Cache.get("k1"))
        self.assertIsNone(Cache.get("k2"))

    def test_ttl_expiry(self):
        Cache.put("exp_key", "expires", ttl=1)
        time.sleep(1.1)
        result = Cache.get("exp_key")
        self.assertIsNone(result, "Cache should have expired")

    def tearDown(self):
        Cache.flush()


if __name__ == "__main__":
    import unittest
    unittest.main()
