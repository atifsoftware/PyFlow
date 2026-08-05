"""
app/api/__init__.py
====================
FastAPI অ্যাপ্লিকেশন — PyFlow-র পাশে /api/* path-এ কাজ করে।
Swagger UI: http://127.0.0.1:8000/api/docs
OpenAPI:    http://127.0.0.1:8000/api/openapi.json
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# FastAPI app তৈরি — prefix /api দিয়ে
api = FastAPI(
    title="PyFlow REST API",
    description=(
        "PyFlow ফ্রেমওয়ার্কের FastAPI ইন্টিগ্রেশন।\n\n"
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
from app.api.routes import features as feature_routes

api.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
api.include_router(user_routes.router, prefix="/api/users", tags=["Users"])
api.include_router(feature_routes.router, prefix="/api/features", tags=["Interactive Features v3.0"])


@api.get("/api", tags=["Root"])
async def api_root():
    """API Root — সংযোগ যাচাই করুন"""
    return {
        "message": "PyFlow FastAPI সফলভাবে চলছে! 🚀",
        "docs": "/api/docs",
        "version": "1.0.0",
        "framework": "PyFlow + FastAPI",
    }


from fastapi import WebSocket, WebSocketDisconnect

@api.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    রিয়েল-টাইম বাই-ডিরেকশনাল কমিউনিকেশনের জন্য টেস্ট WebSocket এন্ডপয়েন্ট।
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"PyFlow WebSocket Response: {data}")
    except WebSocketDisconnect:
        pass
