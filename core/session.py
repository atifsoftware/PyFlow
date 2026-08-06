"""
core/session.py
================
সার্ভার-সাইড ফাইল-বেসড সেশন (production-এ চাইলে Redis-এ সহজে সুইচ করা যাবে,
ইন্টারফেস একই থাকবে)। সেশন আইডি সবসময় httponly+secure cookie-তে রাখা হয়,
এবং cryptographically random token দিয়ে তৈরি হয় (session hijacking ঠেকাতে)।

উন্নয়ন (v2):
  - বাগ ফিক্স: _created এখন একবারই সেট হয়; _last_active আলাদাভাবে ট্র্যাক হয়।
    আগে প্রতি save()-এ _created রিসেট হতো, তাই সেশন কখনো এক্সপায়ার হতো না।
  - পারফরম্যান্স: _dirty flag যোগ করা হয়েছে — ডেটা না বদলালে disk write হবে না।
"""

import os
import json
import secrets
import time
import logging

logger = logging.getLogger("pyflow")


class FileLock:
    """
    একটি সাধারণ ক্রস-প্লাটফর্ম ফাইল লকিং মেকানিজম।
    অ্যাটমিক ডিরেক্টরি তৈরির (os.mkdir) মাধ্যমে রেস কন্ডিশন প্রতিরোধ করে।
    """
    def __init__(self, lock_path: str, timeout: float = 2.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self.has_lock = False

    def acquire(self) -> bool:
        start = time.time()
        while time.time() - start < self.timeout:
            try:
                os.mkdir(self.lock_path)
                self.has_lock = True
                return True
            except OSError:
                time.sleep(0.05)
        return False

    def release(self) -> None:
        if self.has_lock:
            try:
                os.rmdir(self.lock_path)
            except OSError:
                pass
            self.has_lock = False


class Session:
    COOKIE_NAME = "PyFlow_session"
    LIFETIME_SECONDS = 2 * 60 * 60  # 2 ঘণ্টা
    IDLE_TIMEOUT_SECONDS = 30 * 60  # ৩০ মিনিট idle হলে expire

    def __init__(self, storage_dir="storage/sessions", session_id=None):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.session_id = session_id or self._generate_id()
        self.is_new = session_id is None
        self._dirty = False          # শুধু পরিবর্তন হলেই disk-এ লিখবে
        self._data = self._load()

    @staticmethod
    def _generate_id() -> str:
        return secrets.token_hex(32)

    def _path(self):
        # session_id হেক্স স্ট্রিং, তাই path traversal সম্ভব না, তাও ডাবল-চেক
        safe_id = "".join(c for c in self.session_id if c.isalnum())
        return os.path.join(self.storage_dir, f"sess_{safe_id}.json")

    def _load(self) -> dict:
        path = self._path()
        if not os.path.exists(path):
            return {}
        lock = FileLock(path + ".lock")
        if not lock.acquire():
            logger.warning("সেশন ফাইল লক অর্জন করা যায়নি (load): %s", path)
        try:
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            now = time.time()

            # ফিক্স: সর্বোচ্চ আয়ু চেক (absolute lifetime)
            created_at = payload.get("_created", 0)
            if now - created_at > self.LIFETIME_SECONDS:
                try:
                    os.remove(path)
                except OSError:
                    pass
                return {}

            # ফিক্স: idle timeout চেক (last_active থেকে হিসাব)
            last_active = payload.get("_last_active", created_at)
            if now - last_active > self.IDLE_TIMEOUT_SECONDS:
                try:
                    os.remove(path)
                except OSError:
                    pass
                return {}

            return payload.get("data", {})
        except (json.JSONDecodeError, OSError):
            return {}
        finally:
            lock.release()

    def save(self):
        """_dirty না হলে disk write এড়িয়ে যায় — I/O কমায়, এবং লক ব্যবহার করে রেস কন্ডিশন প্রতিরোধ করে।"""
        if not self._dirty:
            return
        path = self._path()
        lock = FileLock(path + ".lock")
        if not lock.acquire():
            logger.warning("সেশন ফাইল লক অর্জন করা যায়নি (save): %s", path)
        try:
            now = time.time()
            existing_created = None
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing_created = json.load(f).get("_created")
                except (json.JSONDecodeError, OSError):
                    pass

            payload = {
                "_created": existing_created or now,
                "_last_active": now,
                "data": self._data,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            self._dirty = False
        finally:
            lock.release()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        if self._data.get(key) != value:          # প্রকৃত পরিবর্তন হলেই dirty হবে
            self._data[key] = value
            self._dirty = True
            self.save()

    def has(self, key) -> bool:
        return key in self._data

    def forget(self, key):
        if key in self._data:
            self._data.pop(key, None)
            self._dirty = True
            self.save()

    def flash(self, key, value):
        """পরের রিকোয়েস্টেই শুধু পাওয়া যাবে (যেমন success message)"""
        flashes = self._data.setdefault("_flash", {})
        flashes[key] = value
        self._dirty = True
        self.save()

    def get_flash(self, key, default=None):
        flashes = self._data.get("_flash", {})
        if key in flashes:
            value = flashes.pop(key)
            self._dirty = True
            self.save()
            return value
        return default

    def all_flash(self) -> dict:
        """সব flash মেসেজ একবারে পড়ে মুছে ফেলে"""
        flashes = self._data.pop("_flash", {})
        if flashes:
            self._dirty = True
            self.save()
        return flashes

    def regenerate(self):
        """লগইনের পরে অবশ্যই কল করবেন - session fixation attack ঠেকানোর জন্য"""
        old_path = self._path()
        lock = FileLock(old_path + ".lock")
        if not lock.acquire():
            logger.warning("সেশন ফাইল লক অর্জন করা যায়নি (regenerate): %s", old_path)
        try:
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass
        finally:
            lock.release()

        self.session_id = self._generate_id()
        self._dirty = True
        self.save()

    def destroy(self):
        path = self._path()
        lock = FileLock(path + ".lock")
        if not lock.acquire():
            logger.warning("সেশন ফাইল লক অর্জন করা যায়নি (destroy): %s", path)
        try:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
            self._data = {}
            self._dirty = False
        finally:
            lock.release()

    def touch(self):
        """_last_active আপডেট করতে জোর করে save করে (long-running page-এর জন্য)"""
        self._dirty = True
        self.save()
