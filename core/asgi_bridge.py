"""
core/asgi_bridge.py
====================
ASGI/WSGI Bridge — PyMVC এবং FastAPI একই পোর্টে চালায়।

কীভাবে কাজ করে:
  - path /api/* হলে → FastAPI (ASGI) হ্যান্ডেল করে
  - বাকি সব path → PyMVC WSGI অ্যাপ (a2wsgi.WsgiToAsgi দিয়ে ASGI-তে রূপান্তরিত)

ব্যবহার:
  uvicorn core.asgi_bridge:application --host 0.0.0.0 --port 8000 --reload
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from a2wsgi import WSGIMiddleware
from app.api import api as fastapi_app
from core.application import Application
from config.config import get_config
from config.routes import build_router


def _build_pymvc_wsgi():
    """PyMVC WSGI অ্যাপ তৈরি করা"""
    config = get_config()
    router = build_router()

    os.makedirs("storage/logs", exist_ok=True)
    os.makedirs("storage/sessions", exist_ok=True)

    return Application(router, config)


# PyMVC WSGI → ASGI-তে রূপান্তর
_pymvc_wsgi = _build_pymvc_wsgi()
_pymvc_asgi = WSGIMiddleware(_pymvc_wsgi)


async def application(scope, receive, send):
    """
    মূল ASGI callable:
    - /api/* এবং /openapi.json → FastAPI
    - বাকি সব → PyMVC
    """
    path = scope.get("path", "/")

    # FastAPI paths: /api/*, /api/docs, /api/redoc, /api/openapi.json
    if path == "/api" or path.startswith("/api/"):
        await fastapi_app(scope, receive, send)
    else:
        await _pymvc_asgi(scope, receive, send)
