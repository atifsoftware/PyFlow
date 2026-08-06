"""
core/application.py
====================
মূল WSGI Application। প্রতিটা HTTP রিকোয়েস্টের জীবনচক্র এখানে হ্যান্ডেল হয়:
  1. Request পার্স করা
  2. Session লোড করা (cookie থেকে)
  3. Router দিয়ে handler খুঁজে বের করা
  4. Middleware চেইন চালানো
  5. Controller action কল করা
  6. Response পাঠানো + session cookie সেট করা + security headers অ্যাটাচ করা

কোনো এক্সটার্নাল ওয়েব ফ্রেমওয়ার্ক (Flask/Django) ব্যবহার হয়নি - শুধু stdlib।
"""

import sys
import traceback
import logging
import json
from core.request import Request
from core.response import Response
from core.session import Session
from core.view import TemplateEngine, ViewError
from core.database import Database, QueryError, Profiler
from core.security import RateLimiter
from core.static import serve_static


class ProfilerLogHandler(logging.Handler):
    """লগিং সিস্টেমের লগগুলোকে প্রফাইলারে পাঠায় যাতে ডিবাগ বারে দেখা যায়"""
    def emit(self, record):
        try:
            msg = self.format(record)
            Profiler.log_message(record.levelname, msg)
        except Exception:
            self.handleError(record)


