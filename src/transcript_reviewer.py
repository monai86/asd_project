"""Rule-based CHAT transcript reviewer for clinical-readiness QA.

The reviewer flags likely formatting and ASR-segmentation issues before a
transcript is used for feature extraction. It never edits transcript text.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

SPEAKER_RE = re.compile(r"^\*([A-Z]{3}):\s*(.*)$")
ADULT_PROMPT_RE = re.compile(r"\b(what is|tell me|can you|do you)\b", re.I)
THAI_RE = re.compile(r"[ก-๙]")
CONFIDENCE_RE = re.compile(
    r"(?:%conf(?:idence)?\s*:?\s*|(?:asr|diari[sz]ation)[^\n:]*confidence(?:\s+scores?)?\s*[:=]\s*)(0(?:\.\d+)?|1(?:\.0+)?)",
    re.I,
)
AGE_RE = re.compile(r"^\d{1,2};\d{1,2}(?:\.\d{1,2})?$")
TERMINATOR_RE = re.compile(
    r"(\.|\?|!|\+\.\.\.|\+\.\.|\+\/\.|\+\/\/\.|\+\/\?)\s*$"
)

STRUCTURAL_CODES = {
    "MISSING_BEGIN",
    "MISSING_END",
    "MISSING_LANGUAGES",
    "MISSING_PARTICIPANTS",
    "MISSING_ID",
    "MISSING_CHI_TIER",
    "MALFORMED_SPEAKER_TIER",
    "PARTICIPANT_ID_COUNT_MISMATCH",
}

LIGHT_WARNING_PENALTY_CODES = {
    "LANG_TAG_MISMATCH",
    "LOW_ASR_CONFIDENCE",
    "SHORT_CHILD_SAMPLE_FOR_KIDEVAL",
    "LOW_CHILD_TOKEN_COUNT_FOR_VOCD",
}
REFERENCE_READINESS_BLOCKER_CODES = {
    "MISSING_CHILD_AGE",
    "UNPARSEABLE_CHILD_AGE",
    "MISSING_CHILD_ID",
    "MISSING_TARGET_CHILD_ROLE",
}
CLAN_READINESS_WARNING_CODES = {
    "SHORT_CHILD_SAMPLE_FOR_KIDEVAL",
    "LOW_CHILD_TOKEN_COUNT_FOR_VOCD",
}


def _issue(
    severity: str,
    code: str,
    message: str,
    line: int | None,
    suggestion: str,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "line": line,
        "suggestion": suggestion,
    }


def _marker_counts(text: str) -> dict[str, int]:
    speaker_lines = [
        match.group(2).strip()
        for line in text.splitlines()
        if (match := SPEAKER_RE.match(line.strip()))
    ]
    return {
        "xxx": len(re.findall(r"\bxxx\b", text)),
        "yyy": len(re.findall(r"\byyy\b", text)),
        "www": len(re.findall(r"\bwww\b", text)),
        "zero_vocalization": sum(
            1 for utterance in speaker_lines
            if re.fullmatch(r"0\s*[.?!]?", utterance)
        ),
        "laugh": len(re.findall(r"&=laugh\b", text, flags=re.I)),
        "gasp": len(re.findall(r"&=gasp\b", text, flags=re.I)),
        "repetition": len(re.findall(r"\[/\]", text)),
    }


def _languages_header(lines: list[str]) -> str:
    for line in lines:
        if line.lower().startswith("@languages"):
            return line.lower()
    return ""


def _header_values(lines: list[str], header: str) -> list[str]:
    prefix = f"@{header.lower()}:"
    values = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(prefix):
            values.append(stripped.split(":", 1)[1].strip())
    return values


def _participants(lines: list[str]) -> dict[str, dict[str, str]]:
    participants: dict[str, dict[str, str]] = {}
    for value in _header_values(lines, "Participants"):
        for raw_entry in value.split(","):
            parts = raw_entry.strip().split()
            if not parts:
                continue
            code = parts[0].upper()
            participants[code] = {
                "name": parts[1] if len(parts) > 1 else "",
                "role": parts[-1] if len(parts) > 2 else "",
            }
    return participants


def _id_records(lines: list[str]) -> list[dict[str, str]]:
    records = []
    for value in _header_values(lines, "ID"):
        parts = [part.strip() for part in value.split("|")]
        records.append({
            "language": parts[0] if len(parts) > 0 else "",
            "corpus": parts[1] if len(parts) > 1 else "",
            "code": parts[2].upper() if len(parts) > 2 else "",
            "age": parts[3] if len(parts) > 3 else "",
            "sex": parts[4] if len(parts) > 4 else "",
            "group": parts[5] if len(parts) > 5 else "",
            "ses": parts[6] if len(parts) > 6 else "",
            "role": parts[7] if len(parts) > 7 else "",
        })
    return records


def _confidence_values(text: str) -> list[float]:
    values = []
    for match in CONFIDENCE_RE.finditer(text):
        try:
            values.append(float(match.group(1)))
        except ValueError:
            continue
    return values


def _child_tokens(utterance: str) -> list[str]:
    tokens = []
    for raw_token in re.findall(r"\S+", utterance):
        token = raw_token.strip().strip(".,?!;:")
        if token and token not in {"+...", "+..", "+/.", "+//.", "+/?"}:
            tokens.append(token)
    return tokens


def _run_pylangacq_parse_check(text: str) -> list[dict[str, Any]]:
    try:
        import pylangacq
    except ImportError:
        return [
            _issue(
                "info",
                "PYLANGACQ_PARSE_SKIPPED",
                "pylangacq is not installed, so CHAT parse validation was skipped.",
                None,
                "Install pylangacq to enable parser-level transcript validation.",
            )
        ]

    with tempfile.NamedTemporaryFile(
        suffix=".cha", mode="w", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)

    try:
        try:
            pylangacq.read_chat(str(tmp_path))
        except Exception:
            pylangacq.read_chat(str(tmp_path), strict=False)
    except Exception as exc:  # noqa: BLE001
        return [
            _issue(
                "error",
                "PYLANGACQ_PARSE_FAILED",
                f"pylangacq could not parse this CHAT transcript: {exc}",
                None,
                "Review CHAT headers, speaker tiers, terminators, and dependent tiers before feature extraction.",
            )
        ]
    finally:
        tmp_path.unlink(missing_ok=True)

    return []


def _has_explanation_tier(lines: list[str]) -> bool:
    return any(line.strip().lower().startswith("%exp:") for line in lines)


def _media_basename(text: str) -> str | None:
    media_values = _header_values(text.splitlines(), "Media")
    if not media_values:
        return None
    raw_name = media_values[0].split(",", 1)[0].strip()
    return Path(raw_name).stem if raw_name else None


def _readiness_from_issues(issues: list[dict[str, Any]]) -> dict[str, Any]:
    codes = {issue["code"] for issue in issues}
    structural_blockers = [
        issue["code"] for issue in issues
        if issue["severity"] == "error" and issue["code"] in STRUCTURAL_CODES
    ]
    reference_blockers = structural_blockers + sorted(codes & REFERENCE_READINESS_BLOCKER_CODES)
    clan_warnings = sorted(codes & CLAN_READINESS_WARNING_CODES)

    return {
        "feature_extraction_ready": not structural_blockers,
        "reference_comparison_ready": not reference_blockers,
        "clan_metric_ready": not clan_warnings and not structural_blockers,
        "blockers": {
            "feature_extraction": structural_blockers,
            "reference_comparison": reference_blockers,
        },
        "warnings": {
            "clan_metric": clan_warnings,
        },
    }


def review_cha_text(text: str, source_name: str | None = None) -> dict[str, Any]:
    """Review CHAT text and return score, status, summary, and issues."""
    lines = text.splitlines()
    issues: list[dict[str, Any]] = []
    utterance_count = 0
    child_utterance_count = 0
    child_token_count = 0
    thai_in_utterances = False
    participants = _participants(lines)
    id_records = _id_records(lines)

    if not any(line.strip() == "@Begin" for line in lines):
        issues.append(_issue(
            "error", "MISSING_BEGIN", "Missing @Begin header.", None,
            "Add @Begin as the first CHAT header line.",
        ))
    if not any(line.strip() == "@End" for line in lines):
        issues.append(_issue(
            "error", "MISSING_END", "Missing @End footer.", None,
            "Add @End after the final transcript tier.",
        ))
    if not any(line.startswith("@Languages") for line in lines):
        issues.append(_issue(
            "error", "MISSING_LANGUAGES", "Missing @Languages header.",
            None, "Add @Languages with the transcript language code, such as eng or tha.",
        ))
    if not any(line.startswith("@Participants") for line in lines):
        issues.append(_issue(
            "error", "MISSING_PARTICIPANTS", "Missing @Participants header.",
            None, "Add @Participants with CHI and adult speaker roles.",
        ))
    if not any(line.startswith("@ID") for line in lines):
        issues.append(_issue(
            "error", "MISSING_ID", "Missing @ID participant metadata.",
            None, "Add at least one @ID line, including the child participant.",
        ))
    elif participants and len(id_records) != len(participants):
        issues.append(_issue(
            "error",
            "PARTICIPANT_ID_COUNT_MISMATCH",
            "@ID line count does not match @Participants entries.",
            None,
            "Add one @ID line for each participant declared in @Participants.",
        ))

    child_id = next((record for record in id_records if record["code"] == "CHI"), None)
    if id_records and child_id is None:
        issues.append(_issue(
            "warning",
            "MISSING_CHILD_ID",
            "No @ID line for the CHI child participant was found.",
            None,
            "Add an @ID line for CHI before using reference comparison.",
        ))
    if child_id is not None:
        if not child_id["age"]:
            issues.append(_issue(
                "warning",
                "MISSING_CHILD_AGE",
                "The CHI @ID line does not include child age.",
                None,
                "Add child age in CHAT years;months.days format before reference comparison.",
            ))
        elif not AGE_RE.match(child_id["age"]):
            issues.append(_issue(
                "warning",
                "UNPARSEABLE_CHILD_AGE",
                "The CHI @ID age is not in CHAT years;months.days format.",
                None,
                "Use a value such as 4;00.00 for child age.",
            ))
        participant_role = participants.get("CHI", {}).get("role", "")
        id_role = child_id.get("role", "")
        if "target_child" not in f"{participant_role} {id_role}".lower():
            issues.append(_issue(
                "warning",
                "MISSING_TARGET_CHILD_ROLE",
                "CHI is present but not marked as Target_Child.",
                None,
                "Mark the target child role in @Participants or the CHI @ID line.",
            ))

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line.startswith("*"):
            continue

        match = SPEAKER_RE.match(line)
        if not match:
            issues.append(_issue(
                "error",
                "MALFORMED_SPEAKER_TIER",
                "Speaker tier does not follow CHAT-like *XXX: format.",
                idx,
                "Use a three-letter uppercase speaker code such as *CHI: or *MOT:.",
            ))
            continue

        speaker, utterance = match.groups()
        utterance = utterance.strip()
        utterance_count += 1
        if speaker == "CHI":
            child_utterance_count += 1
            child_token_count += len(_child_tokens(utterance))
        if THAI_RE.search(utterance):
            thai_in_utterances = True

        if not utterance:
            issues.append(_issue(
                "warning",
                "EMPTY_UTTERANCE",
                "Speaker tier has no utterance text.",
                idx,
                "Remove the empty tier or add the reviewed utterance text.",
            ))
            continue

        if not TERMINATOR_RE.search(utterance):
            issues.append(_issue(
                "warning",
                "MISSING_TERMINATOR",
                "Utterance does not end with a reasonable CHAT terminator.",
                idx,
                "End utterance lines with ., ?, !, +..., +.., +/., +//., or +/? as appropriate.",
            ))

        token_count = len(re.findall(r"\S+", utterance))
        if token_count > 40 or len(utterance) > 250:
            issues.append(_issue(
                "warning",
                "LONG_UTTERANCE",
                "Very long utterance may indicate ASR segmentation problems.",
                idx,
                "Review segmentation and split long turns before feature extraction.",
            ))

        if speaker == "CHI" and ADULT_PROMPT_RE.search(utterance):
            issues.append(_issue(
                "warning",
                "SUSPICIOUS_CHI_PROMPT",
                "Child tier contains wording that looks like an adult prompt.",
                idx,
                "Confirm speaker assignment before using this transcript for features.",
            ))

    if child_utterance_count == 0:
        issues.append(_issue(
            "error",
            "MISSING_CHI_TIER",
            "No child speaker tier (*CHI:) was found.",
            None,
            "Add or correct child speaker tiers before feature extraction.",
        ))

    if child_utterance_count and child_utterance_count < 50:
        issues.append(_issue(
            "warning",
            "SHORT_CHILD_SAMPLE_FOR_KIDEVAL",
            "Child language sample has fewer than 50 child utterances.",
            None,
            "Do not treat KIDEVAL-style comparisons as ready until the sample reaches the expected minimum.",
        ))
    if child_token_count and child_token_count < 50:
        issues.append(_issue(
            "warning",
            "LOW_CHILD_TOKEN_COUNT_FOR_VOCD",
            "Child language sample has fewer than 50 child tokens.",
            None,
            "Suppress or label VOCD-style metrics as low confidence until at least 50 child tokens are available.",
        ))

    if thai_in_utterances and "tha" not in _languages_header(lines):
        issues.append(_issue(
            "warning",
            "LANG_TAG_MISMATCH",
            "Thai characters were found in speaker utterances, but @Languages does not include tha.",
            None,
            "Add 'tha' to @Languages if using Thai words.",
        ))

    confidences = _confidence_values(text)
    average_confidence = None
    if confidences:
        average_confidence = round(sum(confidences) / len(confidences), 4)
        if average_confidence < 0.6:
            issues.append(_issue(
                "warning",
                "LOW_ASR_CONFIDENCE",
                "Average ASR/diarization confidence is below 0.60.",
                None,
                "Human review is recommended before feature extraction or risk estimate interpretation.",
            ))

    if re.search(r"\bwww\b", text) and not _has_explanation_tier(lines):
        issues.append(_issue(
            "warning",
            "WWW_WITHOUT_EXPLANATION",
            "A www marker was found without a %exp explanation tier.",
            None,
            "Add a %exp tier explaining the excluded material or confirm the marker during human review.",
        ))

    media_basename = _media_basename(text)
    if media_basename and source_name and media_basename != Path(source_name).stem:
        issues.append(_issue(
            "warning",
            "MEDIA_BASENAME_MISMATCH",
            "@Media basename does not match the transcript filename.",
            None,
            "Keep CHAT @Media and transcript basenames aligned when media is linked.",
        ))

    issues.extend(_run_pylangacq_parse_check(text))

    score = 100
    for issue in issues:
        if issue["severity"] == "error":
            score -= 20
        elif issue["severity"] == "warning":
            score -= 5 if issue["code"] in LIGHT_WARNING_PENALTY_CODES else 8
        elif issue["severity"] == "info":
            score -= 2
    score = max(0, min(100, score))

    has_structural_error = any(
        issue["severity"] == "error" and issue["code"] in STRUCTURAL_CODES
        for issue in issues
    )
    has_warning = any(issue["severity"] == "warning" for issue in issues)
    if has_structural_error or score < 60:
        status = "fail"
    elif has_warning or score < 85:
        status = "needs_review"
    else:
        status = "pass"

    return {
        "quality_score": score,
        "status": status,
        "summary": {
            "line_count": len(lines),
            "utterance_count": utterance_count,
            "child_utterance_count": child_utterance_count,
            "child_token_count": child_token_count,
            "marker_counts": _marker_counts(text),
            "average_confidence": average_confidence,
        },
        "readiness": _readiness_from_issues(issues),
        "issues": issues,
    }


def review_cha_file(path: str | Path) -> dict[str, Any]:
    """Review a CHAT file from disk."""
    cha_path = Path(path)
    return review_cha_text(cha_path.read_text(encoding="utf-8"), source_name=cha_path.name)
