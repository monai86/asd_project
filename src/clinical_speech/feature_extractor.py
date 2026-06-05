"""Line-based clinical speech feature extraction.

Outputs are descriptive decision-support values. Possible ASD-relevant markers
are always surfaced as review flags, never as automatic diagnostic findings.
"""

from __future__ import annotations

import re
from typing import Any, Sequence

from src.feature_schema import FEATURES, OPTIONAL_INDICATORS

from .models import NormalizedTranscriptLine


def is_thai_text(text: str) -> bool:
    return any('\u0e00' <= char <= '\u0e7f' for char in text)


def thai_content_tokens(text: str) -> list[str]:
    raw = str(text or "")
    raw = re.sub(r"\x15\d+_\d+\x15", " ", raw)
    raw = re.sub(r"\[[^\]]+\]", " ", raw)
    raw = re.sub(r"&\=[A-Za-z0-9ก-๙_-]+", " ", raw)
    raw = re.sub(r"\b(?:xxx|yyy|www)\b", " ", raw)
    raw = re.sub(r"\b0\b", " ", raw)
    
    try:
        from pythainlp.tokenize import word_tokenize
        raw_tokens = word_tokenize(raw)
    except ImportError:
        raw_tokens = re.findall(r"[\w'-]+", raw, re.UNICODE)
        
    cleaned = []
    for token in raw_tokens:
        token_clean = token.strip()
        if token_clean and any(c.isalnum() or '\u0e00' <= c <= '\u0e7f' for c in token_clean):
            cleaned.append(token_clean.lower())
    return cleaned


def thai_syllable_count(text: str) -> int:
    raw = str(text or "")
    raw = re.sub(r"\x15\d+_\d+\x15", " ", raw)
    raw = re.sub(r"\[[^\]]+\]", " ", raw)
    raw = re.sub(r"&\=[A-Za-z0-9ก-๙_-]+", " ", raw)
    raw = re.sub(r"\b(?:xxx|yyy|www)\b", " ", raw)
    raw = re.sub(r"\b0\b", " ", raw)
    
    try:
        from pythainlp.tokenize import syllable_tokenize
        syllables = syllable_tokenize(raw, engine="dict")
    except Exception:
        try:
            from pythainlp.tokenize import word_tokenize
            syllables = word_tokenize(raw)
        except ImportError:
            syllables = re.findall(r"[\w'-]+", raw, re.UNICODE)
            
    count = 0
    for syl in syllables:
        syl_clean = syl.strip()
        if syl_clean and any(c.isalnum() or '\u0e00' <= c <= '\u0e7f' for c in syl_clean):
            count += 1
    return count


TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)
UNINTELLIGIBLE_RE = re.compile(r"\b(?:xxx|yyy|www)\b", re.IGNORECASE)
VOCALIZATION_RE = re.compile(r"&=[A-Za-zก-๙_-]+")
PRONOUN_REVERSAL_PATTERNS = [
    re.compile(r"\byou\s+(?:want|need|have|like|go|do|see|get|play)\b", re.IGNORECASE),
    re.compile(r"\byou\s+(?:am|was)\b", re.IGNORECASE),
    re.compile(r"\bme\s+(?:am|want|need|have|like|go|do|see|get|play)\b", re.IGNORECASE),
    re.compile(r"\bmy\s+(?:want|need|have|like|go|do|see|get|play)\b", re.IGNORECASE),
    re.compile(r"\bi\s+(?:are|is)\b", re.IGNORECASE),
    re.compile(r"\byour\s+(?:want|need|have|like|go|do|see|get|play)\b", re.IGNORECASE),
]
RESTRICTED_INTEREST_TERMS = {
    "train",
    "trains",
    "wheel",
    "wheels",
    "number",
    "numbers",
    "letter",
    "letters",
    "map",
    "maps",
    "dinosaur",
    "dinosaurs",
    "schedule",
    "schedules",
}
CHAT_CODES = {"0", "xxx", "yyy", "www"}


