"""Build CHA feature datasets and train baseline reference cohort classifiers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import shutil
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from packages.features.transcript_features import extract_transcript_features
from src.feature_schema import FEATURES, UNCERTAIN_HIGH, UNCERTAIN_LOW


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
MODEL_DIR = PROJECT_ROOT / "models"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
RANDOM_STATE = 42
MODEL_VERSION = "reference-cohort-similarity-v1"
REQUIRED_METADATA_COLUMNS = {"file_id", "label", "age", "sex", "language", "notes"}


@dataclass(frozen=True)
class DatasetValidation:
    ok: bool
    errors: list[str]
    warnings: list[str]


def build_dataset_from_metadata(
    dataset_dir: str | Path,
    metadata_path: str | Path | None = None,
    *,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Read CHA files and metadata.csv, then write a features table."""
    root = Path(dataset_dir)
    metadata_file = Path(metadata_path) if metadata_path else root / "metadata.csv"
    metadata = pd.read_csv(metadata_file)
    missing_columns = REQUIRED_METADATA_COLUMNS - set(metadata.columns)
    if missing_columns:
        raise ValueError(f"metadata.csv missing columns: {', '.join(sorted(missing_columns))}")

    rows: list[dict[str, Any]] = []
    for record in metadata.to_dict(orient="records"):
        file_id = str(record.get("file_id") or "").strip()
        if not file_id:
            continue
        cha_path = root / f"{file_id}.cha"
        if not cha_path.exists():
            cha_path = root / file_id
        if not cha_path.exists():
            rows.append({"file_id": file_id, "label": record.get("label"), "error": "missing_cha_file"})
            continue

        age_months = _coerce_age_months(record.get("age"))
        try:
            extracted = extract_transcript_features(cha_path, age_months=age_months)
        except Exception as exc:  # noqa: BLE001
            rows.append({"file_id": file_id, "label": record.get("label"), "error": str(exc)})
            continue

        rows.append({
            "file_id": file_id,
            "participant_id": record.get("participant_id") or file_id,
            "group": _normalize_label(record.get("label")),
            "label": _normalize_label(record.get("label")),
            "age_months": age_months,
            "sex": record.get("sex"),
            "language": record.get("language"),
            "notes": record.get("notes"),
            **extracted["canonical_features"],
            **extracted["optional_indicators"],
        })

    df = pd.DataFrame(rows)
    out = Path(output_path) if output_path else root / "features.csv"
    df.to_csv(out, index=False)
    return df


def load_curated_corpus_features(path: str | Path | None = None) -> pd.DataFrame:
    """Load the existing curated feature table used by the project."""
    csv_path = Path(path) if path else PROJECT_ROOT / "data" / "combined_features.csv"
    df = pd.read_csv(csv_path)
    if "label" not in df.columns and "group" in df.columns:
        df["label"] = df["group"]
    if "file_id" not in df.columns and "participant_id" in df.columns:
        df["file_id"] = df["participant_id"]
    return df


def validate_training_dataset(df: pd.DataFrame, *, min_per_class: int = 2) -> DatasetValidation:
    errors: list[str] = []
    warnings: list[str] = []
    label_col = "label" if "label" in df.columns else "group" if "group" in df.columns else None
    if label_col is None:
        errors.append("missing_label_column")
        return DatasetValidation(False, errors, warnings)

    missing_labels = int(df[label_col].isna().sum() + (df[label_col].astype(str).str.strip() == "").sum())
    if missing_labels:
        errors.append(f"missing_labels:{missing_labels}")

    for feature in FEATURES:
        if feature not in df.columns:
            errors.append(f"missing_feature:{feature}")

    labeled = df.dropna(subset=[label_col]).copy()
    labeled[label_col] = labeled[label_col].map(_normalize_label)
    counts = labeled[label_col].value_counts()
    if len(counts) < 2:
        errors.append("insufficient_classes")
    for label, count in counts.items():
        if count < min_per_class:
            errors.append(f"insufficient_samples:{label}:{count}")

    if "participant_id" not in df.columns and "child_id" not in df.columns:
        warnings.append("missing_group_key_for_group_based_split")

    return DatasetValidation(not errors, errors, warnings)


