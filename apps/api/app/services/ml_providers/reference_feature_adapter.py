from __future__ import annotations

from dataclasses import dataclass

from app.schemas.clinical import FeatureSet


RUNTIME_TO_CANONICAL = {
    "child_utterance_count": "total_utterances",
    "total_word_count": "total_words",
    "type_token_ratio": "ttr",
    "mean_length_of_utterance_words": "mluw",
    "unintelligible_ratio": "unintelligible_ratio",
    "question_ratio": "question_ratio",
    "echolalia_cue_count": "echolalia_count",
    "pronoun_reversal_cue_count": "pronoun_reversal_count",
}


@dataclass(frozen=True)
class CanonicalRuntimeFeatures:
    values: dict[str, float | int]
    missing_required: list[str]
    schema_version: str


def adapt_runtime_features(
    features: FeatureSet,
    required_features: set[str] | None = None,
) -> CanonicalRuntimeFeatures:
    runtime_values = {item.name: item.value for item in features.features}
    canonical_values: dict[str, float | int] = {}
    for runtime_name, canonical_name in RUNTIME_TO_CANONICAL.items():
        value = runtime_values.get(runtime_name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        canonical_values[canonical_name] = value

    required = required_features or set(RUNTIME_TO_CANONICAL.values())
    return CanonicalRuntimeFeatures(
        values=canonical_values,
        missing_required=sorted(required - canonical_values.keys()),
        schema_version=features.schema_version,
    )
