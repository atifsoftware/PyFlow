"""
app/controllers/auth_controller.py
====================================
রেজিস্ট্রেশন, লগইন, লগআউট - সিকিউরিটি বেস্ট প্র্যাকটিস সহ:
- পাসওয়ার্ড PBKDF2 দিয়ে হ্যাশ করা হয়, প্লেইনটেক্সট কখনো স্টোর হয় না
- লগইনের সময় user existence leak এড়াতে generic error message
- ব্রুট-ফোর্স ঠেকাতে rate limiting
- সফল লগইনের পরে session.regenerate() (session fixation প্রতিরোধ)
- CSRF verify_csrf() দিয়ে চেক করা হয়
"""

from core.controller import Controller
from core.security import Sanitize, RateLimiter
from app.models.user_model import User


class AuthController(Controller):
    def show_register(self):
        return self.view("auth.register")

    def register(self):
        if not self.verify_csrf():
            return self.back_with_errors({"_token": ["সেশন মেয়াদোত্তীর্ণ, আবার চেষ্টা করুন"]})

        from config.config import get_config
        cfg = get_config()
        max_attempts = cfg.get("REGISTER_LIMIT_ATTEMPTS", 3)
        window_seconds = cfg.get("REGISTER_LIMIT_SECONDS", 300)

        ip_key = f"register:{self.request.ip()}"
        if RateLimiter.too_many_attempts(ip_key, max_attempts=max_attempts, window_seconds=window_seconds):
            return self.back_with_errors(
                {"email": [f"অতিরিক্ত অ্যাকাউন্ট খোলার চেষ্টা সনাক্ত হয়েছে। দয়া করে {window_seconds // 60} মিনিট পর আবার চেষ্টা করুন।"]}
            )
        RateLimiter.hit(ip_key)

        errors = self.validate({
            "name": ["required", "max:100"],
            "email": ["required", "email"],
            "password": ["required", "min:8"],
        })

        email = Sanitize.email(self.request.input("email"))
        if not errors.get("email") and email and User.find_by("email", email):
            errors.setdefault("email", []).append("এই ইমেইল দিয়ে ইতিমধ্যে অ্যাকাউন্ট আছে")

        if errors:
            return self.back_with_errors(errors)

        name = Sanitize.string(self.request.input("name"), max_length=100)
        password = self.request.input("password")

        User.create_with_password(name, email, password)
        return self.redirect_with_success("/login", "রেজিস্ট্রেশন সফল হয়েছে, এখন লগইন করুন")

    def show_login(self):
        return self.view("auth.login")

    def login(self):
        if not self.verify_csrf():
            return self.back_with_errors({"_token": ["সেশন মেয়াদোত্তীর্ণ, আবার চেষ্টা করুন"]})

        from config.config import get_config
        cfg = get_config()
        max_attempts = cfg.get("LOGIN_LIMIT_ATTEMPTS", 5)
        window_seconds = cfg.get("LOGIN_LIMIT_SECONDS", 300)

        ip_key = f"login:{self.request.ip()}"
        if RateLimiter.too_many_attempts(ip_key, max_attempts=max_attempts, window_seconds=window_seconds):
            return self.back_with_errors(
                {"email": [f"অনেকবার ভুল চেষ্টা হয়েছে, {window_seconds // 60} মিনিট পর আবার চেষ্টা করুন"]}
            )


        email = Sanitize.email(self.request.input("email"))
        password = self.request.input("password") or ""

        user = User.find_by("email", email) if email else None

        # ইচ্ছাকৃতভাবে generic error - "ইমেইল নেই" vs "পাসওয়ার্ড ভুল" আলাদা করে বলা হয় না,
        # কারণ এতে attacker বুঝে যেতে পারে কোন ইমেইল রেজিস্টার্ড আছে (user enumeration)
        if not user or not user.check_password(password):
            RateLimiter.hit(ip_key)
            from app.models.activity_log_model import ActivityLog
            ActivityLog.log(
                self.request,
                action="auth.login_failed",
                description=f"লগইন চেষ্টা ব্যর্থ হয়েছে (ইমেইল: {email})。"
            )
            return self.back_with_errors({"email": ["ইমেইল অথবা পাসওয়ার্ড ভুল"]})

        RateLimiter.clear(ip_key)

        self.session.regenerate()  # session fixation প্রতিরোধ
        self.session.set("user_id", user.id)
        self.session.set("user_name", user.name)
        self.session.set("role", user.role or "user")

        from app.models.activity_log_model import ActivityLog
        ActivityLog.log(
            self.request,
            action="auth.login",
            description=f"ব্যবহারকারী '{user.name}' ড্যাশবোর্ডে লগইন করেছেন।",
            user_id=user.id
        )

        return self.redirect("/dashboard")

    def logout(self):
        user_id = self.session.get("user_id")
        user_name = self.session.get("user_name")
        if user_id:
            from app.models.activity_log_model import ActivityLog
            ActivityLog.log(
                self.request,
                action="auth.logout",
                description=f"ব্যবহারকারী '{user_name}' লগআউট করেছেন।",
                user_id=user_id
            )
        self.session.destroy()
        return self.redirect("/login")

    def dashboard(self):
        # ড্যাশবোর্ডের জন্য ডাইনামিক মেট্রিক্স কুয়েরি করা
        from config.config import get_config
        config = get_config()
        total_users = User.query().count()
        return self.view("auth.dashboard", {
            "user_name": self.session.get("user_name"),
            "total_users": total_users,
            "db_driver": config.get("DB_DRIVER", "sqlite").upper(),
            "gemini_active": bool(config.get("GEMINI_API_KEY"))
        })

    def api_login(self):
        """API Login - ইউজারনেম/পাসওয়ার্ড চেক করে JWT Token রিটার্ন করে"""
        email = Sanitize.email(self.request.input("email"))
        password = self.request.input("password") or ""

        user = User.find_by("email", email) if email else None
        if not user or not user.check_password(password):
            from app.models.activity_log_model import ActivityLog
            ActivityLog.log(
                self.request,
                action="auth.api_login_failed",
                description=f"API লগইন চেষ্টা ব্যর্থ হয়েছে (ইমেইল: {email})।"
            )
            return self.json({"error": "Invalid email or password"}, status=401)

        from core.security import JWT
        from config.config import get_config
        
        config = get_config()
        secret = config.get("SECRET_KEY", "")
        
        # Token-এ User ID ও Role ক্লেইম হিসেবে থাকবে
        token = JWT.encode(
            payload={"sub": user.id, "role": user.role or "user"},
            secret=secret,
            expires_in=3600  # ১ ঘণ্টার মেয়াদ
        )
        
        from app.models.activity_log_model import ActivityLog
        ActivityLog.log(
            self.request,
            action="auth.api_login",
            description=f"ব্যবহারকারী '{user.name}' এপিআই টোকেন সংগ্রহ করেছেন।",
            user_id=user.id
        )
        
        return self.json({
            "token": token,
            "expires_in": 3600,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
        })

    def api_profile(self):
        """সুরক্ষিত API Profile - JWT Authentication Middleware হয়ে এখানে আসবে"""
        user_id = getattr(self.request, "user_id", None)
        if not user_id:
            return self.json({"error": "Unauthorized"}, status=401)
            
        user = User.find(user_id)
        if not user:
            return self.json({"error": "User not found"}, status=404)
            
        return self.json({
            "user": user.to_dict()
        })

