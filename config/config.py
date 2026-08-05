"""
config/config.py
=================
Environment-ভিত্তিক Config লোডার।
APP_ENV অনুযায়ী .env.{environment} লোড করে, না থাকলে .env থেকে নেয়।

ফাইল চেইন (সবচেয়ে উচ্চ priority উপরে):
  1. Environment variables (OS থেকে)
  2. .env.{APP_ENV}  (e.g., .env.production)
  3. .env           (base fallback)
  4. Default values

উদাহরণ:
  APP_ENV=production → .env.production লোড হবে
  APP_ENV=testing    → .env.testing লোড হবে (in-memory SQLite)
  APP_ENV না থাকলে   → .env লোড হবে (development ধরা হবে)
"""

import os


def load_env(path: str) -> dict:
    """একটি .env ফাইল parse করে dict রিটার্ন করে"""
    env = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def get_config() -> dict:
    """
    সব .env ফাইল চেইন করে merge করে এবং OS environment দিয়ে override করে।
    """
    # Step 1: Base .env লোড করা
    base_env = load_env(".env")

    # Step 2: APP_ENV পড়া (OS env > .env এর মান)
    app_env = os.environ.get("APP_ENV") or base_env.get("APP_ENV", "development")

    # Step 3: Environment-specific .env লোড করা
    env_specific = {}
    env_file = f".env.{app_env}"
    if os.path.exists(env_file):
        env_specific = load_env(env_file)

    # Step 4: Merge — specific file override করে base .env
    merged = {**base_env, **env_specific}

    # Step 5: OS environment variable দিয়ে সব override করা
    for key in list(merged.keys()):
        if key in os.environ:
            merged[key] = os.environ[key]

    # testing environment-এ in-memory SQLite ব্যবহার করা
    if app_env == "testing":
        merged.setdefault("DB_DRIVER", "sqlite")
        merged.setdefault("DB_NAME", ":memory:")

    return {
        "APP_NAME":    merged.get("APP_NAME", "PyFlow App"),
        "APP_VERSION": merged.get("APP_VERSION", "v3.0.0"),
        "APP_ENV":     app_env,
        "APP_DEBUG":   merged.get("APP_DEBUG", "true").lower() == "true",
        "APP_URL":     merged.get("APP_URL", "http://localhost:8000"),
        "SECRET_KEY":  merged.get("SECRET_KEY", ""),


        "DB_DRIVER":    merged.get("DB_DRIVER", "sqlite"),
        "DB_HOST":      merged.get("DB_HOST", "127.0.0.1"),
        "DB_PORT":      merged.get("DB_PORT", "3306"),
        "DB_NAME":      merged.get("DB_NAME", "storage/database.sqlite"),
        "DB_USER":      merged.get("DB_USER", "root"),
        "DB_PASSWORD":  merged.get("DB_PASSWORD", ""),
        "DB_POOL_SIZE": merged.get("DB_POOL_SIZE", "5"),
        "DB_TIMEZONE":  merged.get("DB_TIMEZONE", "+06:00"),

        "SESSION_DIR":            merged.get("SESSION_DIR", "storage/sessions"),
        "SESSION_SECURE_COOKIE":  merged.get("SESSION_SECURE_COOKIE", "false").lower() == "true",

        "VIEWS_DIR": merged.get("VIEWS_DIR", "app/views"),
        "LOG_FILE":  merged.get("LOG_FILE", "storage/logs/app.log"),

        "GEMINI_API_KEY": merged.get("GEMINI_API_KEY", ""),

        # Mail settings
        "MAIL_HOST":         merged.get("MAIL_HOST", "smtp.mailtrap.io"),
        "MAIL_PORT":         merged.get("MAIL_PORT", "587"),
        "MAIL_USERNAME":     merged.get("MAIL_USERNAME", ""),
        "MAIL_PASSWORD":     merged.get("MAIL_PASSWORD", ""),
        "MAIL_ENCRYPTION":   merged.get("MAIL_ENCRYPTION", "tls"),
        "MAIL_FROM_ADDRESS": merged.get("MAIL_FROM_ADDRESS", "noreply@pyflow.dev"),
        "MAIL_FROM_NAME":    merged.get("MAIL_FROM_NAME", "PyFlow App"),

        # Cache settings
        "CACHE_DIR": merged.get("CACHE_DIR", "storage/cache"),
        "CACHE_TTL": int(merged.get("CACHE_TTL", "3600")),

        # Storage
        "STORAGE_ROOT": merged.get("STORAGE_ROOT", "public/static"),
    }

