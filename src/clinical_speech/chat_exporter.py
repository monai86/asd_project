"""Line-first CHAT export and import helpers for clinical transcript review."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Sequence

from .models import NormalizedTranscriptLine, normalize_speaker_code, speaker_role_for_code


MEDIA_MARKER_RE = re.compile(r"\x15(\d+)_(\d+)\x15")
SPEAKER_TIER_RE = re.compile(r"^\*([A-Za-z]{2,4}):\s*(.*)$")
TIM_TIER_RE = re.compile(r"^%tim:\s*([0-9:.]+)(?:-([0-9:.]+))?\s*$")
CHAT_DEPENDENT_TIER_RE = re.compile(r"^%[A-Za-z]+:")
WHITESPACE_RE = re.compile(r"\s+")
TERMINATORS = (".", "?", "!", "+...", "+/.", "+//.", "+/?")


ROLE_LABELS = {
    "child": "Child",
    "therapist": "Investigator",
    "parent": "Parent",
    "family": "Family",
    "other": "Participant",
}
CHAT_ID_ROLES = {
    "child": "Target_Child",
    "therapist": "Investigator",
    "parent": "Mother",
    "family": "Sibling",
    "other": "Participant",
}


@dataclass(frozen=True)
class ChatExportMetadata:
    session_id: str
    language: str = "eng"
    corpus: str = "asd-project"
    media_filename: str | None = None
    child_id: str = "CHI001"
    child_age_months: int | float | None = None
    child_sex: str | None = None
    child_group: str = ""
    coder: str = "Clinical review"
    include_tim_tiers: bool = False
    allow_preliminary: bool = False


def format_chat_time(milliseconds: int | float | None) -> str:
    """Return HH:MM:SS.sss for a millisecond timestamp."""
    ms = max(0, int(round(float(milliseconds or 0))))
    seconds = ms / 1000.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def format_media_marker(start_ms: int | None, end_ms: int | None) -> str:
    if start_ms is None or end_ms is None:
        return ""
    start = max(0, int(start_ms))
    end = max(start, int(end_ms))
    return f"\x15{start}_{end}\x15"


def parse_chat_time_to_ms(value: str | None) -> int | None:
    if not value:
        return None
    raw = value.strip()
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return int(round(((hours * 3600) + (minutes * 60) + seconds) * 1000))
        return int(round(float(raw) * 1000))
    except ValueError:
        return None


def build_reviewed_chat_export(
    lines: Sequence[NormalizedTranscriptLine],
    *,
    metadata: ChatExportMetadata,
) -> str:
    """Build a CLAN-compatible CHAT file from reviewed transcript lines."""
    ordered = sorted(
        [line for line in lines if line.session_id == metadata.session_id],
        key=lambda line: (
            line.start_ms if line.start_ms is not None else 10**12,
            line.line_number if line.line_number is not None else 10**9,
            line.line_id or "",
        ),
    )
    if not ordered:
        raise ValueError("At least one transcript line is required for CHAT export.")
    if not metadata.allow_preliminary and any(not line.is_reviewed for line in ordered):
        raise ValueError("Transcript review sign-off is required before reviewed CHAT export.")

    participants = _participant_roles(ordered)
    rows = ["@UTF8", "@Begin", f"@Languages:\t{metadata.language}"]
    rows.append("@Participants:\t" + _participants_line(participants))
    rows.extend(_id_lines(participants, metadata))
    if metadata.media_filename:
        rows.append(f"@Media:\t{Path(metadata.media_filename).stem}, audio")
    rows.append(f"@Coder:\t{_clean_header(metadata.coder)}")
    if metadata.allow_preliminary:
        rows.append("@Comment:\tPreliminary export; requires clinician review before interpretation.")

    for line in ordered:
        text = clean_utterance_text(line.effective_text)
        marker = format_media_marker(line.start_ms, line.end_ms)
        suffix = f" {marker}" if marker else ""
        rows.append(f"*{normalize_speaker_code(line.speaker_code)}:\t{text}{suffix}")
        if metadata.include_tim_tiers and line.start_ms is not None:
            if line.end_ms is not None:
                rows.append(f"%tim:\t{format_chat_time(line.start_ms)}-{format_chat_time(line.end_ms)}")
            else:
                rows.append(f"%tim:\t{format_chat_time(line.start_ms)}")

    rows.append("@End")
    return "\n".join(rows) + "\n"


def clean_utterance_text(text: str | None) -> str:
    """Clean one speaker-tier body without erasing clinical markers."""
    cleaned = (text or "").replace("\x00", " ")
    cleaned = MEDIA_MARKER_RE.sub("", cleaned)
    cleaned = cleaned.replace("\t", " ")
    cleaned = WHITESPACE_RE.sub(" ", cleaned).strip()
    if not cleaned:
        cleaned = "xxx"
    if _is_unintelligible_wording(cleaned):
        cleaned = "xxx"
    if not cleaned.endswith(TERMINATORS):
        cleaned = f"{cleaned} ."
    return cleaned


def parse_chat_to_lines(chat_text: str, *, session_id: str) -> list[NormalizedTranscriptLine]:
    """Parse main speaker tiers from CHAT text into normalized transcript lines."""
    parsed: list[NormalizedTranscriptLine] = []
    last_index: int | None = None
    for line_number, raw_line in enumerate(str(chat_text or "").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("@") or CHAT_DEPENDENT_TIER_RE.match(stripped) is None:
            speaker_match = SPEAKER_TIER_RE.match(stripped)
        else:
            speaker_match = None

        if speaker_match:
            speaker_code = normalize_speaker_code(speaker_match.group(1))
            body = speaker_match.group(2).strip()
            marker = MEDIA_MARKER_RE.search(body)
            start_ms = int(marker.group(1)) if marker else None
            end_ms = int(marker.group(2)) if marker else None
            body = MEDIA_MARKER_RE.sub("", body).strip()
            parsed.append(
                NormalizedTranscriptLine(
                    session_id=session_id,
                    speaker_code=speaker_code,
                    speaker_role=speaker_role_for_code(speaker_code),
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=clean_utterance_text(body),
                    reviewed_text=None,
                    confidence=1.0,
                    is_reviewed=False,
                    line_number=line_number,
                )
            )
            last_index = len(parsed) - 1
            continue

        tim_match = TIM_TIER_RE.match(stripped)
        if tim_match and last_index is not None:
            start_ms = parse_chat_time_to_ms(tim_match.group(1))
            end_ms = parse_chat_time_to_ms(tim_match.group(2)) if tim_match.group(2) else None
            current = parsed[last_index]
            parsed[last_index] = NormalizedTranscriptLine(
                session_id=current.session_id,
                speaker_code=current.speaker_code,
                speaker_role=current.speaker_role,
                start_ms=current.start_ms if current.start_ms is not None else start_ms,
                end_ms=current.end_ms if current.end_ms is not None else end_ms,
                text=current.text,
                reviewed_text=current.reviewed_text,
                confidence=current.confidence,
                is_reviewed=current.is_reviewed,
                word_timestamps=current.word_timestamps,
                line_id=current.line_id,
                line_number=current.line_number,
                flags=current.flags,
            )
    return parsed


def _participant_roles(lines: Iterable[NormalizedTranscriptLine]) -> dict[str, str]:
    participants: dict[str, str] = {}
    for line in lines:
        code = normalize_speaker_code(line.speaker_code)
        participants.setdefault(code, line.speaker_role or speaker_role_for_code(code))
    if "CHI" not in participants:
        participants = {"CHI": "child", **participants}
    return participants


def _participants_line(participants: dict[str, str]) -> str:
    parts = []
    for code, role in participants.items():
        label = "Child" if code == "CHI" else ROLE_LABELS.get(role, "Participant")
        role_label = "Target_Child" if code == "CHI" else CHAT_ID_ROLES.get(role, "Participant")
        parts.append(f"{code} {label} {role_label}")
    return ", ".join(parts)


def _id_lines(participants: dict[str, str], metadata: ChatExportMetadata) -> list[str]:
    rows: list[str] = []
    age = _age_months_to_chat(metadata.child_age_months)
    sex = (metadata.child_sex or "").lower()
    if sex not in {"male", "female"}:
        sex = ""
    for code, role in participants.items():
        if code == "CHI":
            rows.append(
                f"@ID:\t{metadata.language}|{metadata.corpus}|CHI|{age}|{sex}|"
                f"{_clean_header(metadata.child_group)}||Target_Child||{_clean_header(metadata.child_id)}|"
            )
        else:
            rows.append(
                f"@ID:\t{metadata.language}|{metadata.corpus}|{code}|||||"
                f"{CHAT_ID_ROLES.get(role, 'Participant')}|||"
            )
    return rows


def _age_months_to_chat(age_months: int | float | None) -> str:
    if age_months is None:
        return ""
    months_float = max(0.0, float(age_months))
    years = int(months_float // 12)
    months = int(months_float - years * 12)
    return f"{years};{months:02d}.00"


def _clean_header(value: str | None) -> str:
    return WHITESPACE_RE.sub(" ", str(value or "").replace("|", " ").strip())


def _is_unintelligible_wording(text: str) -> bool:
    return text.strip().lower() in {"unintelligible", "[unintelligible]", "(unintelligible)", "inaudible", "[inaudible]"}
