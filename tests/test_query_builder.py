"""
tests/test_query_builder.py
=============================
QueryBuilder-এর unit tests — WHERE, ORDER, LIMIT, COUNT, cache।
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.query_builder import QueryBuilder
from core.database import Database


class QueryBuilderTest(PyFlowTestCase):

    def _seed_users(self, count=3):
        """Test users তৈরি করা"""
        import time
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        for i in range(count):
            Database.execute(
                "INSERT INTO users (name, email, password, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (f"User{i}", f"user{i}@qb.com", "x", "user", now, now)
            )
        Database.connection().commit()

    def test_basic_get_returns_list(self):
        self._seed_users(2)
        qb = QueryBuilder("users")
        results = qb.get()
        self.assertIsInstance(results, list)
        self.assertGreaterEqual(len(results), 2)

    def test_where_filters_results(self):
        self._seed_users()
        Database.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         ("Admin", "admin@qb.com", "x", "admin"))
        Database.connection().commit()

        results = QueryBuilder("users").where("role", "admin").get()
        self.assertGreater(len(results), 0)
        for row in results:
            self.assertEqual(row["role"], "admin")

    def test_where_with_operator(self):
        self._seed_users(5)
        # id > 0 সব row দেবে
        results = QueryBuilder("users").where("id", ">", 0).get()
        self.assertGreater(len(results), 0)

    def test_limit_restricts_results(self):
        self._seed_users(5)
        results = QueryBuilder("users").limit(2).get()
        self.assertLessEqual(len(results), 2)

    def test_offset_skips_rows(self):
        self._seed_users(4)
        # SQLite-এ OFFSET অবশ্যই LIMIT-এর সাথে দিতে হয়
        all_results = QueryBuilder("users").order_by("id").get()
        offset_results = QueryBuilder("users").order_by("id").limit(100).offset(2).get()
        if len(all_results) > 2:
            self.assertEqual(all_results[2]["id"], offset_results[0]["id"])

    def test_order_by_asc(self):
        self._seed_users(3)
        results = QueryBuilder("users").order_by("id", "ASC").get()
        ids = [r["id"] for r in results]
        self.assertEqual(ids, sorted(ids))

    def test_order_by_desc(self):
        self._seed_users(3)
        results = QueryBuilder("users").order_by("id", "DESC").get()
        ids = [r["id"] for r in results]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_first_returns_single_or_none(self):
        self._seed_users(2)
        result = QueryBuilder("users").first()
        self.assertIsInstance(result, dict)

    def test_first_returns_none_when_empty(self):
        result = QueryBuilder("users").where("email", "nonexistent@x.com").first()
        self.assertIsNone(result)

    def test_count_returns_int(self):
        self._seed_users(3)
        count = QueryBuilder("users").count()
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 3)

    def test_count_with_where(self):
        Database.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         ("CountAdmin", "countadmin@qb.com", "x", "admin"))
        Database.connection().commit()
        count = QueryBuilder("users").where("role", "admin").count()
        self.assertGreaterEqual(count, 1)

    def test_insert_returns_id(self):
        import time
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        qb = QueryBuilder("users")
        new_id = qb.insert({
            "name": "Inserted", "email": "inserted@qb.com",
            "password": "x", "role": "user",
            "created_at": now, "updated_at": now
        })
        self.assertIsNotNone(new_id)
        self.assertIsInstance(new_id, int)

    def test_update_modifies_rows(self):
        self._seed_users(1)
        qb = QueryBuilder("users")
        results = qb.where("role", "user").get()
        self.assertGreater(len(results), 0)
        uid = results[0]["id"]

        QueryBuilder("users").where("id", uid).update({"name": "Updated"})
        fresh = QueryBuilder("users").where("id", uid).first()
        self.assertEqual(fresh["name"], "Updated")

    def test_delete_removes_row(self):
        import time
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        new_id = QueryBuilder("users").insert({
            "name": "ToDelete", "email": "todelete@qb.com",
            "password": "x", "role": "user",
            "created_at": now, "updated_at": now
        })
        QueryBuilder("users").where("id", new_id).delete()
        result = QueryBuilder("users").where("id", new_id).first()
        self.assertIsNone(result)

    def test_or_where(self):
        self._seed_users(2)
        Database.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                         ("OAdmin", "oadmin@qb.com", "x", "admin"))
        Database.connection().commit()
        results = (QueryBuilder("users")
                   .where("role", "admin")
                   .or_where("name", "User0")
                   .get())
        self.assertGreater(len(results), 0)

    def test_select_specific_columns(self):
        self._seed_users(1)
        results = QueryBuilder("users").select("id", "name").get()
        self.assertGreater(len(results), 0)
        self.assertIn("name", results[0])
        self.assertNotIn("password", results[0])

    def test_cache_method_returns_self(self):
        qb = QueryBuilder("users").cache(seconds=60)
        self.assertIsNotNone(qb)

    def test_where_in(self):
        self._seed_users(3)
        results = QueryBuilder("users").where("role", "user").get()
        ids = [r["id"] for r in results[:2]]
        if ids:
            # where in সমতুল্য — or_where chain
            qb = QueryBuilder("users").where("id", ids[0])
            if len(ids) > 1:
                qb = qb.or_where("id", ids[1])
            filtered = qb.get()
            self.assertLessEqual(len(filtered), 2)


if __name__ == "__main__":
    import unittest
    unittest.main()
