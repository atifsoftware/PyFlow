"""
core/static.py
===============
DEV সার্ভারের জন্য সাধারণ static file handler (CSS/JS/images)।
প্রোডাকশনে আসল Apache/Nginx-কে static ফাইল সার্ভ করতে দেওয়াই ভালো অভ্যাস -
এইটা শুধু ডেভেলপমেন্ট সুবিধার জন্য।
"""

import os
import mimetypes
from core.response import Response


def serve_static(path: str, static_root: str = "public/static") -> Response:
    # path traversal (../../etc/passwd) ঠেকানোর জন্য realpath দিয়ে বাউন্ডারি চেক
    relative = path[len("/static/"):] if path.startswith("/static/") else path
    real_root = os.path.realpath(static_root)
    target = os.path.realpath(os.path.join(static_root, relative))

    if not target.startswith(real_root) or not os.path.isfile(target):
        return Response.not_found("Static file পাওয়া যায়নি")

    content_type, _ = mimetypes.guess_type(target)
    with open(target, "rb") as f:
        body = f.read()

    resp = Response(body, status=200, content_type=content_type or "application/octet-stream")
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp
