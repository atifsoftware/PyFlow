"""
config/routes/auth.py
======================
অথেন্টিকেশন রাউট (লগইন, রেজিস্টার, লগআউট, ড্যাশবোর্ড)
"""

from core.controller import action
from core.middleware import guest_middleware, auth_middleware, rate_limit_middleware


def register_auth_routes(router):
    """অথেন্টিকেশন রাউট রেজিস্টার করে।"""
    
    from app.controllers.auth_controller import AuthController
    from app.controllers.api_key_controller import ApiKeyController
    
    # পাবলিক অথেন্টিকেশন (গেস্ট মিডেলওয়্যার)
    with router.group(prefix="", middleware=[guest_middleware]):
        router.get("/register", action(AuthController, "show_register"), name="register")
        router.post(
            "/register",
            action(AuthController, "register"),
            name="register.store",
            middleware=[rate_limit_middleware(max_attempts=10, window_seconds=60)],
        )
        router.get("/login", action(AuthController, "show_login"), name="login")
        router.post(
            "/login",
            action(AuthController, "login"),
            name="login.store",
            middleware=[rate_limit_middleware(max_attempts=10, window_seconds=60)],
        )
    
    # প্রোটেক্টেড অথেন্টিকেশন (অথ মিডেলওয়্যার)
    with router.group(prefix="", middleware=[auth_middleware]):
        router.get("/logout", action(AuthController, "logout"), name="logout")
        router.get("/dashboard", action(AuthController, "dashboard"), name="dashboard")
        
        # API কী ম্যানেজমেন্ট
        router.get("/api-keys", action(ApiKeyController, "index"), name="api_keys")
        router.post("/api-keys", action(ApiKeyController, "store"), name="api_keys.store")
        router.delete("/api-keys/{id:int}", action(ApiKeyController, "destroy"), name="api_keys.destroy")
