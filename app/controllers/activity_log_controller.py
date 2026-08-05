"""
app/controllers/activity_log_controller.py
===========================================
সিস্টেম অ্যাক্টিভিটি লগ (Audit Trail) প্রদর্শন করার কন্ট্রোলার।
"""

from app.models.activity_log_model import ActivityLog
from app.models.user_model import User
from core.controller import Controller


class ActivityLogController(Controller):
    def index(self):
        if self.session.get("role") != "admin":
            return self.back_with_errors({"error": ["আপনার এই পেজে ঢোকার অনুমতি নেই।"]})

        # Fetch logs ordered by created_at DESC using unified paginator
        paginator = ActivityLog.query().order_by("created_at", "DESC").paginate(self.request, 20)

        # Hydrate user details to avoid N+1 query problem
        user_ids = {row.get("user_id") for row in paginator.items if row.get("user_id") is not None}
        users_map = {}
        if user_ids:
            users = User.query().where_in("id", list(user_ids)).get()
            users_map = {u.get("id"): u.get("name") for u in users}

        formatted_logs = []
        for row in paginator.items:
            user_id = row.get("user_id")
            formatted_logs.append({
                "id": row.get("id"),
                "user_name": users_map.get(user_id, "System / Guest") if user_id else "System / Guest",
                "action": row.get("action"),
                "description": row.get("description"),
                "ip_address": row.get("ip_address"),
                "user_agent": row.get("user_agent"),
                "created_at": row.get("created_at"),
            })

        # Replace paginator items with formatted list
        paginator.items = formatted_logs

        return self.view(
            "logs.index",
            {
                "logs": paginator,
            },
        )
