"""Fairness and calibration metrics for binary screening support models."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import (
    brier_score_loss,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)


def _as_array(values: Iterable[float]) -> np.ndarray:
    return np.asarray(list(values), dtype=float)


def brier_score(y_true: Iterable[int], y_prob: Iterable[float]) -> float:
    """Mean squared error between binary labels and predicted probabilities."""
    y = _as_array(y_true)
    p = _as_array(y_prob)
    if len(y) != len(p):
        raise ValueError("y_true and y_prob must have the same length.")
    if len(y) == 0:
        raise ValueError("At least one prediction is required.")
    return float(np.mean((p - y) ** 2))


def expected_calibration_error(
    y_true: Iterable[int],
    y_prob: Iterable[float],
    n_bins: int = 10,
) -> float:
    """Compute binary Expected Calibration Error with equal-width bins."""
    if n_bins <= 0:
        raise ValueError("n_bins must be positive.")
    y = _as_array(y_true)
    p = _as_array(y_prob)
    if len(y) != len(p):
        raise ValueError("y_true and y_prob must have the same length.")
    if len(y) == 0:
        raise ValueError("At least one prediction is required.")

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        left, right = bins[i], bins[i + 1]
        if i == n_bins - 1:
            mask = (p >= left) & (p <= right)
        else:
            mask = (p >= left) & (p < right)
        if not np.any(mask):
            continue
        confidence = float(np.mean(p[mask]))
        accuracy = float(np.mean(y[mask]))
        ece += (np.sum(mask) / len(y)) * abs(accuracy - confidence)
    return float(ece)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def _group_metrics(frame: pd.DataFrame, threshold: float) -> dict[str, float | int]:
    y_true = frame["y_true"].astype(int).to_numpy()
    pred = (frame["prob_asd"].astype(float).to_numpy() >= threshold).astype(int)
    tp = int(((y_true == 1) & (pred == 1)).sum())
    fp = int(((y_true == 0) & (pred == 1)).sum())
    tn = int(((y_true == 0) & (pred == 0)).sum())
    fn = int(((y_true == 1) & (pred == 0)).sum())
    return {
        "n": int(len(frame)),
        "positives": int((y_true == 1).sum()),
        "predicted_positive": int((pred == 1).sum()),
        "tpr": _safe_rate(tp, tp + fn),
        "fpr": _safe_rate(fp, fp + tn),
        "demographic_parity": _safe_rate(int((pred == 1).sum()), len(frame)),
    }


def _max_min_difference(values: pd.Series) -> float:
    finite = values.dropna()
    if finite.empty:
        return float("nan")
    return float(finite.max() - finite.min())


def fairness_by_group(
    df: pd.DataFrame,
    sensitive_attributes: list[str],
    y_true_col: str = "y_true",
    prob_col: str = "prob_asd",
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Compute group fairness rates and max-minus-min differences."""
    required = {y_true_col, prob_col, *sensitive_attributes}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    work = df.rename(columns={y_true_col: "y_true", prob_col: "prob_asd"}).copy()
    rows = []
    for attribute in sensitive_attributes:
        for group, group_df in work.groupby(attribute, dropna=False):
            label = "missing" if pd.isna(group) else str(group)
            metrics = _group_metrics(group_df, threshold)
            rows.append({
                "attribute": attribute,
                "group": label,
                "threshold": threshold,
                **metrics,
            })

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    for metric in ("tpr", "fpr", "demographic_parity"):
        diff_col = f"{metric}_difference"
        result[diff_col] = result.groupby("attribute")[metric].transform(
            _max_min_difference
        )
    return result


def calibration_summary(
    y_true: Iterable[int],
    y_prob: Iterable[float],
    n_bins: int = 10,
) -> dict[str, float | int]:
    """Return ECE and Brier score as a one-row serializable dict."""
    y = list(y_true)
    p = list(y_prob)
    return {
        "n": len(y),
        "n_bins": n_bins,
        "ece": expected_calibration_error(y, p, n_bins=n_bins),
        "brier_score": brier_score(y, p),
    }


def binary_metric_summary(
    y_true: Iterable[int],
    y_prob: Iterable[float],
    threshold: float = 0.5,
) -> dict[str, float]:
    """Return binary screening metrics from labels and probabilities."""
    y = np.asarray(list(y_true), dtype=int)
    p = np.asarray(list(y_prob), dtype=float)
    if len(y) != len(p):
        raise ValueError("y_true and y_prob must have the same length.")
    if len(y) == 0:
        raise ValueError("At least one prediction is required.")
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else float("nan"),
        "sensitivity": float(recall_score(y, pred, pos_label=1, zero_division=0)),
        "specificity": _safe_rate(int(tn), int(tn + fp)),
        "ppv": float(precision_score(y, pred, pos_label=1, zero_division=0)),
        "npv": _safe_rate(int(tn), int(tn + fn)),
        "brier_score": float(brier_score_loss(y, p)),
    }


def bootstrap_binary_metric_ci(
    y_true: Iterable[int],
    y_prob: Iterable[float],
    threshold: float = 0.5,
    n_boot: int = 1000,
    random_state: int = 42,
) -> pd.DataFrame:
    """Bootstrap 95% CIs for core binary screening metrics."""
    if n_boot <= 0:
        raise ValueError("n_boot must be positive.")
    y = np.asarray(list(y_true), dtype=int)
    p = np.asarray(list(y_prob), dtype=float)
    if len(y) != len(p):
        raise ValueError("y_true and y_prob must have the same length.")
    if len(y) == 0:
        raise ValueError("At least one prediction is required.")

    point = binary_metric_summary(y, p, threshold=threshold)
    samples: dict[str, list[float]] = {metric: [] for metric in point}
    rng = np.random.default_rng(random_state)
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        metrics = binary_metric_summary(y[idx], p[idx], threshold=threshold)
        for metric, value in metrics.items():
            if np.isfinite(value):
                samples[metric].append(value)

    rows = []
    for metric, point_value in point.items():
        values = np.asarray(samples[metric], dtype=float)
        if len(values) == 0:
            low = high = float("nan")
        else:
            low, high = np.quantile(values, [0.025, 0.975])
        rows.append({
            "metric": metric,
            "point": round(float(point_value), 4) if np.isfinite(point_value) else float("nan"),
            "ci_low": round(float(low), 4) if np.isfinite(low) else float("nan"),
            "ci_high": round(float(high), 4) if np.isfinite(high) else float("nan"),
            "n_boot": int(n_boot),
            "threshold": float(threshold),
        })
    return pd.DataFrame(rows)


def subgroup_reliability_flags(
    fairness: pd.DataFrame,
    min_n: int = 20,
    min_class_count: int = 5,
) -> pd.DataFrame:
    """Add reliability flags for subgroup audit rows.

    A subgroup is flagged when its total sample or either class count is too
    small for a stable estimate. The output is meant for model governance UI,
    not for excluding groups from review.
    """
    required = {"attribute", "group", "n", "positives"}
    missing = required - set(fairness.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    result = fairness.copy()
    result["negatives"] = result["n"].astype(int) - result["positives"].astype(int)
    result["reliability_status"] = np.where(
        (result["n"].astype(int) < min_n)
        | (result["positives"].astype(int) < min_class_count)
        | (result["negatives"].astype(int) < min_class_count),
        "insufficient_n",
        "reviewable",
    )
    result["reliability_note"] = np.where(
        result["reliability_status"] == "insufficient_n",
        f"Interpret cautiously: subgroup n<{min_n} or class count<{min_class_count}.",
        "Subgroup size is sufficient for a descriptive audit row.",
    )
    return result
