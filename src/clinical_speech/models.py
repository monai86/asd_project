"""Normalized clinical speech line models used by service adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SpeakerRole = Literal["child", "therapist", "parent", "family", "other"]


@dataclass(frozen=True)
class WordTimestamp:
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "WordTimestamp":
        return cls(
            text=str(value.get("text") or value.get("word") or "").strip(),
            start_ms=_optional_int(value.get("start_ms")),
            end_ms=_optional_int(value.get("end_ms")),
            confidence=_optional_float(value.get("confidence")),
        )


@dataclass(frozen=True)
class NormalizedTranscriptLine:
    session_id: str
    speaker_code: str
    speaker_role: SpeakerRole
    start_ms: int | None
    end_ms: int | None
    text: str
    reviewed_text: str | None = None
    confidence: float | None = None
    is_reviewed: bool = False
    word_timestamps: list[WordTimestamp] = field(default_factory=list)
    line_id: str | None = None
    line_number: int | None = None
    flags: list[dict[str, Any]] = field(default_factory=list)

    @property
    def effective_text(self) -> str:
        """Return clinician-reviewed text when present, otherwise the source text."""
        if self.is_reviewed and self.reviewed_text and self.reviewed_text.strip():
            return self.reviewed_text.strip()
        return (self.text or "").strip()


def speaker_role_for_code(speaker_code: str) -> SpeakerRole:
    code = (speaker_code or "").strip().upper()
    if code == "CHI":
        return "child"
    if code in {"INV", "CLI", "SLP", "EXP"}:
        return "therapist"
    if code in {"MOT", "FAT", "PAR", "MOM", "DAD"}:
        return "parent"
    if code in {"SIS", "BRO", "GRA", "GRF", "GRM", "SIB"}:
        return "family"
    return "other"


def normalize_speaker_code(speaker_code: str) -> str:
    code = "".join(ch for ch in (speaker_code or "").upper() if ch.isalpha())
    if not code:
        return "INV"
    return code[:3].ljust(3, "X")


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
