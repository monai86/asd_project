"""Fairness and calibration metrics for binary screening support models."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


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
