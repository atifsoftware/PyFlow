"""
config/config.py
=================
.env ফাইল থেকে কনফিগ লোড করে (কোনো external dependency ছাড়াই, নিজে parse করে)।
"""

import os


def load_env(path=".env") -> dict:
    env = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"').strip("'")
    # .env-এর মান environment variable দিয়ে override করা যাবে (deployment-এর জন্য ভালো)
    for key in list(env.keys()):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def get_config() -> dict:
    env = load_env()
    return {
        "APP_NAME": env.get("APP_NAME", "PyFlow App"),
        "APP_DEBUG": env.get("APP_DEBUG", "true").lower() == "true",
        "APP_URL": env.get("APP_URL", "http://localhost:8000"),
        "SECRET_KEY": env.get("SECRET_KEY", ""),

        "DB_DRIVER":    env.get("DB_DRIVER", "sqlite"),      # sqlite | mysql
        "DB_HOST":      env.get("DB_HOST", "127.0.0.1"),
        "DB_PORT":      env.get("DB_PORT", "3306"),
        "DB_NAME":      env.get("DB_NAME", "storage/database.sqlite"),
        "DB_USER":      env.get("DB_USER", "root"),
        "DB_PASSWORD":  env.get("DB_PASSWORD", ""),
        "DB_POOL_SIZE": env.get("DB_POOL_SIZE", "5"),        # MySQL connection pool
        "DB_TIMEZONE":  env.get("DB_TIMEZONE", "+06:00"),    # বাংলাদেশ সময়

        "SESSION_DIR": env.get("SESSION_DIR", "storage/sessions"),
        "SESSION_SECURE_COOKIE": env.get("SESSION_SECURE_COOKIE", "false").lower() == "true",

        "VIEWS_DIR": env.get("VIEWS_DIR", "app/views"),
        "LOG_FILE": env.get("LOG_FILE", "storage/logs/app.log"),
        
        "GEMINI_API_KEY": env.get("GEMINI_API_KEY", ""),
    }
