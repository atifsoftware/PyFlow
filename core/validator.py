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
