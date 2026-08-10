"""
config/routes/web.py
=====================
পাবলিক ওয়েব রাউট (হোম, ডক্স, ইত্যাদি)
"""

from core.controller import action


def register_web_routes(router):
    """পাবলিক ওয়েব রাউট রেজিস্টার করে।"""
    
    from app.controllers.home_controller import HomeController
    
    # হোম পেজ
    router.get("/", action(HomeController, "index"), name="home")
    
    # ডকুমেন্টেশন পেজ
    router.get("/docs", action(HomeController, "docs"), name="docs")
