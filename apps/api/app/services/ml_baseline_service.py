from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from app.schemas.clinical import (
    BaselineEvaluationResult,
    DatasetBuildResult,
    FeatureTableRow,
    ModelCardResult,
)
from app.services.cha_service import parse_cha_metadata, parse_cha_utterances


FEATURE_NAMES = [
    "child_utterance_count",
    "total_word_count",
    "number_of_different_words",
    "type_token_ratio",
    "mean_length_of_utterance_words",
    "unintelligible_ratio",
    "unknown_speaker_ratio",
    "question_ratio",
    "repetition_marker_count",
]


def build_dataset(source_dir: str | Path = "data/demo", *, include_unlabeled: bool = True) -> DatasetBuildResult:
    root = Path(source_dir)
    rows: list[FeatureTableRow] = []
    warnings: list[str] = []
    if not root.exists():
        return DatasetBuildResult(rows=[], dataset_size=0, class_distribution={}, warnings=[f"Source directory not found: {root}"])
    for path in sorted(root.rglob("*.cha")):
        label = infer_label(path)
        if label is None and not include_unlabeled:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        headers = parse_cha_metadata(text)
        utterances = parse_cha_utterances(text)
        features = compute_dataset_features(utterances)
        metadata = parse_metadata(headers)
        missing = [key for key, value in metadata.items() if value is None]
        rows.append(
            FeatureTableRow(
                source_path=str(path),
                label=label,
                age_months=metadata["age_months"],
                sex=metadata["sex"],
                language=metadata["language"],
                missing_metadata=missing,
                features=features,
            )
        )
    class_distribution = dict(Counter(row.label or "unlabeled" for row in rows))
    if not rows:
        warnings.append("No CHA files found for dataset builder.")
    if any(row.label is None for row in rows):
        warnings.append("Some rows are unlabeled and cannot be used for supervised baseline metrics.")
    return DatasetBuildResult(rows=rows, dataset_size=len(rows), class_distribution=class_distribution, warnings=warnings)


def evaluate_baselines(source_dir: str | Path = "data/demo") -> BaselineEvaluationResult:
    dataset = build_dataset(source_dir, include_unlabeled=False)
    warnings = list(dataset.warnings)
    labeled_rows = [row for row in dataset.rows if row.label]
    labels = [row.label for row in labeled_rows if row.label]
    class_distribution = dict(Counter(labels))
    models: dict[str, dict] = {
        "Logistic Regression": {"status": "not_run"},
        "Random Forest": {"status": "not_run"},
    }
    if len(labeled_rows) < 4 or len(class_distribution) < 2:
        warnings.append("Insufficient labeled rows for train/test baseline evaluation.")
        for value in models.values():
            value.update({"status": "insufficient_data", "metrics": {}})
        return BaselineEvaluationResult(
            dataset_size=len(labeled_rows),
            class_distribution=class_distribution,
            models=models,
            warnings=warnings,
        )

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score
        from sklearn.model_selection import train_test_split
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"scikit-learn unavailable: {exc}")
        for value in models.values():
            value.update({"status": "dependency_unavailable", "metrics": {}})
        return BaselineEvaluationResult(dataset_size=len(labeled_rows), class_distribution=class_distribution, models=models, warnings=warnings)

    x = [[float(row.features[name]) for name in FEATURE_NAMES] for row in labeled_rows]
    y = labels
    stratify = y if min(class_distribution.values()) >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=42, stratify=stratify)
    estimators = {
        "Logistic Regression": LogisticRegression(max_iter=500),
        "Random Forest": RandomForestClassifier(n_estimators=50, random_state=42),
    }
    for name, estimator in estimators.items():
        estimator.fit(x_train, y_train)
        predictions = estimator.predict(x_test)
        metrics = {
            "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
            "confusion_matrix": confusion_matrix(y_test, predictions, labels=sorted(class_distribution)).tolist(),
            "labels": sorted(class_distribution),
        }
        if len(class_distribution) == 2 and hasattr(estimator, "predict_proba"):
            labels_sorted = sorted(class_distribution)
            binary_matrix = confusion_matrix(y_test, predictions, labels=labels_sorted)
            tn, fp, fn, tp = binary_matrix.ravel()
            metrics["sensitivity"] = round(float(tp / (tp + fn)), 4) if (tp + fn) else "unavailable"
            metrics["specificity"] = round(float(tn / (tn + fp)), 4) if (tn + fp) else "unavailable"
            try:
                probabilities = estimator.predict_proba(x_test)[:, 1]
                positive_label = labels_sorted[1]
                binary_y = [1 if item == positive_label else 0 for item in y_test]
                metrics["roc_auc"] = round(float(roc_auc_score(binary_y, probabilities)), 4)
            except Exception:
                metrics["roc_auc"] = "unavailable"
        models[name] = {"status": "completed", "metrics": metrics}
    return BaselineEvaluationResult(dataset_size=len(labeled_rows), class_distribution=class_distribution, models=models, warnings=warnings)


