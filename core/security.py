"""
core/security.py
=================
সব ধরনের Security utility একসাথে:
- Password hashing (PBKDF2-HMAC-SHA256, salt সহ)
- CSRF token generation / verification
- XSS প্রতিরোধের জন্য output escaping
- Input sanitization / validation
- Secure random token generation
- Simple rate limiter (brute-force আটকাতে)
- Security headers middleware
"""

import hashlib
import hmac
import os
import re
import time
import html
import secrets
import json
from typing import Optional


# --------------------------------------------------------------------------
# Password Hashing (bcrypt না থাকলেও কাজ করবে - stdlib দিয়ে PBKDF2)
# --------------------------------------------------------------------------
class Hash:
    ALGO = "sha256"
    ITERATIONS = 260_000  # OWASP 2023 recommendation অনুযায়ী
    SALT_BYTES = 16

    @classmethod
    def make(cls, plain_password: str) -> str:
        """পাসওয়ার্ড হ্যাশ করে 'algo$iterations$salt$hash' ফরম্যাটে রিটার্ন করে"""
        if not plain_password or len(plain_password) < 1:
            raise ValueError("Password cannot be empty")
        salt = os.urandom(cls.SALT_BYTES)
        dk = hashlib.pbkdf2_hmac(
            cls.ALGO, plain_password.encode("utf-8"), salt, cls.ITERATIONS
        )
        return f"{cls.ALGO}${cls.ITERATIONS}${salt.hex()}${dk.hex()}"

    @classmethod
    def check(cls, plain_password: str, hashed: str) -> bool:
        """constant-time compare দিয়ে পাসওয়ার্ড ভেরিফাই করে (timing attack প্রতিরোধ)"""
        try:
            algo, iterations, salt_hex, hash_hex = hashed.split("$")
            iterations = int(iterations)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
        except (ValueError, AttributeError):
            return False

        dk = hashlib.pbkdf2_hmac(algo, plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)

    @classmethod
    def needs_rehash(cls, hashed: str) -> bool:
        """পুরনো ইটারেশন কাউন্ট দিয়ে হ্যাশ হলে rehash দরকার কিনা চেক করে"""
        try:
            _, iterations, _, _ = hashed.split("$")
            return int(iterations) < cls.ITERATIONS
        except (ValueError, AttributeError):
            return True


# --------------------------------------------------------------------------
# CSRF Protection
# --------------------------------------------------------------------------
class Csrf:
    TOKEN_KEY = "_csrf_token"
    FIELD_NAME = "_token"
    HEADER_NAME = "X-CSRF-Token"

    @classmethod
    def generate(cls, session) -> str:
        """সেশনে টোকেন না থাকলে নতুন টোকেন তৈরি করে সেশনে রাখে"""
        token = session.get(cls.TOKEN_KEY)
        if not token:
            token = secrets.token_hex(32)
            session.set(cls.TOKEN_KEY, token)
        return token

    @classmethod
    def verify(cls, session, submitted_token: Optional[str]) -> bool:
        """constant-time compare - session-এর টোকেনের সাথে submitted টোকেন মিলায়"""
        real_token = session.get(cls.TOKEN_KEY)
        if not real_token or not submitted_token:
            return False
        return hmac.compare_digest(str(real_token), str(submitted_token))

    @classmethod
    def rotate(cls, session):
        """টোকেন ব্যবহারের পর (sensitive action-এর পরে) নতুন টোকেন বানানো ভালো অভ্যাস"""
        session.set(cls.TOKEN_KEY, secrets.token_hex(32))


