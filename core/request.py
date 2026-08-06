"""
core/request.py
================
WSGI environ-কে সহজে ব্যবহারযোগ্য Request অবজেক্টে রূপান্তর করে।
GET/POST/JSON/ফাইল আপলোড/কুকি/হেডার সবকিছু এখান থেকে পাওয়া যায়।

উন্নয়ন (v2):
  - cgi.FieldStorage (Python 3.11-এ deprecated, 3.13-এ removed) বাদ দেওয়া হয়েছে।
    পরিবর্তে email.parser ও stdlib দিয়ে multipart/form-data পার্স করা হয়।
  - is_ajax(), wants_json(), scheme property যোগ করা হয়েছে।
"""

import json
import re
from urllib.parse import parse_qs
from http.cookies import SimpleCookie
from io import BytesIO
from email.parser import BytesHeaderParser


class UploadedFile:
    def __init__(self, filename, content_type, data: bytes):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    def read(self) -> bytes:
        return self._data

    def save(self, destination_path: str):
        with open(destination_path, "wb") as f:
            f.write(self._data)

    @property
    def size(self) -> int:
        return len(self._data)


def _parse_multipart(body: bytes, boundary: str) -> tuple[dict, dict]:
    """
    multipart/form-data body পার্স করে (fields, files) টাপল রিটার্ন করে।
    Python stdlib শুধু email.parser ব্যবহার করা হয় - cgi নির্ভরতা নেই।
    """
    fields = {}
    files = {}

    # boundary bytes-এ রূপান্তর
    sep = f"--{boundary}".encode()
    end_sep = f"--{boundary}--".encode()

    parts = body.split(sep)
    for part in parts:
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.startswith(b"--"):
            break

        # header ও body আলাদা করা (প্রথম \r\n\r\n বা \n\n)
        if b"\r\n\r\n" in part:
            raw_headers, _, field_body = part.partition(b"\r\n\r\n")
        elif b"\n\n" in part:
            raw_headers, _, field_body = part.partition(b"\n\n")
        else:
            continue

        # trailing \r\n সরানো
        field_body = field_body.rstrip(b"\r\n")

        # হেডার পার্স করা
        parser = BytesHeaderParser()
        headers = parser.parsebytes(raw_headers + b"\r\n\r\n")

        content_disposition = headers.get("Content-Disposition", "")
        content_type = headers.get("Content-Type", "text/plain")

        # name এবং filename বের করা
        name_match = re.search(r'name="([^"]*)"', content_disposition)
        filename_match = re.search(r'filename="([^"]*)"', content_disposition)

        if not name_match:
            continue

        field_name = name_match.group(1)

        if filename_match:
            filename = filename_match.group(1)
            files[field_name] = UploadedFile(filename, content_type, field_body)
        else:
            fields[field_name] = field_body.decode("utf-8", errors="replace")

    return fields, files


