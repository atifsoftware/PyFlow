"""
tests/test_hooks_events.py
===========================
Event এবং Hook সিস্টেমের ইউনিট টেস্ট।
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.event import Event
from core.hook import Hook


class EventsAndHooksTest(PyFlowTestCase):

    def setUp(self):
        super().setUp()
        # Reset global registries before each test
        Event._listeners = {}
        Hook._actions = {}
        Hook._filters = {}

    # ────────────────────────────────────────── Event Tests ──────────────────
    def test_event_firing_calls_all_listeners(self):
        fired_data = []

        def listener_one(data):
            fired_data.append(f"one:{data}")

        def listener_two(data):
            fired_data.append(f"two:{data}")

        # Listen
        Event.listen("UserCreated", listener_one)
        Event.listen("UserCreated", listener_two)

        # Fire
        Event.fire("UserCreated", "atif")

        self.assertEqual(len(fired_data), 2)
        self.assertIn("one:atif", fired_data)
        self.assertIn("two:atif", fired_data)

    # ────────────────────────────────────────── Action Tests ─────────────────
    def test_action_hooks_execute_in_priority_order(self):
        execution_order = []

        # callbacks with different priorities
        def low_priority():
            execution_order.append("low")

        def high_priority():
            execution_order.append("high")

        def default_priority():
            execution_order.append("default")

        # Add actions (lower priority runs first)
        Hook.add_action("before_render", low_priority, priority=30)
        Hook.add_action("before_render", high_priority, priority=5)
        Hook.add_action("before_render", default_priority, priority=10) # default is 10

        # Run action
        Hook.action("before_render")

        # Expect execution order: high (5) -> default (10) -> low (30)
        self.assertEqual(execution_order, ["high", "default", "low"])

    # ────────────────────────────────────────── Filter Tests ─────────────────
    def test_filter_hooks_chain_and_modify_values(self):
        # Filter: numbers formatting
        def add_vat(amount):
            return amount + 15

        def apply_discount(amount):
            return amount - 10

        # Add filters with order: apply discount (5) then add VAT (10)
        Hook.add_filter("calculate_total", apply_discount, priority=5)
        Hook.add_filter("calculate_total", add_vat, priority=10)

        # Original value: 100
        # Formula: (100 - 10) + 15 = 105
        final_val = Hook.filter("calculate_total", 100)
        self.assertEqual(final_val, 105)

    def test_filter_hooks_with_additional_arguments(self):
        def prepend_tax_class(text, tax_rate):
            return f"[{tax_rate}%] {text}"

        Hook.add_filter("format_tax_label", prepend_tax_class)

        result = Hook.filter("format_tax_label", "Standard Goods", tax_rate=15)
        self.assertEqual(result, "[15%] Standard Goods")


if __name__ == "__main__":
    import unittest
    unittest.main()
