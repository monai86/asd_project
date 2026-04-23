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

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIG_DIR = PROJECT_ROOT / "reports" / "figures"
METRIC_DIR = PROJECT_ROOT / "reports" / "metrics"
FIG_DIR.mkdir(parents=True, exist_ok=True)
METRIC_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="talk")

FEATURES = [
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
]

RANDOM_STATE = 42


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
        row = {"task": task, "model": name,
               "accuracy": round(acc, 4),
               "f1_macro": round(f1_macro, 4)}
        if task == "binary":
            y_proba = cross_val_predict(
                pipe, X, y, cv=skf, method="predict_proba", n_jobs=-1
            )[:, 1]
            probs[name] = y_proba
            row["roc_auc"] = round(roc_auc_score(y, y_proba), 4)
        rows.append(row)

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
    rows, _, probs = _cv_evaluate(
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
    y_m = multi_df["group"].values
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
    print("\n=== SUMMARY ===")
    print(results_df.to_string(index=False))


if __name__ == "__main__":
    main()
