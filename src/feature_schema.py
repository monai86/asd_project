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
    "pronoun_reversal_count",
]

OPTIONAL_INDICATORS: list[str] = [
    "pause_count",
    "pause_ratio",
    "therapist_utterances",
    "caregiver_utterances",
    "turn_taking_count",
    "response_latency_avg",
    "restricted_interest_words",
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
    "pronoun_reversal_count",
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
    "pronoun_reversal_count": FeatureDoc(
        "Pronoun reversal count",
        "ASD-relevant markers",
        "Conservative count of obvious I/you, me/you, or my/your reversals",
        "Flags a pragmatic-language pattern discussed in ASD language review.",
        "higher can be marker",
        "Heuristic only; many pronoun uses are context-dependent and need human review.",
    ),
}

OPTIONAL_INDICATOR_DOCS: dict[str, FeatureDoc] = {
    "pause_count": FeatureDoc(
        "Long pause count",
        "Interaction context",
        "Count of gaps longer than the configured pause threshold",
        "Adds context about conversational flow and response timing.",
        "context-dependent",
        "Requires reliable timestamps and task context.",
    ),
    "pause_ratio": FeatureDoc(
        "Long pause ratio",
        "Interaction context",
        "pause_count / total_utterances",
        "Normalizes long pauses by child utterance count.",
        "context-dependent",
        "Can reflect task structure or recording artifacts.",
    ),
    "therapist_utterances": FeatureDoc(
        "Therapist utterances",
        "Interaction context",
        "Count of therapist or investigator utterances",
        "Helps interpret child language values relative to adult prompting.",
        "context-dependent",
        "Not an ASD marker by itself.",
    ),
    "caregiver_utterances": FeatureDoc(
        "Caregiver utterances",
        "Interaction context",
        "Count of parent or caregiver utterances",
        "Helps interpret parent-child interaction balance.",
        "context-dependent",
        "Depends on the session activity.",
    ),
    "turn_taking_count": FeatureDoc(
        "Turn-taking transitions",
        "Interaction context",
        "Count of adjacent speaker-label changes",
        "Adds descriptive context about reciprocal interaction.",
        "higher often better",
        "Requires correct speaker diarization and transcript review.",
    ),
    "response_latency_avg": FeatureDoc(
        "Average response latency",
        "Interaction context",
        "Mean gap between adjacent utterance end/start timestamps",
        "Adds descriptive timing context for conversational response.",
        "context-dependent",
        "Requires reliable timestamps; do not compare across unlike tasks.",
    ),
    "restricted_interest_words": FeatureDoc(
        "Restricted-interest word count",
        "Optional language marker",
        "Count of words from a reviewable restricted-interest lexicon",
        "Flags possible topic clustering for therapist review.",
        "context-dependent",
        "Optional indicator only; not part of the core 14-feature schema.",
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


def optional_indicator_rows() -> list[dict[str, str]]:
    """Return optional indicator metadata without changing the core schema."""
    rows = []
    for feature in OPTIONAL_INDICATORS:
        doc = OPTIONAL_INDICATOR_DOCS[feature]
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
