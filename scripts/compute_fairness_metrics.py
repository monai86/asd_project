"""Compute fairness and calibration summaries for the screening prototype."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fairness_metrics import (
    calibration_summary,
    fairness_by_group,
    subgroup_reliability_flags,
)

METRIC_DIR = PROJECT_ROOT / "reports" / "metrics"
PREDICTIONS_PATH = METRIC_DIR / "binary_oof_predictions.csv"
THRESHOLD_PATH = METRIC_DIR / "threshold_metrics.csv"
FAIRNESS_OUT = METRIC_DIR / "fairness_metrics.csv"
CALIBRATION_OUT = METRIC_DIR / "calibration_summary.csv"
RELIABILITY_OUT = METRIC_DIR / "subgroup_reliability.csv"


def _age_band(age_months: float | int | None) -> str:
    if pd.isna(age_months):
        return "missing"
    age = float(age_months)
    if age < 48:
        return "<48m"
    if age < 72:
        return "48-71m"
    return "72m+"


def _default_threshold() -> float:
    if not THRESHOLD_PATH.exists():
        return 0.5
    thresholds = pd.read_csv(THRESHOLD_PATH)
    if "threshold" not in thresholds.columns or thresholds.empty:
        return 0.5
    thresholds = thresholds.copy()
    thresholds["distance"] = (thresholds["threshold"].astype(float) - 0.5).abs()
    return float(thresholds.sort_values("distance").iloc[0]["threshold"])


def main() -> int:
    if not PREDICTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Missing {PREDICTIONS_PATH}. Run src/classifier.py before fairness metrics."
        )
    df = pd.read_csv(PREDICTIONS_PATH)
    required = {"y_true", "prob_asd", "sex", "age_months", "corpus"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required prediction columns: {sorted(missing)}")

    df = df.copy()
    df["age_band"] = df["age_months"].apply(_age_band)
    threshold = _default_threshold()

    fairness = fairness_by_group(
        df,
        sensitive_attributes=["sex", "age_band", "corpus"],
        y_true_col="y_true",
        prob_col="prob_asd",
        threshold=threshold,
    )
    calibration = pd.DataFrame([
        {
            "threshold": threshold,
            **calibration_summary(df["y_true"], df["prob_asd"], n_bins=10),
        }
    ])
    reliability = subgroup_reliability_flags(fairness)

    METRIC_DIR.mkdir(parents=True, exist_ok=True)
    fairness.to_csv(FAIRNESS_OUT, index=False)
    calibration.to_csv(CALIBRATION_OUT, index=False)
    reliability.to_csv(RELIABILITY_OUT, index=False)
    print(f"[saved] {FAIRNESS_OUT.relative_to(PROJECT_ROOT)}")
    print(f"[saved] {CALIBRATION_OUT.relative_to(PROJECT_ROOT)}")
    print(f"[saved] {RELIABILITY_OUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
