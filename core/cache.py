"""
core/cache.py
==============
Multi-driver Cache সিস্টেম। CACHE_DRIVER config দিয়ে driver বেছে নেওয়া যায়।

Supported Drivers:
    file    — File-based JSON cache (default, কোনো dependency নেই)
    memory  — In-memory dict cache (testing-এর জন্য আদর্শ)
    redis   — Redis cache (pip install redis প্রয়োজন)

Config (.env):
    CACHE_DRIVER=file      # default
    CACHE_DRIVER=memory
    CACHE_DRIVER=redis
    REDIS_HOST=127.0.0.1
    REDIS_PORT=6379
    REDIS_DB=0

API (driver-agnostic):
    Cache.put("key", value, ttl=3600)
    Cache.get("key", default=None)
    Cache.remember("key", 300, callback)
    Cache.forget("key")
    Cache.flush()
    Cache.has("key")
    Cache.pull("key")
    Cache.increment("key")
    Cache.decrement("key")
"""

import os
import json
import time
import hashlib


# ───────────────────────────────── Abstract Base ──────────────────────────────

class _CacheDriver:
    """সব cache driver-এর base interface"""

    def put(self, key: str, value, ttl: int = 3600) -> bool:
        raise NotImplementedError

    def get(self, key: str, default=None):
        raise NotImplementedError

    def has(self, key: str) -> bool:
        raise NotImplementedError

    def forget(self, key: str) -> bool:
        raise NotImplementedError

    def flush(self) -> int:
        raise NotImplementedError

    def increment(self, key: str, by: int = 1) -> int:
        current = self.get(key, 0)
        new_val = int(current) + by
        self.put(key, new_val, ttl=0)
        return new_val

    def decrement(self, key: str, by: int = 1) -> int:
        return self.increment(key, -by)

    def pull(self, key: str, default=None):
        value = self.get(key, default)
        self.forget(key)
        return value

    def remember(self, key: str, ttl: int, callback):
        value = self.get(key)
        if value is None:
            value = callback()
            if value is not None:
                self.put(key, value, ttl)
        return value


# ───────────────────────────────── File Driver ────────────────────────────────

