from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.fairness_metrics import (
    bootstrap_binary_metric_ci,
    brier_score,
    expected_calibration_error,
    fairness_by_group,
    subgroup_reliability_flags,
)


def test_brier_and_ece_for_toy_probabilities():
    y_true = [0, 0, 1, 1]
    y_prob = [0.1, 0.2, 0.8, 0.9]

    assert round(brier_score(y_true, y_prob), 4) == 0.025
    ece = expected_calibration_error(y_true, y_prob, n_bins=2)
    assert 0 <= ece <= 0.2
    assert round(ece, 4) == 0.15


def test_fairness_metrics_include_group_rates_and_differences():
    df = pd.DataFrame({
        "y_true": [1, 1, 0, 0, 1, 0, 1, 0],
        "prob_asd": [0.9, 0.4, 0.7, 0.2, 0.8, 0.6, 0.3, 0.1],
        "sex": ["A", "A", "A", "A", "B", "B", "B", "B"],
    })

    result = fairness_by_group(
        df,
        sensitive_attributes=["sex"],
        y_true_col="y_true",
        prob_col="prob_asd",
        threshold=0.5,
    )

    rows = result.set_index("group")
    assert rows.loc["A", "tpr"] == 0.5
    assert rows.loc["A", "fpr"] == 0.5
    assert rows.loc["B", "tpr"] == 0.5
    assert rows.loc["B", "fpr"] == 0.5
    assert rows.loc["A", "demographic_parity"] == 0.5
    assert rows.loc["B", "demographic_parity"] == 0.5
    assert set(result["tpr_difference"]) == {0.0}
    assert set(result["fpr_difference"]) == {0.0}
    assert set(result["demographic_parity_difference"]) == {0.0}


def test_bootstrap_ci_is_stable_for_toy_predictions():
    y_true = [0, 0, 0, 1, 1, 1]
    y_prob = [0.05, 0.2, 0.4, 0.6, 0.8, 0.95]

    result = bootstrap_binary_metric_ci(
        y_true,
        y_prob,
        n_boot=25,
        random_state=7,
    )

    assert set(result["metric"]) == {
        "roc_auc",
        "sensitivity",
        "specificity",
        "ppv",
        "npv",
        "brier_score",
    }
    assert (result["ci_low"] <= result["ci_high"]).all()
    assert set(result["n_boot"]) == {25}


def test_subgroup_reliability_flags_small_groups():
    fairness = pd.DataFrame({
        "attribute": ["sex", "sex"],
        "group": ["small", "large"],
        "n": [12, 40],
        "positives": [4, 20],
    })

    result = subgroup_reliability_flags(fairness, min_n=20, min_class_count=5)
    rows = result.set_index("group")

    assert rows.loc["small", "reliability_status"] == "insufficient_n"
    assert rows.loc["large", "reliability_status"] == "reviewable"
