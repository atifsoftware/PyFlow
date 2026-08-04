"""
app/controllers/api_key_controller.py
=======================================
ইউজারদের এপিআই কি (API Key) ম্যানেজ করার কন্ট্রোলার।
"""

from app.models.activity_log_model import ActivityLog
from app.models.api_key_model import ApiKey
from core.controller import Controller
from core.security import Sanitize


class ApiKeyController(Controller):
    def index(self):
        user_id = self.session.get("user_id")
        if not user_id:
            return self.redirect("/login")

        # Fetch API keys belonging to current user
        keys = ApiKey.query().where("user_id", user_id).order_by("created_at", "DESC").get()

        # Get plain text token from flash if just created
        new_token = self.session.get_flash("new_api_token")

        return self.view("api_keys.index", {"keys": keys, "new_token": new_token})

    def store(self):
        user_id = self.session.get("user_id")
        if not user_id:
            return self.redirect("/login")

        if not self.verify_csrf():
            return self.back_with_errors({"_token": ["সেশন মেয়াদোত্তীর্ণ"]})

        errors = self.validate({
            "name": ["required", "max:100"],
        })
        if errors:
            return self.back_with_errors(errors)

        name = Sanitize.string(self.request.input("name"))

        # Generate new token
        token, key_instance = ApiKey.generate(user_id, name)

        # Log activity
        ActivityLog.log(
            self.request,
            action="api_key.create",
            description=f"এপিআই কী '{name}' তৈরি করা হয়েছে।",
            user_id=user_id,
        )

        # Flash plain text token to show once
        self.session.flash("new_api_token", token)

        return self.redirect_with_success(
            "/api-keys",
            "এপিআই কী সফলভাবে তৈরি করা হয়েছে। এটি একবারই দেখানো হবে, দয়া করে সেভ করে রাখুন।",
        )

    def destroy(self):
        user_id = self.session.get("user_id")
        if not user_id:
            return self.redirect("/login")

        # In resources or custom DELETE request, Csrf should be verified
        if not self.verify_csrf():
            return self.back_with_errors({"_token": ["সেশন মেয়াদোত্তীর্ণ"]})

        key_id = self.request.params.get("id")
        key_instance = ApiKey.find(key_id)

        if key_instance and key_instance.user_id == user_id:
            name = key_instance._attributes.get("name")
            key_instance.delete()

            # Log activity
            ActivityLog.log(
                self.request,
                action="api_key.delete",
                description=f"এপিআই কী '{name}' মুছে ফেলা হয়েছে।",
                user_id=user_id,
            )

            return self.redirect_with_success("/api-keys", f"এপিআই কী '{name}' বাতিল করা হয়েছে।")

        return self.back_with_errors({"error": ["এপিআই কী পাওয়া যায়নি বা বাতিল করার অনুমতি নেই।"]})