def build_model_card(path: str | Path = "artifacts/model_card_v2.md", source_dir: str | Path = "data/demo") -> ModelCardResult:
    dataset = build_dataset(source_dir)
    baseline = evaluate_baselines(source_dir)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_model_card(dataset, baseline), encoding="utf-8")
    return ModelCardResult(
        path=str(target),
        dataset_size=dataset.dataset_size,
        feature_list=FEATURE_NAMES,
        limitations=[
            "Not validated for Thai clinical diagnosis.",
            "Not a diagnostic tool.",
            "Requires therapist review.",
        ],
        class_distribution=dataset.class_distribution,
        metrics=baseline.models,
    )


def render_model_card(dataset: DatasetBuildResult, baseline: BaselineEvaluationResult) -> str:
    metrics_lines = []
    for model_name, payload in baseline.models.items():
        metrics_lines.append(f"- {model_name}: {payload.get('status')}")
        for metric_name, metric_value in payload.get("metrics", {}).items():
            metrics_lines.append(f"  - {metric_name}: {metric_value}")
    warnings = dataset.warnings + baseline.warnings
    warning_lines = [f"- {warning}" for warning in warnings] or ["- No automated warning generated."]
    class_lines = [f"- {label}: {count}" for label, count in dataset.class_distribution.items()] or ["- No rows"]
    return f"""# Model Card v2

## Intended Use

This baseline is for review support only. It may support review priority,
contributing feature explanation, cohort similarity, and research dashboard
summaries. It is not a diagnostic tool and is not validated for Thai clinical
diagnosis.

## Dataset Source

Local public CHAT/CHA research transcripts and demo feature tables when present.
No private clinical data should be included by default.

## Dataset Size

{dataset.dataset_size}

## Class Distribution

{chr(10).join(class_lines)}

## Feature List

{chr(10).join(f"- {name}" for name in FEATURE_NAMES)}

## Baseline Models

- Logistic Regression
- Random Forest

## Metrics

{chr(10).join(metrics_lines)}

## Dataset Warnings

{chr(10).join(warning_lines)}

## Limitations

- Public research corpora do not establish clinical validity for local practice.
- Small or imbalanced cohorts require caution and confidence intervals.
- Subgroup reports should warn when age, sex, or language cells are too small.
- Review cues are not diagnostic markers.

## Out-of-Scope Use

Automated diagnosis, unsupervised clinical triage, or labeling a child as normal
or abnormal.
"""


def compute_dataset_features(utterances) -> dict[str, float | int]:
    child = [utterance for utterance in utterances if str(utterance.speaker).upper() == "CHI"]
    tokens = [token for utterance in child for token in tokenize(utterance.text)]
    total = len(utterances) or 1
    child_total = len(child) or 1
    return {
        "child_utterance_count": len(child),
        "total_word_count": len(tokens),
        "number_of_different_words": len(set(tokens)),
        "type_token_ratio": round(len(set(tokens)) / len(tokens), 4) if tokens else 0.0,
        "mean_length_of_utterance_words": round(len(tokens) / len(child), 4) if child else 0.0,
        "unintelligible_ratio": round(sum(1 for utterance in utterances if utterance.unintelligible) / total, 4),
        "unknown_speaker_ratio": round(sum(1 for utterance in utterances if str(utterance.speaker).upper() == "UNK") / total, 4),
        "question_ratio": round(sum(1 for utterance in child if is_question(utterance.text)) / child_total, 4) if child else 0.0,
        "repetition_marker_count": sum(repetition_marker_count(utterance.text) for utterance in child),
    }


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\w']+", text) if token.lower() not in {"xxx", "yyy", "www"}]


def is_question(text: str) -> bool:
    return "?" in str(text or "")


def repetition_marker_count(text: str) -> int:
    value = str(text or "")
    marker_count = len(re.findall(r"\[/+\]", value))
    tokens = tokenize(value)
    adjacent_repeats = sum(1 for index in range(1, len(tokens)) if tokens[index] == tokens[index - 1])
    return marker_count + adjacent_repeats


def infer_label(path: Path) -> str | None:
    parts = {part.upper() for part in path.parts}
    for label in ("ASD", "TD", "DD"):
        if label in parts:
            return label
    return None


def parse_metadata(headers: dict[str, list[str]]) -> dict[str, int | str | None]:
    language = None
    if headers.get("@Languages"):
        language = headers["@Languages"][0]
    age_months = None
    sex = None
    for value in headers.get("@ID", []):
        parts = [part.strip() for part in value.split("|")]
        if len(parts) > 3 and parts[3]:
            age_months = age_to_months(parts[3])
        if len(parts) > 4 and parts[4]:
            sex = parts[4]
    return {"age_months": age_months, "sex": sex, "language": language}


def age_to_months(value: str) -> int | None:
    match = re.match(r"(?P<years>\d{1,2});(?P<months>\d{1,2})", value)
    if not match:
        return None
    return int(match.group("years")) * 12 + int(match.group("months"))
