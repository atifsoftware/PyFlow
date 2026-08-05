"""
core/storage.py
================
Generic File Storage সিস্টেম। ফাইল আপলোড ও ম্যানেজমেন্টের জন্য।
PHP-এর Storage facade-এর সমতুল্য।

ব্যবহার:
    from core.storage import Storage
    from core.request import UploadedFile

    # ফাইল সেভ করা
    path = Storage.put("uploads/avatars", request.file("avatar"))
    # => "uploads/avatars/1720000000_photo.jpg"

    # Public URL পাওয়া
    url = Storage.url(path)
    # => "/static/uploads/avatars/1720000000_photo.jpg"

    # ফাইল মুছে দেওয়া
    Storage.delete(path)

    # ফাইল পড়া
    data = Storage.get_bytes(path)
"""

import os
import time
import re


class Storage:
    # সব ডিস্ক public/ ফোল্ডারের ভেতরে থাকবে (static serving-এর জন্য)
    STATIC_ROOT = "public/static"

    @classmethod
    def _resolve_path(cls, relative_path: str) -> str:
        """Relative path কে absolute filesystem path-এ রূপান্তর করে"""
        # Security: path traversal attack প্রতিরোধ
        safe = os.path.normpath(relative_path).replace("\\", "/")
        if safe.startswith(".."):
            raise ValueError(f"নিরাপত্তার জন্য অবৈধ path: {relative_path}")
        return os.path.join(cls.STATIC_ROOT, safe)

    @classmethod
    def _safe_filename(cls, original_name: str) -> str:
        """ফাইল নাম sanitize করে Unix-safe নাম তৈরি করে, collision ঠেকাতে timestamp যোগ করে"""
        base, _, ext = original_name.rpartition(".")
        base = re.sub(r"[^\w\-]", "_", base)[:60]
        ext = re.sub(r"[^\w]", "", ext)[:8].lower()
        timestamp = int(time.time())
        return f"{timestamp}_{base}.{ext}" if ext else f"{timestamp}_{base}"

    @classmethod
    def put(cls, directory: str, file_or_bytes, filename: str = None) -> str:
        """
        ফাইল সেভ করে relative path রিটার্ন করে।

        Args:
            directory: ফোল্ডার path যেমন "uploads/avatars"
            file_or_bytes: UploadedFile অবজেক্ট বা bytes
            filename: কাস্টম ফাইল নাম (না দিলে original নাম থেকে তৈরি হবে)

        Returns:
            str: Relative path যেমন "uploads/avatars/123_photo.jpg"
        """
        from core.request import UploadedFile

        if isinstance(file_or_bytes, UploadedFile):
            data = file_or_bytes.read()
            original_name = filename or file_or_bytes.filename or "file.bin"
        elif isinstance(file_or_bytes, (bytes, bytearray)):
            data = bytes(file_or_bytes)
            original_name = filename or "file.bin"
        else:
            raise TypeError("file_or_bytes must be an UploadedFile or bytes object")

        safe_name = cls._safe_filename(original_name)
        rel_path = os.path.join(directory, safe_name).replace("\\", "/")
        abs_path = cls._resolve_path(rel_path)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "wb") as f:
            f.write(data)

        return rel_path

    @classmethod
    def put_content(cls, relative_path: str, content: str, encoding: str = "utf-8") -> str:
        """Text content সরাসরি নির্দিষ্ট path-এ সেভ করে"""
        abs_path = cls._resolve_path(relative_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding=encoding) as f:
            f.write(content)
        return relative_path.replace("\\", "/")

    @classmethod
    def get_bytes(cls, relative_path: str) -> bytes:
        """ফাইল পড়ে bytes রিটার্ন করে"""
        abs_path = cls._resolve_path(relative_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"ফাইল পাওয়া যায়নি: {relative_path}")
        with open(abs_path, "rb") as f:
            return f.read()

    @classmethod
    def get_text(cls, relative_path: str, encoding: str = "utf-8") -> str:
        """Text ফাইল পড়ে string রিটার্ন করে"""
        return cls.get_bytes(relative_path).decode(encoding)

    @classmethod
    def url(cls, relative_path: str) -> str:
        """
        Relative path থেকে Public URL তৈরি করে (static serving)
        উদাহরণ: "uploads/avatars/123.jpg" → "/static/uploads/avatars/123.jpg"
        """
        clean = relative_path.replace("\\", "/").lstrip("/")
        return f"/static/{clean}"

    @classmethod
    def exists(cls, relative_path: str) -> bool:
        """ফাইল আছে কিনা চেক করে"""
        try:
            abs_path = cls._resolve_path(relative_path)
            return os.path.isfile(abs_path)
        except ValueError:
            return False

    @classmethod
    def delete(cls, relative_path: str) -> bool:
        """ফাইল মুছে দেয়। সফল হলে True, না হলে False।"""
        try:
            abs_path = cls._resolve_path(relative_path)
            if os.path.isfile(abs_path):
                os.remove(abs_path)
                return True
            return False
        except Exception:
            return False

    @classmethod
    def size(cls, relative_path: str) -> int:
        """ফাইলের সাইজ bytes-এ রিটার্ন করে"""
        abs_path = cls._resolve_path(relative_path)
        return os.path.getsize(abs_path)

    @classmethod
    def list(cls, directory: str) -> list:
        """নির্দিষ্ট directory-র সব ফাইলের relative path list রিটার্ন করে"""
        abs_dir = cls._resolve_path(directory)
        if not os.path.isdir(abs_dir):
            return []
        files = []
        for fname in os.listdir(abs_dir):
            fpath = os.path.join(abs_dir, fname)
            if os.path.isfile(fpath):
                files.append(os.path.join(directory, fname).replace("\\", "/"))
        return files
