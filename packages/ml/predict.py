"""Inference helpers for Reference Cohort Similarity."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from packages.features.transcript_features import extract_transcript_features, feature_aliases
from src.feature_schema import FEATURE_DOCS, FEATURES


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = PROJECT_ROOT / "artifacts" / "screening_model.joblib"
SAFETY_DISCLAIMER = (
    "AI output is for clinical decision support only and must be reviewed by a qualified clinician."
)


def predict_reference_cohort_similarity(
    transcript_or_features: str | Path | dict[str, Any],
    *,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    inference_status: str = "preliminary",
    age_months: int | float | None = None,
) -> dict[str, Any]:
    """Return model-assisted reference cohort similarity for therapist review."""
    bundle = load_model_bundle(model_path)
    if isinstance(transcript_or_features, dict):
        extracted = {
            "features": dict(transcript_or_features),
            "canonical_features": {
                key: transcript_or_features.get(key, 0)
                for key in bundle.get("features", FEATURES)
            },
            "feature_aliases": feature_aliases(transcript_or_features),
        }
    else:
        extracted = extract_transcript_features(transcript_or_features, age_months=age_months)

    feature_names = list(bundle.get("features") or FEATURES)
    feature_row = {
        feature: _safe_number(extracted["canonical_features"].get(feature, extracted["features"].get(feature, 0)))
        for feature in feature_names
    }
    model = bundle["model"]
    model_input = _model_input(model, feature_row, feature_names)
    probabilities = model.predict_proba(model_input)[0]
    raw_classes = list(getattr(model, "classes_", bundle.get("classes", [])))
    if not raw_classes:
        raw_classes = list(bundle.get("classes", []))
    classes = _class_labels(raw_classes)
    probability_map = {
        label: round(float(probability), 4)
        for label, probability in zip(classes, probabilities)
    }
    most_similar = max(probability_map, key=probability_map.get) if probability_map else "unknown"
    similarity_probability = probability_map.get(most_similar, 0.0)
    top_features = top_contributing_features(model, feature_row, feature_names, target_class=most_similar)
    warnings = quality_warnings(extracted["features"], inference_status=inference_status)

    return {
        "model_version": bundle.get("model_version", "unknown"),
        "model_type": bundle.get("model_type", type(model).__name__),
        "inference_status": inference_status,
        "reference_cohort_probabilities": probability_map,
        "most_similar_reference_cohort": most_similar,
        "similarity_probability": round(float(similarity_probability), 4),
        "top_contributing_features": top_features,
        "safety_warnings": warnings,
        "feature_schema": feature_names,
        "feature_aliases": extracted.get("feature_aliases", {}),
        "plain_language_explanation": (
            f"This transcript has feature patterns most similar to the {most_similar} "
            f"reference cohort with probability {similarity_probability:.0%}. "
            "This is a reference cohort similarity output, not a diagnosis."
        ),
        "safety_disclaimer": SAFETY_DISCLAIMER,
    }


def load_model_bundle(model_path: str | Path = DEFAULT_MODEL_PATH) -> dict[str, Any]:
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    loaded = joblib.load(path)
    if isinstance(loaded, dict) and "model" in loaded:
        return loaded
    return {
        "model": loaded,
        "features": FEATURES,
        "model_version": "legacy-model",
        "model_type": type(loaded).__name__,
    }


def top_contributing_features(
    model: Any,
    feature_row: dict[str, float],
    feature_names: list[str],
    *,
    target_class: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Return approximate feature contributions for review, not explanation proof."""
    classifier = getattr(model, "named_steps", {}).get("classifier") if hasattr(model, "named_steps") else None
    if classifier is None:
        classifier = getattr(model, "named_steps", {}).get("clf") if hasattr(model, "named_steps") else model
    coefs = getattr(classifier, "coef_", None)
    if coefs is None:
        importances = getattr(classifier, "feature_importances_", None)
        if importances is None:
            return []
        ranked = sorted(zip(feature_names, importances), key=lambda item: abs(float(item[1])), reverse=True)
        return [_feature_item(name, feature_row.get(name), float(value)) for name, value in ranked[:limit]]

    raw_classes = list(getattr(classifier, "classes_", []))
    classes = _class_labels(raw_classes)
    class_index = classes.index(target_class) if target_class in classes and np.ndim(coefs) > 1 else 0
    coef_row = coefs[class_index] if np.ndim(coefs) > 1 else coefs[0]
    contributions = [
        (feature, float(feature_row.get(feature, 0)) * float(coef))
        for feature, coef in zip(feature_names, coef_row)
    ]
    ranked = sorted(contributions, key=lambda item: abs(item[1]), reverse=True)
    return [_feature_item(name, feature_row.get(name), value) for name, value in ranked[:limit]]


def quality_warnings(features: dict[str, Any], *, inference_status: str) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    child_utterances = float(features.get("total_utterances") or features.get("child_utterance_count") or 0)
    child_words = float(features.get("total_words") or features.get("total_child_words") or 0)
    if inference_status == "preliminary":
        warnings.append({
            "code": "PRELIMINARY_TRANSCRIPT",
            "message": "Output is based on an unreviewed transcript and is not report-ready.",
        })
    if child_utterances < 5:
        warnings.append({
            "code": "SHORT_TRANSCRIPT",
            "message": "Fewer than 5 child utterances may make similarity output unstable.",
        })
    if child_words < 20:
        warnings.append({
            "code": "LOW_CHILD_WORD_COUNT",
            "message": "Low child word count limits linguistic feature reliability.",
        })
    return warnings


def _feature_item(feature: str, value: Any, contribution: float) -> dict[str, Any]:
    doc = FEATURE_DOCS.get(feature)
    return {
        "feature_key": feature,
        "display_name": doc.title if doc else feature.replace("_", " "),
        "value": value,
        "contribution": round(float(contribution), 4),
        "direction": "higher_similarity" if contribution >= 0 else "lower_similarity",
    }


def _model_input(model: Any, feature_row: dict[str, float], feature_names: list[str]) -> pd.DataFrame | np.ndarray:
    values = [[feature_row.get(feature, 0.0) for feature in feature_names]]
    first_step = None
    if hasattr(model, "steps") and getattr(model, "steps"):
        first_step = model.steps[0][1]
    if getattr(first_step or model, "feature_names_in_", None) is not None:
        return pd.DataFrame(values, columns=feature_names)
    return np.asarray(values, dtype=float)


def _safe_number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number != number:
        return 0.0
    return number


def _class_labels(classes: list[Any]) -> list[str]:
    labels = [str(label) for label in classes]
    if set(labels) == {"0", "1"}:
        return ["non-ASD" if label == "0" else "ASD" for label in labels]
    return labels