def train_reference_cohort_models(
    df: pd.DataFrame,
    *,
    artifact_dir: str | Path = ARTIFACT_DIR,
    model_dir: str | Path = MODEL_DIR,
    report_dir: str | Path = REPORT_DIR,
) -> dict[str, Any]:
    """Train baseline models and save the selected runtime artifact."""
    validation = validate_training_dataset(df)
    if not validation.ok:
        raise ValueError(f"Training dataset failed validation: {validation.errors}")

    working = df.dropna(subset=["label" if "label" in df.columns else "group"]).copy()
    label_col = "label" if "label" in working.columns else "group"
    working[label_col] = working[label_col].map(_normalize_label)
    X = working[FEATURES]
    y = working[label_col].astype(str)
    train_idx, test_idx = _split_indices(working, y)
    models = _build_candidate_models()

    rows = []
    fitted: dict[str, Pipeline] = {}
    for name, model in models.items():
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        fitted[name] = model
        pred = model.predict(X.iloc[test_idx])
        proba = model.predict_proba(X.iloc[test_idx]) if hasattr(model, "predict_proba") else None
        rows.append(_metric_row(name, y.iloc[test_idx].to_numpy(), pred, proba, model.classes_))

    metrics = pd.DataFrame(rows).sort_values(["f1_macro", "accuracy"], ascending=False)
    selected_name = _select_runtime_model(metrics)
    selected_model = fitted[selected_name]

    artifact_path = Path(artifact_dir)
    model_path = Path(model_dir)
    report_path = Path(report_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)
    model_path.mkdir(parents=True, exist_ok=True)
    report_path.mkdir(parents=True, exist_ok=True)

    bundle = {
        "model": selected_model,
        "model_version": MODEL_VERSION,
        "model_type": selected_name,
        "features": FEATURES,
        "classes": list(selected_model.classes_),
        "thresholds": {
            "uncertain_low": UNCERTAIN_LOW,
            "uncertain_high": UNCERTAIN_HIGH,
        },
        "training_metadata": {
            "trained_on": date.today().isoformat(),
            "n_rows": int(len(working)),
            "labels": working[label_col].value_counts().to_dict(),
            "validation_warnings": validation.warnings,
        },
        "output_semantics": "Reference Cohort Similarity; not diagnosis.",
    }
    runtime_file = artifact_path / "screening_model.joblib"
    compatibility_file = model_path / "transcript_classifier.pkl"
    joblib.dump(bundle, runtime_file)
    joblib.dump(bundle, compatibility_file)

    metrics_file = report_path / "reference_cohort_classification_results.csv"
    metrics.to_csv(metrics_file, index=False)
    model_card_file = artifact_path / "model_card.json"
    model_card_file.write_text(
        json.dumps(_model_card(bundle, metrics), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "selected_model": selected_name,
        "runtime_artifact": str(runtime_file),
        "compatibility_export": str(compatibility_file),
        "metrics_path": str(metrics_file),
        "metrics": metrics.to_dict(orient="records"),
    }


def _build_candidate_models() -> dict[str, Pipeline]:
    candidates: dict[str, Pipeline] = {
        "LogisticRegression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
        ]),
        "RandomForest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=RANDOM_STATE)),
        ]),
    }
    try:
        from xgboost import XGBClassifier  # type: ignore

        candidates["XGBoost"] = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", XGBClassifier(eval_metric="mlogloss", random_state=RANDOM_STATE)),
        ])
    except Exception:  # noqa: BLE001
        pass
    try:
        from lightgbm import LGBMClassifier  # type: ignore

        candidates["LightGBM"] = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", LGBMClassifier(random_state=RANDOM_STATE)),
        ])
    except Exception:  # noqa: BLE001
        pass
    return candidates


def _split_indices(df: pd.DataFrame, y: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    group_col = "participant_id" if "participant_id" in df.columns else "child_id" if "child_id" in df.columns else None
    indices = np.arange(len(df))
    if group_col and df[group_col].nunique() >= 4:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=RANDOM_STATE)
        return next(splitter.split(indices, y, groups=df[group_col]))
    return train_test_split(indices, test_size=0.25, random_state=RANDOM_STATE, stratify=y)


def _metric_row(name: str, y_true: np.ndarray, y_pred: np.ndarray, proba: np.ndarray | None, classes: np.ndarray) -> dict[str, Any]:
    row = {
        "model": name,
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred, average="macro")), 4),
        "sensitivity_macro": round(float(recall_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "specificity_macro": round(_macro_specificity(y_true, y_pred, classes), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=classes).tolist(),
    }
    if proba is not None and len(classes) == 2:
        positive_index = 1
        row["auc"] = round(float(roc_auc_score(y_true == classes[positive_index], proba[:, positive_index])), 4)
    else:
        row["auc"] = None
    return row


def _macro_specificity(y_true: np.ndarray, y_pred: np.ndarray, classes: np.ndarray) -> float:
    values = []
    for cls in classes:
        true_negative = int(((y_true != cls) & (y_pred != cls)).sum())
        false_positive = int(((y_true != cls) & (y_pred == cls)).sum())
        values.append(true_negative / (true_negative + false_positive) if true_negative + false_positive else 0.0)
    return float(np.mean(values)) if values else 0.0


def _select_runtime_model(metrics: pd.DataFrame) -> str:
    logreg = metrics[metrics["model"] == "LogisticRegression"]
    if logreg.empty:
        return str(metrics.iloc[0]["model"])
    best = metrics.iloc[0]
    logreg_row = logreg.iloc[0]
    if float(best["f1_macro"]) - float(logreg_row["f1_macro"]) <= 0.03:
        return "LogisticRegression"
    return str(best["model"])


def _model_card(bundle: dict[str, Any], metrics: pd.DataFrame) -> dict[str, Any]:
    return {
        "model_version": bundle["model_version"],
        "model_type": bundle["model_type"],
        "intended_use": "Reference Cohort Similarity for therapist review.",
        "not_intended_use": "Autonomous ASD diagnosis or clinical determination.",
        "inputs": FEATURES,
        "training_metadata": bundle["training_metadata"],
        "selection_policy": "Favor interpretable runtime model when benchmark performance is similar.",
        "metrics": metrics.to_dict(orient="records"),
    }


def _normalize_label(value: Any) -> str:
    if pd.isna(value):
        return ""
    raw = str(value or "").strip().upper()
    if raw in {"TYP", "NT", "CONTROL"}:
        return "TD"
    if raw in {"AUTISM"}:
        return "ASD"
    if raw in {"DELAY"}:
        return "DD"
    return raw


def _coerce_age_months(value: Any) -> float | None:
    if value is None or value == "":
        return None
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        pass
    if ";" in text:
        years, rest = text.split(";", 1)
        months_text = rest.split(".", 1)[0] or "0"
        return int(years) * 12 + int(months_text)
    return None


def main() -> None:
    df = load_curated_corpus_features()
    result = train_reference_cohort_models(df)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
