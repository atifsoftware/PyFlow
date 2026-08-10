"""
app/routes/__init__.py
==========================
রাউট মডিউল ইম্পোর্ট এবং একত্রিত করে।
"""

from app.routes.web import register_web_routes
from app.routes.auth import register_auth_routes
from app.routes.admin import register_admin_routes
from app.routes.api import register_api_routes


def build_router():
    """সব রাউট রেজিস্টার করে Router রিটার্ন করে।"""
    from core.router import Router
    
    router = Router()
    
    # সব রাউট ফাইল থেকে রেজিস্টার করুন
    register_web_routes(router)
    register_auth_routes(router)
    register_admin_routes(router)
    register_api_routes(router)
    
    return router
