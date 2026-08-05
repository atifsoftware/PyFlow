"""
app/api/resources/user_resource.py
====================================
User Model-এর API Resource। Password হ্যাশ বাদ দিয়ে নিরাপদ output তৈরি করে।
"""
from core.resource import Resource


class UserResource(Resource):
    def to_dict(self) -> dict:
        return {
            "id":         self.model.id,
            "name":       self.model.name,
            "email":      self.model.email,
            "role":       self.model.role if hasattr(self.model, 'role') else None,
            "created_at": str(self.model.created_at) if hasattr(self.model, 'created_at') else None,
        }
