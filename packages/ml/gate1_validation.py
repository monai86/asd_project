"""Research-only validation for the TD versus non-TD proxy task."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.feature_schema import FEATURES


@dataclass(frozen=True)
class SplitAudit:
    fold: int
    train_participants: tuple[str, ...]
    test_participants: tuple[str, ...]


@dataclass(frozen=True)
class PromotionGate:
    sensitivity_ci_lower: float
    specificity: float
    ece: float
    brier: float
    baseline_brier: float
    abstention_rate: float
    corpus_holdout_completed: bool
    feature_parity_passed: bool

    @property
    def failed_reasons(self) -> list[str]:
        checks = {
            "sensitivity_ci_lower": self.sensitivity_ci_lower >= 0.80,
            "specificity": self.specificity >= 0.60,
            "ece": self.ece <= 0.10,
            "brier": self.brier <= self.baseline_brier,
            "abstention_rate": self.abstention_rate <= 0.40,
            "corpus_holdout_completed": self.corpus_holdout_completed,
            "feature_parity_passed": self.feature_parity_passed,
        }
        return [name for name, passed in checks.items() if not passed]

    @property
    def passed(self) -> bool:
        return not self.failed_reasons


@dataclass
class Gate1Evaluation:
    metrics: dict[str, float | None]
    confidence_intervals: dict[str, dict[str, float]]
    split_audit: list[SplitAudit]
    corpus_holdout: list[dict[str, Any]]
    subgroup_reliability: list[dict[str, Any]]
    promotion_gate: PromotionGate
    predictions: pd.DataFrame

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": "td_vs_non_td_public_corpus_proxy",
            "metrics": self.metrics,
            "confidence_intervals": self.confidence_intervals,
            "split_audit": [asdict(item) for item in self.split_audit],
            "corpus_holdout": self.corpus_holdout,
            "subgroup_reliability": self.subgroup_reliability,
            "promotion_gate": {
                **asdict(self.promotion_gate),
                "passed": self.promotion_gate.passed,
                "failed_reasons": self.promotion_gate.failed_reasons,
            },
        }


def _pipeline(random_state: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=random_state,
                ),
            ),
        ]
    )


@dataclass
class _CalibratedModel:
    estimator: Pipeline
    calibrator: LogisticRegression | None

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        raw = self.estimator.predict_proba(features)[:, 1]
        if self.calibrator is None:
            return raw
        logits = _logit(raw).reshape(-1, 1)
        return self.calibrator.predict_proba(logits)[:, 1]


def _logit(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped))


def _fit_calibrated(
    features: pd.DataFrame,
    labels: np.ndarray,
    groups: np.ndarray,
    *,
    random_state: int,
) -> _CalibratedModel:
    for offset in range(20):
        splitter = GroupShuffleSplit(
            n_splits=1,
            test_size=0.20,
            random_state=random_state + offset,
        )
        fit_index, calibration_index = next(
            splitter.split(features, labels, groups)
        )
        if (
            len(np.unique(labels[fit_index])) < 2
            or len(np.unique(labels[calibration_index])) < 2
        ):
            continue
        estimator = _pipeline(random_state + offset)
        estimator.fit(features.iloc[fit_index], labels[fit_index])
        raw = estimator.predict_proba(features.iloc[calibration_index])[:, 1]
        calibrator = LogisticRegression(
            max_iter=1000,
            random_state=random_state + offset,
        )
        calibrator.fit(
            _logit(raw).reshape(-1, 1),
            labels[calibration_index],
        )
        return _CalibratedModel(estimator, calibrator)

    estimator = _pipeline(random_state)
    estimator.fit(features, labels)
    return _CalibratedModel(estimator, None)


def _specificity(labels: np.ndarray, predictions: np.ndarray) -> float:
    tn, fp, _, _ = confusion_matrix(
        labels,
        predictions,
        labels=[0, 1],
    ).ravel()
    return float(tn / (tn + fp)) if tn + fp else 0.0


def _sensitivity(labels: np.ndarray, predictions: np.ndarray) -> float:
    _, _, fn, tp = confusion_matrix(
        labels,
        predictions,
        labels=[0, 1],
    ).ravel()
    return float(tp / (tp + fn)) if tp + fn else 0.0


def expected_calibration_error(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    bins: int = 10,
) -> float:
    boundaries = np.linspace(0, 1, bins + 1)
    error = 0.0
    for index in range(bins):
        lower, upper = boundaries[index], boundaries[index + 1]
        mask = (
            (probabilities >= lower)
            & (
                probabilities <= upper
                if index == bins - 1
                else probabilities < upper
            )
        )
        if not mask.any():
            continue
        error += float(mask.mean()) * abs(
            float(probabilities[mask].mean())
            - float(labels[mask].mean())
        )
    return float(error)


def _participant_bootstrap_sensitivity(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    random_state: int,
) -> dict[str, float]:
    participants = predictions["participant_key"].drop_duplicates().to_numpy()
    rng = np.random.default_rng(random_state)
    values: list[float] = []
    for _ in range(n_bootstrap):
        sampled = rng.choice(participants, size=len(participants), replace=True)
        sample = pd.concat(
            [
                predictions[predictions["participant_key"] == participant]
                for participant in sampled
            ],
            ignore_index=True,
        )
        labels = sample["label"].to_numpy(dtype=int)
        if labels.sum() == 0:
            continue
        values.append(
            _sensitivity(
                labels,
                sample["prediction"].to_numpy(dtype=int),
            )
        )
    if not values:
        return {"lower": 0.0, "upper": 0.0, "mean": 0.0}
    return {
        "lower": float(np.percentile(values, 2.5)),
        "upper": float(np.percentile(values, 97.5)),
        "mean": float(np.mean(values)),
    }


def _valid_rows(rows: pd.DataFrame) -> pd.DataFrame:
    required = {
        "participant_key",
        "corpus",
        "original_group",
        *FEATURES,
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(
            f"Gate 1 dataset is missing required columns: {', '.join(missing)}"
        )
    valid = rows[
        rows["original_group"].isin(["TD", "DD", "ASD", "LT", "STI", "HL"])
    ].copy()
    valid["label"] = (valid["original_group"] != "TD").astype(int)
    return valid.reset_index(drop=True)


def _subgroup_reliability(predictions: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dimension in ("corpus", "original_group"):
        for value, group in predictions.groupby(dimension, sort=True):
            participant_count = int(group["participant_key"].nunique())
            labels = group["label"].to_numpy(dtype=int)
            status = (
                "not_evaluable"
                if participant_count < 20 or len(np.unique(labels)) < 2
                else "evaluable"
            )
            rows.append(
                {
                    "dimension": dimension,
                    "value": str(value),
                    "participant_count": participant_count,
                    "status": status,
                }
            )
    return rows


def evaluate_gate1(
    canonical_rows: pd.DataFrame,
    *,
    random_state: int = 42,
    n_splits: int = 5,
    n_bootstrap: int = 500,
    feature_parity_passed: bool = True,
) -> Gate1Evaluation:
    """Evaluate a calibrated public-corpus proxy without promoting it."""
    rows = _valid_rows(canonical_rows)
    participant_labels = (
        rows.groupby("participant_key", sort=True)["label"].max()
    )
    minimum_class_participants = int(
        participant_labels.value_counts().min()
    )
    folds = min(n_splits, minimum_class_participants)
    if folds < 2:
        raise ValueError(
            "Gate 1 requires at least two independent participants per class."
        )

    features = rows[FEATURES]
    labels = rows["label"].to_numpy(dtype=int)
    groups = rows["participant_key"].to_numpy()
    splitter = StratifiedGroupKFold(
        n_splits=folds,
        shuffle=True,
        random_state=random_state,
    )
    probabilities = np.zeros(len(rows), dtype=float)
    split_audit: list[SplitAudit] = []

    for fold, (train_index, test_index) in enumerate(
        splitter.split(features, labels, groups),
        start=1,
    ):
        model = _fit_calibrated(
            features.iloc[train_index],
            labels[train_index],
            groups[train_index],
            random_state=random_state + fold,
        )
        probabilities[test_index] = model.predict_proba(
            features.iloc[test_index]
        )
        split_audit.append(
            SplitAudit(
                fold=fold,
                train_participants=tuple(
                    sorted(set(groups[train_index]))
                ),
                test_participants=tuple(
                    sorted(set(groups[test_index]))
                ),
            )
        )

    predictions = (probabilities >= 0.5).astype(int)
    uncertain = (probabilities >= 0.40) & (probabilities < 0.60)
    prediction_rows = rows[
        ["participant_key", "corpus", "original_group", "label"]
    ].copy()
    prediction_rows["probability"] = probabilities
    prediction_rows["prediction"] = predictions
    prediction_rows["abstained"] = uncertain

    prevalence = float(labels.mean())
    baseline_probabilities = np.full(len(labels), prevalence)
    metrics: dict[str, float | None] = {
        "sensitivity": _sensitivity(labels, predictions),
        "specificity": _specificity(labels, predictions),
        "macro_f1": float(f1_score(labels, predictions, average="macro")),
        "roc_auc": (
            float(roc_auc_score(labels, probabilities))
            if len(np.unique(labels)) == 2
            else None
        ),
        "pr_auc": (
            float(average_precision_score(labels, probabilities))
            if len(np.unique(labels)) == 2
            else None
        ),
        "brier": float(brier_score_loss(labels, probabilities)),
        "baseline_brier": float(
            brier_score_loss(labels, baseline_probabilities)
        ),
        "ece": expected_calibration_error(labels, probabilities),
        "abstention_rate": float(uncertain.mean()),
    }
    sensitivity_ci = _participant_bootstrap_sensitivity(
        prediction_rows,
        n_bootstrap=n_bootstrap,
        random_state=random_state,
    )

    corpus_holdout: list[dict[str, Any]] = []
    for corpus in sorted(rows["corpus"].dropna().unique()):
        test_mask = rows["corpus"] == corpus
        train_mask = ~test_mask
        train_labels = labels[train_mask.to_numpy()]
        test_labels = labels[test_mask.to_numpy()]
        if (
            len(np.unique(train_labels)) < 2
            or len(np.unique(test_labels)) < 2
        ):
            corpus_holdout.append(
                {
                    "corpus": str(corpus),
                    "status": "not_evaluable",
                }
            )
            continue
        model = _fit_calibrated(
            features.loc[train_mask],
            train_labels,
            groups[train_mask.to_numpy()],
            random_state=random_state,
        )
        held_probabilities = model.predict_proba(features.loc[test_mask])
        corpus_holdout.append(
            {
                "corpus": str(corpus),
                "status": "completed",
                "participant_count": int(
                    rows.loc[test_mask, "participant_key"].nunique()
                ),
                "roc_auc": float(
                    roc_auc_score(test_labels, held_probabilities)
                ),
            }
        )

    completed_holdouts = [
        item for item in corpus_holdout if item["status"] == "completed"
    ]
    gate = PromotionGate(
        sensitivity_ci_lower=sensitivity_ci["lower"],
        specificity=float(metrics["specificity"] or 0.0),
        ece=float(metrics["ece"] or 0.0),
        brier=float(metrics["brier"] or 0.0),
        baseline_brier=float(metrics["baseline_brier"] or 0.0),
        abstention_rate=float(metrics["abstention_rate"] or 0.0),
        corpus_holdout_completed=bool(completed_holdouts),
        feature_parity_passed=feature_parity_passed,
    )
    if not all(math.isfinite(float(value)) for value in metrics.values() if value is not None):
        raise ValueError("Gate 1 produced a non-finite evaluation metric.")

    return Gate1Evaluation(
        metrics=metrics,
        confidence_intervals={"sensitivity": sensitivity_ci},
        split_audit=split_audit,
        corpus_holdout=corpus_holdout,
        subgroup_reliability=_subgroup_reliability(prediction_rows),
        promotion_gate=gate,
        predictions=prediction_rows,
    )
