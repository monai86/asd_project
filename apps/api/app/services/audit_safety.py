from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from uuid import uuid4

from app.services.notification_safety import sanitize_notification_text


class AuditSafetyError(ValueError):
    pass


ALLOWED_OUTCOMES = {"success", "failure", "denied", "cancelled"}
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


@dataclass(frozen=True)
class AuditEvent:
    audit_id: str
    actor_id: str
    action: str
    target_id: str
    outcome: str
    correlation_id: str
    message: str
    timestamp: str

    def as_dict(self) -> dict[str, str]:
        return {
            "audit_id": self.audit_id,
            "actor_id": self.actor_id,
            "action": self.action,
            "target_id": self.target_id,
            "outcome": self.outcome,
            "correlation_id": self.correlation_id,
            "message": self.message,
            "timestamp": self.timestamp,
        }


def validate_audit_event(
    *,
    actor_id: str,
    action: str,
    target_id: str,
    outcome: str,
    correlation_id: str,
    message: str,
    audit_id: str | None = None,
    timestamp: str | None = None,
) -> AuditEvent:
    _require_safe_identifier("actor_id", actor_id)
    _require_safe_identifier("action", action)
    _require_safe_identifier("target_id", target_id)
    _require_safe_identifier("correlation_id", correlation_id)
    if outcome not in ALLOWED_OUTCOMES:
        raise AuditSafetyError("Audit event outcome is not allowed.")
    if sanitize_notification_text(message) != message:
        raise AuditSafetyError("Audit event contains restricted clinical or identifying content.")
    return AuditEvent(
        audit_id=audit_id or f"audit_{uuid4().hex[:10]}",
        actor_id=actor_id,
        action=action,
        target_id=target_id,
        outcome=outcome,
        correlation_id=correlation_id,
        message=message,
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
    )


def _require_safe_identifier(field_name: str, value: str) -> None:
    if not value or not SAFE_ID_RE.match(value):
        raise AuditSafetyError(f"Audit event {field_name} is invalid.")
