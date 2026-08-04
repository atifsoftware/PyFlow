"""
app/controllers/home_controller.py
"""

from core.controller import Controller


class HomeController(Controller):
    def index(self):
        return self.view("home.index", {
            "title": "PyMVC Framework",
            "user_name": self.session.get("user_name"),
        })
