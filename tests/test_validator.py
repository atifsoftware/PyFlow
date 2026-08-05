"""
tests/test_validator.py
========================
Validator engine-এর unit tests।
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.validator import Validator


class ValidatorTest(PyFlowTestCase):

    def test_required_rule_fails_on_empty(self):
        v = Validator({"name": ""}, {"name": "required"})
        self.assertTrue(v.fails())
        self.assertIn("name", v.errors())

    def test_required_rule_passes(self):
        v = Validator({"name": "Alice"}, {"name": "required"})
        self.assertFalse(v.fails())

    def test_email_rule_fails_on_invalid(self):
        v = Validator({"email": "not-an-email"}, {"email": "email"})
        self.assertTrue(v.fails())

    def test_email_rule_passes(self):
        v = Validator({"email": "user@example.com"}, {"email": "email"})
        self.assertFalse(v.fails())

    def test_min_rule(self):
        v = Validator({"age": "5"}, {"age": "numeric|min:18"})
        self.assertTrue(v.fails())

    def test_max_rule(self):
        v = Validator({"age": "200"}, {"age": "numeric|max:120"})
        self.assertTrue(v.fails())

    def test_in_rule_passes(self):
        v = Validator({"role": "admin"}, {"role": "in:admin,user,moderator"})
        self.assertFalse(v.fails())

    def test_in_rule_fails(self):
        v = Validator({"role": "superadmin"}, {"role": "in:admin,user,moderator"})
        self.assertTrue(v.fails())

    def test_confirmed_rule_passes(self):
        data = {"password": "secret123", "password_confirmation": "secret123"}
        v = Validator(data, {"password": "confirmed"})
        self.assertFalse(v.fails())

    def test_confirmed_rule_fails(self):
        data = {"password": "secret123", "password_confirmation": "different"}
        v = Validator(data, {"password": "confirmed"})
        self.assertTrue(v.fails())

    def test_regex_rule_passes(self):
        v = Validator({"code": "ABC123"}, {"code": r"regex:^[A-Z]{3}\d{3}$"})
        self.assertFalse(v.fails())

    def test_regex_rule_fails(self):
        v = Validator({"code": "abc123"}, {"code": r"regex:^[A-Z]{3}\d{3}$"})
        self.assertTrue(v.fails())

    def test_url_rule_passes(self):
        v = Validator({"site": "https://example.com"}, {"site": "url"})
        self.assertFalse(v.fails())

    def test_url_rule_fails(self):
        v = Validator({"site": "not-a-url"}, {"site": "url"})
        self.assertTrue(v.fails())

    def test_date_rule_passes(self):
        v = Validator({"dob": "2000-01-15"}, {"dob": "date"})
        self.assertFalse(v.fails())

    def test_date_rule_fails(self):
        v = Validator({"dob": "not-a-date"}, {"dob": "date"})
        self.assertTrue(v.fails())

    def test_multiple_rules_stop_on_first_error(self):
        v = Validator({"age": ""}, {"age": "required|numeric|min:18"})
        errors = v.errors().get("age", [])
        # only 'required' error, not 'numeric' or 'min'
        self.assertEqual(len(errors), 1)
        self.assertIn("আবশ্যক", errors[0])

    def test_custom_error_messages(self):
        v = Validator(
            {"name": ""},
            {"name": "required"},
            {"name.required": "নাম দিতে হবে।"}
        )
        self.assertEqual(v.errors()["name"][0], "নাম দিতে হবে।")


if __name__ == "__main__":
    import unittest
    unittest.main()
