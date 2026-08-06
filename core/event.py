"""
core/event.py
==============
Model Lifecycle Event ও Custom Event সিস্টেম।

ব্যবহার:
    # Listener রেজিস্ট্রেশন (app boot-এ একবার)
    Event.listen("user.created", lambda user: ActivityLog.log(...))

    # Custom Event fire করা
    Event.fire("user.created", user_instance)

    # Model lifecycle hooks (Model subclass-এ override করুন)
    class User(Model):
        @classmethod
        def on_created(cls, instance):
            ActivityLog.log(...)
"""

import logging
from typing import Callable, Any, List

logger = logging.getLogger("pyflow.event")


class Event:
    _listeners: dict[str, List[Callable]] = {}

    @classmethod
    def listen(cls, event_name: str, callback: Callable) -> None:
        """একটি event-এ listener যোগ করে। একই event-এ একাধিক listener হতে পারে।"""
        if event_name not in cls._listeners:
            cls._listeners[event_name] = []
        cls._listeners[event_name].append(callback)

    @classmethod
    def fire(cls, event_name: str, *args, **kwargs) -> list:
        """
        নির্দিষ্ট event-এর সব listener-কে call করে।
        সব listener-এর রিটার্ন ভ্যালুর list রিটার্ন করে।
        """
        results = []
        for callback in cls._listeners.get(event_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as exc:
                logger.error(f"Event '{event_name}' listener error: {exc}")
        return results

    @classmethod
    def has_listeners(cls, event_name: str) -> bool:
        return bool(cls._listeners.get(event_name))

    @classmethod
    def forget(cls, event_name: str) -> None:
        """নির্দিষ্ট event-এর সব listener সরিয়ে দেয়"""
        cls._listeners.pop(event_name, None)

    @classmethod
    def flush(cls) -> None:
        """সব event listener সরিয়ে দেয় (testing-এর জন্য)"""
        cls._listeners.clear()
