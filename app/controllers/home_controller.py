"""
app/controllers/home_controller.py
"""

from core.controller import Controller


class HomeController(Controller):
    def index(self):
        return self.view("home.index", {
            "title": "PyFlow Framework",
            "user_name": self.session.get("user_name"),
        })

    def docs(self):
        return self.view("docs.index", {
            "title": "ডকুমেন্টেশন — PyFlow Framework"
        })
