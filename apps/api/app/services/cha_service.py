from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import uuid4

from app.schemas.clinical import Utterance, DependentTier, OrphanDependentTier

SPEAKER_RE = re.compile(r"^\*([A-Za-z][A-Za-z0-9_]{0,7}):\s*(.*)$")
MEDIA_BULLET_RE = re.compile(r"\x15(\d+)_(\d+)\x15")


@dataclass
class ParsedChaDocument:
    metadata: dict
    utterances: list[Utterance]
    warnings: list[str]
    validation_issues: list[str]
    orphan_dependent_tiers: list[OrphanDependentTier]
    malformed_lines: list[dict]


def parse_cha_metadata(text: str) -> dict[str, list[str]]:
    headers: dict[str, list[str]] = {}
    for line in str(text or "").splitlines():
        if line.startswith("@"):
            key, _, value = line.partition(":")
            headers.setdefault(key.strip(), []).append(value.strip())
    return headers


def parse_cha_utterances(text: str) -> list[Utterance]:
    return parse_cha_document(text).utterances


def parse_cha_document(text: str) -> ParsedChaDocument:
    utterances: list[Utterance] = []
    warnings: list[str] = []
    validation_issues: list[str] = []
    orphan_dependent_tiers: list[OrphanDependentTier] = []
    malformed_lines: list[dict] = []
    source_lines = str(text or "").splitlines()
    headers = parse_cha_metadata(text)
    participants = parse_participants(headers.get("@Participants", []))
    declared_codes = {item["code"] for item in participants}

    if not participants:
        validation_issues.append("Missing @Participants header.")

    for line_number, raw_line in enumerate(source_lines, start=1):
        line = raw_line.strip()
        if not line or line in {"@Begin", "@End", "@UTF8"} or line.startswith("@"):
            continue
        if line.startswith("%"):
            tier_match = re.match(r"^(%[^:\s]+):\s*(.*)$", line)
            if tier_match:
                tier = tier_match.group(1)
                tier_text = tier_match.group(2)
            else:
                parts = line.split(None, 1)
                tier = parts[0].rstrip(":")
                tier_text = parts[1] if len(parts) > 1 else ""
            
            warning = f"Line {line_number}: dependent tier {tier} is preserved but not analyzed by BasicFeatureProvider."
            if warning not in warnings:
                warnings.append(warning)
                
            if utterances:
                utterances[-1].dependent_tiers.append(
                    DependentTier(
                        tier=tier,
                        raw_text=tier_text,
                        line_number=line_number,
                        supported=False,
                        analyzed=False,
                        parser_action="preserved_not_analyzed"
                    )
                )
            else:
                orphan_dependent_tiers.append(
                    OrphanDependentTier(
                        tier=tier,
                        raw_text=tier_text,
                        line_number=line_number,
                        parser_action="preserved_unattached"
                    )
                )
            continue
        match = SPEAKER_RE.match(raw_line)
        if not match:
            if raw_line[:1].isspace():
                stripped = raw_line.strip()
                if stripped and not (stripped.startswith("@") or stripped.startswith("*") or stripped.startswith("%")):
                    if utterances:
                        body, start_ms, end_ms = parse_media_bullet(stripped)
                        previous = utterances[-1]
                        previous.text = f"{previous.text} {body}".strip()
                        if start_ms is not None:
                            previous.start_ms = start_ms
                            previous.end_ms = end_ms
                        continue
            
            if line:
                malformed_lines.append({"line_number": line_number, "raw_text": raw_line})
                validation_issues.append(f"Line {line_number} is malformed and was not imported.")
            continue
        speaker = normalize_speaker(match.group(1))
        utterance_text, start_ms, end_ms = parse_media_bullet(match.group(2).strip())
        if not utterance_text:
            validation_issues.append(f"Line {line_number} has an empty utterance.")
        if speaker not in declared_codes:
            validation_issues.append(f"Speaker {speaker} is not declared in @Participants.")
        utterances.append(
            Utterance(
                utterance_id=f"utt_{uuid4().hex[:10]}",
                speaker=speaker,
                text=utterance_text,
                start_ms=start_ms,
                end_ms=end_ms,
                unintelligible=has_unintelligible_marker(utterance_text),
            )
        )
    return ParsedChaDocument(
        metadata={
            "languages": parse_languages(headers.get("@Languages", [])),
            "participants": participants,
            "ids": parse_ids(headers.get("@ID", [])),
            "media": parse_media(headers.get("@Media", [])),
            "headers": headers,
        },
        utterances=utterances,
        warnings=warnings,
        validation_issues=validation_issues,
        orphan_dependent_tiers=orphan_dependent_tiers,
        malformed_lines=malformed_lines,
    )


def manual_text_to_utterances(text: str) -> list[Utterance]:
    utterances: list[Utterance] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        speaker = "UNK"
        body = line
        if ":" in line:
            left, right = line.split(":", 1)
            speaker = normalize_speaker(left.strip().lstrip("*"))
            body = right.strip()
        utterances.append(
            Utterance(
                utterance_id=f"utt_{uuid4().hex[:10]}",
                speaker=speaker,
                text=body,
                unintelligible=has_unintelligible_marker(body),
            )
        )
    return utterances


