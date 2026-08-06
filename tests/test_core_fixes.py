"""
tests/test_core_fixes.py
=========================
Core fixes and security enhancements unit tests.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.query_builder import QueryBuilder, _safe_identifier
from core.database import Database, QueryError
from app.models.user_model import User


class CoreFixesTest(PyFlowTestCase):

    def test_alias_sql_injection_is_blocked(self):
        # SQL injection attempts via column select alias
        injection_columns = [
            "id FROM users; DROP TABLE users;-- ",
            "id AS user_id; DROP TABLE users;-- ",
            "id user_id; DROP TABLE users;-- ",
            "name AS username; UNION SELECT password FROM users;-- "
        ]
        
        for col in injection_columns:
            with self.assertRaises(QueryError, msg=f"Should reject injection attempt: {col}"):
                _safe_identifier(col)

    def test_valid_aliases_are_quoted_correctly(self):
        # Valid column and table aliases should be properly validated and driver-quoted
        valid_cases = [
            ("id AS user_id", '"id" AS "user_id"'),
            ("name user_name", '"name" "user_name"'),
            ("users.name AS username", '"users"."name" AS "username"'),
            ("role", '"role"')
        ]
        
        for raw, expected in valid_cases:
            quoted = _safe_identifier(raw)
            self.assertEqual(quoted, expected)

    def test_paginate_does_not_mutate_state(self):
        qb = User.where("role", "user")
        
        # Verify limit and offset are initially None
        self.assertIsNone(qb._limit)
        self.assertIsNone(qb._offset)
        
        # Paginate
        page_result = qb.paginate(1, per_page=10)
        
        # The pagination result should have cloned constraints
        self.assertEqual(page_result._limit, 10)
        self.assertEqual(page_result._offset, 0)
        
        # The original query builder instance MUST remain unchanged
        self.assertIsNone(qb._limit)
        self.assertIsNone(qb._offset)

    def test_empty_update_returns_zero(self):
        # Empty updates should return 0 directly without SQL syntax errors
        qb = User.where("id", 1)
        res = qb.update({})
        self.assertEqual(res, 0)
        
        res_all = qb.update_all({})
        self.assertEqual(res_all, 0)


if __name__ == "__main__":
    import unittest
    unittest.main()
