"""
core/middleware.py
===================
Middleware ফাংশন প্যাটার্ন: (request, session) -> Response | None
None রিটার্ন করলে পরের middleware/handler-এ যাবে, Response রিটার্ন করলে
সেখানেই চেইন বন্ধ হয়ে যাবে (যেমন redirect to login)।
"""

from core.response import Response
from core.security import Csrf, RateLimiter


def auth_middleware(request, session):
    """লগইন না থাকলে লগইন পেজে পাঠিয়ে দেয়"""
    if not session.get("user_id"):
        return Response.redirect("/login")
    return None


def guest_middleware(request, session):
    """লগইন করা ইউজার login/register পেজে গেলে home-এ পাঠিয়ে দেয়"""
    if session.get("user_id"):
        return Response.redirect("/dashboard")
    return None


def csrf_middleware(request, session):
    """POST/PUT/PATCH/DELETE-এ CSRF টোকেন বাধ্যতামূলক চেক করে"""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        submitted = request.input("_token") or request.header("X-CSRF-Token")
        if not Csrf.verify(session, submitted):
            return Response("419 Page Expired - CSRF token mismatch", status=419)
    return None


def rate_limit_middleware(max_attempts=60, window_seconds=60):
    """
    ব্যবহার: router.get("/api/x", handler, middleware=[rate_limit_middleware()])
    IP অনুযায়ী rate limit করে - brute force / scraping থেকে সুরক্ষা দেয়।
    """
    def middleware(request, session):
        key = f"rl:{request.ip()}:{request.path}"
        if RateLimiter.too_many_attempts(key, max_attempts, window_seconds):
            return Response("429 Too Many Requests", status=429)
        RateLimiter.hit(key)
        return None
    return middleware


def admin_middleware(request, session):
    """শুধু admin role-এর ইউজারদের জন্য - auth_middleware-এর পরে চেইন করে ব্যবহার করুন"""
    if session.get("role") != "admin":
        return Response.forbidden("403 - শুধু অ্যাডমিনরা এই পেজে ঢুকতে পারবেন")
    return None


def api_auth_middleware(request, session):
    """
    API Authentication (JWT-based) Middleware
    Authorization: Bearer <token> হেডার চেক করে এবং ভ্যালিড টোকেন হলে
    request.user_id ও request.user_role সেট করে দেয়।
    """
    from core.security import JWT
    from config.config import get_config
    
    auth_header = request.header("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response.json({"error": "Unauthorized - missing or invalid token"}, status=401)
        
    token = auth_header.partition("Bearer ")[2].strip()
    config = get_config()
    secret = config.get("SECRET_KEY", "")
    
    payload = JWT.decode(token, secret)
    if not payload:
        return Response.json({"error": "Unauthorized - token invalid or expired"}, status=401)
        
    # রিকোয়েস্টে ইউজার আইডি এবং রোল বাইন্ড করে দেয়া
    request.user_id = payload.get("sub")
    request.user_role = payload.get("role", "user")
    
    return None


def api_admin_middleware(request, session):
    """API Admin Verification Middleware - api_auth_middleware-এর পরে ব্যবহার করুন"""
    role = getattr(request, "user_role", "user")
    if role != "admin":
        return Response.json({"error": "Forbidden - admin role required"}, status=403)
    return None


def permission_middleware(permission_name: str):
    """
    RBAC Permission Middleware — নির্দিষ্ট permission আছে কিনা চেক করে।
    auth_middleware-এর পরে চেইন করে ব্যবহার করুন।

    ব্যবহার:
        router.delete("/users/{id:int}", handler,
            middleware=[auth_middleware, permission_middleware("users.delete")])
    """
    def middleware(request, session):
        user_id = session.get("user_id")
        if not user_id:
            return Response.redirect("/login")
        from app.models.user_model import User
        user = User.find(user_id)
        if not user:
            return Response.redirect("/login")
        if not user.has_permission(permission_name):
            return Response.forbidden(f"403 - আপনার '{permission_name}' করার অনুমতি নেই।")
        return None
    middleware.__name__ = f"permission:{permission_name}"
    return middleware


def api_key_rate_middleware():
    """
    API Key-ভিত্তিক Rate Limiting Middleware।
    API Key-এর `rate_limit` কলামে সেট করা সীমা অনুযায়ী throttle করে।
    api_auth_middleware বা api_key_middleware-এর পরে চেইন করুন।
    """
    def middleware(request, session):
        from app.models.api_key_model import ApiKey
        from core.security import RateLimiter
        import time

        auth_header = request.header("X-API-Key") or request.header("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.partition("Bearer ")[2].strip()
        else:
            token = auth_header

        if not token:
            return None  # token নেই, অন্য middleware handle করবে

        import hashlib
        hashed = hashlib.sha256(token.encode("utf-8")).hexdigest()
        from core.database import Database
        cursor = Database.execute(
            f"SELECT id, rate_limit FROM api_keys WHERE key = {Database.placeholder()}",
            (hashed,)
        )
        row = cursor.fetchone() if cursor else None
        if not row:
            return None  # invalid key, অন্য middleware handle করবে

        row = dict(row) if not isinstance(row, dict) else row
        api_key_id = row.get("id")
        rate_limit = int(row.get("rate_limit") or 1000)

        window_key = f"api_key_rl:{api_key_id}:hour"
        if RateLimiter.too_many_attempts(window_key, rate_limit, 3600):
            return Response.json({
                "error": "Rate limit exceeded",
                "limit": rate_limit,
                "retry_after": 3600
            }, status=429)
        RateLimiter.hit(window_key)
        return None
    return middleware


def gzip_middleware(min_size: int = 1024):
    """
    Gzip Response Compression Middleware.
    min_size bytes-এর বেশি HTML/JSON response গুলো compress করে।
    Accept-Encoding: gzip header না থাকলে compress করে না।

    ব্যবহার (global middleware হিসেবে application.py-তে):
        app = Application(..., global_middleware=[gzip_middleware()])
    """
    def middleware(request, session):
        # এটি pre-handler middleware, response compress করার কাজটি
        # after-handler stage-এ করতে হয়। আপাতত signal সেট করুন।
        accept_encoding = request.header("Accept-Encoding", "")
        if "gzip" in accept_encoding:
            request._gzip_requested = True
        return None
    return middleware