def extract_clinical_features(
    lines: Sequence[NormalizedTranscriptLine],
    *,
    age_months: int | float | None = None,
) -> dict[str, Any]:
    ordered = sorted(
        lines,
        key=lambda line: (
            line.start_ms if line.start_ms is not None else 10**12,
            line.line_number if line.line_number is not None else 10**9,
            line.line_id or "",
        ),
    )
    child_lines = [line for line in ordered if line.speaker_role == "child" or line.speaker_code.upper() == "CHI"]
    adult_therapist_lines = [line for line in ordered if line.speaker_role == "therapist"]
    caregiver_lines = [line for line in ordered if line.speaker_role in {"parent", "family"}]

    has_thai = any(is_thai_text(line.effective_text) for line in child_lines)
    if has_thai:
        child_tokens_by_line = [thai_content_tokens(line.effective_text) for line in child_lines]
        child_syllables_by_line = [thai_syllable_count(line.effective_text) for line in child_lines]
        child_tokens = [token for tokens in child_tokens_by_line for token in tokens]
        total_words = len(child_tokens)
        unique_words = len(set(child_tokens))
        total_syllables = sum(child_syllables_by_line)
        total_utterances = len(child_lines)
        mlu_s = round(total_syllables / total_utterances, 3) if total_utterances else 0.0
        mlu_w = round(total_words / total_utterances, 3) if total_utterances else 0.0
    else:
        child_tokens_by_line = [content_tokens(line.effective_text) for line in child_lines]
        child_tokens = [token for tokens in child_tokens_by_line for token in tokens]
        total_words = len(child_tokens)
        unique_words = len(set(child_tokens))
        total_utterances = len(child_lines)
        mlu_s = 0.0
        mlu_w = round(total_words / total_utterances, 3) if total_utterances else 0.0

    unintelligible_count = sum(1 for line in child_lines if UNINTELLIGIBLE_RE.search(line.effective_text))
    zero_vocalization_count = sum(1 for line in child_lines if _is_zero_vocalization(line.effective_text))
    nonverbal_vocalization_count = sum(1 for line in child_lines if VOCALIZATION_RE.search(line.effective_text))
    question_count = sum(1 for line in child_lines if "?" in line.effective_text)
    echolalia = possible_echolalia_like_repetition(ordered)
    pronouns = possible_pronoun_reversals(child_lines)
    pauses = long_pauses(ordered)
    response = response_latencies(ordered)
    turn_count = turn_taking_count(ordered)
    restricted_interest_words = sum(1 for token in child_tokens if token in RESTRICTED_INTEREST_TERMS)

    core_features = {
        "age_months": age_months if age_months is not None else 0,
        "total_utterances": total_utterances,
        "mlu": round(total_words / total_utterances, 3) if total_utterances else 0.0,
        "mluw": mlu_w,
        "ttr": round(unique_words / total_words, 4) if total_words else 0.0,
        "total_words": total_words,
        "unintelligible_count": unintelligible_count,
        "unintelligible_ratio": round(unintelligible_count / total_utterances, 4) if total_utterances else 0.0,
        "zero_vocalization_count": zero_vocalization_count,
        "nonverbal_vocalization_count": nonverbal_vocalization_count,
        "question_ratio": round(question_count / total_utterances, 4) if total_utterances else 0.0,
        "echolalia_count": echolalia["count"],
        "echolalia_ratio": round(echolalia["count"] / total_utterances, 4) if total_utterances else 0.0,
        "pronoun_reversal_count": pronouns["count"],
    }
    optional_indicators = {
        "pause_count": pauses["count"],
        "pause_ratio": round(pauses["count"] / total_utterances, 4) if total_utterances else 0.0,
        "therapist_utterances": len(adult_therapist_lines),
        "caregiver_utterances": len(caregiver_lines),
        "turn_taking_count": turn_count,
        "response_latency_avg": response["average_seconds"],
        "restricted_interest_words": restricted_interest_words,
    }

    review_flags = [
        *echolalia["flags"],
        *pronouns["flags"],
        *[
            _review_flag(
                "unintelligible_token",
                line,
                "Possible unintelligible token; requires clinician review.",
            )
            for line in child_lines
            if UNINTELLIGIBLE_RE.search(line.effective_text)
        ],
    ]

    return {
        "feature_schema_version": "14-feature-schema",
        "features": {
            **_ordered(core_features, FEATURES),
            **_ordered(optional_indicators, OPTIONAL_INDICATORS),
            "mlu_s": mlu_s,
            "mlu_w": mlu_w,
        },
        "core_features": _ordered(core_features, FEATURES),
        "optional_indicators": {
            **_ordered(optional_indicators, OPTIONAL_INDICATORS),
            "total_words_all_speakers": sum(len(content_tokens(line.effective_text)) for line in ordered),
            "unique_words": unique_words,
            "response_latency_ms_values": response["values_ms"],
        },
        "review_flags": review_flags,
        "safety_labels": [
            "clinical decision-support only",
            "does not diagnose ASD",
            "possible markers require clinician review",
        ],
    }


