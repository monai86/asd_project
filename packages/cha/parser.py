"""Lightweight CHAT (.cha) parser for clinical decision-support pipelines.

The parser preserves raw utterance text while deriving normalized text, cleaned
tokens, speaker roles, and timestamps. It intentionally avoids diagnostic
interpretation; downstream modules decide how to use the structured transcript.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterable

from src.clinical_speech.models import NormalizedTranscriptLine, speaker_role_for_code


MAIN_TIER_RE = re.compile(r"^\*([A-Za-z]{1,6}):\s*(.*)$")
DEPENDENT_TIER_RE = re.compile(r"^%([A-Za-z]{3}):\s*(.*)$")
MEDIA_BULLET_RE = re.compile(r"\x15\s*(\d+)\s*[_-]\s*(\d+)\s*\x15")
TIM_RANGE_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}(?:\.\d{1,3})?)\s*[-_]\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}(?:\.\d{1,3})?)"
)
TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
CHAT_CODE_RE = re.compile(r"\x15\d+[_-]\d+\x15|\[[^\]]+\]|&=[^\s]+|&-[^\s]+")
TERMINATOR_RE = re.compile(r"\s+(?:[.?!]|[+][/\\.]|[+][.]{2,})\s*$")


@dataclass(frozen=True)
class ParsedChaUtterance:
    speaker_code: str
    speaker_role: str
    raw_text: str
    normalized_text: str
    tokens: list[str]
    line_number: int
    start_ms: int | None = None
    end_ms: int | None = None
    dependent_tiers: dict[str, list[str]] = field(default_factory=dict)

    def to_normalized_line(self, *, session_id: str) -> NormalizedTranscriptLine:
        return NormalizedTranscriptLine(
            session_id=session_id,
            speaker_code=self.speaker_code,
            speaker_role=self.speaker_role,  # type: ignore[arg-type]
            start_ms=self.start_ms,
            end_ms=self.end_ms,
            text=self.raw_text,
            line_number=self.line_number,
        )


@dataclass(frozen=True)
class ParsedChaTranscript:
    file_id: str
    utterances: list[ParsedChaUtterance]
    headers: dict[str, list[str]]
    source_path: str | None = None

    def to_normalized_lines(self, *, session_id: str | None = None) -> list[NormalizedTranscriptLine]:
        resolved_session_id = session_id or self.file_id
        return [
            utterance.to_normalized_line(session_id=resolved_session_id)
            for utterance in self.utterances
        ]


def parse_cha_file(path: str | Path) -> ParsedChaTranscript:
    cha_path = Path(path)
    return parse_cha_text(
        cha_path.read_text(encoding="utf-8", errors="replace"),
        file_id=cha_path.stem,
        source_path=str(cha_path),
    )


def parse_cha_text(
    text: str,
    *,
    file_id: str = "transcript",
    source_path: str | None = None,
) -> ParsedChaTranscript:
    headers: dict[str, list[str]] = {}
    rows: list[dict] = []
    current: dict | None = None

    for line_number, raw_line in enumerate(str(text or "").splitlines(), start=1):
        line = raw_line.rstrip("\n")
        if not line.strip():
            continue

        main_match = MAIN_TIER_RE.match(line)
        if main_match:
            if current is not None:
                rows.append(current)
            speaker_code = _speaker_code(main_match.group(1))
            current = {
                "speaker_code": speaker_code,
                "raw_text": main_match.group(2).strip(),
                "line_number": line_number,
                "dependent_tiers": {},
                "active_dependent_tier": None,
            }
            continue

        dependent_match = DEPENDENT_TIER_RE.match(line)
        if dependent_match and current is not None:
            tier = dependent_match.group(1).lower()
            value = dependent_match.group(2).strip()
            current["dependent_tiers"].setdefault(tier, []).append(value)
            current["active_dependent_tier"] = tier
            continue

        if line.startswith("@"):
            key, _, value = line.partition(":")
            headers.setdefault(key.strip(), []).append(value.strip())
            continue

        if current is not None and (line.startswith("\t") or line.startswith(" ")):
            continuation = line.strip()
            active_tier = current.get("active_dependent_tier")
            if active_tier:
                values = current["dependent_tiers"][active_tier]
                values[-1] = f"{values[-1]} {continuation}".strip()
            else:
                current["raw_text"] = f"{current['raw_text']} {continuation}".strip()

    if current is not None:
        rows.append(current)

    utterances = [
        _build_utterance(row)
        for row in rows
    ]
    return ParsedChaTranscript(
        file_id=file_id,
        utterances=utterances,
        headers=headers,
        source_path=source_path,
    )


def cleaned_tokens(text: str) -> list[str]:
    normalized = normalize_utterance_text(text)
    return [
        token.lower()
        for token in TOKEN_RE.findall(normalized)
        if token and token.lower() not in {"0", "xxx", "yyy", "www"}
    ]


def normalize_utterance_text(text: str) -> str:
    value = CHAT_CODE_RE.sub(" ", str(text or ""))
    value = re.sub(r"\([^)]*\)", " ", value)
    value = TERMINATOR_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _build_utterance(row: dict) -> ParsedChaUtterance:
    raw_text = str(row["raw_text"])
    start_ms, end_ms = _extract_timestamps(raw_text, row.get("dependent_tiers", {}))
    normalized_text = normalize_utterance_text(raw_text)
    speaker_code = _speaker_code(row["speaker_code"])
    return ParsedChaUtterance(
        speaker_code=speaker_code,
        speaker_role=speaker_role_for_code(speaker_code),
        raw_text=raw_text,
        normalized_text=normalized_text,
        tokens=cleaned_tokens(raw_text),
        line_number=int(row["line_number"]),
        start_ms=start_ms,
        end_ms=end_ms,
        dependent_tiers=row.get("dependent_tiers", {}),
    )


def _extract_timestamps(raw_text: str, dependent_tiers: dict[str, Iterable[str]]) -> tuple[int | None, int | None]:
    media_match = MEDIA_BULLET_RE.search(raw_text or "")
    if media_match:
        return int(media_match.group(1)), int(media_match.group(2))

    for value in dependent_tiers.get("tim", []):
        tim_match = TIM_RANGE_RE.search(value)
        if tim_match:
            return _time_to_ms(tim_match.group("start")), _time_to_ms(tim_match.group("end"))
    return None, None


def _time_to_ms(value: str) -> int:
    hours, minutes, seconds = value.split(":")
    return int(round((int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 1000))


def _speaker_code(value: str) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalpha())[:6] or "INV"
