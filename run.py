"""
run.py
======
ডেভেলপমেন্ট সার্ভার।

মোড ১ — FastAPI সহ (Recommended):
    python run.py
    → uvicorn দিয়ে চলে, /api/* FastAPI, বাকি সব PyFlow

মোড ২ — শুধু PyFlow (Legacy):
    python run.py --wsgi
    → wsgiref দিয়ে চলে, FastAPI ছাড়া

পোর্ট নির্দিষ্ট করতে:
    python run.py 8080
    python run.py 8080 --wsgi
"""

import sys
import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config.config import get_config


def run_wsgi(port: int):
    """Legacy: শুধু PyFlow WSGI মোড (wsgiref)"""
    from wsgiref.simple_server import make_server
    from core.application import Application
    from config.routes import build_router

    config = get_config()
    router = build_router()
    app = Application(router, config)

    os.makedirs("storage/logs", exist_ok=True)
    os.makedirs("storage/sessions", exist_ok=True)

    print(f"🚀 {config['APP_NAME']} চলছে (WSGI): http://127.0.0.1:{port}")
    print(f"   DB Driver: {config['DB_DRIVER']}  |  Debug: {config['APP_DEBUG']}")
    print("   ℹ️  FastAPI ছাড়া — /api/docs উপলব্ধ নয়")
    print("   বন্ধ করতে Ctrl+C চাপুন\n")

    with make_server("127.0.0.1", port, app) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nসার্ভার বন্ধ হয়ে গেছে।")


def run_asgi(port: int):
    """FastAPI + PyFlow একসাথে (uvicorn ASGI)"""
    try:
        import uvicorn
    except ImportError:
        print("❌ uvicorn ইনস্টল নেই। চালান: python -m pip install uvicorn[standard]")
        print("   অথবা: python run.py --wsgi (শুধু PyFlow মোড)")
        sys.exit(1)

    config = get_config()
    os.makedirs("storage/logs", exist_ok=True)
    os.makedirs("storage/sessions", exist_ok=True)

    print(f"🚀 {config['APP_NAME']} চলছে (FastAPI + PyFlow): http://127.0.0.1:{port}")
    print(f"   DB Driver: {config['DB_DRIVER']}  |  Debug: {config['APP_DEBUG']}")
    print(f"   📖 Swagger UI:  http://127.0.0.1:{port}/api/docs")
    print(f"   📋 ReDoc:       http://127.0.0.1:{port}/api/redoc")
    print(f"   🔗 API Root:    http://127.0.0.1:{port}/api")
    print("   বন্ধ করতে Ctrl+C চাপুন\n")

    reload = config.get("APP_DEBUG", False)
    uvicorn.run(
        "core.asgi_bridge:application",
        host="127.0.0.1",
        port=port,
        reload=reload,
        log_level="info",
    )


def main():
    parser = argparse.ArgumentParser(description="PyFlow Development Server Launcher")
    parser.add_argument(
        "port",
        type=int,
        nargs="?",
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )
    parser.add_argument(
        "--wsgi",
        action="store_true",
        help="Run in legacy WSGI-only mode (without FastAPI/ASGI bridge)"
    )

    args = parser.parse_args()

    if args.wsgi:
        run_wsgi(args.port)
    else:
        run_asgi(args.port)


if __name__ == "__main__":
    main()
