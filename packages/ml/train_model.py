"""Build CHA feature datasets and train baseline reference cohort classifiers."""

from __future__ import annotations

import argparse
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
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import calibration_curve

from packages.features.transcript_features import extract_transcript_features
from src.feature_schema import FEATURES, UNCERTAIN_HIGH, UNCERTAIN_LOW
from src.chat_feature_extractor import extract_chat_features


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
MODEL_DIR = PROJECT_ROOT / "models"
REPORT_DIR = PROJECT_ROOT / "reports" / "metrics"
RANDOM_STATE = 42
MODEL_VERSION = "reference-cohort-similarity-v1"
REQUIRED_METADATA_COLUMNS = {"file_id", "label", "age", "sex", "language", "notes"}
DEFAULT_CURATED_TRANSCRIPT_DIR = PROJECT_ROOT / "data" / "curated" / "english_child_transcripts"
FOLDER_LABEL_ALIASES = {
    "ASD": "ASD",
    "AUTISM": "ASD",
    "TD": "TD",
    "TYP": "TD",
    "CONTROL": "TD",
    "DD": "DD",
    "DELAY": "DD",
    "SLI": "STI",
    "STI": "STI",
    "DLD": "STI",
    "LT": "LT",
    "HL": "HL",
    # QuigleyMcNally-specific convention already used elsewhere in the repo.
    "HR": "ASD",
    "LR": "TD",
}


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


