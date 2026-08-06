import os
import json
import datetime
import threading
import logging
from logging.handlers import RotatingFileHandler
from config.config import get_config

_local = threading.local()

def set_current_request(request):
    _local.current_request = request

def get_current_request():
    return getattr(_local, "current_request", None)

class Logger:
    EMERGENCY = 'emergency'
    ALERT = 'alert'
    CRITICAL = 'critical'
    ERROR = 'error'
    WARNING = 'warning'
    NOTICE = 'notice'
    INFO = 'info'
    DEBUG = 'debug'

    _levels = {
        EMERGENCY: 0,
        ALERT: 1,
        CRITICAL: 2,
        ERROR: 3,
        WARNING: 4,
        NOTICE: 5,
        INFO: 6,
        DEBUG: 7
    }

    _initialized = False
    _app_logger = None
    _err_logger = None
    _log_file = 'storage/logs/app.log'
    _error_log_file = 'storage/logs/error.log'

    @classmethod
    def init(cls):
        if cls._initialized:
            return
        
        config = get_config()
        cls._log_file = config.get("LOG_FILE", "storage/logs/app.log")
        log_dir = os.path.dirname(os.path.abspath(cls._log_file))
        os.makedirs(log_dir, exist_ok=True)
        cls._error_log_file = os.path.join(log_dir, "error.log")

        max_bytes = 10 * 1024 * 1024  # 10MB
        backup_count = 5

        cls._app_logger = logging.getLogger("pyflow.app_file")
        cls._app_logger.setLevel(logging.DEBUG)
        cls._app_logger.propagate = False
        if not cls._app_logger.handlers:
            handler = RotatingFileHandler(cls._log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(message)s"))
            cls._app_logger.addHandler(handler)

        cls._err_logger = logging.getLogger("pyflow.error_file")
        cls._err_logger.setLevel(logging.WARNING)
        cls._err_logger.propagate = False
        if not cls._err_logger.handlers:
            handler = RotatingFileHandler(cls._error_log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(message)s"))
            cls._err_logger.addHandler(handler)

        cls._initialized = True

    @classmethod
    def emergency(cls, message, context=None): cls.log(cls.EMERGENCY, message, context)
    @classmethod
    def alert(cls, message, context=None): cls.log(cls.ALERT, message, context)
    @classmethod
    def critical(cls, message, context=None): cls.log(cls.CRITICAL, message, context)
    @classmethod
    def error(cls, message, context=None): cls.log(cls.ERROR, message, context)
    @classmethod
    def warning(cls, message, context=None): cls.log(cls.WARNING, message, context)
    @classmethod
    def notice(cls, message, context=None): cls.log(cls.NOTICE, message, context)
    @classmethod
    def info(cls, message, context=None): cls.log(cls.INFO, message, context)
    @classmethod
    def debug(cls, message, context=None): cls.log(cls.DEBUG, message, context)

    @classmethod
    def log(cls, level, message, context=None):
        if context is None:
            context = {}
            
        cls.init()
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get request info
        request = get_current_request()
        ip = "0.0.0.0"
        user_id = "guest"
        request_uri = "CLI"
        
        if request is not None:
            ip = request.ip()
            request_uri = f"{request.method} {request.path}"
            session = getattr(request, "session", None)
            if session and session.get("user_id"):
                user_id = str(session.get("user_id"))
                
        context_str = f" | Context: {json.dumps(context, ensure_ascii=False)}" if context else ""
        
        log_entry = f"[{timestamp}] {level.upper()} | IP: {ip} | User: {user_id} | {request_uri} | {message}{context_str}"
        
        try:
            if level in (cls.EMERGENCY, cls.ALERT, cls.CRITICAL, cls.ERROR):
                cls._err_logger.warning(log_entry)
            else:
                cls._app_logger.info(log_entry)
        except Exception as e:
            print(f"Logging failed: {e}")
            
        # Also integrate with the standard python logging, so it shows up in the Debug Bar!
        logger = logging.getLogger("pyflow")
        level_map = {
            cls.EMERGENCY: logging.CRITICAL,
            cls.ALERT: logging.CRITICAL,
            cls.CRITICAL: logging.CRITICAL,
            cls.ERROR: logging.ERROR,
            cls.WARNING: logging.WARNING,
            cls.NOTICE: logging.INFO,
            cls.INFO: logging.INFO,
            cls.DEBUG: logging.DEBUG,
        }
        py_level = level_map.get(level, logging.INFO)
        logger.log(py_level, f"{message}{context_str}")

        if level in (cls.EMERGENCY, cls.ALERT, cls.CRITICAL):
            cls.send_alert(level, message, context)

    @classmethod
    def send_alert(cls, level, message, context):
        import sys
        print(f"CRITICAL ALERT: {level.upper()} - {message}", file=sys.stderr)

    @classmethod
    def log_query(cls, query, bindings=None, execution_time=None):
        if bindings is None:
            bindings = []
        context = {
            'query': query,
            'bindings': bindings,
            'execution_time': execution_time
        }
        if execution_time and execution_time > 100:  # in ms
            cls.warning("Slow query detected", context)
        else:
            cls.debug("Database query executed", context)

    @classmethod
    def log_activity(cls, action, details=None):
        if details is None:
            details = {}
        request = get_current_request()
        user_agent = "Unknown"
        referer = "Direct"
        if request is not None:
            user_agent = request.header("User-Agent", "Unknown")
            referer = request.header("Referer", "Direct")
            
        context = {
            **details,
            'action': action,
            'user_agent': user_agent,
            'referer': referer
        }
        cls.info(f"User activity: {action}", context)

    @classmethod
    def log_security(cls, event, details=None):
        if details is None:
            details = {}
        context = {
            **details,
            'event': event,
            'severity': 'high'
        }
        cls.warning(f"Security event: {event}", context)

    @classmethod
    def get_recent_logs(cls, lines=50, file_path=None):
        cls.init()
        if file_path is None:
            file_path = cls._log_file
            
        if not os.path.exists(file_path):
            return []
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                logs = f.readlines()
            return logs[::-1][:lines]
        except Exception:
            return []
