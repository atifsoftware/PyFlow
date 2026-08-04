"""
core/controller.py
===================
বেস Controller - request/session/response হেল্পার সবগুলো এখান থেকে পাওয়া যায়।
app/controllers/*.py এর প্রতিটা কন্ট্রোলার এই ক্লাস থেকে ইনহেরিট করবে।
"""

from core.response import Response
from core.security import Csrf, Sanitize


def action(controller_cls, method_name: str):
    """
    রাউট রেজিস্টার করার সময় কন্ট্রোলার মেথড বাইন্ড করার হেল্পার:
        router.get("/", action(HomeController, "index"))
    প্রতিটা রিকোয়েস্টে কন্ট্রোলারের নতুন instance তৈরি হয় (thread-safe থাকার জন্য)।
    """
    def handler(request, session, view_engine):
        controller = controller_cls(request, session, view_engine)
        method = getattr(controller, method_name)
        return method()
    return handler


class Controller:
    def __init__(self, request, session, view_engine):
        self.request = request
        self.session = session
        self.view_engine = view_engine

    # ------------------------------------------------------------- rendering
    def view(self, template: str, data: dict = None, status: int = 200) -> Response:
        data = data or {}

        # Language Switcher (Query Param takes priority, then Session, default 'bn')
        lang_param = self.request.input("lang")
        if lang_param in ["bn", "en"]:
            self.session.set("lang", lang_param)

        current_lang = self.session.get("lang", "bn")

        import os
        import json

        translations = {}
        lang_file = os.path.join("app", "lang", f"{current_lang}.json")
        if os.path.exists(lang_file):
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    translations = json.load(f)
            except Exception:
                translations = {}

        def translate(key, default=""):
            return translations.get(key, default or key)

        data.setdefault("csrf_token", Csrf.generate(self.session))
        data.setdefault("old", self.session.get_flash("_old_input", {}))
        data.setdefault("errors", self.session.get_flash("_errors", {}))
        data.setdefault("success", self.session.get_flash("_success"))
        data.setdefault("user_name", self.session.get("user_name"))
        data.setdefault("user_role", self.session.get("role"))
        data.setdefault("current_lang", current_lang)
        data.setdefault("__", translate)

        html = self.view_engine.render(template, data)
        return Response.html(html, status=status)

    def json(self, data, status=200) -> Response:
        return Response.json(data, status=status)

    def redirect(self, url, status=302) -> Response:
        return Response.redirect(url, status=status)

    def back_with_errors(self, errors: dict, old_input: dict = None):
        self.session.flash("_errors", errors)
        self.session.flash("_old_input", old_input or self.request.all())
        referer = self.request.header("Referer", "/")
        return Response.redirect(referer)

    def redirect_with_success(self, url, message):
        self.session.flash("_success", message)
        return Response.redirect(url)

    # ------------------------------------------------------------- security
    def verify_csrf(self) -> bool:
        submitted = self.request.input("_token")
        return Csrf.verify(self.session, submitted)

    def validate(self, rules: dict) -> dict:
        """
        সহজ ভ্যালিডেশন হেল্পার কাস্টম Validator ইঞ্জিন ব্যবহার করে:
            errors = self.validate({
                "email": ["required", "email"],
                "name": ["required", "max:100"],
            })
        """
        from core.validator import Validator

        formatted_rules = {}
        for field, rule_item in rules.items():
            if isinstance(rule_item, list):
                formatted_rules[field] = "|".join(rule_item)
            else:
                formatted_rules[field] = rule_item

        validator = Validator(self.request.all(), formatted_rules)
        if validator.fails():
            return validator.errors()
        return {}
