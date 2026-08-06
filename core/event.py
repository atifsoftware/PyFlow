"""
core/event.py
=============
Thread-safe Event Dispatcher (Laravel style) & Model Lifecycle Hook engine.
"""

import threading
import logging
from typing import Callable, List

logger = logging.getLogger("pyflow.event")


class Event:
    _listeners: dict[str, List[Callable]] = {}
    _lock = threading.Lock()

    @classmethod
    def listen(cls, event_name: str, callback: Callable) -> None:
        """একটি event-এ listener যোগ করে (Thread-safe)।"""
        with cls._lock:
            cls._listeners.setdefault(event_name, []).append(callback)

    @classmethod
    def fire(cls, event_name: str, *args, **kwargs) -> list:
        """
        নির্দিষ্ট event-এর সব listener-কে call করে (Thread-safe)।
        সব listener-এর রিটার্ন ভ্যালুর list রিটার্ন করে।
        """
        listeners = []
        with cls._lock:
            listeners = list(cls._listeners.get(event_name, []))

        results = []
        for callback in listeners:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as exc:
                logger.error(f"Event '{event_name}' listener error: {exc}")
        return results

    @classmethod
    def has_listeners(cls, event_name: str) -> bool:
        """কোনো নির্দিষ্ট ইভেন্টে লিসেনার রেজিস্টার্ড আছে কিনা তা চেক করে"""
        with cls._lock:
            return bool(cls._listeners.get(event_name))

    @classmethod
    def forget(cls, event_name: str) -> None:
        """নির্দিষ্ট event-এর সব listener সরিয়ে দেয়"""
        with cls._lock:
            cls._listeners.pop(event_name, None)

    @classmethod
    def flush(cls) -> None:
        """সব event listener সরিয়ে দেয় (testing-এর জন্য)"""
        with cls._lock:
            cls._listeners.clear()
