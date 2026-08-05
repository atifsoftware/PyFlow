"""
core/asgi_bridge.py
====================
ASGI/WSGI Bridge — PyFlow এবং FastAPI একই পোর্টে চালায়।

কীভাবে কাজ করে:
  - path /api/* হলে → FastAPI (ASGI) হ্যান্ডেল করে
  - বাকি সব path → PyFlow WSGI অ্যাপ (a2wsgi.WsgiToAsgi দিয়ে ASGI-তে রূপান্তরিত)

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


def _build_pyflow_wsgi():
    """PyFlow WSGI অ্যাপ তৈরি করা"""
    config = get_config()
    router = build_router()

    os.makedirs("storage/logs", exist_ok=True)
    os.makedirs("storage/sessions", exist_ok=True)

    return Application(router, config)


# PyFlow WSGI → ASGI-তে রূপান্তর
_pyflow_wsgi = _build_pyflow_wsgi()
_pyflow_asgi = WSGIMiddleware(_pyflow_wsgi)


async def application(scope, receive, send):
    """
    মূল ASGI callable:
    - /api/* এবং /openapi.json → FastAPI
    - WebSockets → FastAPI
    - বাকি সব → PyFlow
    """
    path = scope.get("path", "/")
    scope_type = scope.get("type", "")

    # FastAPI paths: /api/*, /api/docs, /api/redoc, /api/openapi.json
    # WebSockets ও FastAPI-র মাধ্যমে হ্যান্ডেল করা হবে
    if scope_type == "websocket" or path == "/api" or path.startswith("/api/"):
        await fastapi_app(scope, receive, send)
    else:
        await _pyflow_asgi(scope, receive, send)