def build_cha_text(
    utterances: list[Utterance],
    *,
    language: str = "eng",
    participants: str = "CHI Child Target_Child, THER Therapist Investigator",
    participant_ids: list[str] | None = None,
    media_name: str | None = None,
) -> str:
    participant_rows = parse_participants([participants])
    existing_codes = {participant["code"] for participant in participant_rows}
    for utterance in utterances:
        code = normalize_speaker(utterance.speaker)
        if code not in existing_codes:
            participant_rows.append(default_participant(code))
            existing_codes.add(code)
    participant_text = ", ".join(
        f"{participant['code']} {participant['name']} {participant['role']}"
        for participant in participant_rows
    )
    lines = ["@Begin", f"@Languages:\t{language}", f"@Participants:\t{participant_text}"]
    ids_by_code = {
        value.split("|")[2].upper(): value
        for value in participant_ids or []
        if len(value.split("|")) > 2 and value.split("|")[2]
    }
    for participant in participant_rows:
        code = participant["code"]
        raw_id = ids_by_code.get(code) or f"{language}|TherapistAppV2|{code}|||||{participant['role']}|||"
        lines.append(f"@ID:\t{raw_id}")
    if media_name:
        lines.append(f"@Media:\t{sanitize_media_name(media_name)}, audio")
    for utterance in utterances:
        speaker = normalize_speaker(utterance.speaker)
        text = utterance.text.strip() or "0"
        terminator = "" if text.endswith((".", "?", "!")) else " ."
        media_bullet = (
            f" \x15{utterance.start_ms}_{utterance.end_ms}\x15"
            if utterance.start_ms is not None and utterance.end_ms is not None
            else ""
        )
        lines.append(f"*{speaker}:\t{text}{terminator}{media_bullet}")
        for dt in getattr(utterance, "dependent_tiers", []):
            lines.append(f"{dt.tier}:\t{dt.raw_text}")
        if utterance.notes:
            lines.append(f"%exp:\t{utterance.notes}")
    lines.append("@End")
    return "\n".join(lines)


def normalize_speaker(value) -> str:
    raw = getattr(value, "value", value)
    code = "".join(ch for ch in str(raw or "").upper() if ch.isalnum() or ch == "_")[:8]
    return code if re.fullmatch(r"[A-Z][A-Z0-9_]{0,7}", code) else "UNK"


def has_unintelligible_marker(text: str) -> bool:
    return bool(re.search(r"\b(?:xxx|yyy|www)\b", str(text or ""), flags=re.I))


def parse_media_bullet(value: str) -> tuple[str, int | None, int | None]:
    match = MEDIA_BULLET_RE.search(value)
    text = MEDIA_BULLET_RE.sub("", value).strip()
    if not match:
        return text, None, None
    return text, int(match.group(1)), int(match.group(2))


def parse_languages(values: list[str]) -> list[str]:
    return [code for value in values for code in re.split(r"[,;\s]+", value) if code]


def parse_participants(values: list[str]) -> list[dict[str, str]]:
    participants: list[dict[str, str]] = []
    for value in values:
        for raw_participant in value.split(","):
            parts = raw_participant.strip().split()
            if not parts:
                continue
            code = normalize_speaker(parts[0])
            participants.append(
                {
                    "code": code,
                    "name": parts[1] if len(parts) > 1 else default_participant(code)["name"],
                    "role": " ".join(parts[2:]) if len(parts) > 2 else default_participant(code)["role"],
                }
            )
    return participants


def default_participant(code: str) -> dict[str, str]:
    defaults = {
        "CHI": {"name": "Child", "role": "Target_Child"},
        "INV": {"name": "Investigator", "role": "Investigator"},
        "THER": {"name": "Therapist", "role": "Investigator"},
        "PAR": {"name": "Parent", "role": "Adult"},
        "MOT": {"name": "Mother", "role": "Adult"},
        "FAT": {"name": "Father", "role": "Adult"},
    }
    return {"code": code, **defaults.get(code, {"name": code, "role": "Adult"})}


def parse_ids(values: list[str]) -> list[dict[str, str]]:
    ids: list[dict[str, str]] = []
    for raw in values:
        parts = raw.split("|")
        if len(parts) > 2 and parts[2]:
            ids.append({"code": normalize_speaker(parts[2]), "raw": raw})
    return ids


def parse_media(values: list[str]) -> dict[str, str] | None:
    if not values:
        return None
    parts = [part.strip() for part in values[0].split(",")]
    return {"name": parts[0], "type": parts[1] if len(parts) > 1 else "audio"}


def sanitize_media_name(value: str) -> str:
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", str(value or ""))
    return re.sub(r"[^A-Za-z0-9_-]", "_", stem) or "session_audio"
