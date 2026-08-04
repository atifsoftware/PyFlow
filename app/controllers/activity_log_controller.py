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

        # Pagination
        try:
            page = int(self.request.input("page", 1))
        except ValueError:
            page = 1

        per_page = 20
        total_logs = ActivityLog.query().count()

        # Fetch logs ordered by created_at DESC
        logs_rows = ActivityLog.query().order_by("created_at", "DESC").paginate(page, per_page).get()

        # Hydrate user details to avoid N+1 query problem
        user_ids = {row.get("user_id") for row in logs_rows if row.get("user_id") is not None}
        users_map = {}
        if user_ids:
            users = User.query().where_in("id", list(user_ids)).get()
            users_map = {u.get("id"): u.get("name") for u in users}

        formatted_logs = []
        for row in logs_rows:
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

        total_pages = max(1, (total_logs + per_page - 1) // per_page)

        return self.view(
            "logs.index",
            {
                "logs": formatted_logs,
                "current_page": page,
                "total_pages": total_pages,
                "total_logs": total_logs,
            },
        )