def content_tokens(text: str) -> list[str]:
    raw = str(text or "")
    raw = re.sub(r"\x15\d+_\d+\x15", " ", raw)
    raw = re.sub(r"\[[^\]]+\]", " ", raw)
    tokens = [token.lower() for token in TOKEN_RE.findall(raw)]
    return [
        token
        for token in tokens
        if token not in CHAT_CODES
        and not token.startswith("&")
        and not token.startswith("-")
    ]


def possible_echolalia_like_repetition(lines: Sequence[NormalizedTranscriptLine]) -> dict[str, Any]:
    flags: list[dict[str, Any]] = []
    count = 0
    recent_token_sets: list[set[str]] = []
    for line in lines:
        tokens = content_tokens(line.effective_text)
        token_set = set(tokens)
        is_child = line.speaker_role == "child" or line.speaker_code.upper() == "CHI"
        if is_child and len(tokens) >= 1:
            adjacent_repeat = any(tokens[index] == tokens[index + 1] for index in range(len(tokens) - 1))
            overlap = max((_jaccard(token_set, prev) for prev in recent_token_sets[-3:] if prev), default=0.0)
            short_overlap = len(tokens) <= 5 and overlap >= 0.5
            if adjacent_repeat or short_overlap:
                count += 1
                flags.append(
                    _review_flag(
                        "possible_echolalia_like_repetition",
                        line,
                        "Possible echolalia-like lexical repetition; requires clinician review.",
                        {"lexical_overlap": round(overlap, 3), "adjacent_repeat": adjacent_repeat},
                    )
                )
        if token_set:
            recent_token_sets.append(token_set)
    return {"count": count, "flags": flags}


def possible_pronoun_reversals(lines: Sequence[NormalizedTranscriptLine]) -> dict[str, Any]:
    flags: list[dict[str, Any]] = []
    count = 0
    for line in lines:
        matches = sum(len(pattern.findall(line.effective_text)) for pattern in PRONOUN_REVERSAL_PATTERNS)
        if matches:
            count += matches
            flags.append(
                _review_flag(
                    "possible_pronoun_reversal",
                    line,
                    "Possible pronoun reversal pattern; requires clinician review.",
                    {"match_count": matches},
                )
            )
    return {"count": count, "flags": flags}


def response_latencies(lines: Sequence[NormalizedTranscriptLine]) -> dict[str, Any]:
    values_ms: list[int] = []
    for current, nxt in zip(lines, lines[1:]):
        if current.end_ms is None or nxt.start_ms is None:
            continue
        if nxt.speaker_role != "child":
            continue
        if current.speaker_role == "child":
            continue
        gap = nxt.start_ms - current.end_ms
        if gap >= 0:
            values_ms.append(gap)
    average_ms = round(sum(values_ms) / len(values_ms), 1) if values_ms else 0.0
    return {
        "average_ms": average_ms,
        "average_seconds": round(average_ms / 1000.0, 3),
        "values_ms": values_ms,
    }


def long_pauses(lines: Sequence[NormalizedTranscriptLine], threshold_ms: int = 1500) -> dict[str, Any]:
    values_ms: list[int] = []
    for current, nxt in zip(lines, lines[1:]):
        if current.end_ms is None or nxt.start_ms is None:
            continue
        gap = nxt.start_ms - current.end_ms
        if gap > threshold_ms:
            values_ms.append(gap)
    return {"count": len(values_ms), "values_ms": values_ms}


def turn_taking_count(lines: Sequence[NormalizedTranscriptLine]) -> int:
    return sum(
        1
        for current, nxt in zip(lines, lines[1:])
        if current.speaker_code.upper() != nxt.speaker_code.upper()
    )


def _review_flag(
    marker_type: str,
    line: NormalizedTranscriptLine,
    explanation: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "marker_type": marker_type,
        "line_id": line.line_id,
        "line_number": line.line_number,
        "speaker_code": line.speaker_code,
        "utterance_text": line.effective_text,
        "label": "possible",
        "requires_clinician_review": True,
        "explanation": explanation,
        "evidence": evidence or {},
        "disposition": "needs_more_context",
    }


def _is_zero_vocalization(text: str) -> bool:
    return str(text or "").strip().rstrip(".?!").strip() == "0"


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _ordered(values: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: values.get(key, 0) for key in keys}
