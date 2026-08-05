"""
app/api/v1/user_controller.py
===============================
API v1 — User endpoints।
Resource Transformer দিয়ে safe JSON output।
"""

from core.controller import Controller
from app.api.resources.user_resource import UserResource


class UserApiV1Controller(Controller):

    def index(self):
        """GET /api/v1/users — সব user (paginated)"""
        from app.models.user_model import User
        paginator = User.query().order_by("id", "DESC").paginate(self.request, per_page=15)
        return self.json(UserResource.paginated(paginator))

    def show(self):
        """GET /api/v1/users/{id} — একজন user"""
        from app.models.user_model import User
        user_id = self.request.params.get("id")
        user = User.find(user_id)
        if not user:
            return self.json({"error": "User পাওয়া যায়নি"}, status=404)
        return self.json(UserResource(user).to_response())

    def store(self):
        """POST /api/v1/users — নতুন user তৈরি"""
        from core.validator import Validator
        from app.models.user_model import User
        from core.security import Hash

        v = Validator(self.request.all(), {
            "name":     "required|min:2|max:100",
            "email":    "required|email|unique:users,email",
            "password": "required|min:6|confirmed",
        })
        if v.fails():
            return self.json({"errors": v.errors()}, status=422)

        data = v.validated()
        data["password"] = Hash.make(data["password"])
        data["role"] = "user"
        user = User.create(data)
        return self.json(UserResource(user).to_response(), status=201)

    def update(self):
        """PUT /api/v1/users/{id} — user আপডেট"""
        from app.models.user_model import User
        user_id = self.request.params.get("id")
        user = User.find(user_id)
        if not user:
            return self.json({"error": "User পাওয়া যায়নি"}, status=404)

        allowed = {k: v for k, v in self.request.all().items() if k in ("name", "email")}
        user.update(allowed)
        return self.json(UserResource(user).to_response())

    def destroy(self):
        """DELETE /api/v1/users/{id} — user মুছে দেওয়া"""
        from app.models.user_model import User
        user_id = self.request.params.get("id")
        user = User.find(user_id)
        if not user:
            return self.json({"error": "User পাওয়া যায়নি"}, status=404)
        user.delete()
        return self.json({"message": "User মুছে দেওয়া হয়েছে"})