class Application:
    def __init__(self, router, config: dict):
        self.router = router
        self.config = config
        self.debug = config.get("APP_DEBUG", False)
        self.view_engine = TemplateEngine(
            views_dir=config.get("VIEWS_DIR", "app/views"),
            cache_enabled=not self.debug,
        )
        Database.init(config)
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            filename=self.config.get("LOG_FILE", "storage/logs/app.log"),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
        )
        self.logger = logging.getLogger("pyflow")
        
        # প্রফাইলার হ্যান্ডলার যোগ করা
        self.logger.addHandler(ProfilerLogHandler())

    # -------------------------------------------------------------- WSGI call
    def __call__(self, environ, start_response):
        try:
            response = self._handle_request(environ)
        except Exception as exc:
            response = self._handle_exception(exc)
        finally:
            Database.close()

        start_response(response.status_line(), response.wsgi_headers())
        return response.wsgi_body()

    def _handle_request(self, environ) -> Response:
        path_info = environ.get("PATH_INFO", "/")
        if path_info.startswith("/static/"):
            return serve_static(path_info, static_root=self.config.get("STATIC_DIR", "public/static"))

        # প্রফাইলার শুরু করা
        Profiler.start_request(environ.get("REQUEST_METHOD", "GET"), path_info)

        request = Request(environ)
        from core.logger import set_current_request
        set_current_request(request)

        # login-attempt spam ঠেকাতে একটা global soft-limit (per-IP)
        global_key = f"global:{request.ip()}"
        if RateLimiter.too_many_attempts(global_key, max_attempts=300, window_seconds=60):
            return Response("429 Too Many Requests", status=429)
        RateLimiter.hit(global_key)

        cookie_session_id = request.cookie(Session.COOKIE_NAME)
        session = Session(
            storage_dir=self.config.get("SESSION_DIR", "storage/sessions"),
            session_id=cookie_session_id,
        )
        request.session = session

        # HTML ফর্ম PUT/DELETE সরাসরি পাঠাতে পারে না, তাই hidden _method
        # ফিল্ড দিয়ে override করার সুযোগ দেওয়া হয়েছে (শুধু POST-এর ক্ষেত্রে)
        if request.method == "POST":
            override = request.input("_method")
            if override and override.upper() in ("PUT", "PATCH", "DELETE"):
                request.method = override.upper()

        route, params = self.router.resolve(request.method, request.path)

        if route is None:
            response = self._render_error_page(404, request_path=request.path)
        elif route == "METHOD_NOT_ALLOWED":
            response = Response("405 Method Not Allowed", status=405)
        else:
            request.params = params or {}
            response = self._run_route(route, request, session)

        # সেশন কুকি প্রতিটা রেসপন্সেই রিফ্রেশ করে দেওয়া হয় (expiry বাড়ানোর জন্য),
        # redirect হলেও এটা দরকার তাই কোনো শর্ত ছাড়াই সেট করা হচ্ছে
        response.set_cookie(
            Session.COOKIE_NAME,
            session.session_id,
            max_age=Session.LIFETIME_SECONDS,
            http_only=True,
            secure=self.config.get("SESSION_SECURE_COOKIE", False),
            same_site="Lax",
        )

        # ডিবাগ বার ইনজেক্ট করা
        if self.debug and response.headers.get("Content-Type", "").startswith("text/html"):
            response = self._inject_debug_bar(response, request, session)

        # Gzip compression — client Accept-Encoding: gzip চাইলে compress করা হবে
        if getattr(request, "_gzip_requested", False):
            response = self._compress_response(response)

        return response

    def _compress_response(self, response: Response) -> Response:
        """gzip দিয়ে response body compress করে"""
        import gzip
        compressible = ("text/html", "text/css", "text/javascript",
                        "application/json", "application/javascript", "text/plain")
        content_type = response.headers.get("Content-Type", "")
        is_compressible = any(ct in content_type for ct in compressible)
        if not is_compressible:
            return response
        try:
            body_bytes = b"".join(response.wsgi_body())
            if len(body_bytes) < 1024:
                # ছোট response compress করা লাভজনক নয়
                response._body = body_bytes
                return response
            compressed = gzip.compress(body_bytes, compresslevel=6)
            response._body = compressed
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = str(len(compressed))
            response.headers["Vary"] = "Accept-Encoding"
        except Exception:
            pass
        return response



    def _inject_debug_bar(self, response: Response, request: Request, session: Session) -> Response:
        """রেসপন্স এইচটিএমএল-এ একটি কাস্টম ডিবাগ বার যুক্ত করে"""
        try:
            body_bytes = b"".join(response.wsgi_body())
            html_text = body_bytes.decode("utf-8")
        except Exception:
            return response

        if "</body>" not in html_text:
            return response

        prof_data = Profiler.get_data()
        queries = prof_data["queries"]
        logs = prof_data["logs"]
        duration = prof_data["duration"]
        
        # HTML template of the debug bar
        debug_html = f"""
<!-- PyFlow Debug Bar -->
<style>
    #pyflow-debugbar-header-info {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    @media (max-width: 768px) {
        .pm-db-hide-mobile {
            display: none !important;
        }
        #pyflow-debugbar-header {
            flex-direction: column;
            align-items: flex-start !important;
            gap: 8px;
            padding: 10px 12px !important;
        }
        #pyflow-debugbar-header-info {
            flex-wrap: wrap;
            gap: 8px !important;
        }
    }
</style>
<div id="pyflow-debugbar" style="position: fixed; bottom: 0; left: 0; right: 0; background: rgba(20, 20, 25, 0.95); border-top: 2px solid #5a32a8; color: #e1e1e6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13px; z-index: 999999; box-shadow: 0 -4px 12px rgba(0,0,0,0.5); backdrop-filter: blur(8px);">
    <div id="pyflow-debugbar-header" style="display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; cursor: pointer; border-bottom: 1px solid #333;" onclick="togglePyFlowDebugbar()">
        <div id="pyflow-debugbar-header-info">
            <span style="font-weight: bold; color: #9d4edd; display: flex; align-items: center; gap: 4px;">
                ⚡ PyFlow Debugbar
            </span>
            <span title="Request Method & Path" style="background: #24242e; padding: 2px 6px; border-radius: 4px; font-size: 11px; border: 1px solid #3c3c4e;">
                {request.method} {request.path}
            </span>
            <span title="Status Code" style="color: {'#52b788' if response.status_code < 400 else '#ff595e'}; font-weight: bold;">
                {response.status_code}
            </span>
            <span title="Total Execution Time" style="display: flex; align-items: center; gap: 4px;">
                ⏱️ {duration:.1f} ms
            </span>
            <span title="Database Queries" style="display: flex; align-items: center; gap: 4px;">
                🗄️ {len(queries)} Queries ({sum(q['duration'] for q in queries):.1f} ms)
            </span>
            <span title="Logs Count" style="display: flex; align-items: center; gap: 4px;">
                📋 {len(logs)} Logs
            </span>
        </div>
        <div class="pm-db-hide-mobile" style="color: #888;">[Click to Toggle]</div>
    </div>

    
    <div id="pyflow-debugbar-content" style="display: none; max-height: 350px; overflow-y: auto; padding: 16px; border-top: 1px solid #222;">
        <!-- Tabs -->
        <div style="display: flex; gap: 8px; margin-bottom: 16px; border-bottom: 1px solid #333; padding-bottom: 8px;">
            <button onclick="switchPyFlowTab('queries')" class="pm-tab-btn pm-tab-active" style="background: none; border: none; color: #fff; cursor: pointer; padding: 6px 12px; font-weight: bold;">Queries ({len(queries)})</button>
            <button onclick="switchPyFlowTab('session')" class="pm-tab-btn" style="background: none; border: none; color: #aaa; cursor: pointer; padding: 6px 12px; font-weight: bold;">Session</button>
            <button onclick="switchPyFlowTab('logs')" class="pm-tab-btn" style="background: none; border: none; color: #aaa; cursor: pointer; padding: 6px 12px; font-weight: bold;">Logs ({len(logs)})</button>
        </div>
        
        <!-- Queries Tab -->
        <div id="pm-tab-queries" class="pm-tab-content">
            {f'<p style="color: #888; text-align: center; margin: 20px 0;">কোনো Database Query চালানো হয়নি।</p>' if not queries else ''}
            <div style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; min-width: 600px;">
                    <thead>
                        <tr style="border-bottom: 1px solid #444; color: #aaa;">
                            <th style="padding: 8px;">SQL Statement</th>
                            <th style="padding: 8px; width: 250px;">Parameters</th>
                            <th style="padding: 8px; width: 100px; text-align: right;">Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(f'''
                        <tr style="border-bottom: 1px solid #2d2d38;">
                            <td style="padding: 8px; font-family: monospace; color: #70e000; font-size: 12px; word-break: break-all;">{q['sql']}</td>
                            <td style="padding: 8px; font-family: monospace; color: #f72585; font-size: 11px;">{q['params']}</td>
                            <td style="padding: 8px; text-align: right; color: {'#ff595e' if q['duration'] > 100 else '#ffb703'}; font-weight: bold;">{q['duration']:.2f} ms</td>
                        </tr>
                        ''' for q in queries)}
                    </tbody>
                </table>
            </div>
        </div>

        
        <!-- Session Tab -->
        <div id="pm-tab-session" class="pm-tab-content" style="display: none;">
            <pre style="background: #121216; padding: 12px; border-radius: 6px; border: 1px solid #2d2d38; overflow-x: auto; color: #4cc9f0; font-family: monospace; font-size: 12px; margin: 0;">{json.dumps(session._data, indent=2, ensure_ascii=False) if session._data else '{}'}</pre>
        </div>
        
        <!-- Logs Tab -->
        <div id="pm-tab-logs" class="pm-tab-content" style="display: none;">
            {f'<p style="color: #888; text-align: center; margin: 20px 0;">রিকোয়েস্টে কোনো লগ তৈরি হয়নি।</p>' if not logs else ''}
            <div style="display: flex; flex-direction: column; gap: 6px;">
                {"".join(f'''
                <div style="font-family: monospace; padding: 6px 12px; border-radius: 4px; background: #181822; border-left: 4px solid {'#ff595e' if l['level'] == 'ERROR' else '#3a86c8' if l['level'] == 'INFO' else '#ffb703'};">
                    <span style="color: #888; font-size: 11px; margin-right: 8px;">[{l['time']}]</span>
                    <span style="font-weight: bold; color: {'#ff595e' if l['level'] == 'ERROR' else '#4cc9f0' if l['level'] == 'INFO' else '#ffb703'}; margin-right: 8px;">{l['level']}</span>
                    <span style="color: #ddd; font-size: 12px;">{l['message']}</span>
                </div>
                ''' for l in logs)}
            </div>
        </div>
    </div>
</div>

<script>
function togglePyFlowDebugbar() {{
    var content = document.getElementById('pyflow-debugbar-content');
    if (content.style.display === 'none') {{
        content.style.display = 'block';
        localStorage.setItem('pyflow_debugbar_open', 'true');
    }} else {{
        content.style.display = 'none';
        localStorage.setItem('pyflow_debugbar_open', 'false');
    }}
}}

// পেজ লোডের সময় পূর্ববর্তী অবস্থা বজায় রাখা
if (localStorage.getItem('pyflow_debugbar_open') === 'true') {{
    document.getElementById('pyflow-debugbar-content').style.display = 'block';
}}

function switchPyFlowTab(tabName) {{
    // সব ট্যাব কনটেন্ট হাইড করা
    var contents = document.getElementsByClassName('pm-tab-content');
    for (var i = 0; i < contents.length; i++) {{
        contents[i].style.display = 'none';
    }}
    
    // সব ট্যাব বাটন ইনঅ্যাক্টিভ করা
    var buttons = document.getElementsByClassName('pm-tab-btn');
    for (var i = 0; i < buttons.length; i++) {{
        buttons[i].style.color = '#aaa';
        buttons[i].classList.remove('pm-tab-active');
        buttons[i].style.borderBottom = 'none';
    }}
    
    // সিলেক্টেড ট্যাব ও বাটন অ্যাক্টিভ করা
    document.getElementById('pm-tab-' + tabName).style.display = 'block';
    var event = window.event;
    var target = event ? event.target : null;
    if (target) {{
        target.style.color = '#fff';
        target.classList.add('pm-tab-active');
    }}
}}
</script>
"""
        # HTML </body> ট্যাগের আগে ইনজেক্ট করা
        html_text = html_text.replace("</body>", f"{debug_html}</body>")
        return Response(html_text.encode("utf-8"), status=response.status_code, headers=response.headers)

    def _run_route(self, route, request, session) -> Response:
        for mw in route.middleware:
            result = mw(request, session)
            if result is not None:
                return result

        import inspect
        try:
            sig = inspect.signature(route.handler)
            has_view_engine = len(sig.parameters) >= 3 or any(p.name == 'view_engine' for p in sig.parameters.values())
        except ValueError:
            # Fallback if signature cannot be obtained
            has_view_engine = True

        if has_view_engine:
            controller_instance_or_result = route.handler(request, session, self.view_engine)
        else:
            controller_instance_or_result = route.handler(request, session)


        if isinstance(controller_instance_or_result, Response):
            return controller_instance_or_result
        if isinstance(controller_instance_or_result, str):
            return Response.html(controller_instance_or_result)
        if isinstance(controller_instance_or_result, (dict, list)):
            return Response.json(controller_instance_or_result)
        return Response.server_error("Handler থেকে অবৈধ রিটার্ন টাইপ")

    def _render_error_page(self, status: int, request_path: str = "", extra: dict = None) -> Response:
        """Error template render করে। না পেলে fallback plain HTML দেয়।"""
        context = {
            "app_name": self.config.get("APP_NAME", "PyFlow"),
            "request_path": request_path,
            "status": status,
        }
        if extra:
            context.update(extra)
        try:
            html = self.view_engine.render(f"errors.{status}", context)
            return Response(html.encode("utf-8") if isinstance(html, str) else html,
                           status=status,
                           headers={"Content-Type": "text/html; charset=utf-8"})
        except Exception:
            # Template না থাকলে minimal HTML
            messages = {
                404: "পাতা পাওয়া যায়নি",
                403: "অনুমতি নেই",
                429: "অনেক বেশি Request",
                500: "সার্ভার সমস্যা হয়েছে",
            }
            msg = messages.get(status, "Error")
            html = f"""<!DOCTYPE html><html lang='bn'><head>
<meta charset='UTF-8'><title>{status} {msg}</title>
<style>body{{background:#0f172a;color:#e2e8f0;font-family:sans-serif;
  display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;}}
.box{{padding:48px;}} .code{{font-size:6rem;font-weight:900;color:#6366f1;line-height:1;}}
</style></head><body><div class='box'>
<div class='code'>{status}</div><h1>{msg}</h1>
<p><a href='/' style='color:#818cf8;'>← হোমে ফিরুন</a></p>
</div></body></html>"""
            return Response(html.encode("utf-8"), status=status,
                           headers={"Content-Type": "text/html; charset=utf-8"})

    def _handle_exception(self, exc: Exception) -> Response:
        self.logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
        if self.debug:
            # Debug mode: Stack trace সহ 500 page
            try:
                import traceback as tb
                frames_raw = tb.extract_tb(exc.__traceback__)
                stack_frames = []
                for frame in reversed(frames_raw):
                    stack_frames.append({
                        "file": frame.filename,
                        "line": frame.lineno,
                        "function": frame.name,
                        "is_app": "PyFlow" in frame.filename or "app" in frame.filename.lower(),
                    })
                context = {
                    "debug_mode": True,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "stack_frames": stack_frames,
                }
                return self._render_error_page(500, extra=context)
            except Exception:
                from core.error_handler import IntelligentErrorHandler
                html_body = IntelligentErrorHandler.render(exc)
                return Response.html(html_body, status=500)
        return self._render_error_page(500, extra={"debug_mode": False})