# --------------------------------------------------------------------------
# XSS Protection - output escaping helpers
# --------------------------------------------------------------------------
def e(value) -> str:
    """HTML escape - ভিউতে সবসময় এইটা দিয়ে ইউজার ইনপুট প্রিন্ট করবেন"""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def clean_html(value: str, allowed_tags=None) -> str:
    """
    বেসিক HTML স্যানিটাইজার - script/style/iframe/on* attribute এবং
    javascript: URI বাদ দেয়। rich-text ইনপুটের জন্য (যেমন blog body)।
    পুরোপুরি bleach/nh3-এর বিকল্প না, কিন্তু বেসিক নিরাপত্তা দেয়।
    """
    if not value:
        return ""
    value = re.sub(r"<script.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style.*?</style>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<iframe.*?</iframe>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r'on\w+\s*=\s*(".*?"|\'.*?\'|[^\s>]+)', "", value, flags=re.IGNORECASE)
    value = re.sub(r"javascript\s*:", "", value, flags=re.IGNORECASE)
    return value


# --------------------------------------------------------------------------
# Input Sanitization / Validation
# --------------------------------------------------------------------------
class Sanitize:
    @staticmethod
    def string(value, max_length: int = 255) -> str:
        if value is None:
            return ""
        value = str(value).strip()
        return value[:max_length]

    @staticmethod
    def email(value) -> Optional[str]:
        value = str(value or "").strip().lower()
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return value if re.match(pattern, value) else None

    @staticmethod
    def integer(value, default=None):
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def alnum(value) -> str:
        return re.sub(r"[^a-zA-Z0-9_\-]", "", str(value or ""))

    @staticmethod
    def filename(value) -> str:
        """path traversal আটকানোর জন্য ফাইলনেম স্যানিটাইজ করে"""
        value = os.path.basename(str(value or ""))
        value = re.sub(r"[^a-zA-Z0-9._\-]", "_", value)
        return value or "file"

    @staticmethod
    def bd_phone(value) -> Optional[str]:
        """বাংলাদেশি মোবাইল নাম্বার ভ্যালিডেশন (01XXXXXXXXX)"""
        value = re.sub(r"\D", "", str(value or ""))
        if re.match(r"^(01)[3-9]\d{8}$", value):
            return value
        return None


# --------------------------------------------------------------------------
# Rate Limiter (brute-force / login-spam প্রতিরোধ) - in-memory, single-process
# প্রোডাকশনে বড় স্কেলে Redis ব্যবহার করা উচিত, কিন্তু এখানে dependency-free রাখা হলো
# --------------------------------------------------------------------------
class RateLimiter:
    _hits = {}  # key -> list[timestamps]

    @classmethod
    def too_many_attempts(cls, key: str, max_attempts: int = 5, window_seconds: int = 60) -> bool:
        now = time.time()
        attempts = cls._hits.get(key, [])
        attempts = [t for t in attempts if now - t < window_seconds]
        cls._hits[key] = attempts
        return len(attempts) >= max_attempts

    @classmethod
    def hit(cls, key: str):
        cls._hits.setdefault(key, []).append(time.time())

    @classmethod
    def clear(cls, key: str):
        cls._hits.pop(key, None)


# --------------------------------------------------------------------------
# Security headers - প্রতিটা response-এ যোগ হবে (middleware থেকে কল হয়)
# --------------------------------------------------------------------------
def security_headers() -> dict:
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://code.jquery.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "frame-ancestors 'none'"
        ),
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }


def generate_secret_key() -> str:
    """.env-এর SECRET_KEY বসানোর জন্য একবার রান করার মতো হেল্পার"""
    return secrets.token_hex(32)


# --------------------------------------------------------------------------
# JWT Support (Dependency-Free HS256 JWT implementation)
# --------------------------------------------------------------------------
class JWT:
    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        import base64
        # padding ঠিক করার জন্য = যোগ করা হয়
        padding = "=" * (4 - (len(data) % 4))
        return base64.urlsafe_b64decode(data + padding)

    @classmethod
    def encode(cls, payload: dict, secret: str, expires_in: int = 3600) -> str:
        """
        HS256 অ্যালগরিদমে JWT Token তৈরি করে।
        expires_in সেকেন্ড পর টোকেনের মেয়াদ শেষ হয়ে যাবে।
        """
        import time
        header = {"alg": "HS256", "typ": "JWT"}
        
        payload_copy = dict(payload)
        payload_copy.setdefault("exp", int(time.time()) + expires_in)
        payload_copy.setdefault("iat", int(time.time()))

        # base64url encode
        header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
        payload_json = json.dumps(payload_copy, separators=(",", ":")).encode("utf-8")

        header_b64 = cls._base64url_encode(header_json)
        payload_b64 = cls._base64url_encode(payload_json)

        # Signature তৈরি
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        signature_b64 = cls._base64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{signature_b64}"

    @classmethod
    def decode(cls, token: str, secret: str) -> Optional[dict]:
        """
        JWT Token ডিকোড ও সিগনেচার ভেরিফাই করে।
        মেয়াদ উত্তীর্ণ হলে বা টোকেন অবৈধ হলে None রিটার্ন করে।
        """
        import time
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts
            
            # Signature ভেরিফাই করা
            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
            expected_signature_b64 = cls._base64url_encode(expected_signature)

            # Constant-time comparison (Timing Attack প্রতিরোধে)
            if not hmac.compare_digest(signature_b64, expected_signature_b64):
                return None

            # Payload ডিকোড করা
            payload_json = cls._base64url_decode(payload_b64)
            payload = json.loads(payload_json.decode("utf-8"))

            # Expiry চেক করা
            if "exp" in payload and time.time() > payload["exp"]:
                return None

            return payload
        except Exception:
            return None