def build_dataset_from_labeled_folders(
    root_dir: str | Path = DEFAULT_CURATED_TRANSCRIPT_DIR,
    *,
    output_path: str | Path | None = None,
    label_aliases: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Extract features from .cha files under folders named by clinical group.

    The expected layout is flexible, for example:
    ``Corpus/download_2026-06-01/TD/file.cha`` or ``Corpus/ASD/file.cha``.
    The nearest label-like parent folder supplies the group label. For
    longitudinal child folders under a label folder, the child folder is used
    as the group key so sessions from the same child stay together in CV.
    """
    root = Path(root_dir)
    aliases = {**FOLDER_LABEL_ALIASES, **(label_aliases or {})}
    rows: list[dict[str, Any]] = []
    for cha_path in sorted(root.rglob("*.cha")):
        inferred = _infer_labeled_folder_record(cha_path, root, aliases)
        if inferred is None:
            continue
        label, corpus, group_key = inferred
        try:
            header_features = extract_chat_features(cha_path)
            extracted = extract_transcript_features(
                cha_path,
                age_months=header_features.get("age_months") if header_features else None,
            )
        except Exception as exc:  # noqa: BLE001
            rows.append({
                "file_id": cha_path.stem,
                "source_path": _relative_path(cha_path),
                "corpus": corpus,
                "group": label,
                "label": label,
                "participant_id": group_key,
                "error": str(exc),
            })
            continue
        if header_features is None:
            rows.append({
                "file_id": cha_path.stem,
                "source_path": _relative_path(cha_path),
                "corpus": corpus,
                "group": label,
                "label": label,
                "participant_id": group_key,
                "error": "no_child_utterances_or_unreadable_chat",
            })
            continue

        canonical_features = {
            key: header_features.get(key, extracted["canonical_features"].get(key, 0))
            for key in FEATURES
        }

        rows.append({
            "file_id": f"{corpus}:{cha_path.stem}",
            "participant_id": group_key,
            "source_path": _relative_path(cha_path),
            "corpus": corpus,
            "group": label,
            "label": label,
            "sex": header_features.get("sex") or "",
            "language": "eng",
            "notes": "Built from labeled CHAT folder structure.",
            **canonical_features,
            **extracted["optional_indicators"],
        })

    df = pd.DataFrame(rows)
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
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


def _bootstrap_confidence_intervals(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None,
    classes: np.ndarray,
    *,
    n_bootstrap: int = 1000,
    seed: int = RANDOM_STATE,
) -> dict[str, dict[str, float]]:
    rng = np.random.RandomState(seed)
    
    metrics_list: dict[str, list[float]] = {
        "accuracy": [],
        "f1_macro": [],
        "sensitivity_macro": [],
        "specificity_macro": [],
        "auc": [],
    }
    
    n_samples = len(y_true)
    for _ in range(n_bootstrap):
        boot_idx = rng.choice(n_samples, size=n_samples, replace=True)
        y_true_b = y_true[boot_idx]
        y_pred_b = y_pred[boot_idx]
        y_proba_b = y_proba[boot_idx] if y_proba is not None else None
        
        metrics_list["accuracy"].append(float(accuracy_score(y_true_b, y_pred_b)))
        metrics_list["f1_macro"].append(float(f1_score(y_true_b, y_pred_b, average="macro", zero_division=0)))
        metrics_list["sensitivity_macro"].append(float(recall_score(y_true_b, y_pred_b, average="macro", zero_division=0)))
        metrics_list["specificity_macro"].append(float(_macro_specificity(y_true_b, y_pred_b, classes)))
        
        if y_proba_b is not None and len(classes) == 2:
            try:
                if len(np.unique(y_true_b)) == 2:
                    positive_index = 1
                    auc_val = float(roc_auc_score(y_true_b == classes[positive_index], y_proba_b[:, positive_index]))
                    metrics_list["auc"].append(auc_val)
            except Exception:  # noqa: BLE001
                pass
                
    cis = {}
    for metric, vals in metrics_list.items():
        if not vals:
            cis[metric] = {"lower": 0.0, "upper": 0.0, "mean": 0.0}
            continue
        vals_sorted = np.sort(vals)
        lower = float(np.percentile(vals_sorted, 2.5))
        upper = float(np.percentile(vals_sorted, 97.5))
        mean_val = float(np.mean(vals_sorted))
        cis[metric] = {
            "lower": round(lower, 4),
            "upper": round(upper, 4),
            "mean": round(mean_val, 4),
        }
    return cis


def train_reference_cohort_models(
    df: pd.DataFrame,
    *,
    artifact_dir: str | Path = ARTIFACT_DIR,
    model_dir: str | Path = MODEL_DIR,
    report_dir: str | Path = REPORT_DIR,
    output_dir: str | Path | None = None,
    model_allowlist: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Train reference cohort models with group-based cross-validation and save artifacts."""
    if output_dir:
        output_path = Path(output_dir)
        artifact_dir = output_path / "artifacts"
        model_dir = output_path / "models"
        report_dir = output_path / "reports" / "metrics"
    else:
        artifact_dir = Path(artifact_dir)
        model_dir = Path(model_dir)
        report_dir = Path(report_dir)

    validation = validate_training_dataset(df)
    if not validation.ok:
        raise ValueError(f"Training dataset failed validation: {validation.errors}")

    working = df.dropna(subset=["label" if "label" in df.columns else "group"]).copy()
    label_col = "label" if "label" in working.columns else "group"
    working[label_col] = working[label_col].map(_normalize_label)
    X = working[FEATURES]
    y = working[label_col].astype(str)

    group_col = "participant_id" if "participant_id" in working.columns else "child_id" if "child_id" in working.columns else None
    if group_col:
        groups = working[group_col].fillna("unknown_group_" + pd.Series(range(len(working))).astype(str))
    else:
        groups = pd.Series(range(len(working)))

    all_models = _build_candidate_models()
    if model_allowlist:
        models = {k: v for k, v in all_models.items() if k in model_allowlist}
        if not models:
            raise ValueError(f"No models from allowlist {model_allowlist} are available.")
    else:
        models = all_models

    n_splits = 5
    if group_col:
        unique_groups = groups.nunique()
        if unique_groups < n_splits:
            n_splits = max(2, unique_groups)

    gkf = GroupKFold(n_splits=n_splits)
    classes = np.array(sorted(y.unique()))

    cv_results = []
    oof_predictions = {}
    oof_probabilities = {}

    from sklearn.base import clone

    for name, model in models.items():
        oof_pred = np.empty(len(working), dtype=object)
        oof_proba = np.zeros((len(working), len(classes)))

        for train_idx, val_idx in gkf.split(X, y, groups=groups):
            X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
            X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]

            fold_model = clone(model)
            fold_model.fit(X_train, y_train)

            oof_pred[val_idx] = fold_model.predict(X_val)
            if hasattr(fold_model, "predict_proba"):
                oof_proba[val_idx] = fold_model.predict_proba(X_val)
            else:
                pred_labels = fold_model.predict(X_val)
                dummy_proba = np.zeros((len(X_val), len(classes)))
                for idx_val, label in enumerate(pred_labels):
                    class_idx = np.where(classes == label)[0][0]
                    dummy_proba[idx_val, class_idx] = 1.0
                oof_proba[val_idx] = dummy_proba

        oof_predictions[name] = oof_pred
        oof_probabilities[name] = oof_proba

        proba_to_pass = oof_proba if len(classes) == 2 else None
        cv_results.append(_metric_row(name, y.to_numpy(), oof_pred, proba_to_pass, classes))

    metrics = pd.DataFrame(cv_results).sort_values(["f1_macro", "accuracy"], ascending=False)
    selected_name = _select_runtime_model(metrics)
    selected_model = clone(models[selected_name])
    selected_model.fit(X, y)

    selected_oof_pred = oof_predictions[selected_name]
    selected_oof_proba = oof_probabilities[selected_name]

    # Compute bootstrap confidence intervals for the selected model
    proba_for_ci = selected_oof_proba if len(classes) == 2 else None
    cis = _bootstrap_confidence_intervals(y.to_numpy(), selected_oof_pred, proba_for_ci, classes)

    # Compute calibration curve for the selected model
    calibration_report = {}
    for idx, cls in enumerate(classes):
        y_true_binary = (y.to_numpy() == cls)
        y_proba_cls = selected_oof_proba[:, idx]
        prob_true, prob_pred = calibration_curve(y_true_binary, y_proba_cls, n_bins=5, strategy="uniform")
        calibration_report[str(cls)] = {
            "true_probabilities": prob_true.tolist(),
            "predicted_probabilities": prob_pred.tolist(),
        }

    # Generate Dataset Card demographic summary and warnings
    demographics: dict[str, Any] = {
        "total_samples": int(len(working)),
        "total_participants": int(groups.nunique()),
        "class_distribution": working[label_col].value_counts().to_dict(),
    }
    if "sex" in working.columns:
        demographics["sex_distribution"] = working["sex"].fillna("Unknown").value_counts().to_dict()
    if "age_months" in working.columns:
        valid_ages = working["age_months"].dropna()
        if not valid_ages.empty:
            demographics["age_months_summary"] = {
                "mean": round(float(valid_ages.mean()), 2),
                "std": round(float(valid_ages.std()), 2) if len(valid_ages) > 1 else 0.0,
                "min": round(float(valid_ages.min()), 2),
                "max": round(float(valid_ages.max()), 2),
            }
    if "language" in working.columns:
        demographics["language_distribution"] = working["language"].fillna("Unknown").value_counts().to_dict()
    if "corpus" in working.columns:
        demographics["corpus_distribution"] = working["corpus"].fillna("Unknown").value_counts().to_dict()

    warnings = []
    if len(working) < 100:
        warnings.append({
            "code": "SMALL_SAMPLE_SIZE",
            "message": f"Training dataset is relatively small ({len(working)} samples), which may lead to overfitting."
        })
    class_counts = working[label_col].value_counts()
    if len(class_counts) >= 2:
        min_count = class_counts.min()
        max_count = class_counts.max()
        if min_count / max_count < 0.3:
            warnings.append({
                "code": "CLASS_IMBALANCE",
                "message": f"Significant class imbalance detected (smallest class {min_count} vs largest class {max_count})."
            })
    if "age_months" in working.columns:
        valid_ages = working["age_months"].dropna()
        if not valid_ages.empty:
            if valid_ages.min() < 18 or valid_ages.max() > 96:
                warnings.append({
                    "code": "EXTREME_AGE_RANGE",
                    "message": f"Dataset contains ages outside typical screening range (min: {valid_ages.min()}, max: {valid_ages.max()} months)."
                })
    if "sex" in working.columns and working["sex"].isna().any():
        warnings.append({
            "code": "MISSING_SEX_METADATA",
            "message": "Some records are missing sex metadata."
        })
    if "corpus" in working.columns and working["corpus"].nunique() <= 1:
        warnings.append({
            "code": "SINGLE_CORPUS_BIAS",
            "message": "Dataset is sourced from a single corpus, potentially limiting generalizability."
        })

    dataset_card = {
        "demographics": demographics,
        "clinical_warnings": warnings,
    }

    if dry_run:
        return {
            "selected_model": selected_name,
            "dry_run": True,
            "metrics": metrics.to_dict(orient="records"),
            "bootstrap_confidence_intervals": cis,
            "calibration_report": calibration_report,
            "dataset_card": dataset_card,
        }

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
    
    calibration_file = report_path / "calibration_report.json"
    calibration_file.write_text(json.dumps(calibration_report, ensure_ascii=False, indent=2), encoding="utf-8")
    
    dataset_card_file = artifact_path / "dataset_card.json"
    dataset_card_file.write_text(json.dumps(dataset_card, ensure_ascii=False, indent=2), encoding="utf-8")

    card_data = _model_card(bundle, metrics)
    card_data["evaluation_metrics_confidence_intervals"] = cis
    model_card_file = artifact_path / "model_card.json"
    model_card_file.write_text(
        json.dumps(card_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "selected_model": selected_name,
        "runtime_artifact": str(runtime_file),
        "compatibility_export": str(compatibility_file),
        "metrics_path": str(metrics_file),
        "metrics": metrics.to_dict(orient="records"),
        "bootstrap_confidence_intervals": cis,
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
    if raw in {"SLI", "DLD"}:
        return "STI"
    return raw


def _infer_labeled_folder_record(
    cha_path: Path,
    root: Path,
    aliases: dict[str, str],
) -> tuple[str, str, str] | None:
    try:
        rel = cha_path.relative_to(root)
    except ValueError:
        rel = cha_path
    parts = rel.parts
    label_index = None
    label = None
    for index, part in enumerate(parts[:-1]):
        normalized = aliases.get(part.upper())
        if normalized:
            label_index = index
            label = normalized
    if label_index is None or label is None:
        return None

    corpus = parts[0] if parts else "unknown"
    parent_after_label = parts[label_index + 1:-1]
    if parent_after_label:
        group_key = f"{corpus}:{label}:{'/'.join(parent_after_label)}"
    else:
        group_key = f"{corpus}:{label}:{cha_path.stem}"
    return label, corpus, group_key


def _relative_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train reference cohort ML models.")
    parser.add_argument("--dataset-dir", "--dataset-folder", type=str, default=None, help="Path to folder containing dataset CHA files.")
    parser.add_argument("--metadata-csv", type=str, default=None, help="Path to metadata CSV file.")
    parser.add_argument("--labeled-cha-root", type=str, default=None, help="Path to a recursive CHA directory with group labels in folder names.")
    parser.add_argument("--features-csv", type=str, default=None, help="Write/read the extracted feature table at this path.")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for artifacts.")
    parser.add_argument("--seed", type=int, default=RANDOM_STATE, help="Random seed for reproducibility.")
    parser.add_argument("--model-allowlist", nargs="+", default=None, help="List of allowed model names.")
    parser.add_argument("--dry-run", action="store_true", help="Perform validation and cross-validation, but do not write output files.")
    return parser


def main() -> None:
    parser = get_parser()
    args = parser.parse_args()

    global RANDOM_STATE
    RANDOM_STATE = args.seed

    if args.labeled_cha_root:
        df = build_dataset_from_labeled_folders(
            args.labeled_cha_root,
            output_path=args.features_csv,
        )
    elif args.features_csv:
        df = load_curated_corpus_features(args.features_csv)
    elif args.dataset_dir:
        df = build_dataset_from_metadata(
            dataset_dir=args.dataset_dir,
            metadata_path=args.metadata_csv,
        )
    else:
        df = load_curated_corpus_features()

    result = train_reference_cohort_models(
        df,
        output_dir=args.output_dir,
        model_allowlist=args.model_allowlist,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
