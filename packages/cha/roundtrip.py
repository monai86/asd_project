"""Deterministic semantic round-trip checks for the maintained CHAT subset.

This is intentionally not a complete CHAT implementation. It serializes only
the headers, main tiers, timestamps, and dependent tiers already represented by
``packages.cha.parser`` and compares their parsed meaning rather than source
formatting.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import unicodedata

from .parser import ParsedChaTranscript, parse_cha_text


CHAT_SUBSET_VERSION = "lingualens-chat-subset-v1"
CHAT_PARSER_VERSION = "lingualens-cha-parser-v1"
CHAT_SERIALIZER_VERSION = "lingualens-cha-serializer-v1"
_STRUCTURAL_HEADERS = {"@UTF8", "@Begin", "@End"}
_HEADER_ORDER = ("@Languages", "@Participants", "@ID", "@Media")


@dataclass(frozen=True)
class ChaRoundTripIssue:
    code: str
    message: str


@dataclass(frozen=True)
class ChaRoundTripResult:
    ok: bool
    document: ParsedChaTranscript
    exported_text: str
    input_semantic_checksum_sha256: str
    output_semantic_checksum_sha256: str
    issues: tuple[ChaRoundTripIssue, ...] = ()
    subset_version: str = CHAT_SUBSET_VERSION
    parser_version: str = CHAT_PARSER_VERSION
    serializer_version: str = CHAT_SERIALIZER_VERSION


def serialize_cha_subset(transcript: ParsedChaTranscript) -> str:
    """Serialize the represented CHAT subset into stable UTF-8 text."""

    lines = ["@UTF8", "@Begin"]
    header_keys = [
        *_HEADER_ORDER,
        *sorted(set(transcript.headers) - _STRUCTURAL_HEADERS - set(_HEADER_ORDER)),
    ]
    for key in header_keys:
        if key in _STRUCTURAL_HEADERS:
            continue
        for value in transcript.headers.get(key, []):
            normalized = _normalize(value)
            lines.append(f"{key}:\t{normalized}" if normalized else f"{key}:")

    for utterance in transcript.utterances:
        lines.append(f"*{utterance.speaker_code}:\t{_normalize(utterance.raw_text)}")
        for tier in sorted(utterance.dependent_tiers):
            for value in utterance.dependent_tiers[tier]:
                lines.append(f"%{tier}:\t{_normalize(value)}")

    lines.append("@End")
    return "\n".join(lines) + "\n"


def semantic_cha_checksum(transcript: ParsedChaTranscript) -> str:
    """Return a checksum of represented meaning, excluding path and layout."""

    payload = {
        "subset_version": CHAT_SUBSET_VERSION,
        "headers": {
            key: [_normalize(value) for value in values]
            for key, values in sorted(transcript.headers.items())
            if key not in _STRUCTURAL_HEADERS
        },
        "utterances": [
            {
                "speaker_code": utterance.speaker_code,
                "speaker_role": utterance.speaker_role,
                "raw_text": _normalize(utterance.raw_text),
                "normalized_text": _normalize(utterance.normalized_text),
                "tokens": list(utterance.tokens),
                "start_ms": utterance.start_ms,
                "end_ms": utterance.end_ms,
                "dependent_tiers": {
                    tier: [_normalize(value) for value in values]
                    for tier, values in sorted(utterance.dependent_tiers.items())
                },
            }
            for utterance in transcript.utterances
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def verify_cha_round_trip(text: str, *, file_id: str = "transcript") -> ChaRoundTripResult:
    """Parse, serialize, parse again, and fail if represented meaning changes."""

    source = parse_cha_text(text, file_id=file_id)
    exported = serialize_cha_subset(source)
    output = parse_cha_text(exported, file_id=file_id)
    input_checksum = semantic_cha_checksum(source)
    output_checksum = semantic_cha_checksum(output)
    issues: list[ChaRoundTripIssue] = []
    if input_checksum != output_checksum:
        issues.append(
            ChaRoundTripIssue(
                code="CHAT_SEMANTIC_ROUND_TRIP_CHANGED",
                message="The maintained CHAT subset changed during parse and serialization.",
            )
        )
    if serialize_cha_subset(output) != exported:
        issues.append(
            ChaRoundTripIssue(
                code="CHAT_SERIALIZATION_NOT_DETERMINISTIC",
                message="A second serialization produced different bytes.",
            )
        )
    return ChaRoundTripResult(
        ok=not issues,
        document=output,
        exported_text=exported,
        input_semantic_checksum_sha256=input_checksum,
        output_semantic_checksum_sha256=output_checksum,
        issues=tuple(issues),
    )


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", str(value or "").strip())
