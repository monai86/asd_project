"""Shared contracts for ML reference evidence review."""

from dataclasses import dataclass
from typing import Literal

MIN_PARTICIPANTS_PER_CELL = 20
MIN_CORPORA_PER_CELL = 2
SUPPORTED_LANGUAGE = "eng"
FEATURE_TOLERANCES = {
    "age_months": 0.01,
    "total_utterances": 0.0,
    "mlu": 0.001,
    "mluw": 0.001,
    "ttr": 0.0001,
    "total_words": 0.0,
    "unintelligible_count": 0.0,
    "unintelligible_ratio": 0.0001,
    "zero_vocalization_count": 0.0,
    "nonverbal_vocalization_count": 0.0,
    "question_ratio": 0.0001,
    "echolalia_count": 0.0,
    "echolalia_ratio": 0.0001,
    "pronoun_reversal_count": 0.0,
}

OriginalGroup = Literal["TD", "DD", "ASD", "LT", "STI", "HL"]
PresentationGroup = Literal["TD", "DD", "ASD", "OTHER"]
SupportReasonCode = Literal[
    "insufficient_participants",
    "insufficient_corpus_diversity",
]

_ORIGINAL_GROUP_ALIASES: dict[str, OriginalGroup] = {
    "TD": "TD",
    "TYP": "TD",
    "CONTROL": "TD",
    "DD": "DD",
    "ASD": "ASD",
    "LT": "LT",
    "SLI": "STI",
    "STI": "STI",
    "DLD": "STI",
    "HL": "HL",
}


def original_group(value: object) -> OriginalGroup:
    """Return the distinct research label represented by ``value``."""
    normalized_value = str(value or "").strip().upper()
    try:
        return _ORIGINAL_GROUP_ALIASES[normalized_value]
    except KeyError as exc:
        raise ValueError(f"Unsupported reference group: {value}") from exc


def presentation_group(value: object) -> PresentationGroup:
    """Return the presentation label without collapsing research labels."""
    group = original_group(value)
    if group in {"LT", "STI", "HL"}:
        return "OTHER"
    return group


@dataclass(frozen=True)
class SupportDecision:
    supported: bool
    participant_count: int
    corpus_count: int
    reason_code: SupportReasonCode | None


def evaluate_support(participant_count: int, corpus_count: int) -> SupportDecision:
    """Evaluate whether a reference cell meets preregistered support thresholds."""
    if participant_count < MIN_PARTICIPANTS_PER_CELL:
        return SupportDecision(
            supported=False,
            participant_count=participant_count,
            corpus_count=corpus_count,
            reason_code="insufficient_participants",
        )
    if corpus_count < MIN_CORPORA_PER_CELL:
        return SupportDecision(
            supported=False,
            participant_count=participant_count,
            corpus_count=corpus_count,
            reason_code="insufficient_corpus_diversity",
        )
    return SupportDecision(
        supported=True,
        participant_count=participant_count,
        corpus_count=corpus_count,
        reason_code=None,
    )
