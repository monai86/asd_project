"""Canonical, deterministic CHAT subset for the v1.7.0 testbed.

This module deliberately models only the frozen LinguaLens subset.  It does
not pretend to be a complete CHAT parser: content outside the subset is either
kept as an opaque extension or returned as a blocking structured error.
"""

from __future__ import annotations

from hashlib import sha256
import json
import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.speech_pipeline import ChatRoundTripError, QaDisposition


CHAT_SUBSET_VERSION = "lingualens-chat-v1.7.0"
CHAT_PARSER_VERSION = "lingualens-chat-parser-v1.7.0"
CHAT_SERIALIZER_VERSION = "lingualens-chat-serializer-v1.7.0"
EXTERNAL_IMPORT_PROFILE = "external-chat-import-v1.7.0"

SUPPORTED_HEADERS = {
    "@UTF8",
    "@Begin",
    "@End",
    "@Languages",
    "@Participants",
    "@ID",
    "@Media",
    "@Date",
    "@Location",
    "@Situation",
    "@Activities",
    "@Comment",
    "@Transcriber",
    "@Options",
    "@x-lingualens-utterance-id",
}
SUPPORTED_DEPENDENT_TIERS = {"%mor", "%gra", "%pho", "%com", "%act", "%sit"}
SUPPORTED_ANNOTATION_PATTERNS = (
    (re.compile(r"\[\?\]"), "uncertainty", "?"),
    (re.compile(r"\[/\]"), "repetition", "/"),
    (re.compile(r"\[//\]"), "retracing", "//"),
    (re.compile(r"\[\*\s+([^\]]+)\]"), "coded_error", None),
    (re.compile(r"\[=\s+([^\]]+)\]"), "explanation", None),
    (re.compile(r"\[=!\s+([^\]]+)\]"), "event", None),
    (re.compile(r"&-([^\s]+)"), "filled_pause", None),
    (re.compile(r"&\+([^\s]+)"), "partial_word", None),
    (re.compile(r"&~([^\s]+)"), "nonword", None),
)
MEDIA_BULLET_RE = re.compile(r"\x15([0-9]+)_([0-9]+)\x15$")
MEDIA_SENTINEL_RE = re.compile(r"\x15")
SPEAKER_RE = re.compile(r"^\*([A-Za-z][A-Za-z0-9_]{0,7}):(?:\t|\s+)(.*)$")
DEPENDENT_RE = re.compile(r"^(%[^:\s]+):(?:\t|\s+)?(.*)$")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CanonicalParticipant(_Frozen):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,7}$")
    display_name: str
    role: str
    id_fields: tuple[str, ...] = ()


class CanonicalAnnotation(_Frozen):
    kind: str
    payload: str = ""
    scope: str = "utterance"


class CanonicalDependentTier(_Frozen):
    tier: str
    text: str
    continuation_parts: tuple[str, ...] = ()


class CanonicalOpaqueExtension(_Frozen):
    action: Literal[
        "preserved_opaque",
        "unsupported_blocking",
        "unsupported_non_blocking",
    ]
    location: Literal["header", "utterance", "dependent_tier", "annotation"]
    key: str
    content: str
    owner_utterance_id: str | None = None


class CanonicalChatUtterance(_Frozen):
    utterance_id: str
    speaker_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,7}$")
    reviewed_text_nfc: str
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    terminator: Literal[".", "?", "!", "", ";"] = "."
    continuation_parts: tuple[str, ...] = ()
    dependent_tiers: tuple[CanonicalDependentTier, ...] = ()
    annotations: tuple[CanonicalAnnotation, ...] = ()

    @model_validator(mode="after")
    def validate_interval_and_unicode(self) -> "CanonicalChatUtterance":
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError("CHAT utterance timestamps must have both start and end")
        if self.start_ms is not None and self.end_ms is not None and self.start_ms >= self.end_ms:
            raise ValueError("CHAT utterance end timestamp must be greater than start")
        if unicodedata.normalize("NFC", self.reviewed_text_nfc) != self.reviewed_text_nfc:
            raise ValueError("CHAT reviewed text must be NFC normalized")
        return self