class Request:
    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB - বড় payload দিয়ে DoS ঠেকাতে

    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/") or "/"
        self.query = parse_qs(environ.get("QUERY_STRING", ""))
        self.params = {}  # router বসিয়ে দেবে (dynamic segment গুলো)
        self._files = {}
        self._post = {}
        self._json = None
        self._parse_body()

    # ------------------------------------------------------------ body parsing
    def _parse_body(self):
        if self.method not in ("POST", "PUT", "PATCH"):
            return

        content_type = self.environ.get("CONTENT_TYPE", "")
        try:
            content_length = int(self.environ.get("CONTENT_LENGTH", 0) or 0)
        except ValueError:
            content_length = 0

        if content_length > self.MAX_BODY_SIZE:
            raise ValueError("Request body খুব বড় (সর্বোচ্চ 10MB অনুমোদিত)")

        if content_length == 0:
            return

        raw_body = self.environ["wsgi.input"].read(content_length)

        if "multipart/form-data" in content_type:
            # boundary বের করা (cgi ছাড়াই)
            boundary_match = re.search(r"boundary=([^\s;]+)", content_type)
            if boundary_match:
                boundary = boundary_match.group(1).strip('"')
                self._post, self._files = _parse_multipart(raw_body, boundary)

        elif "application/json" in content_type:
            try:
                self._json = json.loads(raw_body.decode("utf-8")) if raw_body else {}
            except json.JSONDecodeError:
                self._json = {}

        else:
            # application/x-www-form-urlencoded (সাধারণ HTML form)
            parsed = parse_qs(raw_body.decode("utf-8"))
            self._post = {k: v[0] for k, v in parsed.items()}

    # ------------------------------------------------------------------ getters
    def input(self, key, default=None):
        """GET, POST, JSON body - যেকোনো জায়গা থেকে ভ্যালু খোঁজে (Laravel-এর মতো)"""
        if key in self._post:
            return self._post[key]
        if self._json and key in self._json:
            return self._json[key]
        if key in self.query:
            return self.query[key][0]
        if key in self.params:
            return self.params[key]
        return default

    def all(self) -> dict:
        """সব ইনপুট একটা dict-এ মার্জ করে রিটার্ন করে"""
        data = {}
        data.update({k: v[0] for k, v in self.query.items()})
        data.update(self._post)
        if self._json:
            data.update(self._json)
        return data

    def only(self, *keys) -> dict:
        """নির্দিষ্ট কিছু key-এর ইনপুট নেওয়া"""
        return {k: self.input(k) for k in keys if self.input(k) is not None}

    def except_keys(self, *keys) -> dict:
        """নির্দিষ্ট কিছু key বাদ দিয়ে বাকি সব ইনপুট নেওয়া"""
        all_data = self.all()
        return {k: v for k, v in all_data.items() if k not in keys}

    def file(self, key) -> UploadedFile:
        return self._files.get(key)

    def has_file(self, key) -> bool:
        return key in self._files

    def header(self, name, default=None):
        name_upper = name.upper().replace("-", "_")
        if name_upper in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            key = name_upper
        else:
            key = "HTTP_" + name_upper
        return self.environ.get(key, default)

    def cookie(self, name, default=None):
        raw = self.environ.get("HTTP_COOKIE", "")
        jar = SimpleCookie()
        jar.load(raw)
        if name in jar:
            return jar[name].value
        return default

    def ip(self) -> str:
        # X-Forwarded-For শুধুমাত্র তখনই ব্যবহার করব যখন TRUST_PROXY=true কনফিগার করা থাকবে
        from config.config import get_config
        try:
            config = get_config()
            trust_proxy = str(config.get("TRUST_PROXY", "false")).lower() in ("true", "1")
        except Exception:
            trust_proxy = False

        if trust_proxy:
            cf_ip = self.environ.get("HTTP_CF_CONNECTING_IP")
            if cf_ip:
                return cf_ip.strip()
            forwarded = self.environ.get("HTTP_X_FORWARDED_FOR")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return self.environ.get("REMOTE_ADDR", "0.0.0.0")

    def is_json(self) -> bool:
        """Content-Type application/json কিনা"""
        return "application/json" in self.environ.get("CONTENT_TYPE", "")

    def is_ajax(self) -> bool:
        """XMLHttpRequest বা Fetch API দিয়ে পাঠানো রিকোয়েস্ট কিনা"""
        return (
            self.header("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in self.header("Accept", "")
        )

    def wants_json(self) -> bool:
        """ক্লায়েন্ট JSON রেসপন্স চাইছে কিনা (API ক্লায়েন্ট detect করতে)"""
        accept = self.header("Accept", "")
        return "application/json" in accept or self.is_json()

    @property
    def scheme(self) -> str:
        """http নাকি https"""
        return self.environ.get("wsgi.url_scheme", "http")

    def full_url(self) -> str:
        host = self.environ.get("HTTP_HOST", "localhost")
        return f"{self.scheme}://{host}{self.path}"

    def query_string(self) -> str:
        return self.environ.get("QUERY_STRING", "")
