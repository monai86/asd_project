"""
Baseline classifiers for screening: ASD vs TD vs DD.

Two tasks are run:
    (A) Binary:       ASD  vs  non-ASD (TD + DD)   -> screening use-case
    (B) Multi-class:  ASD vs DD vs TD              -> differential

Models:
    - Logistic Regression
    - Random Forest
    - Support Vector Machine (RBF)

Evaluation: stratified 5-fold cross-validation.
Outputs:
    reports/metrics/classification_results.csv
    reports/figures/confusion_matrix_<task>_<model>.png
    reports/figures/feature_importance.png
    reports/figures/roc_curve_binary.png
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

try:
    from src.feature_schema import (
        FEATURES,
        UNCERTAIN_HIGH,
        UNCERTAIN_LOW,
        feature_schema_rows,
    )
except ModuleNotFoundError:  # running as `python src/classifier.py`
    from feature_schema import (
        FEATURES,
        UNCERTAIN_HIGH,
        UNCERTAIN_LOW,
        feature_schema_rows,
    )

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIG_DIR = PROJECT_ROOT / "reports" / "figures"
METRIC_DIR = PROJECT_ROOT / "reports" / "metrics"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
FIG_DIR.mkdir(parents=True, exist_ok=True)
METRIC_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")

RANDOM_STATE = 42
MODEL_VERSION = "v0.17.0-trust-dashboard"


def _build_models():
    return {
        "LogReg": Pipeline([
            ("imp", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000,
                                       class_weight="balanced",
                                       random_state=RANDOM_STATE)),
        ]),
        "RandomForest": Pipeline([
            ("imp", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced",
                random_state=RANDOM_STATE,
            )),
        ]),
        "SVM": Pipeline([
            ("imp", SimpleImputer(strategy="median")),
            ("sc", StandardScaler()),
            ("clf", SVC(kernel="rbf", probability=True,
                        class_weight="balanced",
                        random_state=RANDOM_STATE)),
        ]),
    }


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def _binary_metric_row(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    *,
    threshold: float,
) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    uncertain = (y_proba >= UNCERTAIN_LOW) & (y_proba < UNCERTAIN_HIGH)
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "f1_macro": f1_score(y_true, y_pred, average="macro"),
        "roc_auc": roc_auc_score(y_true, y_proba),
        "pr_auc": average_precision_score(y_true, y_proba),
        "sensitivity": recall_score(y_true, y_pred, pos_label=1, zero_division=0),
        "specificity": _safe_div(tn, tn + fp),
        "ppv": precision_score(y_true, y_pred, pos_label=1, zero_division=0),
        "npv": _safe_div(tn, tn + fn),
        "brier_score": brier_score_loss(y_true, y_proba),
        "threshold": threshold,
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "uncertain_count": int(uncertain.sum()),
        "uncertain_rate": float(uncertain.mean()),
    }


def _round_metric_row(row: dict) -> dict:
    rounded = {}
    for key, value in row.items():
        if isinstance(value, (float, np.floating)):
            rounded[key] = round(float(value), 4)
        else:
            rounded[key] = value
    return rounded


def _cv_evaluate(X, y, models, task: str, class_order, display_labels):
    """Run 5-fold CV for each model.

    class_order: labels as they appear in y (e.g. [0, 1] or ['ASD', 'DD', 'TD'])
    display_labels: human-readable names in the same order.
    """
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    rows = []
    preds = {}
    probs = {}
    for name, pipe in models.items():
        y_pred = cross_val_predict(pipe, X, y, cv=skf, n_jobs=-1)
        preds[name] = y_pred
        acc = accuracy_score(y, y_pred)
        f1_macro = f1_score(y, y_pred, average="macro")
        row = {"task": task, "model": name}
        if task == "binary":
            y_proba = cross_val_predict(
                pipe, X, y, cv=skf, method="predict_proba", n_jobs=-1
            )[:, 1]
            probs[name] = y_proba
            row.update(_binary_metric_row(
                np.asarray(y), np.asarray(y_pred), np.asarray(y_proba),
                threshold=0.5,
            ))
        else:
            row.update({
                "accuracy": acc,
                "f1_macro": f1_macro,
            })
        rows.append(_round_metric_row(row))

        cm = confusion_matrix(y, y_pred, labels=class_order)
        fig, ax = plt.subplots(figsize=(6, 5))
        ConfusionMatrixDisplay(cm, display_labels=display_labels).plot(
            ax=ax, cmap="Blues", values_format="d", colorbar=False,
        )
        ax.set_title(f"{task} | {name}\nacc={acc:.3f}  f1={f1_macro:.3f}")
        fig.tight_layout()
        out = FIG_DIR / f"confusion_matrix_{task}_{name}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  saved  {out.relative_to(PROJECT_ROOT)}")

        print(f"\n[{task} / {name}]")
        print(classification_report(y, y_pred, labels=class_order,
                                    target_names=display_labels, digits=3))
    return rows, preds, probs


def _plot_feature_importance(X, y):
    pipe = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("clf", RandomForestClassifier(n_estimators=500,
                                       class_weight="balanced",
                                       random_state=RANDOM_STATE)),
    ])
    pipe.fit(X, y)
    imp = pipe.named_steps["clf"].feature_importances_
    order = np.argsort(imp)[::-1]
    feats = np.array(FEATURES)[order]
    vals = imp[order]

    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(x=vals, y=feats, ax=ax, color="#4C72B0")
    ax.set_title("Random Forest feature importance (multi-class)")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    out = FIG_DIR / "feature_importance.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved  {out.relative_to(PROJECT_ROOT)}")


def _plot_roc_curves(X, y, probs):
    fig, ax = plt.subplots(figsize=(7, 6))
    for name, p in probs.items():
        RocCurveDisplay.from_predictions(y, p, name=name, ax=ax)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_title("ROC curves - ASD vs non-ASD (5-fold CV)")
    fig.tight_layout()
    out = FIG_DIR / "roc_curve_binary.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved  {out.relative_to(PROJECT_ROOT)}")


def _data_hash(df: pd.DataFrame) -> str:
    payload = df.sort_values(["corpus", "participant_id"]).to_csv(index=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _threshold_table(y_true: np.ndarray, y_proba: np.ndarray) -> pd.DataFrame:
    rows = []
    for threshold in np.round(np.arange(0.05, 0.96, 0.05), 2):
        y_pred = (y_proba >= threshold).astype(int)
        row = _binary_metric_row(y_true, y_pred, y_proba, threshold=float(threshold))
        rows.append(_round_metric_row(row))
    return pd.DataFrame(rows)


def _calibration_bins(y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    bins = np.linspace(0, 1, n_bins + 1)
    labels = [f"{bins[i]:.1f}-{bins[i + 1]:.1f}" for i in range(n_bins)]
    df = pd.DataFrame({"y_true": y_true, "prob_asd": y_proba})
    df["bin"] = pd.cut(df["prob_asd"], bins=bins, labels=labels,
                       include_lowest=True, right=True)
    rows = []
    for label, group in df.groupby("bin", observed=False):
        if group.empty:
            continue
        rows.append({
            "bin": str(label),
            "n": int(len(group)),
            "predicted_mean": round(float(group["prob_asd"].mean()), 4),
            "observed_rate": round(float(group["y_true"].mean()), 4),
        })
    return pd.DataFrame(rows)


def _decision_curve(y_true: np.ndarray, y_proba: np.ndarray) -> pd.DataFrame:
    n = len(y_true)
    prevalence = float(np.mean(y_true))
    rows = []
    for threshold in np.round(np.arange(0.05, 0.96, 0.05), 2):
        y_pred = y_proba >= threshold
        tp = int(((y_true == 1) & y_pred).sum())
        fp = int(((y_true == 0) & y_pred).sum())
        odds = threshold / (1 - threshold)
        rows.append({
            "threshold": float(threshold),
            "model_net_benefit": round(tp / n - fp / n * odds, 4),
            "treat_all_net_benefit": round(prevalence - (1 - prevalence) * odds, 4),
            "treat_none_net_benefit": 0.0,
        })
    return pd.DataFrame(rows)


def _subgroup_performance(df: pd.DataFrame, y_true: np.ndarray, y_proba: np.ndarray) -> pd.DataFrame:
    rows = []
    eval_df = df.copy()
    eval_df["y_true"] = y_true
    eval_df["prob_asd"] = y_proba
    eval_df["pred"] = (y_proba >= 0.5).astype(int)
    eval_df["age_band"] = pd.cut(
        eval_df["age_months"],
        bins=[0, 36, 48, 60, 72, 200],
        labels=["<36", "36-47", "48-59", "60-71", "72+"],
        include_lowest=True,
    ).astype(str)

    for dimension in ["corpus", "sex", "age_band"]:
        for value, sub in eval_df.groupby(dimension, dropna=False):
            if len(sub) < 5 or sub["y_true"].nunique() < 2:
                continue
            metrics = _binary_metric_row(
                sub["y_true"].to_numpy(),
                sub["pred"].to_numpy(),
                sub["prob_asd"].to_numpy(),
                threshold=0.5,
            )
            rows.append(_round_metric_row({
                "dimension": dimension,
                "value": str(value),
                "n": len(sub),
                **metrics,
            }))
    return pd.DataFrame(rows)


def _leave_one_corpus_out(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES].values
    y = (df["group"] == "ASD").astype(int).values
    groups = df["corpus"].values
    rows = []
    for train_idx, test_idx in LeaveOneGroupOut().split(X, y, groups):
        test_corpus = str(groups[test_idx][0])
        if len(np.unique(y[test_idx])) < 2:
            rows.append({
                "held_out_corpus": test_corpus,
                "n_test": int(len(test_idx)),
                "status": "skipped_single_class",
            })
            continue
        pipe = _build_models()["LogReg"]
        pipe.fit(X[train_idx], y[train_idx])
        proba = pipe.predict_proba(X[test_idx])[:, 1]
        pred = (proba >= 0.5).astype(int)
        rows.append(_round_metric_row({
            "held_out_corpus": test_corpus,
            "n_test": int(len(test_idx)),
            "status": "evaluated",
            **_binary_metric_row(y[test_idx], pred, proba, threshold=0.5),
        }))
    return pd.DataFrame(rows)


def _write_model_bundle(df: pd.DataFrame) -> dict:
    X = df[FEATURES].values
    y = (df["group"] == "ASD").astype(int).values
    model = _build_models()["LogReg"]
    model.fit(X, y)
    bundle = {
        "model": model,
        "model_version": MODEL_VERSION,
        "features": FEATURES,
        "thresholds": {
            "uncertain_low": UNCERTAIN_LOW,
            "uncertain_high": UNCERTAIN_HIGH,
            "default_binary": 0.5,
        },
        "training_metadata": {
            "trained_on": date.today().isoformat(),
            "n_rows": int(len(df)),
            "n_asd": int(y.sum()),
            "n_non_asd": int((1 - y).sum()),
            "corpora": sorted(df["corpus"].dropna().unique().tolist()),
            "data_hash": _data_hash(df),
        },
    }
    out = ARTIFACT_DIR / "screening_model.joblib"
    joblib.dump(bundle, out)
    print(f"  saved  {out.relative_to(PROJECT_ROOT)}")
    return bundle


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  saved  {path.relative_to(PROJECT_ROOT)}")


def main() -> None:
    csv_path = DATA_DIR / "combined_features.csv"
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["group"])
    print(f"Loaded {len(df)} rows. Group counts:")
    print(df["group"].value_counts().to_string())

    X = df[FEATURES].values

    all_rows = []

    # ---------------- Binary: ASD vs non-ASD ----------------
    print("\n" + "=" * 70)
    print("TASK A: Binary  ASD (1)  vs  non-ASD (0)")
    print("=" * 70)
    y_bin = (df["group"] == "ASD").astype(int).values
    rows, preds, probs = _cv_evaluate(
        X, y_bin, _build_models(),
        task="binary",
        class_order=[0, 1],
        display_labels=["non-ASD", "ASD"],
    )
    all_rows.extend(rows)
    if probs:
        _plot_roc_curves(X, y_bin, probs)

    # ---------------- Multi-class: ASD / DD / TD ----------------
    print("\n" + "=" * 70)
    print("TASK B: Multi-class  ASD vs DD vs TD")
    print("=" * 70)
    multi_df = df[df["group"].isin(["ASD", "DD", "TD"])]
    X_m = multi_df[FEATURES].values
    y_m = multi_df["group"].astype(str).to_numpy()
    rows, _, _ = _cv_evaluate(
        X_m, y_m, _build_models(),
        task="multiclass",
        class_order=["ASD", "DD", "TD"],
        display_labels=["ASD", "DD", "TD"],
    )
    all_rows.extend(rows)

    _plot_feature_importance(X_m, y_m)

    # Save results
    results_df = pd.DataFrame(all_rows)
    out = METRIC_DIR / "classification_results.csv"
    results_df.to_csv(out, index=False)
    print(f"\n[saved] {out.relative_to(PROJECT_ROOT)}")

    # Model Trust Dashboard inputs focus on LogReg, the selected interpretable
    # screening model. These CSVs are static assets for project_dashboard/.
    logreg_prob = probs.get("LogReg")
    logreg_pred = preds.get("LogReg")
    if logreg_prob is not None and logreg_pred is not None:
        pred_df = df[[
            "participant_id", "corpus", "group", "sex", "age_months",
        ]].copy()
        pred_df["y_true"] = y_bin
        pred_df["prob_asd"] = np.round(logreg_prob, 6)
        pred_df["pred_050"] = logreg_pred
        pred_df["uncertainty_zone"] = np.select(
            [
                logreg_prob < UNCERTAIN_LOW,
                (logreg_prob >= UNCERTAIN_LOW) & (logreg_prob < UNCERTAIN_HIGH),
                logreg_prob >= UNCERTAIN_HIGH,
            ],
            ["low", "uncertain", "high"],
            default="unknown",
        )
        pred_out = METRIC_DIR / "binary_oof_predictions.csv"
        pred_df.to_csv(pred_out, index=False)
        print(f"[saved] {pred_out.relative_to(PROJECT_ROOT)}")

        threshold_out = METRIC_DIR / "threshold_metrics.csv"
        _threshold_table(y_bin, logreg_prob).to_csv(threshold_out, index=False)
        print(f"[saved] {threshold_out.relative_to(PROJECT_ROOT)}")

        calibration_out = METRIC_DIR / "calibration_bins.csv"
        _calibration_bins(y_bin, logreg_prob).to_csv(calibration_out, index=False)
        print(f"[saved] {calibration_out.relative_to(PROJECT_ROOT)}")

        dca_out = METRIC_DIR / "decision_curve.csv"
        _decision_curve(y_bin, logreg_prob).to_csv(dca_out, index=False)
        print(f"[saved] {dca_out.relative_to(PROJECT_ROOT)}")

        subgroup_out = METRIC_DIR / "subgroup_performance.csv"
        _subgroup_performance(df, y_bin, logreg_prob).to_csv(subgroup_out, index=False)
        print(f"[saved] {subgroup_out.relative_to(PROJECT_ROOT)}")

    loco_out = METRIC_DIR / "leave_one_corpus_out.csv"
    _leave_one_corpus_out(df).to_csv(loco_out, index=False)
    print(f"[saved] {loco_out.relative_to(PROJECT_ROOT)}")

    feature_schema_out = ARTIFACT_DIR / "feature_schema.json"
    _write_json(feature_schema_out, {
        "features": FEATURES,
        "feature_docs": feature_schema_rows(),
        "thresholds": {
            "uncertain_low": UNCERTAIN_LOW,
            "uncertain_high": UNCERTAIN_HIGH,
        },
    })

    bundle = _write_model_bundle(df)
    model_card_out = ARTIFACT_DIR / "model_card.json"
    _write_json(model_card_out, {
        "model_version": MODEL_VERSION,
        "model_type": "Logistic Regression with median imputation and standard scaling",
        "intended_use": "ASD screening support and research demo; not diagnostic.",
        "not_intended_use": "Autonomous diagnosis, emergency triage, or replacement for clinician assessment.",
        "inputs": FEATURES,
        "training_metadata": bundle["training_metadata"],
        "thresholds": bundle["thresholds"],
        "reporting_guidance": [
            "TRIPOD+AI prediction model reporting",
            "DECIDE-AI early clinical decision-support evaluation",
            "Model card and dataset-card transparency",
        ],
        "clinical_caveats": [
            "TalkBank/ASDBank cohorts are not a Thai external validation set.",
            "Audio-derived predictions require transcript QA and feature-drift checks.",
            "Probability estimates require calibration review before clinical use.",
        ],
    })
    print("\n=== SUMMARY ===")
    print(results_df.to_string(index=False))


if __name__ == "__main__":
    main()
