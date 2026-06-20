from pathlib import Path
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.ml.gate1_validation import (  # noqa: E402
    PromotionGate,
    evaluate_gate1,
)
from src.feature_schema import FEATURES  # noqa: E402


def _gate1_rows(participants: int = 40) -> pd.DataFrame:
    rows = []
    corpora = ["CorpusA", "CorpusB", "CorpusC", "CorpusD"]
    for index in range(participants):
        label = 0 if index % 2 == 0 else 1
        group = "TD" if label == 0 else ("ASD" if index % 4 == 1 else "DD")
        corpus = corpora[(index // 2) % len(corpora)]
        for session in range(2):
            base = 2.0 if label == 0 else -2.0
            row = {
                "participant_key": f"participant-{index}",
                "session_key": f"session-{index}-{session}",
                "corpus": corpus,
                "original_group": group,
            }
            for feature_index, feature in enumerate(FEATURES):
                row[feature] = (
                    48 + index % 12
                    if feature == "age_months"
                    else base + feature_index * 0.01 + session * 0.001
                )
            rows.append(row)
    return pd.DataFrame(rows)


def test_participant_never_crosses_train_and_test():
    result = evaluate_gate1(
        _gate1_rows(),
        random_state=42,
        n_bootstrap=50,
    )

    for split in result.split_audit:
        assert set(split.train_participants).isdisjoint(
            split.test_participants
        )
    assert len(result.predictions) == 80


def test_failed_sensitivity_lower_bound_keeps_candidate_research_only():
    gate = PromotionGate(
        sensitivity_ci_lower=0.79,
        specificity=0.80,
        ece=0.05,
        brier=0.10,
        baseline_brier=0.20,
        abstention_rate=0.10,
        corpus_holdout_completed=True,
        feature_parity_passed=True,
    )

    assert gate.passed is False
    assert "sensitivity_ci_lower" in gate.failed_reasons


def test_every_preregistered_gate_is_enforced():
    passing = {
        "sensitivity_ci_lower": 0.80,
        "specificity": 0.60,
        "ece": 0.10,
        "brier": 0.20,
        "baseline_brier": 0.20,
        "abstention_rate": 0.40,
        "corpus_holdout_completed": True,
        "feature_parity_passed": True,
    }
    assert PromotionGate(**passing).passed is True

    for field in (
        "sensitivity_ci_lower",
        "specificity",
        "ece",
        "brier",
        "abstention_rate",
        "corpus_holdout_completed",
        "feature_parity_passed",
    ):
        failing = dict(passing)
        if field == "sensitivity_ci_lower":
            failing[field] = 0.799
        elif field == "specificity":
            failing[field] = 0.599
        elif field == "ece":
            failing[field] = 0.101
        elif field == "brier":
            failing[field] = 0.201
        elif field == "abstention_rate":
            failing[field] = 0.401
        else:
            failing[field] = False
        gate = PromotionGate(**failing)
        assert gate.passed is False
        assert field in gate.failed_reasons


def test_evaluation_reports_calibration_bootstrap_and_corpus_holdouts():
    result = evaluate_gate1(
        _gate1_rows(),
        random_state=7,
        n_bootstrap=50,
    )
    payload = result.to_dict()

    assert 0 <= result.metrics["ece"] <= 1
    assert 0 <= result.metrics["brier"] <= 1
    assert 0 <= result.metrics["abstention_rate"] <= 1
    assert set(result.confidence_intervals["sensitivity"]) == {
        "lower",
        "upper",
        "mean",
    }
    assert any(item["status"] == "completed" for item in result.corpus_holdout)
    assert "predictions" not in payload
    assert payload["task"] == "td_vs_non_td_public_corpus_proxy"
    assert payload["promotion_gate"]["passed"] in {True, False}


def test_subgroups_without_enough_independent_participants_are_not_evaluable():
    result = evaluate_gate1(
        _gate1_rows(participants=20),
        n_splits=2,
        n_bootstrap=20,
    )

    assert result.subgroup_reliability
    assert all(
        item["status"] == "not_evaluable"
        for item in result.subgroup_reliability
        if item["dimension"] == "original_group"
    )


def test_missing_required_feature_fails_closed():
    rows = _gate1_rows().drop(columns=["mlu"])

    with pytest.raises(ValueError, match="missing required columns: mlu"):
        evaluate_gate1(rows, n_bootstrap=10)
