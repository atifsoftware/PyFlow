"""
app/controllers/user_controller.py
====================================
CRUD উদাহরণ - router.resource() দিয়ে RESTful রুট বানানোর ডেমো।
"""

from core.controller import Controller
from core.security import Sanitize
from app.models.user_model import User


class UserController(Controller):
    def index(self):
        users = [u.to_dict() for u in User.all()]
        return self.view("users.index", {"users": users})

    def create(self):
        return self.view("users.create")

    def store(self):
        if not self.verify_csrf():
            return self.back_with_errors({"_token": ["সেশন মেয়াদোত্তীর্ণ"]})

        errors = self.validate({
            "name": ["required", "max:100"],
            "email": ["required", "email", "unique:users,email"],
            "password": ["required", "min:8"],
        })
        if errors:
            return self.back_with_errors(errors)

        name = Sanitize.string(self.request.input("name"))
        email = Sanitize.email(self.request.input("email"))
        password = self.request.input("password")

        user = User.create_with_password(name, email, password)
        
        from app.models.activity_log_model import ActivityLog
        ActivityLog.log(
            self.request,
            action="user.create",
            description=f"নতুন ব্যবহারকারী '{name}' ({email}) তৈরি করা হয়েছে।",
            user_id=self.session.get("user_id")
        )
        return self.redirect_with_success("/users", "ইউজার তৈরি হয়েছে")

    def show(self):
        user_id = self.request.params.get("id")
        user = User.find(user_id)
        if not user:
            return self.json({"error": "পাওয়া যায়নি"}, status=404)
        return self.view("users.show", {"user": user.to_dict()})

    def edit(self):
        user_id = self.request.params.get("id")
        user = User.find(user_id)
        if not user:
            return self.json({"error": "পাওয়া যায়নি"}, status=404)
        return self.view("users.edit", {"user": user.to_dict()})

    def update(self):
        if not self.verify_csrf():
            return self.back_with_errors({"_token": ["সেশন মেয়াদোত্তীর্ণ"]})

        user_id = self.request.params.get("id")
        user = User.find(user_id)
        if not user:
            return self.json({"error": "পাওয়া যায়নি"}, status=404)

        errors = self.validate({
            "name": ["required", "max:100"],
            "role": ["required"],
        })
        if errors:
            return self.back_with_errors(errors)

        name = Sanitize.string(self.request.input("name"))
        role = self.request.input("role")
        user.update({"name": name, "role": role})
        
        from app.models.activity_log_model import ActivityLog
        ActivityLog.log(
            self.request,
            action="user.update",
            description=f"ব্যবহারকারী '{user.name}' (রোল: {role}) এর তথ্য আপডেট করা হয়েছে।",
            user_id=self.session.get("user_id")
        )
        return self.redirect_with_success("/users", "আপডেট সম্পন্ন হয়েছে")

    def destroy(self):
        if not self.verify_csrf():
            return self.json({"error": "CSRF token মিলছে না"}, status=419)

        user_id = self.request.params.get("id")
        user = User.find(user_id)
        if user:
            name = user.name
            email = user.email
            user.delete()
            
            from app.models.activity_log_model import ActivityLog
            ActivityLog.log(
                self.request,
                action="user.delete",
                description=f"ব্যবহারকারী '{name}' ({email}) মুছে ফেলা হয়েছে।",
                user_id=self.session.get("user_id")
            )
        return self.redirect_with_success("/users", "ডিলিট করা হয়েছে")
