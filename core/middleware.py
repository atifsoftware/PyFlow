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

