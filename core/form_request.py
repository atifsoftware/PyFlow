"""
core/form_request.py
====================
Form Request & DTO Validation Layer for PyFlow.
Encapsulates authorization, validation rules, custom messages, and safe input parsing.
"""

from typing import Any, Dict, Optional
from core.response import Response
from core.validator import Validator


class AuthorizationException(Exception):
    """Raised when request authorization fails."""
    def __init__(self, message: str = "This action is unauthorized."):
        super().__init__(message)
        self.message = message


class ValidationException(Exception):
    """Raised when form validation fails."""
    def __init__(self, errors: Dict[str, Any], response: Optional[Response] = None):
        super().__init__("The given data was invalid.")
        self.errors = errors
        self.response = response


class FormRequest:
    """
    Base FormRequest class for request-level validation and authorization.
    """

    def __init__(self, request, session=None):
        self.request = request
        self.session = session
        self._validated_data: Optional[Dict[str, Any]] = None

    def authorize(self) -> bool:
        """
        Determine if the user is authorized to make this request.
        Override in subclasses (defaults to True).
        """
        return True

    def rules(self) -> Dict[str, Any]:
        """
        Get the validation rules that apply to the request.
        Must be overridden in subclasses.
        """
        return {}

    def messages(self) -> Dict[str, str]:
        """
        Get custom error messages for defined validation rules.
        """
        return {}

    def user(self) -> Optional[Any]:
        """
        Get the authenticated user from session.
        """
        if not self.session:
            return None
        user = self.session.get("user")
        if user:
            return user
        user_id = self.session.get("user_id")
        if user_id:
            try:
                from app.models.user_model import User
                return User.find(user_id)
            except Exception:
                return None
        return None

    def _format_rules(self) -> Dict[str, str]:
        """Format rules dictionary where values can be list or pipe-separated string."""
        raw_rules = self.rules() or {}
        formatted = {}
        for field, rule_item in raw_rules.items():
            if isinstance(rule_item, list):
                formatted[field] = "|".join(rule_item)
            else:
                formatted[field] = str(rule_item)
        return formatted

    def validate(self) -> "FormRequest":
        """
        Run authorization and validation. Raises AuthorizationException or ValidationException on failure.
        """
        if not self.authorize():
            raise AuthorizationException("This action is unauthorized.")

        rules = self._format_rules()
        validator = Validator(self.request.all(), rules, self.messages())

        if validator.fails():
            errors = validator.errors()
            if self.request.wants_json():
                resp = Response.json({
                    "message": "The given data was invalid.",
                    "errors": errors
                }, status=422)
            else:
                if self.session:
                    self.session.flash("_errors", errors)
                    self.session.flash("_old_input", self.request.all())
                referer = self.request.header("Referer", "/")
                resp = Response.redirect(referer)
            raise ValidationException(errors, response=resp)

        # Store validated fields only
        all_data = self.request.all()
        self._validated_data = {k: all_data.get(k) for k in rules.keys() if k in all_data}
        return self

    def validated(self) -> Dict[str, Any]:
        """
        Return the validated data (only fields defined in rules()).
        """
        if self._validated_data is None:
            self.validate()
        return dict(self._validated_data or {})

    def input(self, key: str, default: Any = None) -> Any:
        return self.request.input(key, default)

    def all(self) -> Dict[str, Any]:
        return self.request.all()

    def file(self, key: str) -> Any:
        return self.request.file(key)

    def has_file(self, key: str) -> bool:
        return self.request.has_file(key)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        val = self.request.input(name)
        if val is not None:
            return val
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute or input '{name}'")
