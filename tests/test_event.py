"""
tests/test_event.py
====================
Event dispatcher এবং Model lifecycle hooks-এর unit tests।
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.event import Event


class EventTest(PyFlowTestCase):

    def setUp(self):
        super().setUp()
        Event.flush()  # প্রতিটি test-এর আগে listeners clear করা

    def test_fire_calls_listener(self):
        called = []
        Event.listen("test.event", lambda payload: called.append(payload))
        Event.fire("test.event", {"key": "value"})
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0], {"key": "value"})

    def test_multiple_listeners_all_called(self):
        results = []
        Event.listen("multi.event", lambda p: results.append("listener1"))
        Event.listen("multi.event", lambda p: results.append("listener2"))
        Event.fire("multi.event", {})
        self.assertIn("listener1", results)
        self.assertIn("listener2", results)
        self.assertEqual(len(results), 2)

    def test_fire_unregistered_event_no_error(self):
        # কোনো listener না থাকলে error হবে না
        try:
            Event.fire("unregistered.event", {})
        except Exception as e:
            self.fail(f"Event.fire raised unexpected exception: {e}")

    def test_listen_with_multiple_fires(self):
        counter = [0]
        Event.listen("count.event", lambda p: counter.__setitem__(0, counter[0] + 1))
        Event.fire("count.event", {})
        Event.fire("count.event", {})
        Event.fire("count.event", {})
        self.assertEqual(counter[0], 3)

    def test_flush_removes_all_listeners(self):
        called = []
        Event.listen("flush.event", lambda p: called.append(1))
        Event.flush()
        Event.fire("flush.event", {})
        self.assertEqual(len(called), 0)

    def test_model_lifecycle_creating_hook(self):
        """Model.on_creating lifecycle hook test"""
        from app.models.user_model import User

        creation_data = []

        original = getattr(User, "on_creating", None)
        User.on_creating = classmethod(lambda cls, data: creation_data.append(dict(data)))

        try:
            User.create({
                "name": "Hook Test", "email": "hook@test.com",
                "password": "x", "role": "user"
            })
            self.assertGreater(len(creation_data), 0)
        finally:
            if original is not None:
                User.on_creating = original
            else:
                try:
                    delattr(User, "on_creating")
                except AttributeError:
                    pass

    def test_event_payload_passed_correctly(self):
        received = []
        Event.listen("payload.test", lambda p: received.append(p))
        Event.fire("payload.test", {"user_id": 42, "action": "login"})
        self.assertEqual(received[0]["user_id"], 42)
        self.assertEqual(received[0]["action"], "login")

    def test_different_events_dont_cross(self):
        result_a = []
        result_b = []
        Event.listen("event.a", lambda p: result_a.append(p))
        Event.listen("event.b", lambda p: result_b.append(p))
        Event.fire("event.a", "only_a")
        self.assertEqual(len(result_a), 1)
        self.assertEqual(len(result_b), 0)


if __name__ == "__main__":
    import unittest
    unittest.main()
