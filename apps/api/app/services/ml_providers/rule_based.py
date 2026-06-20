from __future__ import annotations

from app.schemas.clinical import FeatureSet, ReviewCue
from app.services.ml_providers.base import (
    BaseMLProvider,
    MLProviderAvailability,
    MLProviderContext,
    MLProviderResult,
)


DEFAULT_CONFIG = {
    "minimum_child_utterances": 3,
    "unintelligible_ratio_caution": 0.20,
}


class RuleBasedReviewCueProvider(BaseMLProvider):
    provider_id = "rule_based_review_cue"
    provider_name = "RuleBasedReviewCueProvider"
    provider_version = "0.9.1"

    def check_availability(self) -> MLProviderAvailability:
        return MLProviderAvailability(True)

    def get_model_metadata(self) -> dict:
        return {
            "provider_type": "transparent_rule_based",
            "training_required": False,
            "default_config": DEFAULT_CONFIG,
            "threshold_type": "engineering_review_threshold",
            "not_clinical_norms": True,
        }

    def predict(
        self,
        features: FeatureSet,
        context: MLProviderContext,
        config: dict | None = None,
    ) -> MLProviderResult:
        del context
        cfg = {**DEFAULT_CONFIG, **(config or {})}
        values = {item.name: item.value for item in features.features}
        if features.insufficient_data or int(values.get("child_utterance_count") or 0) < cfg["minimum_child_utterances"]:
            return MLProviderResult(
                status="insufficient_data",
                cues=[ReviewCue(
                    cue_code="insufficient_sample_size",
                    severity="caution",
                    title="Language sample is too small for pattern review",
                    explanation="The reviewed sample contains too few child utterances for additional feature-based pattern cues.",
                    supporting_features={"child_utterance_count": values.get("child_utterance_count")},
                    limitations=["No other pattern cues were generated from this limited sample."],
                    recommended_next_review_step="Collect and review a longer representative language sample.",
                )],
                limitations=["Insufficient sample size prevents reliable pattern review."],
            )

        cues: list[ReviewCue] = []
        child = int(values.get("child_utterance_count") or 0)
        adult = int(values.get("adult_utterance_count") or 0)
        if adult > child:
            cues.append(_cue(
                "adult_dominant_sample", "info", "Adult-dominant language sample",
                "Adult utterances outnumber child utterances in this sample.",
                {"adult_utterance_count": adult, "child_utterance_count": child},
                "Review whether the activity provided enough opportunities for child language.",
            ))
        unclear = values.get("unintelligible_ratio")
        if isinstance(unclear, (int, float)) and unclear > cfg["unintelligible_ratio_caution"]:
            cues.append(_cue(
                "high_unclear_ratio", "caution", "High unclear-speech ratio",
                "The engineering review threshold for unclear or unintelligible utterances was exceeded.",
                {"unintelligible_ratio": unclear},
                "Recheck unclear segments against the recording before interpretation.",
            ))
        for name, code, title, step in (
            ("repetition_marker_count", "high_repetition_cue", "Repetition markers require review", "Review repeated language in transcript context."),
            ("echolalia_cue_count", "echolalia_review_cue", "Possible echoed-language cue", "Verify each possible echo directly in the reviewed transcript."),
            ("pronoun_reversal_cue_count", "pronoun_reversal_review_cue", "Possible pronoun-use cue", "Verify each pronoun-use cue directly in context."),
        ):
            value = values.get(name)
            if isinstance(value, (int, float)) and value > 0:
                cues.append(_cue(code, "review", title, "A transparent transcript heuristic produced one or more review cues.", {name: value}, step))
        return MLProviderResult(
            status="completed",
            cues=cues,
            limitations=[
                "Engineering review thresholds are not clinical norms.",
                "Feature-based review cues require therapist interpretation and are not diagnostic.",
            ],
        )


def _cue(code: str, severity: str, title: str, explanation: str, features: dict, step: str) -> ReviewCue:
    return ReviewCue(
        cue_code=code,
        severity=severity,
        title=title,
        explanation=explanation,
        supporting_features=features,
        limitations=["This heuristic may miss relevant context or flag non-clinical patterns."],
        recommended_next_review_step=step,
    )
