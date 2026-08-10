"""
config/routes/admin.py
=======================
অ্যাডমিন রাউট (ইউজার ম্যানেজমেন্ট, সেটিংস, লগ, ডাটাবেস সিঙ্ক)
"""

from core.controller import action
from core.middleware import auth_middleware, admin_middleware


def register_admin_routes(router):
    """অ্যাডমিন রাউট রেজিস্টার করে।"""
    
    from app.controllers.user_controller import UserController
    from app.controllers.setting_controller import SettingController
    from app.controllers.activity_log_controller import ActivityLogController
    from app.controllers.db_sync_controller import DBSyncController
    
    # অ্যাডমিন প্রোটেক্টেড ওয়েব রাউট
    with router.group(prefix="", middleware=[auth_middleware, admin_middleware]):
        # ইউজার CRUD
        router.resource("/users", UserController, name="users")
        
        # সিস্টেম সেটিংস
        router.get("/settings", action(SettingController, "index"), name="settings")
        router.post("/settings", action(SettingController, "update"), name="settings.update")
        
        # অ্যাক্টিভিটি লগ
        router.get("/logs", action(ActivityLogController, "index"), name="logs")
        
        # ডাটাবেস সিঙ্ক ও কম্পারিজন টুল
        router.get("/admin/db-sync", action(DBSyncController, "index"), name="db_sync")
        router.post("/admin/db-sync/compare", action(DBSyncController, "compare"), name="db_sync.compare")
