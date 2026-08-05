"""
tests/test_transaction.py
==========================
Atomic Transaction system-এর সম্পূর্ণ unit test suite।

Test coverage:
  ① Basic atomic commit
  ② Rollback on exception
  ③ Nested transaction via SAVEPOINT
  ④ @atomic decorator
  ⑤ on_commit hook fires after commit
  ⑥ on_rollback hook fires after rollback
  ⑦ on_commit hook NOT fired on rollback
  ⑧ Named savepoint — partial rollback
  ⑨ Double-entry balance enforcement pattern
  ⑩ Exception propagates (not suppressed)
  ⑪ Transaction level tracking
  ⑫ QueryBuilder auto-commit outside transaction
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.database import Database, atomic, TransactionError, _SavepointContext
from core.query_builder import QueryBuilder


# ─── Helper — direct DB row count ──────────────────────────────────────────

def _count(table, **where):
    qb = QueryBuilder(table)
    for col, val in where.items():
        qb = qb.where(col, val)
    return qb.count()

def _insert_user(name, email, role="user"):
    """Test user তৈরির helper"""
    import time
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    return QueryBuilder("users").insert({
        "name": name, "email": email,
        "password": "x", "role": role,
        "created_at": now, "updated_at": now,
    })


# ─── Tests ─────────────────────────────────────────────────────────────────

class TransactionTest(PyFlowTestCase):

    # ── ① Basic Atomic Commit ──────────────────────────────────────────────

    def test_basic_commit_saves_data(self):
        """Transaction-এ সব কাজ সফল হলে commit হওয়া উচিত"""
        with Database.transaction():
            uid = _insert_user("TxCommit", "txcommit@test.com")

        found = QueryBuilder("users").where("id", uid).first()
        self.assertIsNotNone(found)
        self.assertEqual(found["name"], "TxCommit")

    # ── ② Rollback on Exception ────────────────────────────────────────────

    def test_rollback_on_exception(self):
        """Exception হলে transaction rollback হওয়া উচিত — কোনো data save হবে না"""
        email = "tx_rollback@test.com"
        try:
            with Database.transaction():
                _insert_user("TxRollback", email)
                raise ValueError("ইচ্ছাকৃত error — rollback test")
        except ValueError:
            pass

        found = QueryBuilder("users").where("email", email).first()
        self.assertIsNone(found, "Rollback-এর পরে DB-তে data থাকা উচিত নয়")

    # ── ③ Exception Propagates (Not Suppressed) ────────────────────────────

    def test_exception_propagates_through_transaction(self):
        """Transaction __exit__ exception suppress করবে না"""
        raised = False
        try:
            with Database.transaction():
                raise RuntimeError("এই error caller পাবে")
        except RuntimeError:
            raised = True

        self.assertTrue(raised, "Exception transaction block থেকে propagate হওয়া উচিত")

    # ── ④ Transaction Level Tracking ──────────────────────────────────────

    def test_transaction_level_increments_and_decrements(self):
        """transaction_level() সঠিকভাবে বাড়া-কমা করছে কিনা"""
        self.assertEqual(Database.transaction_level(), 0)
        self.assertFalse(Database.in_transaction())

        with Database.transaction():
            self.assertEqual(Database.transaction_level(), 1)
            self.assertTrue(Database.in_transaction())

        self.assertEqual(Database.transaction_level(), 0)
        self.assertFalse(Database.in_transaction())

    # ── ⑤ Nested Transaction via SAVEPOINT ────────────────────────────────

    def test_nested_transaction_commit(self):
        """Nested transaction সফল হলে দুটোই commit হওয়া উচিত"""
        with Database.transaction():
            uid1 = _insert_user("Outer", "outer@tx.com")
            with Database.transaction():   # SAVEPOINT sp_2
                uid2 = _insert_user("Inner", "inner@tx.com")

        self.assertIsNotNone(QueryBuilder("users").where("id", uid1).first())
        self.assertIsNotNone(QueryBuilder("users").where("id", uid2).first())

    def test_nested_transaction_inner_rollback_outer_commits(self):
        """Inner transaction error হলে inner rollback, outer তবুও commit"""
        outer_email = "outer_ok@tx.com"
        inner_email = "inner_fail@tx.com"

        with Database.transaction():
            uid_outer = _insert_user("OuterOK", outer_email)
            try:
                with Database.transaction():   # SAVEPOINT sp_2
                    _insert_user("InnerFail", inner_email)
                    raise ValueError("Inner error — sp_2 rollback")
            except ValueError:
                pass  # inner rollback handled

        # Outer data থাকবে
        self.assertIsNotNone(
            QueryBuilder("users").where("email", outer_email).first(),
            "Outer transaction-এর data commit হওয়া উচিত"
        )
        # Inner data থাকবে না
        self.assertIsNone(
            QueryBuilder("users").where("email", inner_email).first(),
            "Inner transaction rollback-এর পরে data থাকা উচিত নয়"
        )

    # ── ⑥ @atomic Decorator ───────────────────────────────────────────────

    def test_atomic_decorator_commits_on_success(self):
        """@atomic decorator সফল function-এর data commit করবে"""
        @atomic
        def create_two_users(e1, e2):
            _insert_user("AtomicA", e1)
            _insert_user("AtomicB", e2)

        create_two_users("atomica@test.com", "atomicb@test.com")

        self.assertIsNotNone(QueryBuilder("users").where("email", "atomica@test.com").first())
        self.assertIsNotNone(QueryBuilder("users").where("email", "atomicb@test.com").first())

    def test_atomic_decorator_rollback_on_exception(self):
        """@atomic decorator exception-এ rollback করবে"""
        @atomic
        def failing_operation(email):
            _insert_user("AtomicFail", email)
            raise RuntimeError("atomic failure")

        try:
            failing_operation("atomicfail@test.com")
        except RuntimeError:
            pass

        self.assertIsNone(QueryBuilder("users").where("email", "atomicfail@test.com").first())

    def test_atomic_decorator_returns_value(self):
        """@atomic decorator function-এর return value সঠিকভাবে দেয়"""
        @atomic
        def get_something():
            return 42

        result = get_something()
        self.assertEqual(result, 42)

    # ── ⑦ on_commit Hook ──────────────────────────────────────────────────

    def test_on_commit_hook_fires_after_successful_commit(self):
        """on_commit callback commit-এর পরে চালানো উচিত"""
        called = []

        with Database.transaction():
            _insert_user("HookUser", "hookuser@test.com")
            Database.on_commit(lambda: called.append("committed"))

        self.assertIn("committed", called, "on_commit hook চালানো হয়নি")

    def test_on_commit_hook_not_fired_on_rollback(self):
        """Rollback হলে on_commit callback চালানো উচিত নয়"""
        called = []

        try:
            with Database.transaction():
                _insert_user("HookFail", "hookfail@test.com")
                Database.on_commit(lambda: called.append("committed"))
                raise ValueError("trigger rollback")
        except ValueError:
            pass

        self.assertNotIn("committed", called, "Rollback-এ on_commit hook চালানো উচিত নয়")

    def test_multiple_on_commit_hooks_all_fire(self):
        """একাধিক on_commit hook সবগুলো চালানো উচিত"""
        results = []

        with Database.transaction():
            Database.on_commit(lambda: results.append(1))
            Database.on_commit(lambda: results.append(2))
            Database.on_commit(lambda: results.append(3))

        self.assertEqual(results, [1, 2, 3])

    # ── ⑧ on_rollback Hook ────────────────────────────────────────────────

    def test_on_rollback_hook_fires_on_exception(self):
        """on_rollback callback rollback-এর পরে চালানো উচিত"""
        called = []

        try:
            with Database.transaction():
                Database.on_rollback(lambda: called.append("rolled_back"))
                raise ValueError("trigger rollback")
        except ValueError:
            pass

        self.assertIn("rolled_back", called, "on_rollback hook চালানো হয়নি")

    def test_on_rollback_hook_not_fired_on_commit(self):
        """Commit হলে on_rollback callback চালানো উচিত নয়"""
        called = []

        with Database.transaction():
            Database.on_rollback(lambda: called.append("rolled_back"))

        self.assertNotIn("rolled_back", called, "Commit-এ on_rollback hook চালানো উচিত নয়")

    # ── ⑨ Named Savepoint ─────────────────────────────────────────────────

    def test_named_savepoint_commits_on_success(self):
        """Named savepoint সফল হলে data থাকবে"""
        with Database.transaction():
            with Database.savepoint("test_sp"):
                uid = _insert_user("SavepointOK", "savepointok@test.com")

        self.assertIsNotNone(QueryBuilder("users").where("id", uid).first())

    def test_named_savepoint_rollback_keeps_outer(self):
        """Named savepoint rollback হলে শুধু ওই block-এর data মুছবে, outer data থাকবে"""
        outer_email = "sp_outer@test.com"
        inner_email = "sp_inner@test.com"

        with Database.transaction():
            uid_outer = _insert_user("SPOuter", outer_email)
            try:
                with Database.savepoint("partial"):
                    _insert_user("SPInner", inner_email)
                    raise ValueError("partial failure")
            except ValueError:
                pass  # savepoint rollback হয়েছে, transaction চলছে

        self.assertIsNotNone(
            QueryBuilder("users").where("email", outer_email).first(),
            "Outer data থাকা উচিত"
        )
        self.assertIsNone(
            QueryBuilder("users").where("email", inner_email).first(),
            "Savepoint-rollback data থাকা উচিত নয়"
        )

    def test_savepoint_requires_active_transaction(self):
        """Transaction ছাড়া savepoint ব্যবহার করলে TransactionError হবে"""
        with self.assertRaises(TransactionError):
            with Database.savepoint("orphan"):
                pass

    # ── ⑩ Double-Entry Pattern ────────────────────────────────────────────

    def test_double_entry_balanced_commits(self):
        """Balanced double-entry → দুটো entry-ই DB-তে থাকবে"""
        # posts টেবিল journal_lines হিসেবে ব্যবহার করছি (test table)
        import time
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        @atomic
        def post_balanced_entry(debit, credit):
            total_d = sum(e["debit"]  for e in [debit])
            total_c = sum(e["credit"] for e in [credit])
            if total_d != total_c:
                raise TransactionError(f"Unbalanced! D={total_d} C={total_c}")
            uid = _insert_user("Debit Entry",  f"debit_{now}@acc.com", role="debit")
            uid2 = _insert_user("Credit Entry", f"credit_{now}@acc.com", role="credit")
            return uid, uid2

        uid1, uid2 = post_balanced_entry(
            {"debit": 10000, "credit": 0},
            {"debit": 0,     "credit": 10000},
        )
        self.assertIsNotNone(QueryBuilder("users").where("id", uid1).first())
        self.assertIsNotNone(QueryBuilder("users").where("id", uid2).first())

    def test_double_entry_unbalanced_rollback(self):
        """Unbalanced double-entry → TransactionError + rollback"""
        import time
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        email = f"unbalanced_{now}@acc.com"

        @atomic
        def post_unbalanced_entry():
            total_d, total_c = 10000, 9000  # unbalanced!
            if total_d != total_c:
                raise TransactionError(f"Unbalanced! D={total_d} C={total_c}")
            _insert_user("ShouldNotExist", email)

        with self.assertRaises(TransactionError):
            post_unbalanced_entry()

        self.assertIsNone(QueryBuilder("users").where("email", email).first())

    # ── ⑪ QueryBuilder Auto-Commit Outside Transaction ────────────────────

    def test_querybuilder_insert_auto_commits_outside_transaction(self):
        """Transaction ছাড়া QueryBuilder.insert() auto-commit করে"""
        import time
        now  = time.strftime("%Y-%m-%d %H:%M:%S")
        email = f"autocommit_{now}@test.com"

        # Transaction ছাড়াই insert
        self.assertFalse(Database.in_transaction())
        uid = QueryBuilder("users").insert({
            "name": "AutoCommit", "email": email,
            "password": "x", "role": "user",
            "created_at": now, "updated_at": now,
        })

        # নতুন connection দিয়ে verify
        found = QueryBuilder("users").where("id", uid).first()
        self.assertIsNotNone(found, "Auto-commit ছাড়া data পাওয়া যাচ্ছে না")

    def test_querybuilder_inside_transaction_no_premature_commit(self):
        """Transaction-এর ভেতরে QueryBuilder.insert() premature commit করবে না"""
        email = f"notcommitted@test.com"

        # Transaction শুরু কিন্তু exception দিয়ে rollback
        try:
            with Database.transaction():
                _insert_user("NotCommitted", email)
                self.assertTrue(Database.in_transaction())
                raise ValueError("force rollback")
        except ValueError:
            pass

        self.assertIsNone(
            QueryBuilder("users").where("email", email).first(),
            "Rollback-এর পরে data থাকা উচিত নয়"
        )


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