class _FileDriver(_CacheDriver):
    """File-based JSON cache — stdlib only, কোনো external dependency নেই"""

    def __init__(self, cache_dir: str = "storage/cache"):
        self.cache_dir = cache_dir

    def _ensure_dir(self):
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        safe = hashlib.md5(key.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{safe}.json")

    def put(self, key: str, value, ttl: int = 3600) -> bool:
        self._ensure_dir()
        expires_at = int(time.time()) + ttl if ttl > 0 else 0
        payload = {"key": key, "value": value,
                   "expires_at": expires_at, "created_at": int(time.time())}
        try:
            with open(self._path(key), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get(self, key: str, default=None):
        path = self._path(key)
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            expires_at = payload.get("expires_at", 0)
            if expires_at > 0 and time.time() > expires_at:
                os.remove(path)
                return default
            return payload.get("value", default)
        except Exception:
            return default

    def has(self, key: str) -> bool:
        sentinel = object()
        return self.get(key, sentinel) is not sentinel

    def forget(self, key: str) -> bool:
        try:
            path = self._path(key)
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception:
            return False

    def flush(self) -> int:
        self._ensure_dir()
        count = 0
        try:
            for fname in os.listdir(self.cache_dir):
                if fname.endswith(".json"):
                    os.remove(os.path.join(self.cache_dir, fname))
                    count += 1
        except Exception:
            pass
        return count

    def gc(self) -> int:
        """Expired entries পরিষ্কার করা"""
        self._ensure_dir()
        count = 0
        now = time.time()
        try:
            for fname in os.listdir(self.cache_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(self.cache_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                    expires_at = payload.get("expires_at", 0)
                    if expires_at > 0 and now > expires_at:
                        os.remove(fpath)
                        count += 1
                except Exception:
                    pass
        except Exception:
            pass
        return count


# ───────────────────────────────── Memory Driver ─────────────────────────────

class _MemoryDriver(_CacheDriver):
    """In-memory cache — testing-এর জন্য আদর্শ, process restart-এ মুছে যায়"""

    def __init__(self):
        self._store: dict = {}  # key → {"value": ..., "expires_at": ...}

    def put(self, key: str, value, ttl: int = 3600) -> bool:
        expires_at = time.time() + ttl if ttl > 0 else 0
        self._store[key] = {"value": value, "expires_at": expires_at}
        return True

    def get(self, key: str, default=None):
        entry = self._store.get(key)
        if not entry:
            return default
        expires_at = entry.get("expires_at", 0)
        if expires_at > 0 and time.time() > expires_at:
            del self._store[key]
            return default
        return entry["value"]

    def has(self, key: str) -> bool:
        sentinel = object()
        return self.get(key, sentinel) is not sentinel

    def forget(self, key: str) -> bool:
        self._store.pop(key, None)
        return True

    def flush(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count


# ───────────────────────────────── Redis Driver ───────────────────────────────

class _RedisDriver(_CacheDriver):
    """
    Redis-based cache।
    `pip install redis` প্রয়োজন। না থাকলে ImportError raise করে।
    """

    def __init__(self, host="127.0.0.1", port=6379, db=0, password=None, prefix="pyflow:"):
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis driver ব্যবহার করতে 'redis' package install করুন: pip install redis"
            )
        self._r = redis.Redis(host=host, port=port, db=db, password=password,
                              decode_responses=True)
        self._prefix = prefix

    def _k(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def put(self, key: str, value, ttl: int = 3600) -> bool:
        try:
            payload = json.dumps(value, ensure_ascii=False, default=str)
            if ttl > 0:
                self._r.setex(self._k(key), ttl, payload)
            else:
                self._r.set(self._k(key), payload)
            return True
        except Exception:
            return False

    def get(self, key: str, default=None):
        try:
            val = self._r.get(self._k(key))
            if val is None:
                return default
            return json.loads(val)
        except Exception:
            return default

    def has(self, key: str) -> bool:
        try:
            return self._r.exists(self._k(key)) > 0
        except Exception:
            return False

    def forget(self, key: str) -> bool:
        try:
            self._r.delete(self._k(key))
            return True
        except Exception:
            return False

    def flush(self) -> int:
        try:
            keys = self._r.keys(f"{self._prefix}*")
            if keys:
                return self._r.delete(*keys)
            return 0
        except Exception:
            return 0

    def increment(self, key: str, by: int = 1) -> int:
        try:
            return self._r.incrby(self._k(key), by)
        except Exception:
            return super().increment(key, by)


# ───────────────────────────────── Cache Facade ───────────────────────────────

class Cache:
    """
    Driver-agnostic Cache Facade।
    CACHE_DRIVER config variable দিয়ে driver বেছে নেওয়া যায়।
    ডিফল্ট: file।
    """
    _driver_instance: _CacheDriver = None
    CACHE_DIR = "storage/cache"  # backward compat

    @classmethod
    def _get_driver(cls) -> _CacheDriver:
        if cls._driver_instance is not None:
            return cls._driver_instance

        try:
            from config.config import get
            driver_name = get("CACHE_DRIVER", "file")
        except Exception:
            driver_name = os.environ.get("CACHE_DRIVER", "file")

        if driver_name == "memory":
            cls._driver_instance = _MemoryDriver()

        elif driver_name == "redis":
            try:
                from config.config import get
                cls._driver_instance = _RedisDriver(
                    host=get("REDIS_HOST", "127.0.0.1"),
                    port=int(get("REDIS_PORT", 6379)),
                    db=int(get("REDIS_DB", 0)),
                    password=get("REDIS_PASSWORD", None),
                )
            except Exception:
                # Redis connect ব্যর্থ হলে file-এ fallback
                cls._driver_instance = _FileDriver(cls.CACHE_DIR)

        else:  # file (default)
            cls._driver_instance = _FileDriver(cls.CACHE_DIR)

        return cls._driver_instance

    @classmethod
    def set_driver(cls, driver: _CacheDriver):
        """Testing বা manual override-এর জন্য driver সরাসরি সেট করা"""
        cls._driver_instance = driver

    @classmethod
    def put(cls, key: str, value, ttl: int = 3600) -> bool:
        return cls._get_driver().put(key, value, ttl)

    @classmethod
    def get(cls, key: str, default=None):
        return cls._get_driver().get(key, default)

    @classmethod
    def has(cls, key: str) -> bool:
        return cls._get_driver().has(key)

    @classmethod
    def forget(cls, key: str) -> bool:
        return cls._get_driver().forget(key)

    @classmethod
    def flush(cls) -> int:
        return cls._get_driver().flush()

    @classmethod
    def remember(cls, key: str, ttl: int, callback):
        return cls._get_driver().remember(key, ttl, callback)

    @classmethod
    def pull(cls, key: str, default=None):
        return cls._get_driver().pull(key, default)

    @classmethod
    def increment(cls, key: str, by: int = 1) -> int:
        return cls._get_driver().increment(key, by)

    @classmethod
    def decrement(cls, key: str, by: int = 1) -> int:
        return cls._get_driver().decrement(key, by)

    @classmethod
    def gc(cls) -> int:
        """File driver-এ expired entries পরিষ্কার করে"""
        driver = cls._get_driver()
        if isinstance(driver, _FileDriver):
            return driver.gc()
        return 0
