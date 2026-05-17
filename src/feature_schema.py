"""Shared feature schema for ASD speech-language models.

Keeping the model, dashboard, EDA, and reports on one ordered schema prevents
silent prediction drift when a new feature is added to only one surface.
"""

from __future__ import annotations

from dataclasses import dataclass


FEATURES: list[str] = [
    "age_months",
    "total_utterances",
    "mlu",
    "mluw",
    "ttr",
    "total_words",
    "unintelligible_count",
    "unintelligible_ratio",
    "zero_vocalization_count",
    "nonverbal_vocalization_count",
    "question_ratio",
    "echolalia_count",
    "echolalia_ratio",
]

POSITIVE_FEATURES: list[str] = [
    "mlu",
    "mluw",
    "ttr",
    "total_words",
    "total_utterances",
    "question_ratio",
]

MARKER_FEATURES: list[str] = [
    "unintelligible_ratio",
    "zero_vocalization_count",
    "nonverbal_vocalization_count",
    "echolalia_ratio",
]

UNCERTAIN_LOW = 0.40
UNCERTAIN_HIGH = 0.60


@dataclass(frozen=True)
class FeatureDoc:
    title: str
    group: str
    formula: str
    clinical_meaning: str
    direction: str
    caveat: str


FEATURE_DOCS: dict[str, FeatureDoc] = {
    "age_months": FeatureDoc(
        "Age in months",
        "Demographics",
        "CHAT age converted to months",
        "Controls for rapid language development across early childhood.",
        "neutral",
        "Age distributions differ by corpus; do not interpret as ASD signal alone.",
    ),
    "total_utterances": FeatureDoc(
        "Child utterances",
        "Productivity",
        "Count of *CHI: utterance tiers",
        "Higher participation can reflect richer communicative engagement.",
        "higher often better",
        "Session length and examiner style can strongly affect this count.",
    ),
    "mlu": FeatureDoc(
        "MLU in morphemes",
        "Complexity",
        "Mean morphemes per child utterance",
        "Classic child-language marker for grammatical development.",
        "higher often better",
        "Language-specific morphology and transcript quality matter.",
    ),
    "mluw": FeatureDoc(
        "MLU in words",
        "Complexity",
        "Mean words per child utterance",
        "Simpler length marker that remains useful when morphology is noisy.",
        "higher often better",
        "Can be inflated by repeated phrases or examiner prompting.",
    ),
    "ttr": FeatureDoc(
        "Type-token ratio",
        "Lexical diversity",
        "Unique words divided by total words",
        "Approximates vocabulary diversity in the transcript.",
        "higher often better",
        "Sensitive to transcript length; compare similar session lengths.",
    ),
    "total_words": FeatureDoc(
        "Total child words",
        "Productivity",
        "Non-punctuation child word token count",
        "Proxy for expressive language production during the session.",
        "higher often better",
        "Depends on recording duration and conversational context.",
    ),
    "unintelligible_count": FeatureDoc(
        "Unintelligible utterances",
        "ASD-relevant markers",
        "Count of utterances with xxx/yyy markers",
        "Flags speech/transcript portions that could not be understood.",
        "lower often better",
        "ASR may under-detect unintelligible speech unless human reviewed.",
    ),
    "unintelligible_ratio": FeatureDoc(
        "Unintelligible ratio",
        "ASD-relevant markers",
        "unintelligible_count / total_utterances",
        "Normalizes intelligibility issues by session size.",
        "lower often better",
        "Use with audio quality and transcript confidence.",
    ),
    "zero_vocalization_count": FeatureDoc(
        "Zero vocalizations",
        "ASD-relevant markers",
        "Count of child tiers coded as 0 .",
        "Captures moments with no spoken response in CHAT annotation.",
        "lower often better",
        "May reflect task demands rather than child ability.",
    ),
    "nonverbal_vocalization_count": FeatureDoc(
        "Non-verbal vocalizations",
        "ASD-relevant markers",
        "Count of &= markers such as &=laugh",
        "Captures vocal behavior that is not lexical speech.",
        "context-dependent",
        "Some non-verbal vocalizations are social and positive.",
    ),
    "question_ratio": FeatureDoc(
        "Question ratio",
        "Pragmatic",
        "Child question utterances / total_utterances",
        "Approximates social initiation and pragmatic language.",
        "higher often better",
        "Depends on the interaction task and examiner prompting.",
    ),
    "echolalia_count": FeatureDoc(
        "Echolalia count",
        "ASD-relevant markers",
        "Recent verbatim repetition count",
        "Captures repetition patterns discussed in ASD language literature.",
        "higher can be marker",
        "Rule-based detection needs human transcript review for clinical use.",
    ),
    "echolalia_ratio": FeatureDoc(
        "Echolalia ratio",
        "ASD-relevant markers",
        "echolalia_count / total_utterances",
        "Normalizes repetition markers across session lengths.",
        "higher can be marker",
        "Short transcripts can make the ratio unstable.",
    ),
}


def feature_schema_rows() -> list[dict[str, str]]:
    """Return feature metadata as JSON/CSV-friendly dictionaries."""
    rows = []
    for feature in FEATURES:
        doc = FEATURE_DOCS[feature]
        rows.append({
            "feature": feature,
            "title": doc.title,
            "group": doc.group,
            "formula": doc.formula,
            "clinical_meaning": doc.clinical_meaning,
            "direction": doc.direction,
            "caveat": doc.caveat,
        })
    return rows
