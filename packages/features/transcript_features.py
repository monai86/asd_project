"""Transcript feature extraction built around the canonical project schema."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
from typing import Any, Sequence

from packages.cha.parser import ParsedChaTranscript, ParsedChaUtterance, parse_cha_file
from src.audio_pipeline.acoustic_profile import compute_acoustic_profile
from src.clinical_speech.feature_extractor import content_tokens, extract_clinical_features
from src.clinical_speech.models import NormalizedTranscriptLine
from src.feature_schema import FEATURES, OPTIONAL_INDICATORS


FEATURE_ALIASES: dict[str, str] = {
    "child_utterance_count": "total_utterances",
    "total_child_words": "total_words",
    "mean_length_utterance_child": "mluw",
    "type_token_ratio_child": "ttr",
    "unintelligible_token_count": "unintelligible_count",
}

PRONOUN_REVERSAL_PATTERNS = [
    re.compile(r"\byou\s+(?:want|need|have|like|go|do|see|get|play)\b", re.IGNORECASE),
    re.compile(r"\byou\s+(?:am|was)\b", re.IGNORECASE),
    re.compile(r"\bme\s+(?:am|want|need|have|like|go|do|see|get|play)\b", re.IGNORECASE),
    re.compile(r"\bmy\s+(?:want|need|have|like|go|do|see|get|play)\b", re.IGNORECASE),
    re.compile(r"\bi\s+(?:are|is)\b", re.IGNORECASE),
    re.compile(r"\byour\s+(?:want|need|have|like|go|do|see|get|play)\b", re.IGNORECASE),
]


def extract_transcript_features(
    transcript: ParsedChaTranscript | Sequence[NormalizedTranscriptLine] | str | Path,
    *,
    age_months: int | float | None = None,
) -> dict[str, Any]:
    """Extract canonical features, feature aliases, and extended indicators."""
    parsed: ParsedChaTranscript | None = None
    if isinstance(transcript, (str, Path)):
        parsed = parse_cha_file(transcript)
        lines = parsed.to_normalized_lines()
    elif isinstance(transcript, ParsedChaTranscript):
        parsed = transcript
        lines = transcript.to_normalized_lines()
    else:
        lines = list(transcript)

    extracted = extract_clinical_features(lines, age_months=age_months)
    canonical = {key: extracted["core_features"].get(key, 0) for key in FEATURES}
    optional = {key: extracted["optional_indicators"].get(key, 0) for key in OPTIONAL_INDICATORS}
    extended = _extended_interaction_features(lines, parsed=parsed)
    aliases = feature_aliases({**canonical, **optional, **extended})

    return {
        "feature_schema_version": extracted["feature_schema_version"],
        "canonical_features": canonical,
        "core_features": canonical,
        "optional_indicators": {**optional, **extended},
        "feature_aliases": aliases,
        "features": {**canonical, **optional, **extended, **aliases},
        "review_flags": extracted.get("review_flags", []),
        "safety_labels": extracted.get("safety_labels", []),
    }


def feature_aliases(features: dict[str, Any]) -> dict[str, Any]:
    """Return prompt-facing aliases without changing canonical model inputs."""
    aliases = {
        alias: features.get(canonical, 0)
        for alias, canonical in FEATURE_ALIASES.items()
    }
    child_count = float(features.get("total_utterances") or 0)
    adult_count = float(features.get("adult_utterance_count") or 0)
    aliases["adult_utterance_count"] = int(adult_count)
    aliases["pronoun_reversal_rate"] = round(
        float(features.get("pronoun_reversal_count") or 0) / child_count,
        4,
    ) if child_count else 0.0
    return aliases


def extract_acoustic_features(audio_path: str | Path, utterances: Sequence[Any] | None = None) -> dict[str, float]:
    """Extract context-only acoustic indicators from aligned audio when present."""
    profile = compute_acoustic_profile(audio_path, list(utterances or []))
    profile_dict = profile.to_dict()
    return {
        "speech_rate_words_per_minute": _safe_round(profile_dict.get("child_speech_rate_wps"), scale=60.0),
        "average_pause_duration": 0.0,
        "pitch_mean": _safe_round(profile_dict.get("f0_median_hz")),
        "pitch_variability": _safe_round(profile_dict.get("f0_iqr_hz")),
        "intensity_mean": 0.0,
        "voiced_ratio": _safe_round(profile_dict.get("voiced_ratio")),
        "duration_sec": _safe_round(profile_dict.get("duration_sec")),
        "pause_ratio": _safe_round(profile_dict.get("pause_ratio")),
    }


def _extended_interaction_features(
    lines: Sequence[NormalizedTranscriptLine],
    *,
    parsed: ParsedChaTranscript | None = None,
) -> dict[str, Any]:
    ordered = sorted(
        lines,
        key=lambda line: (
            line.start_ms if line.start_ms is not None else 10**12,
            line.line_number if line.line_number is not None else 10**9,
        ),
    )
    child_lines = [_line for _line in ordered if _is_child(_line)]
    adult_lines = [_line for _line in ordered if _is_adult(_line)]
    child_tokens_by_line = [content_tokens(line.effective_text) for line in child_lines]
    child_words = [token for tokens in child_tokens_by_line for token in tokens]
    all_word_counts = [len(content_tokens(line.effective_text)) for line in ordered]
    adult_child_pairs = _adult_child_pairs(ordered)
    adult_question_count = sum(1 for line in adult_lines if "?" in line.effective_text)
    adult_question_pairs = [
        (adult, child)
        for adult, child in adult_child_pairs
        if "?" in adult.effective_text
    ]
    repetitive_phrase_count = _repetitive_phrase_count(child_tokens_by_line)
    echolalia_similarity_score = _echolalia_similarity_score(ordered)
    incomplete_count = sum(1 for line in child_lines if _is_incomplete(line.effective_text))
    unintelligible_token_count = sum(
        1
        for line in child_lines
        for token in re.findall(r"\b(?:xxx|yyy|www)\b", line.effective_text, flags=re.IGNORECASE)
    )
    pronoun_count = sum(
        len(pattern.findall(line.effective_text))
        for line in child_lines
        for pattern in PRONOUN_REVERSAL_PATTERNS
    )

    if parsed is not None:
        child_count = sum(1 for utt in parsed.utterances if utt.speaker_role == "child")
        adult_count = sum(1 for utt in parsed.utterances if utt.speaker_role != "child")
    else:
        child_count = len(child_lines)
        adult_count = len(adult_lines)

    return {
        "adult_utterance_count": adult_count,
        "mean_words_per_turn": round(sum(all_word_counts) / len(ordered), 4) if ordered else 0.0,
        "child_adult_turn_ratio": round(child_count / adult_count, 4) if adult_count else 0.0,
        "response_ratio": round(len(adult_child_pairs) / len(adult_lines), 4) if adult_lines else 0.0,
        "question_response_ratio": round(len(adult_question_pairs) / adult_question_count, 4)
        if adult_question_count else 0.0,
        "repetitive_phrase_count": repetitive_phrase_count,
        "echolalia_similarity_score": echolalia_similarity_score,
        "pronoun_reversal_rate": round(pronoun_count / len(child_lines), 4) if child_lines else 0.0,
        "unintelligible_token_count": unintelligible_token_count,
        "incomplete_utterance_rate": round(incomplete_count / len(child_lines), 4) if child_lines else 0.0,
        "child_utterance_count": child_count,
        "total_child_words": len(child_words),
        "mean_length_utterance_child": round(len(child_words) / len(child_lines), 4) if child_lines else 0.0,
        "type_token_ratio_child": round(len(set(child_words)) / len(child_words), 4) if child_words else 0.0,
    }


def _adult_child_pairs(lines: Sequence[NormalizedTranscriptLine]) -> list[tuple[NormalizedTranscriptLine, NormalizedTranscriptLine]]:
    pairs = []
    for adult, child in zip(lines, lines[1:]):
        if _is_adult(adult) and _is_child(child):
            pairs.append((adult, child))
    return pairs


def _repetitive_phrase_count(child_tokens_by_line: Sequence[Sequence[str]]) -> int:
    count = 0
    phrases = Counter(tuple(tokens) for tokens in child_tokens_by_line if tokens)
    count += sum(max(0, occurrences - 1) for occurrences in phrases.values())
    for tokens in child_tokens_by_line:
        count += sum(1 for left, right in zip(tokens, tokens[1:]) if left == right)
    return count


def _echolalia_similarity_score(lines: Sequence[NormalizedTranscriptLine]) -> float:
    scores: list[float] = []
    recent_adult: list[set[str]] = []
    for line in lines:
        token_set = set(content_tokens(line.effective_text))
        if _is_child(line) and token_set:
            scores.append(max((_jaccard(token_set, prev) for prev in recent_adult[-3:] if prev), default=0.0))
        elif _is_adult(line) and token_set:
            recent_adult.append(token_set)
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def _is_incomplete(text: str) -> bool:
    stripped = re.sub(r"\x15\d+[_-]\d+\x15", "", str(text or "")).strip()
    return stripped.endswith(("+...", "+/.", "+//.", "+/?")) or stripped.endswith(("[//]", "[/]"))


def _is_child(line: NormalizedTranscriptLine) -> bool:
    return line.speaker_role == "child" or line.speaker_code.upper() == "CHI"


def _is_adult(line: NormalizedTranscriptLine) -> bool:
    return not _is_child(line)


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _safe_round(value: Any, *, scale: float = 1.0) -> float:
    try:
        number = float(value) * scale
    except (TypeError, ValueError):
        return 0.0
    if number != number:
        return 0.0
    return round(number, 4)
