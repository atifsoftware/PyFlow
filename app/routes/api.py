"""
config/routes/api.py
=====================
API রাউট (পাবলিক API, v1 API, ফিচারস)
"""

from core.controller import action
from core.middleware import api_auth_middleware, api_admin_middleware


def register_api_routes(router):
    """API রাউট রেজিস্টার করে।"""
    
    from app.controllers.auth_controller import AuthController
    from app.controllers.feature_controller import FeatureController
    from app.api.v1.user_controller import UserApiV1Controller
    
    # পাবলিক API রাউট
    router.post("/api/login", action(AuthController, "api_login"), name="api.login")
    router.get(
        "/api/version",
        lambda req, sess: __import__("core.response", fromlist=["Response"]).Response.json({
            "version": "v1",
            "framework": "PyFlow",
            "status": "ok"
        }),
        name="api.version"
    )
    
    # ইন্টারঅ্যাক্টিভ ফিচারস (WSGI রাউট)
    router.get("/api/features/db-status", action(FeatureController, "db_status"), name="api.features.db_status")
    router.post("/api/features/money-convert", action(FeatureController, "money_convert"), name="api.features.money_convert")
    router.post("/api/features/transaction-test", action(FeatureController, "transaction_test"), name="api.features.transaction_test")
    
    # API v1 - প্রোটেক্টেড (JWT)
    # সাধারণ ইউজার এক্সেস করতে পারবেন এমন এপিআই রাউট
    with router.group(prefix="/api/v1", middleware=[api_auth_middleware]):
        router.get("/profile", action(AuthController, "api_profile"), name="api.v1.profile")
    
    # অ্যাডমিন ব্যতীত অন্য কেউ এক্সেস করতে পারবেন না এমন এপিআই রাউট
    with router.group(prefix="/api/v1", middleware=[api_auth_middleware, api_admin_middleware]):
        router.get("/users", action(UserApiV1Controller, "index"), name="api.v1.users.index")
        router.get("/users/{id:int}", action(UserApiV1Controller, "show"), name="api.v1.users.show")
        router.post("/users", action(UserApiV1Controller, "store"), name="api.v1.users.store")
        router.put("/users/{id:int}", action(UserApiV1Controller, "update"), name="api.v1.users.update")
        router.delete("/users/{id:int}", action(UserApiV1Controller, "destroy"), name="api.v1.users.destroy")
