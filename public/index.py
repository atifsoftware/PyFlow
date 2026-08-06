"""
public/index.py
================
প্রোডাকশন WSGI এন্ট্রি পয়েন্ট। gunicorn / uWSGI / mod_wsgi যেকোনো WSGI সার্ভার
এই ফাইলের 'application' অবজেক্টকে টার্গেট করবে।

    gunicorn --chdir /path/to/pyflow public.index:application

ডেভেলপমেন্টে সরাসরি চালাতে চাইলে প্রজেক্ট রুট থেকে: python run.py
"""

import sys
import os

# প্রজেক্ট রুট sys.path-এ যোগ করা হচ্ছে যাতে core/app/config ইমপোর্ট করা যায়
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from core.application import Application
from config.config import get_config
from config.routes import build_router

config = get_config()
router = build_router()
pyflow_wsgi = Application(router, config)

_fastapi_wsgi = None

def application(environ, start_response):
    global _fastapi_wsgi
    path = environ.get("PATH_INFO", "")
    
    # Route `/api/*` and `/openapi.json` to FastAPI
    if path == "/api" or path.startswith("/api/") or path == "/openapi.json":
        try:
            if _fastapi_wsgi is None:
                from a2wsgi import ASGIMiddleware
                from app.api import api as fastapi_app
                _fastapi_wsgi = ASGIMiddleware(fastapi_app)
            return _fastapi_wsgi(environ, start_response)
        except Exception as exc:
            status = '500 Internal Server Error'
            headers = [('Content-type', 'application/json; charset=utf-8')]
            start_response(status, headers)
            import json
            return [json.dumps({
                "status": "error",
                "message": "FastAPI initialization failed on this server.",
                "detail": str(exc)
            }).encode('utf-8')]
            
    return pyflow_wsgi(environ, start_response)

