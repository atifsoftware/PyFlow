"""
core/response.py
=================
WSGI-compatible Response অবজেক্ট। সবসময় security headers অটো-অ্যাটাচ হয়।
"""

import json
from http.cookies import SimpleCookie
from core.security import security_headers


class Response:
    def __init__(self, body="", status=200, headers=None, content_type="text/html; charset=utf-8"):
        self.body = body
        self.status_code = status
        self.headers = headers or {}
        self.headers.setdefault("Content-Type", content_type)
        self._cookies = SimpleCookie()
        for k, v in security_headers().items():
            self.headers.setdefault(k, v)

    def set_cookie(self, key, value, max_age=None, http_only=True, secure=False, same_site="Lax", path="/"):
        self._cookies[key] = value
        self._cookies[key]["path"] = path
        if max_age is not None:
            self._cookies[key]["max-age"] = max_age
        if http_only:
            self._cookies[key]["httponly"] = True
        if secure:
            self._cookies[key]["secure"] = True
        self._cookies[key]["samesite"] = same_site

    def delete_cookie(self, key, path="/"):
        self.set_cookie(key, "", max_age=0, path=path)

    def status_line(self) -> str:
        reasons = {
            200: "OK", 201: "Created", 204: "No Content",
            301: "Moved Permanently", 302: "Found",
            400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
            404: "Not Found", 405: "Method Not Allowed",
            419: "Page Expired", 422: "Unprocessable Entity",
            429: "Too Many Requests", 500: "Internal Server Error",
        }
        return f"{self.status_code} {reasons.get(self.status_code, 'OK')}"

    def wsgi_headers(self) -> list:
        header_list = list(self.headers.items())
        for morsel in self._cookies.values():
            header_list.append(("Set-Cookie", morsel.OutputString()))
        return header_list

    def wsgi_body(self):
        if isinstance(self.body, bytes):
            return [self.body]
        body = self.body if isinstance(self.body, str) else str(self.body)
        return [body.encode("utf-8")]

    # --------------------------------------------------------- factory helpers
    @staticmethod
    def json(data, status=200):
        r = Response(json.dumps(data, ensure_ascii=False), status, content_type="application/json; charset=utf-8")
        return r

    @staticmethod
    def redirect(url, status=302):
        r = Response("", status)
        r.headers["Location"] = url
        return r

    @staticmethod
    def html(content, status=200):
        return Response(content, status, content_type="text/html; charset=utf-8")

    @staticmethod
    def not_found(message="404 Not Found"):
        return Response(message, 404)

    @staticmethod
    def forbidden(message="403 Forbidden"):
        return Response(message, 403)

    @staticmethod
    def server_error(message="500 Internal Server Error"):
        return Response(message, 500)
