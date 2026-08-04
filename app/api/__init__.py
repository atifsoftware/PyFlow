"""
app/api/__init__.py
====================
FastAPI অ্যাপ্লিকেশন — PyMVC-র পাশে /api/* path-এ কাজ করে।
Swagger UI: http://127.0.0.1:8000/api/docs
OpenAPI:    http://127.0.0.1:8000/api/openapi.json
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# FastAPI app তৈরি — prefix /api দিয়ে
api = FastAPI(
    title="PyMVC REST API",
    description=(
        "PyMVC ফ্রেমওয়ার্কের FastAPI ইন্টিগ্রেশন।\n\n"
        "- **JWT Authentication** সহ\n"
        "- **Users CRUD** endpoints\n"
        "- **Swagger UI** এই পেজে উপলব্ধ"
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — ডেভেলপমেন্টে সব origin অনুমতি
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes রেজিস্টার
from app.api.routes import auth as auth_routes
from app.api.routes import users as user_routes

api.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
api.include_router(user_routes.router, prefix="/api/users", tags=["Users"])


@api.get("/api", tags=["Root"])
async def api_root():
    """API Root — সংযোগ যাচাই করুন"""
    return {
        "message": "PyMVC FastAPI সফলভাবে চলছে! 🚀",
        "docs": "/api/docs",
        "version": "1.0.0",
        "framework": "PyMVC + FastAPI",
    }