class CanonicalChatDocument(_Frozen):
    subset_version: str = CHAT_SUBSET_VERSION
    language_codes: tuple[str, ...]
    media_reference: str | None = None
    participants: tuple[CanonicalParticipant, ...]
    utterances: tuple[CanonicalChatUtterance, ...]
    optional_headers: tuple[tuple[str, str], ...] = ()
    opaque_extensions: tuple[CanonicalOpaqueExtension, ...] = ()

    @model_validator(mode="after")
    def validate_document(self) -> "CanonicalChatDocument":
        if self.subset_version != CHAT_SUBSET_VERSION:
            raise ValueError(f"unsupported CHAT subset: {self.subset_version}")
        codes = [item.code for item in self.participants]
        if len(codes) != len(set(codes)):
            raise ValueError("CHAT participant codes must be unique")
        return self


class ChatParseResult(_Frozen):
    document: CanonicalChatDocument
    errors: list[ChatRoundTripError] = Field(default_factory=list)


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", str(value or ""))


def escape_text(value: str) -> str:
    value = normalize_text(value)
    if any(ord(char) < 0x20 and char not in {"\t", "\n"} for char in value):
        raise ValueError("CHAT text contains a control character")
    return value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")


def unescape_text(value: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            output.append(char)
            index += 1
            continue
        if index + 1 >= len(value):
            raise ValueError("CHAT trailing escape")
        escaped = value[index + 1]
        if escaped == "t":
            output.append("\t")
        elif escaped == "n":
            output.append("\n")
        elif escaped == "\\":
            output.append("\\")
        else:
            raise ValueError(f"CHAT unsupported escape \\{escaped}")
        index += 2
    return normalize_text("".join(output))


def _error(
    code: str,
    *,
    field_or_tier: str | None = None,
    utterance_or_segment_id: str | None = None,
    expected=None,
    actual=None,
    message: str = "",
    severity: str = "error",
    disposition: QaDisposition = QaDisposition.integrity_blocker,
) -> ChatRoundTripError:
    def serializable(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except TypeError:
            return str(value)

    return ChatRoundTripError(
        code=code,
        field_or_tier=field_or_tier,
        utterance_or_segment_id=utterance_or_segment_id,
        expected=serializable(expected),
        actual=serializable(actual),
        severity=severity,
        parser_version=CHAT_PARSER_VERSION,
        serializer_version=CHAT_SERIALIZER_VERSION,
        subset_version=CHAT_SUBSET_VERSION,
        message=message,
        disposition=disposition,
    )


def _participant_text(participant: CanonicalParticipant) -> str:
    return f"{participant.code} {participant.display_name} {participant.role}".strip()


def _participant_sort_key(participant: CanonicalParticipant) -> tuple[int, str]:
    role = participant.role.lower().replace("-", "_")
    if participant.code == "CHI" or role in {"target_child", "child"}:
        return (0, participant.code)
    if participant.code in {"THE", "THER"} or "therap" in role or "investigator" in role:
        return (1, participant.code)
    return (2, participant.code)


def _id_line(participant: CanonicalParticipant) -> str:
    if participant.id_fields:
        fields = list(participant.id_fields)
        if len(fields) < 10:
            fields.extend([""] * (10 - len(fields)))
        fields[2] = participant.code
        return "|".join(fields)
    return f"tha|LinguaLens|{participant.code}|||||{participant.role}|||"


def _annotation_payloads(text: str) -> tuple[CanonicalAnnotation, ...]:
    annotations: list[CanonicalAnnotation] = []
    for pattern, kind, fixed_payload in SUPPORTED_ANNOTATION_PATTERNS:
        for match in pattern.finditer(text):
            payload = fixed_payload if fixed_payload is not None else (match.group(1) if match.groups() else "")
            annotations.append(CanonicalAnnotation(kind=kind, payload=normalize_text(payload)))
    return tuple(annotations)


def _unknown_annotation_spans(text: str) -> list[str]:
    unknown: list[str] = []
    for match in re.finditer(r"\[[^\]]*\]", text):
        if not any(pattern.fullmatch(match.group(0)) for pattern, _, _ in SUPPORTED_ANNOTATION_PATTERNS if match.group(0).startswith("[")):
            unknown.append(match.group(0))
    return unknown


def _serialize_tier(tier: CanonicalDependentTier) -> list[str]:
    lines = [f"{tier.tier}:\t{escape_text(tier.text)}"]
    lines.extend(f"\t{escape_text(part)}" for part in tier.continuation_parts)
    return lines


def serialize_chat(document: CanonicalChatDocument) -> str:
    if document.subset_version != CHAT_SUBSET_VERSION:
        raise ValueError("unsupported CHAT subset version")
    participants = tuple(sorted(document.participants, key=_participant_sort_key))
    lines = ["@UTF8", "@Begin"]
    lines.append(f"@Languages:\t{escape_text(','.join(document.language_codes))}")
    lines.append(
        "@Participants:\t" + ", ".join(_participant_text(item) for item in participants)
    )
    for participant in participants:
        lines.append(f"@ID:\t{escape_text(_id_line(participant))}")
    if document.media_reference:
        lines.append(f"@Media:\t{escape_text(document.media_reference)}, audio")
    for key in ("@Date", "@Location", "@Situation", "@Activities", "@Comment", "@Transcriber", "@Options"):
        for optional_key, optional_value in document.optional_headers:
            if optional_key == key:
                lines.append(f"{key}:\t{escape_text(optional_value)}")
    for extension in document.opaque_extensions:
        if extension.location == "header":
            lines.append(f"{extension.key}:\t{escape_text(extension.content)}")
    for utterance in document.utterances:
        lines.append(f"@x-lingualens-utterance-id:\t{escape_text(utterance.utterance_id)}")
        body = escape_text(utterance.reviewed_text_nfc)
        if utterance.terminator and not body.endswith(utterance.terminator):
            body = f"{body}{utterance.terminator}"
        if utterance.start_ms is not None and utterance.end_ms is not None:
            body = f"{body} \x15{utterance.start_ms}_{utterance.end_ms}\x15"
        lines.append(f"*{utterance.speaker_code}:\t{body}")
        lines.extend(f"\t{escape_text(part)}" for part in utterance.continuation_parts)
        for tier in utterance.dependent_tiers:
            lines.extend(_serialize_tier(tier))
        for extension in document.opaque_extensions:
            if extension.location != "header" and extension.owner_utterance_id == utterance.utterance_id:
                lines.append(f"{extension.key}:\t{escape_text(extension.content)}")
    lines.append("@End")
    return "\n".join(lines) + "\n"


def _parse_header(raw_line: str) -> tuple[str, str]:
    key, separator, value = raw_line.partition(":")
    return key.strip(), value.lstrip(" \t") if separator else ""


def _parse_participants(value: str) -> tuple[CanonicalParticipant, ...]:
    participants: list[CanonicalParticipant] = []
    for raw in value.split(","):
        fields = raw.strip().split()
        if not fields:
            continue
        code = fields[0].upper()
        display = fields[1] if len(fields) > 1 else code
        role = " ".join(fields[2:]) if len(fields) > 2 else "Adult"
        participants.append(CanonicalParticipant(code=code, display_name=display, role=role))
    return tuple(participants)


def _parse_id(value: str) -> tuple[str, tuple[str, ...]] | None:
    fields = tuple(value.split("|"))
    if len(fields) < 3 or not fields[2]:
        return None
    return fields[2].upper(), fields


def _parse_body(raw_body: str, utterance_id: str, errors: list[ChatRoundTripError]):
    body = raw_body.strip()
    start_ms = end_ms = None
    if MEDIA_SENTINEL_RE.search(body):
        match = MEDIA_BULLET_RE.search(body)
        if match is None:
            errors.append(_error("CHAT_TIMESTAMP_MALFORMED", field_or_tier="timestamp", utterance_or_segment_id=utterance_id, actual=body))
        else:
            start_ms, end_ms = int(match.group(1)), int(match.group(2))
            if start_ms >= end_ms:
                errors.append(_error("CHAT_TIMESTAMP_RANGE_INVALID", field_or_tier="timestamp", utterance_or_segment_id=utterance_id, actual=f"{start_ms}_{end_ms}"))
            body = body[: match.start()].rstrip()
    try:
        body = unescape_text(body)
    except ValueError as exc:
        errors.append(_error("CHAT_ESCAPING_INVALID", field_or_tier="text", utterance_or_segment_id=utterance_id, actual=str(exc)))
        body = normalize_text(body)
    terminator = ""
    if body and body[-1] in ".?!;":
        terminator = body[-1]
        body = body[:-1].rstrip()
    return body, start_ms, end_ms, terminator


def parse_chat(text: str, *, profile: str = CHAT_SUBSET_VERSION) -> ChatParseResult:
    errors: list[ChatRoundTripError] = []
    source = str(text or "")
    lines = source.splitlines()
    headers: list[tuple[str, str]] = []
    participants_raw = ""
    ids: dict[str, tuple[str, ...]] = {}
    media_reference: str | None = None
    languages: tuple[str, ...] = ()
    optional: list[tuple[str, str]] = []
    opaque: list[CanonicalOpaqueExtension] = []
    utterances: list[CanonicalChatUtterance] = []
    pending_id: str | None = None
    current_index: int | None = None
    current_tier: str | None = None
    current_dependent_index: int | None = None
    seen_begin = seen_end = False

    for line_number, raw_line in enumerate(lines, start=1):
        is_continuation = raw_line.startswith("\t")
        line = raw_line.strip() if not is_continuation else raw_line[1:].strip()
        if not line:
            continue
        if line.startswith("@"):
            key, value = _parse_header(line)
            if key == "@UTF8":
                continue
            if key == "@Begin":
                seen_begin = True
                continue
            if key == "@End":
                seen_end = True
                continue
            if key == "@Languages":
                try:
                    languages = tuple(unescape_text(value).replace(";", ",").split(","))
                    languages = tuple(code.strip() for code in languages if code.strip())
                except ValueError:
                    languages = tuple(value.split(","))
                continue
            if key == "@Participants":
                participants_raw = value
                continue
            if key == "@ID":
                parsed_id = _parse_id(value)
                if parsed_id:
                    ids[parsed_id[0]] = parsed_id[1]
                else:
                    errors.append(_error("CHAT_PARTICIPANT_ID_INVALID", field_or_tier="@ID", actual=value))
                continue
            if key == "@Media":
                media_reference = unescape_text(value).split(",", 1)[0].strip()
                continue
            if key == "@x-lingualens-utterance-id":
                try:
                    pending_id = unescape_text(value)
                except ValueError:
                    pending_id = value
                continue
            if key in {"@Date", "@Location", "@Situation", "@Activities", "@Comment", "@Transcriber", "@Options"}:
                optional.append((key, unescape_text(value)))
                continue
            if key.startswith("@x-"):
                opaque.append(CanonicalOpaqueExtension(action="preserved_opaque", location="header", key=key, content=value))
                continue
            errors.append(_error("CHAT_UNKNOWN_HEADER", field_or_tier=key, actual=value))
            continue

        match = SPEAKER_RE.match(line)
        if match:
            speaker = match.group(1).upper()
            utterance_id = pending_id or f"utterance-{len(utterances) + 1:04d}"
            pending_id = None
            body, start_ms, end_ms, terminator = _parse_body(match.group(2), utterance_id, errors)
            for annotation in _unknown_annotation_spans(body):
                errors.append(
                    _error(
                        "CHAT_UNKNOWN_ANNOTATION",
                        field_or_tier="annotation",
                        utterance_or_segment_id=utterance_id,
                        actual=annotation,
                    )
                )
            utterances.append(
                CanonicalChatUtterance(
                    utterance_id=utterance_id,
                    speaker_code=speaker,
                    reviewed_text_nfc=body,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    terminator=terminator,
                    annotations=_annotation_payloads(body),
                )
            )
            current_index = len(utterances) - 1
            current_tier = "main"
            current_dependent_index = None
            continue

        dependent_match = DEPENDENT_RE.match(line)
        if dependent_match:
            tier = dependent_match.group(1)
            tier_text = dependent_match.group(2)
            if current_index is None:
                errors.append(_error("CHAT_ORPHAN_DEPENDENT_TIER", field_or_tier=tier, actual=tier_text))
                if tier.startswith("%x"):
                    opaque.append(CanonicalOpaqueExtension(action="preserved_opaque", location="dependent_tier", key=tier, content=tier_text))
                else:
                    errors.append(_error("CHAT_UNSUPPORTED_DEPENDENT_TIER", field_or_tier=tier, actual=tier_text))
                continue
            if tier not in SUPPORTED_DEPENDENT_TIERS:
                if tier.startswith("%x"):
                    opaque.append(CanonicalOpaqueExtension(action="preserved_opaque", location="dependent_tier", key=tier, content=tier_text, owner_utterance_id=utterances[current_index].utterance_id))
                else:
                    errors.append(_error("CHAT_UNSUPPORTED_DEPENDENT_TIER", field_or_tier=tier, utterance_or_segment_id=utterances[current_index].utterance_id, actual=tier_text))
                current_tier = tier
                current_dependent_index = None
                continue
            tier_obj = CanonicalDependentTier(tier=tier, text=unescape_text(tier_text))
            updated = list(utterances[current_index].dependent_tiers)
            updated.append(tier_obj)
            utterances[current_index] = utterances[current_index].model_copy(update={"dependent_tiers": tuple(updated)})
            current_tier = tier
            current_dependent_index = len(updated) - 1
            continue

        if is_continuation and current_index is not None:
            try:
                continuation = unescape_text(line)
            except ValueError:
                continuation = normalize_text(line)
                errors.append(_error("CHAT_ESCAPING_INVALID", field_or_tier=current_tier, utterance_or_segment_id=utterances[current_index].utterance_id, actual=line))
            if current_tier == "main":
                parts = (*utterances[current_index].continuation_parts, continuation)
                utterances[current_index] = utterances[current_index].model_copy(update={"continuation_parts": parts})
            elif current_tier in SUPPORTED_DEPENDENT_TIERS and current_dependent_index is not None:
                tiers = list(utterances[current_index].dependent_tiers)
                tier = tiers[current_dependent_index]
                tiers[current_dependent_index] = tier.model_copy(update={"continuation_parts": (*tier.continuation_parts, continuation)})
                utterances[current_index] = utterances[current_index].model_copy(update={"dependent_tiers": tuple(tiers)})
            else:
                errors.append(_error("CHAT_CONTINUATION_WITHOUT_OWNER", field_or_tier=current_tier, utterance_or_segment_id=utterances[current_index].utterance_id, actual=continuation))
            continue

        errors.append(_error("CHAT_MALFORMED_LINE", field_or_tier=f"line:{line_number}", actual=raw_line))

    if not seen_begin:
        errors.append(_error("CHAT_MISSING_BEGIN", field_or_tier="@Begin"))
    if not seen_end:
        errors.append(_error("CHAT_MISSING_END", field_or_tier="@End"))
    if not participants_raw:
        errors.append(_error("CHAT_MISSING_PARTICIPANTS", field_or_tier="@Participants"))
    participants = list(_parse_participants(participants_raw))
    by_code = {item.code: item for item in participants}
    for code, id_fields in ids.items():
        if code in by_code:
            by_code[code] = by_code[code].model_copy(update={"id_fields": id_fields})
    participants = list(by_code.values())
    declared_codes = {item.code for item in participants}
    for utterance in utterances:
        if utterance.speaker_code not in declared_codes:
            errors.append(_error("CHAT_UNKNOWN_MAIN_TIER", field_or_tier=f"*{utterance.speaker_code}", utterance_or_segment_id=utterance.utterance_id, actual=utterance.speaker_code))

    document = CanonicalChatDocument(
        language_codes=languages,
        media_reference=media_reference,
        participants=tuple(participants),
        utterances=tuple(utterances),
        optional_headers=tuple(optional),
        opaque_extensions=tuple(opaque),
    )
    if profile not in {CHAT_SUBSET_VERSION, EXTERNAL_IMPORT_PROFILE}:
        errors.append(_error("CHAT_PROFILE_UNSUPPORTED", actual=profile))
    return ChatParseResult(document=document, errors=errors)


def _canonical_json(document: CanonicalChatDocument) -> str:
    return json.dumps(document.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def semantic_checksum(document: CanonicalChatDocument) -> str:
    return sha256(_canonical_json(document).encode("utf-8")).hexdigest()


def compare_semantics(
    expected: CanonicalChatDocument,
    actual: CanonicalChatDocument,
    *,
    profile: str = CHAT_SUBSET_VERSION,
) -> list[ChatRoundTripError]:
    errors: list[ChatRoundTripError] = []

    def check(field: str, expected_value, actual_value, code: str, utterance_id: str | None = None):
        if expected_value != actual_value:
            errors.append(_error(code, field_or_tier=field, utterance_or_segment_id=utterance_id, expected=expected_value, actual=actual_value))

    check("language", expected.language_codes, actual.language_codes, "CHAT_LANGUAGE_CHANGED")
    check("media", expected.media_reference, actual.media_reference, "CHAT_MEDIA_CHANGED")
    expected_participants = tuple(
        item.model_dump(mode="json") for item in expected.participants
    )
    actual_participants = tuple(item.model_dump(mode="json") for item in actual.participants)
    for expected_item, actual_item in zip(expected_participants, actual_participants):
        if not expected_item.get("id_fields") and actual_item.get("id_fields"):
            actual_item["id_fields"] = []
    check("participants", expected_participants, actual_participants, "CHAT_PARTICIPANT_CHANGED")
    if len(expected.utterances) != len(actual.utterances):
        errors.append(_error("CHAT_UTTERANCE_COUNT_CHANGED", field_or_tier="utterances", expected=len(expected.utterances), actual=len(actual.utterances)))
    for index, (left, right) in enumerate(zip(expected.utterances, actual.utterances)):
        utterance_id = left.utterance_id
        check("speaker", left.speaker_code, right.speaker_code, "CHAT_SPEAKER_CHANGED", utterance_id)
        check("text", left.reviewed_text_nfc, right.reviewed_text_nfc, "CHAT_TEXT_CHANGED", utterance_id)
        check("start_ms", left.start_ms, right.start_ms, "CHAT_TIMESTAMP_CHANGED", utterance_id)
        check("end_ms", left.end_ms, right.end_ms, "CHAT_TIMESTAMP_CHANGED", utterance_id)
        check("terminator", left.terminator, right.terminator, "CHAT_TERMINATOR_CHANGED", utterance_id)
        check("continuation", left.continuation_parts, right.continuation_parts, "CHAT_CONTINUATION_CHANGED", utterance_id)
        check("dependent_tiers", left.dependent_tiers, right.dependent_tiers, "CHAT_TIER_CHANGED", utterance_id)
        check("annotations", left.annotations, right.annotations, "CHAT_ANNOTATION_CHANGED", utterance_id)
        check("utterance_id", left.utterance_id, right.utterance_id, "CHAT_UTTERANCE_ID_CHANGED", utterance_id)
    if profile == CHAT_SUBSET_VERSION:
        check("optional_headers", expected.optional_headers, actual.optional_headers, "CHAT_HEADER_CHANGED")
    else:
        check("optional_headers", sorted(expected.optional_headers), sorted(actual.optional_headers), "CHAT_HEADER_CHANGED")
    check("opaque_extensions", expected.opaque_extensions, actual.opaque_extensions, "CHAT_OPAQUE_EXTENSION_CHANGED")
    return errors
