from __future__ import annotations

from dataclasses import dataclass
import re


class NotificationSafetyError(ValueError):
    pass


@dataclass(frozen=True)
class SafeNotification:
    subject: str
    body: str


SENSITIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bC-[A-Z0-9][A-Z0-9_-]{2,}\b"),
    re.compile(r"\b(?:CHI|THER|MOT|FAT|INV|PAR):"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"\b[\w.-]+\.(?:wav|mp3|m4a|flac|ogg|cha|mp4|mov)\b", re.IGNORECASE),
    re.compile(r"\b(?:storage[_ -]?key|audio[_ -]?key|object[_ -]?key)\b", re.IGNORECASE),
    re.compile(r"\b(?:sessions|cases|audio|transcripts)/[^\s]+", re.IGNORECASE),
)


def sanitize_notification_text(text: str) -> str:
    sanitized = text
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return sanitized


def validate_notification(*, subject: str, body: str) -> SafeNotification:
    sanitized_subject = sanitize_notification_text(subject)
    sanitized_body = sanitize_notification_text(body)
    if sanitized_subject != subject or sanitized_body != body:
        raise NotificationSafetyError("Notification contains restricted clinical or identifying content.")
    return SafeNotification(subject=subject, body=body)
