"""
core/audit.py
=============
Enterprise Audit Trail & Change Logger for PyFlow.
Tracks model changes (created, updated, soft_deleted, restored, deleted) with
before/after diffs, user ID, IP address, user agent, and timestamps.
"""

import os
import json
import time
import logging
import contextvars
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional, Dict, Union

from core.database import Database
from core.model import Model

logger = logging.getLogger("pyflow.audit")

# Thread-safe & async-safe ContextVar for current request's audit metadata
_audit_context_var: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "pyflow_audit_context", default={}
)


def _json_serial(obj: Any) -> Any:
    """JSON serializer for dates, datetimes, decimals, and models."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return str(obj)


class AuditTrail:
    """
    Central manager for auditing model mutations and system actions.
    """

    @classmethod
    def set_context(
        cls,
        user_id: Optional[Any] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        url: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set or update the current thread/task's audit context."""
        ctx = dict(_audit_context_var.get())
        if user_id is not None:
            ctx["user_id"] = user_id
        if ip_address is not None:
            ctx["ip_address"] = ip_address
        if user_agent is not None:
            ctx["user_agent"] = user_agent
        if url is not None:
            ctx["url"] = url
        if extra:
            ctx.update(extra)
        _audit_context_var.set(ctx)

    @classmethod
    def set_user_id(cls, user_id: Any) -> None:
        """Convenience method to set authenticated user_id in the audit context."""
        ctx = dict(_audit_context_var.get())
        ctx["user_id"] = user_id
        _audit_context_var.set(ctx)

    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """Return the current audit context."""
        return dict(_audit_context_var.get())

    @classmethod
    def clear_context(cls) -> None:
        """Clear the current audit context."""
        _audit_context_var.set({})

    @classmethod
    def log(
        cls,
        auditable: Any,
        event: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        user_id: Optional[Any] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        url: Optional[str] = None,
    ) -> Optional[int]:
        """
        Record an audit log entry for a model or entity.
        Returns the new audit log ID or None on failure.
        """
        ctx = cls.get_context()

        # Resolve auditable metadata
        if isinstance(auditable, Model):
            auditable_type = auditable.__class__.__name__
            auditable_id = str(getattr(auditable, auditable.primary_key, "") or "")
            excluded = getattr(auditable.__class__, "audit_exclude", ["password", "remember_token"])
        elif isinstance(auditable, type) and issubclass(auditable, Model):
            auditable_type = auditable.__name__
            auditable_id = ""
            excluded = getattr(auditable, "audit_exclude", ["password", "remember_token"])
        elif isinstance(auditable, str):
            auditable_type = auditable
            auditable_id = ""
            excluded = ["password", "remember_token"]
        else:
            auditable_type = str(auditable)
            auditable_id = ""
            excluded = []

        # Sanitize sensitive fields from old and new values
        def sanitize(values: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if not values:
                return None
            return {k: v for k, v in values.items() if k not in excluded}

        clean_old = sanitize(old_values)
        clean_new = sanitize(new_values)

        old_json = json.dumps(clean_old, default=_json_serial) if clean_old is not None else None
        new_json = json.dumps(clean_new, default=_json_serial) if clean_new is not None else None

        final_user_id = user_id if user_id is not None else ctx.get("user_id")
        final_ip = ip_address if ip_address is not None else ctx.get("ip_address")
        final_ua = user_agent if user_agent is not None else ctx.get("user_agent")
        final_url = url if url is not None else ctx.get("url")
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        record = {
            "auditable_type": auditable_type,
            "auditable_id": str(auditable_id),
            "event": event,
            "old_values": old_json,
            "new_values": new_json,
            "user_id": final_user_id,
            "ip_address": final_ip,
            "user_agent": final_ua[:255] if final_ua else None,
            "url": final_url[:255] if final_url else None,
            "created_at": now,
        }

        try:
            conn = Database.connection()
            grammar = conn.grammar
            table = grammar.wrap_table("audit_logs")
            cols = [grammar.wrap(k) for k in record.keys()]
            ph = conn.placeholder
            placeholders = ", ".join([ph] * len(cols))
            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"

            res = conn.execute(sql, tuple(record.values()))
            if not conn.in_transaction():
                conn.commit()

            if isinstance(res, dict) and "id" in res:
                return res["id"]
            return getattr(res, "lastrowid", None)
        except Exception as exc:
            # Audit logging must never crash the primary business logic
            logger.warning(f"Could not persist audit log to DB (table may not exist yet): {exc}")
            return None


class AuditLog(Model):
    """
    Active Record model representing an audit log entry in the 'audit_logs' table.
    """
    table = "audit_logs"
    primary_key = "id"
    timestamps = False
    fillable = [
        "auditable_type",
        "auditable_id",
        "event",
        "old_values",
        "new_values",
        "user_id",
        "ip_address",
        "user_agent",
        "url",
        "created_at",
    ]

    def old_data(self) -> Dict[str, Any]:
        """Parsed dictionary of old values before change."""
        val = self._attributes.get("old_values")
        if not val:
            return {}
        try:
            return json.loads(val)
        except Exception:
            return {}

    def new_data(self) -> Dict[str, Any]:
        """Parsed dictionary of new values after change."""
        val = self._attributes.get("new_values")
        if not val:
            return {}
        try:
            return json.loads(val)
        except Exception:
            return {}

    def diff(self) -> Dict[str, tuple]:
        """
        Returns a dictionary of changed fields with (old_val, new_val) tuples.
        """
        old_d = self.old_data()
        new_d = self.new_data()
        changed = {}
        all_keys = set(old_d.keys()) | set(new_d.keys())
        for k in all_keys:
            ov = old_d.get(k)
            nv = new_d.get(k)
            if ov != nv:
                changed[k] = (ov, nv)
        return changed
