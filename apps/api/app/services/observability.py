from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.services.notification_safety import sanitize_notification_text


class ObservabilitySafetyError(ValueError):
    pass


ALLOWED_SEVERITIES = {"info", "warning", "error", "critical"}
SAFE_EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,120}$")
SAFE_CORRELATION_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{3,128}$")
SAFE_ROUTE_TEMPLATE_RE = re.compile(r"^/[A-Za-z0-9_/{}/.-]+$")


@dataclass(frozen=True)
class ObservabilityEvent:
    name: str
    severity: str
    correlation_id: str
    tags: dict[str, str] = field(default_factory=dict)
    measurements: dict[str, float] = field(default_factory=dict)
    details: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "severity": self.severity,
            "correlation_id": self.correlation_id,
            "tags": dict(self.tags),
            "measurements": dict(self.measurements),
            "details": self.details,
        }


def validate_observability_event(
    *,
    name: str,
    severity: str,
    correlation_id: str,
    tags: dict[str, object] | None = None,
    measurements: dict[str, object] | None = None,
    details: str = "",
) -> ObservabilityEvent:
    normalized_severity = severity.lower()
    if normalized_severity not in ALLOWED_SEVERITIES:
        raise ObservabilitySafetyError("Observability event severity is not allowed.")
    if not SAFE_EVENT_NAME_RE.fullmatch(name):
        raise ObservabilitySafetyError("Observability event name is not allowed.")
    if not SAFE_CORRELATION_ID_RE.fullmatch(correlation_id):
        raise ObservabilitySafetyError("Observability event correlation ID is not allowed.")

    safe_tags = _validate_tags(tags or {})
    safe_measurements = _validate_measurements(measurements or {})
    safe_details = _validate_text(details)
    return ObservabilityEvent(
        name=name,
        severity=normalized_severity,
        correlation_id=correlation_id,
        tags=safe_tags,
        measurements=safe_measurements,
        details=safe_details,
    )


def _validate_tags(tags: dict[str, object]) -> dict[str, str]:
    safe_tags: dict[str, str] = {}
    for key, value in tags.items():
        safe_key = str(key)
        safe_value = str(value)
        if not SAFE_EVENT_NAME_RE.fullmatch(safe_key.replace("/", ".")):
            raise ObservabilitySafetyError("Observability tag key is not allowed.")
        if safe_key == "route" and "{" in safe_value and "}" in safe_value:
            if not SAFE_ROUTE_TEMPLATE_RE.fullmatch(safe_value):
                raise ObservabilitySafetyError("Observability route template is not allowed.")
            safe_tags[safe_key] = safe_value
            continue
        safe_tags[safe_key] = _validate_text(safe_value)
    return safe_tags


def _validate_measurements(measurements: dict[str, object]) -> dict[str, float]:
    safe_measurements: dict[str, float] = {}
    for key, value in measurements.items():
        safe_key = str(key)
        if not SAFE_EVENT_NAME_RE.fullmatch(safe_key):
            raise ObservabilitySafetyError("Observability measurement key is not allowed.")
        try:
            safe_measurements[safe_key] = float(value)
        except (TypeError, ValueError) as exc:
            raise ObservabilitySafetyError("Observability measurement value must be numeric.") from exc
    return safe_measurements


def _validate_text(text: str) -> str:
    if sanitize_notification_text(text) != text:
        raise ObservabilitySafetyError("Observability event contains restricted clinical or identifying content.")
    return text
