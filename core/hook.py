"""
core/hook.py
============
Hook System (WordPress style actions and filters with priorities).
"""

import threading
from core.logger import Logger

class Hook:
    _actions = {}
    _filters = {}
    _lock = threading.Lock()

    # ────────────────────────────────────────── Actions ──────────────────────
    @classmethod
    def add_action(cls, name: str, callback, priority: int = 10):
        """Action হুক রেজিস্টার করে (অগ্রাধিকার বা priority অনুযায়ী সাজানো)"""
        with cls._lock:
            cls._actions.setdefault(name, []).append((priority, callback))
            cls._actions[name].sort(key=lambda x: x[0])

    @classmethod
    def action(cls, name: str, *args, **kwargs):
        """Action হুক ফায়ার করে (সব রেজিস্টার্ড কলব্যাক ক্রমানুসারে রান করায়)"""
        callbacks = []
        with cls._lock:
            callbacks = list(cls._actions.get(name, []))
            
        for priority, callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                Logger.error(f"Error executing action hook '{name}': {e}")

    # ────────────────────────────────────────── Filters ──────────────────────
    @classmethod
    def add_filter(cls, name: str, callback, priority: int = 10):
        """Filter হুক রেজিস্টার করে (অগ্রাধিকার বা priority অনুযায়ী সাজানো)"""
        with cls._lock:
            cls._filters.setdefault(name, []).append((priority, callback))
            cls._filters[name].sort(key=lambda x: x[0])

    @classmethod
    def filter(cls, name: str, value, *args, **kwargs):
        """
        Filter হুক ফায়ার করে ডাটা ক্রমানুসারে মডিফাই করে রিটার্ন করে।
        কলব্যাকগুলো চেইন হিসেবে কাজ করে, অর্থাৎ একটির আউটপুট পরেরটির ইনপুট হিসেবে যায়।
        """
        callbacks = []
        with cls._lock:
            callbacks = list(cls._filters.get(name, []))

        current_value = value
        for priority, callback in callbacks:
            try:
                current_value = callback(current_value, *args, **kwargs)
            except Exception as e:
                Logger.error(f"Error executing filter hook '{name}': {e}")
                
        return current_value
