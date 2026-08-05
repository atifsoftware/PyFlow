"""
core/validator.py
==================
রিকোয়েস্ট ভ্যালিডেশন ইঞ্জিন। HTML ফর্ম ও ইনপুট ডেটা ভ্যালিডেট করার জন্য।
"""

import re
from core.database import Database


class Validator:
    def __init__(self, data: dict, rules: dict, messages: dict = None):
        self.data = data or {}
        self.rules = rules or {}
        self.messages = messages or {}
        self._errors = {}
        self.validate()

    def validate(self):
        for field, rule_string in self.rules.items():
            field_rules = rule_string.split("|")
            val = self.data.get(field)

            # string inputs are stripped to avoid spaces passing 'required'
            if isinstance(val, str):
                val = val.strip()

            for rule in field_rules:
                rule_name = rule
                rule_param = None
                if ":" in rule:
                    rule_name, rule_param = rule.split(":", 1)

                method_name = f"_validate_{rule_name}"
                if hasattr(self, method_name):
                    method = getattr(self, method_name)
                    # If field is empty and not required, skip other validation rules
                    if val in (None, "") and rule_name != "required":
                        continue

                    is_valid = method(field, val, rule_param)
                    if not is_valid:
                        # Break validation for this field on first error
                        break

    def fails(self) -> bool:
        return bool(self._errors)

    def errors(self) -> dict:
        return self._errors

    def _add_error(self, field: str, rule: str, default_message: str):
        if field not in self._errors:
            self._errors[field] = []

        # custom message key: "field.rule" or "rule"
        custom_key = f"{field}.{rule}"
        message = self.messages.get(custom_key, self.messages.get(rule, default_message))
        self._errors[field].append(message)

    # ─── Validation Rules ───────────────────────────────────────────────────

    def _validate_required(self, field: str, val, param) -> bool:
        if val is None or val == "":
            self._add_error(field, "required", f"{field} ফিল্ডটি আবশ্যক।")
            return False
        return True

    def _validate_email(self, field: str, val, param) -> bool:
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not val or not re.match(pattern, str(val)):
            self._add_error(field, "email", "সঠিক ইমেইল ঠিকানা প্রদান করুন।")
            return False
        return True

    def _validate_numeric(self, field: str, val, param) -> bool:
        try:
            float(val)
            return True
        except (ValueError, TypeError):
            self._add_error(field, "numeric", "শুধুমাত্র সংখ্যা প্রদান করুন।")
            return False

    def _validate_min(self, field: str, val, param) -> bool:
        min_val = int(param)
        try:
            val_num = float(val)
            is_valid = val_num >= min_val
        except (ValueError, TypeError):
            is_valid = len(str(val)) >= min_val

        if not is_valid:
            self._add_error(field, "min", f"ন্যূনতম মান বা দৈর্ঘ্য {min_val} হতে হবে।")
            return False
        return True

    def _validate_max(self, field: str, val, param) -> bool:
        max_val = int(param)
        try:
            val_num = float(val)
            is_valid = val_num <= max_val
        except (ValueError, TypeError):
            is_valid = len(str(val)) <= max_val

        if not is_valid:
            self._add_error(field, "max", f"সর্বোচ্চ মান বা দৈর্ঘ্য {max_val} হতে হবে।")
            return False
        return True

    def _validate_unique(self, field: str, val, param) -> bool:
        """
        unique:table,column,except_id
        উদাহরণ: unique:users,email,1
        """
        parts = param.split(",")
        table = parts[0]
        column = parts[1] if len(parts) > 1 else field
        except_id = parts[2] if len(parts) > 2 else None

        conn = Database.connection()
        cursor = conn.cursor()
        sql = f"SELECT id FROM {table} WHERE {column} = {Database.placeholder()}"
        params = [val]

        if except_id:
            sql += f" AND id != {Database.placeholder()}"
            params.append(except_id)

        cursor.execute(sql, tuple(params))
        row = cursor.fetchone()

        if row:
            self._add_error(field, "unique", f"এই {field} ইতোমধ্যে ব্যবহৃত হচ্ছে।")
            return False
        return True

    def _validate_in(self, field: str, val, param) -> bool:
        """in:val1,val2,val3 — নির্দিষ্ট মানগুলোর মধ্যে থাকতে হবে"""
        allowed = [v.strip() for v in param.split(",")]
        if str(val) not in allowed:
            self._add_error(field, "in", f"{field} শুধুমাত্র এই মানগুলোর একটি হতে পারে: {', '.join(allowed)}।")
            return False
        return True

    def _validate_regex(self, field: str, val, param) -> bool:
        """regex:^[A-Z]+ — Custom regular expression দিয়ে যাচাই"""
        try:
            if not re.match(param, str(val)):
                self._add_error(field, "regex", f"{field} সঠিক ফরম্যাটে নেই।")
                return False
        except re.error:
            self._add_error(field, "regex", f"{field} regex pattern ভুল।")
            return False
        return True

    def _validate_confirmed(self, field: str, val, param) -> bool:
        """confirmed — field_confirmation মিলছে কিনা চেক করে (পাসওয়ার্ড কনফার্ম)"""
        confirmation_key = f"{field}_confirmation"
        confirmation_val = self.data.get(confirmation_key, "")
        if isinstance(confirmation_val, str):
            confirmation_val = confirmation_val.strip()
        if val != confirmation_val:
            self._add_error(field, "confirmed", f"{field} এবং {field}_confirmation মিলছে না।")
            return False
        return True

    def _validate_date(self, field: str, val, param) -> bool:
        """date — তারিখ ফরম্যাট চেক করে (YYYY-MM-DD বা কাস্টম: date:DD/MM/YYYY)"""
        import datetime
        fmt = param or "%Y-%m-%d"
        # কমন Bengali/web formats সাপোর্ট
        formats_to_try = [fmt, "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
        for f in formats_to_try:
            try:
                datetime.datetime.strptime(str(val), f)
                return True
            except ValueError:
                continue
        self._add_error(field, "date", f"{field} সঠিক তারিখ ফরম্যাটে নেই (YYYY-MM-DD আশা করা হচ্ছে)।")
        return False

    def _validate_url(self, field: str, val, param) -> bool:
        """url — সঠিক URL ফরম্যাট যাচাই"""
        pattern = r"^https?://[^\s/$.?#].[^\s]*$"
        if not re.match(pattern, str(val), re.IGNORECASE):
            self._add_error(field, "url", f"{field} সঠিক URL হতে হবে (http:// বা https:// দিয়ে শুরু)।")
            return False
        return True

    def _validate_file_size(self, field: str, val, param) -> bool:
        """file_size:500 — ফাইলের সর্বোচ্চ সাইজ KB-তে"""
        from core.request import UploadedFile
        if not isinstance(val, UploadedFile):
            return True  # ফাইল না হলে skip
        max_kb = int(param)
        size_kb = val.size / 1024
        if size_kb > max_kb:
            self._add_error(field, "file_size", f"ফাইলের সাইজ সর্বোচ্চ {max_kb}KB হতে পারবে (বর্তমান: {size_kb:.0f}KB)।")
            return False
        return True

    def _validate_mimes(self, field: str, val, param) -> bool:
        """mimes:jpg,png,pdf — ফাইলের MIME type / extension whitelist"""
        from core.request import UploadedFile
        if not isinstance(val, UploadedFile):
            return True  # ফাইল না হলে skip
        allowed_exts = [e.strip().lower() for e in param.split(",")]
        filename = val.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        # MIME type mapping
        mime_map = {
            "jpg": ["image/jpeg"], "jpeg": ["image/jpeg"],
            "png": ["image/png"], "gif": ["image/gif"],
            "pdf": ["application/pdf"],
            "doc": ["application/msword"],
            "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
            "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
            "csv": ["text/csv", "application/csv"],
            "txt": ["text/plain"],
            "mp4": ["video/mp4"], "mp3": ["audio/mpeg"],
            "zip": ["application/zip"],
        }
        content_type = val.content_type or ""
        # Extension check বা MIME check
        if ext not in allowed_exts:
            allowed_mimes = []
            for ae in allowed_exts:
                allowed_mimes.extend(mime_map.get(ae, []))
            if content_type and allowed_mimes and content_type.lower().split(";")[0].strip() not in allowed_mimes:
                self._add_error(field, "mimes", f"ফাইলের ধরন অনুমোদিত নয়। শুধু {', '.join(allowed_exts)} ফাইল গ্রহণযোগ্য।")
                return False
            elif not allowed_mimes:
                self._add_error(field, "mimes", f"ফাইলের ধরন অনুমোদিত নয়। শুধু {', '.join(allowed_exts)} ফাইল গ্রহণযোগ্য।")
                return False
        return True

