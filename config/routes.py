"""
config/routes.py
=================
সব রুট এখানে রেজিস্টার হয়। App boot হওয়ার সময় এই ফাইল লোড হয়।
"""

from core.router import Router
from core.controller import action
from core.middleware import auth_middleware, guest_middleware, csrf_middleware, rate_limit_middleware

from app.controllers.home_controller import HomeController
from app.controllers.auth_controller import AuthController
from app.controllers.user_controller import UserController


def build_router() -> Router:
    router = Router()

    # ------------------------------------------------------------- public
    router.get("/", action(HomeController, "index"), name="home")
    router.get("/docs", action(HomeController, "docs"), name="docs")

    # --------------------------------------------------------------- auth
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

    with router.group(prefix="", middleware=[auth_middleware]):
        router.get("/logout", action(AuthController, "logout"), name="logout")
        router.get("/dashboard", action(AuthController, "dashboard"), name="dashboard")

        # ইউজার CRUD - লগইন করা থাকলে তবেই অ্যাক্সেস করা যাবে
        router.resource("/users", UserController, name="users")

        # সিস্টেম সেটিংস
        from app.controllers.setting_controller import SettingController
        router.get("/settings", action(SettingController, "index"), name="settings")
        router.post("/settings", action(SettingController, "update"), name="settings.update")

        # অ্যাক্টিভিটি লগ
        from app.controllers.activity_log_controller import ActivityLogController
        router.get("/logs", action(ActivityLogController, "index"), name="logs")

        # API কী ম্যানেজমেন্ট
        from app.controllers.api_key_controller import ApiKeyController
        router.get("/api-keys", action(ApiKeyController, "index"), name="api_keys")
        router.post("/api-keys", action(ApiKeyController, "store"), name="api_keys.store")
        router.delete("/api-keys/{id:int}", action(ApiKeyController, "destroy"), name="api_keys.destroy")

        # ডাটাবেস সিঙ্ক ও কম্পারিজন টুল
        from app.controllers.db_sync_controller import DBSyncController
        router.get("/admin/db-sync", action(DBSyncController, "index"), name="db_sync")
        router.post("/admin/db-sync/compare", action(DBSyncController, "compare"), name="db_sync.compare")

    # ----------------------------------------------------------------- API
    # Public API Routes
    router.post("/api/login", action(AuthController, "api_login"), name="api.login")
    router.get("/api/version", lambda req, sess: __import__("core.response", fromlist=["Response"]).Response.json({"version": "v1", "framework": "PyFlow", "status": "ok"}), name="api.version")

    # ── API v1 — Protected (JWT) ───────────────────────────────────────────
    from core.middleware import api_auth_middleware
    from core.controller import action as act
    from app.api.v1.user_controller import UserApiV1Controller

    with router.group(prefix="/api/v1", middleware=[api_auth_middleware]):
        router.get("/profile",      action(AuthController, "api_profile"),      name="api.v1.profile")
        router.get("/users",        act(UserApiV1Controller, "index"),           name="api.v1.users.index")
        router.get("/users/{id:int}", act(UserApiV1Controller, "show"),          name="api.v1.users.show")
        router.post("/users",       act(UserApiV1Controller, "store"),           name="api.v1.users.store")
        router.put("/users/{id:int}", act(UserApiV1Controller, "update"),        name="api.v1.users.update")
        router.delete("/users/{id:int}", act(UserApiV1Controller, "destroy"),    name="api.v1.users.destroy")

    return router
