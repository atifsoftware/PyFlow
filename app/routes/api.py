"""
app/routes/api.py
=====================
API রাউট (পাবলিক API, v1 API, ফিচারস)
"""

from core.controller import action
from core.middleware import api_auth_middleware, api_admin_middleware


def register_api_routes(router):
    """API রাউট রেজিস্টার করে।"""
    
    from app.controllers.auth_controller import AuthController
    from app.controllers.feature_controller import FeatureController
    from app.api.v1.user_controller import UserApiV1Controller
    
    # পাবলিক API রাউট
    router.post("/api/login", action(AuthController, "api_login"), name="api.login")
    router.get(
        "/api/version",
        lambda req, sess: __import__("core.response", fromlist=["Response"]).Response.json({
            "version": "v1",
            "framework": "PyFlow",
            "status": "ok"
        }),
        name="api.version"
    )
    
    # API Documentation (Swagger/OpenAPI)
    router.get("/api/docs", lambda req, sess: __import__("core.response", fromlist=["Response"]).Response.json(get_openapi_schema()), name="api.docs")
    
    # ইন্টারঅ্যাক্টিভ ফিচারস (WSGI রাউট)
    router.get("/api/features/db-status", action(FeatureController, "db_status"), name="api.features.db_status")
    router.post("/api/features/money-convert", action(FeatureController, "money_convert"), name="api.features.money_convert")
    router.post("/api/features/transaction-test", action(FeatureController, "transaction_test"), name="api.features.transaction_test")
    
    # API v1 - প্রোটেক্টেড (JWT)
    # সাধারণ ইউজার এক্সেস করতে পারবেন এমন এপিআই রাউট
    with router.group(prefix="/api/v1", middleware=[api_auth_middleware]):
        router.get("/profile", action(AuthController, "api_profile"), name="api.v1.profile")
    
    # অ্যাডমিন ব্যতীত অন্য কেউ এক্সেস করতে পারবেন না এমন এপিআই রাউট
    with router.group(prefix="/api/v1", middleware=[api_auth_middleware, api_admin_middleware]):
        router.get("/users", action(UserApiV1Controller, "index"), name="api.v1.users.index")
        router.get("/users/{id:int}", action(UserApiV1Controller, "show"), name="api.v1.users.show")
        router.post("/users", action(UserApiV1Controller, "store"), name="api.v1.users.store")
        router.put("/users/{id:int}", action(UserApiV1Controller, "update"), name="api.v1.users.update")
        router.delete("/users/{id:int}", action(UserApiV1Controller, "destroy"), name="api.v1.users.destroy")


def get_openapi_schema():
    """OpenAPI 3.0 স্কিমা জেনারেট করে।"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "PyFlow API",
            "version": "1.0.0",
            "description": "PyFlow ফ্রেমওয়ার্কের অটোমেটেড API ডকুমেন্টেশন"
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Local Development Server"}
        ],
        "paths": {
            "/api/login": {
                "post": {
                    "summary": "User Login",
                    "tags": ["Authentication"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "username": {"type": "string"},
                                        "password": {"type": "string"}
                                    },
                                    "required": ["username", "password"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Successful login"},
                        "401": {"description": "Unauthorized"}
                    }
                }
            },
            "/api/v1/profile": {
                "get": {
                    "summary": "Get User Profile",
                    "tags": ["User"],
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {"description": "User profile data"},
                        "401": {"description": "Unauthorized"}
                    }
                }
            },
            "/api/v1/users": {
                "get": {
                    "summary": "List All Users",
                    "tags": ["Admin"],
                    "security": [{"bearerAuth": []}],
                    "responses": {
                        "200": {"description": "List of users"},
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden (Admin only)"}
                    }
                },
                "post": {
                    "summary": "Create New User",
                    "tags": ["Admin"],
                    "security": [{"bearerAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                        "password": {"type": "string"}
                                    },
                                    "required": ["name", "email", "password"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "201": {"description": "User created"},
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden (Admin only)"}
                    }
                }
            },
            "/api/v1/users/{id}": {
                "get": {
                    "summary": "Get User by ID",
                    "tags": ["Admin"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {"description": "User data"},
                        "404": {"description": "User not found"}
                    }
                },
                "put": {
                    "summary": "Update User",
                    "tags": ["Admin"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "User updated"},
                        "404": {"description": "User not found"}
                    }
                },
                "delete": {
                    "summary": "Delete User",
                    "tags": ["Admin"],
                    "security": [{"bearerAuth": []}],
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "204": {"description": "User deleted"},
                        "404": {"description": "User not found"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }
