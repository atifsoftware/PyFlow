import os
import shutil
import sys

def main():
    # Find the directories of app, core, config in the installed package
    import app as app_mod
    import core as core_mod
    import config as config_mod

    target_dir = os.getcwd()
    
    # We want to copy these packages
    modules = [
        (app_mod, "app"),
        (core_mod, "core"),
        (config_mod, "config")
    ]
    
    print("PyFlow project initializing...")
    for mod, name in modules:
        src = os.path.dirname(mod.__file__)
        dest = os.path.join(target_dir, name)
        if not os.path.exists(dest):
            shutil.copytree(src, dest)
            print(f" -> Created directory: {name}")
        else:
            print(f" -> {name} already exists.")
            
    # Also write a standard run.py in the current folder if it doesn't exist
    run_py_dest = os.path.join(target_dir, "run.py")
    if not os.path.exists(run_py_dest):
        run_py_content = """import sys
import os
import argparse

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config.config import get_config

def run_wsgi(port: int):
    from wsgiref.simple_server import make_server
    from core.application import Application
    from config.routes import build_router

    config = get_config()
    router = build_router()
    app = Application(router, config)

    os.makedirs("storage/logs", exist_ok=True)
    os.makedirs("storage/sessions", exist_ok=True)

    print(f"🚀 {config['APP_NAME']} running (WSGI): http://127.0.0.1:{port}")
    with make_server("127.0.0.1", port, app) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\nServer stopped.")

def run_asgi(port: int):
    try:
        import uvicorn
    except ImportError:
        print("❌ uvicorn not installed. Run: pip install uvicorn[standard]")
        sys.exit(1)

    config = get_config()
    os.makedirs("storage/logs", exist_ok=True)
    os.makedirs("storage/sessions", exist_ok=True)

    print(f"🚀 {config['APP_NAME']} running (FastAPI + PyFlow): http://127.0.0.1:{port}")
    reload = config.get("APP_DEBUG", False)
    uvicorn.run("core.asgi_bridge:application", host="127.0.0.1", port=port, reload=reload, log_level="info")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, nargs="?", default=8000)
    parser.add_argument("--wsgi", action="store_true")
    args = parser.parse_args()

    if args.wsgi:
        run_wsgi(args.port)
    else:
        run_asgi(args.port)

if __name__ == "__main__":
    main()
"""
        with open(run_py_dest, "w", encoding="utf-8") as f:
            f.write(run_py_content)
        print(" -> Created file: run.py")
        
    print("\nSUCCESS: PyFlow template loaded successfully! Run 'python run.py' to start the development server.")

if __name__ == "__main__":
    main()
