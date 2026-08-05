"""
app/controllers/home_controller.py
"""

from core.controller import Controller
from core.cache import Cache


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

    def dashboard(self):
        """Admin Dashboard — Statistics সহ"""
        # 5 মিনিটের জন্য stats cache করা হবে
        stats = Cache.remember("dashboard_stats", 300, self._compute_stats)

        # সর্বশেষ 5টি activity log (cache করা হয় না — real-time)
        from core.database import Database
        try:
            cursor = Database.execute(
                "SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 5"
            )
            recent_logs = []
            for row in (cursor.fetchall() or []):
                recent_logs.append(dict(row) if not isinstance(row, dict) else row)
        except Exception:
            recent_logs = []

        return self.view("admin.dashboard", {
            "title": "Dashboard — PyFlow",
            "stats": stats,
            "recent_logs": recent_logs,
            "user_name": self.session.get("user_name"),
        })

    def _compute_stats(self) -> dict:
        """Dashboard-এর জন্য DB থেকে statistics গণনা করে"""
        from core.database import Database
        import time

        stats = {
            "total_users": 0,
            "today_logins": 0,
            "pending_jobs": 0,
            "total_logs": 0,
        }

        today = time.strftime("%Y-%m-%d")

        try:
            cursor = Database.execute("SELECT COUNT(*) as cnt FROM users")
            row = cursor.fetchone()
            if row:
                row = dict(row) if not isinstance(row, dict) else row
                stats["total_users"] = row.get("cnt", 0)
        except Exception:
            pass

        try:
            cursor = Database.execute(
                f"SELECT COUNT(*) as cnt FROM activity_logs "
                f"WHERE action = 'login' AND DATE(created_at) = {Database.placeholder()}",
                (today,)
            )
            row = cursor.fetchone()
            if row:
                row = dict(row) if not isinstance(row, dict) else row
                stats["today_logins"] = row.get("cnt", 0)
        except Exception:
            pass

        try:
            cursor = Database.execute(
                "SELECT COUNT(*) as cnt FROM jobs WHERE reserved_at IS NULL"
            )
            row = cursor.fetchone()
            if row:
                row = dict(row) if not isinstance(row, dict) else row
                stats["pending_jobs"] = row.get("cnt", 0)
        except Exception:
            pass

        try:
            cursor = Database.execute("SELECT COUNT(*) as cnt FROM activity_logs")
            row = cursor.fetchone()
            if row:
                row = dict(row) if not isinstance(row, dict) else row
                stats["total_logs"] = row.get("cnt", 0)
        except Exception:
            pass

        return stats
