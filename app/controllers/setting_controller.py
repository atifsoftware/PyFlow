"""
app/controllers/setting_controller.py
=======================================
সিস্টেম সেটিংস পরিচালনা করার কন্ট্রোলার।
"""

from core.controller import Controller
from core.security import Sanitize
from app.models.setting_model import Setting


class SettingController(Controller):
    def index(self):
        # Only admin role can access settings page
        if self.session.get("role") != "admin":
            return self.back_with_errors({"error": ["আপনার এই পেজে ঢোকার অনুমতি নেই।"]})

        settings = {
            "site_name": Setting.get("site_name", "PyFlow App"),
            "site_email": Setting.get("site_email", "admin@example.com"),
            "allow_registration": Setting.get("allow_registration", "1"),
            "maintenance_mode": Setting.get("maintenance_mode", "0"),
        }
        return self.view("settings.index", {"settings": settings})

    def update(self):
        if self.session.get("role") != "admin":
            return self.back_with_errors({"error": ["আপনার এই পেজে ঢোকার অনুমতি নেই।"]})

        if not self.verify_csrf():
            return self.back_with_errors({"_token": ["সেশন মেয়াদোত্তীর্ণ"]})

        errors = self.validate({
            "site_name": ["required", "max:100"],
            "site_email": ["required", "email"],
        })
        if errors:
            return self.back_with_errors(errors)

        site_name = Sanitize.string(self.request.input("site_name"))
        site_email = Sanitize.email(self.request.input("site_email"))
        allow_registration = "1" if self.request.input("allow_registration") else "0"
        maintenance_mode = "1" if self.request.input("maintenance_mode") else "0"

        Setting.set("site_name", site_name)
        Setting.set("site_email", site_email)
        Setting.set("allow_registration", allow_registration)
        Setting.set("maintenance_mode", maintenance_mode)

        from app.models.activity_log_model import ActivityLog
        ActivityLog.log(
            self.request,
            action="settings.update",
            description="সিস্টেম সেটিংস আপডেট করা হয়েছে।",
            user_id=self.session.get("user_id")
        )

        return self.redirect_with_success("/settings", "সিস্টেম সেটিংস সফলভাবে আপডেট করা হয়েছে।")
