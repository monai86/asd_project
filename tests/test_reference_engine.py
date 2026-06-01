from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.feature_schema import FEATURES  # noqa: E402
from src.reference_engine import (  # noqa: E402
    CLAN_METRICS,
    INSUFFICIENT_REFERENCE_DATA,
    OK,
    REFERENCE_TERM,
    ReferenceEngine,
    age_band_12mo,
    assert_descriptive_wording,
    resolve_task_type,
)


def _feature_payload(value: float = 10.0) -> dict[str, float]:
    return {feature: value for feature in FEATURES}


def _write_reference_csvs(tmp_path: Path) -> tuple[Path, Path]:
    feature_rows = []
    for group, base, n in [("ASD", 10, 3), ("TD", 20, 4), ("SLI", 30, 2)]:
        for offset in range(n):
            row = {
                "language": "eng",
                "age_band_12mo": "48-59",
                "task_type": "toyplay",
                "group": group,
                "corpus": "Synthetic",
            }
            row.update(_feature_payload(base + offset))
            feature_rows.append(row)

    unmatched = {
        "language": "eng",
        "age_band_12mo": "60-71",
        "task_type": "narrative",
        "group": "TD",
        "corpus": "Synthetic",
    }
    unmatched.update(_feature_payload(99))
    feature_rows.append(unmatched)

    cohort_rows = []
    for group, confidence_flag, values in [
        ("ASD", "low_n", [10, 11, 12]),
        ("TD", "ok", [20, 21, 22, 23]),
        ("SLI", "low_n", [30, 31]),
    ]:
        row = {
            "age_band_12mo": "48-59",
            "task_type": "toyplay",
            "group": group,
            "cohort_n": len(values),
            "confidence_flag": confidence_flag,
            "corpora": "Synthetic",
            "design_types": "cross",
        }
        series = pd.Series(values)
        for feature in FEATURES:
            row[f"{feature}_q1"] = series.quantile(0.25)
            row[f"{feature}_median"] = series.median()
            row[f"{feature}_q3"] = series.quantile(0.75)
            row[f"{feature}_min"] = series.min()
            row[f"{feature}_max"] = series.max()
        cohort_rows.append(row)

    unmatched_cohort = {
        "age_band_12mo": "60-71",
        "task_type": "narrative",
        "group": "TD",
        "cohort_n": 1,
        "confidence_flag": "low_n",
        "corpora": "Synthetic",
        "design_types": "cross",
    }
    for feature in FEATURES:
        unmatched_cohort[f"{feature}_q1"] = 99
        unmatched_cohort[f"{feature}_median"] = 99
        unmatched_cohort[f"{feature}_q3"] = 99
        unmatched_cohort[f"{feature}_min"] = 99
        unmatched_cohort[f"{feature}_max"] = 99
    cohort_rows.append(unmatched_cohort)

    features_path = tmp_path / "features.csv"
    cohorts_path = tmp_path / "cohorts.csv"
    pd.DataFrame(feature_rows).to_csv(features_path, index=False)
    pd.DataFrame(cohort_rows).to_csv(cohorts_path, index=False)
    return features_path, cohorts_path


def _write_clan_csv(tmp_path: Path) -> Path:
    rows = []
    for group, values in [
        ("ASD", [10, 11, 12]),
        ("TD", [100, 101, 102, 103]),
        ("SLI", [30, 31]),
    ]:
        for offset, value in enumerate(values):
            row = {
                "language": "eng",
                "age_band_12mo": "48-59",
                "task_type": "toyplay",
                "group": group,
                "metric_source": "clan_kideval",
                "kideval_mlu_utts": value,
                "kideval_freq_types": value + 10,
                "kideval_freq_tokens": value + 20,
                "kideval_freq_ttr": "",
                "kideval_vocd_score": value + 30,
                "kideval_dss_utterances": value + 40,
                "kideval_dss": 5 + offset if group == "TD" and offset < 2 else "",
                "kideval_ipsyn_total": value + 50,
            }
            rows.append(row)

    path = tmp_path / "clan_features.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _missing_clan_path(tmp_path: Path) -> Path:
    return tmp_path / "missing_clan_features.csv"


def test_task_mapping_and_explicit_task_override():
    assert resolve_task_type(session_type="free_play") == "toyplay"
    assert resolve_task_type(session_type="parent_child_interaction") == "toyplay"
    assert resolve_task_type(session_type="therapy_session") == "toyplay"
    assert resolve_task_type(session_type="structured_assessment") == "narrative"
    assert resolve_task_type(session_type="structured_assessment", task_type="toyplay") == "toyplay"
    assert resolve_task_type(task_type="picture description") == "picture_description"


def test_reference_engine_compares_all_matching_groups_and_low_n_warns(tmp_path):
    features_path, cohorts_path = _write_reference_csvs(tmp_path)
    engine = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=_missing_clan_path(tmp_path),
    )

    result = engine.compare(features=_feature_payload(21), age_months=50, session_type="free_play")

    assert result.status == OK
    assert result.reference_term == REFERENCE_TERM
    assert result.age_band_12mo == "48-59"
    assert result.task_type == "toyplay"
    assert [cohort.group for cohort in result.cohorts] == ["ASD", "SLI", "TD"]
    assert "low_n:48-59|toyplay|ASD" in result.warnings
    assert "low_n:48-59|toyplay|SLI" in result.warnings
    assert next(cohort for cohort in result.cohorts if cohort.group == "TD").confidence_flag == "ok"


def test_reference_engine_does_not_fallback_when_no_cohort_matches(tmp_path):
    features_path, cohorts_path = _write_reference_csvs(tmp_path)
    engine = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=_missing_clan_path(tmp_path),
    )

    result = engine.compare(features=_feature_payload(21), age_months=50, task_type="narrative")

    assert result.status == INSUFFICIENT_REFERENCE_DATA
    assert result.cohorts == []
    assert "no_matching_reference_cohort" in result.warnings


def test_feature_comparisons_follow_core_14_order_and_positions(tmp_path):
    features_path, cohorts_path = _write_reference_csvs(tmp_path)
    engine = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=_missing_clan_path(tmp_path),
    )

    result = engine.compare(features=_feature_payload(21), age_months=50, task_type="toyplay")
    td = next(cohort for cohort in result.cohorts if cohort.group == "TD")

    assert [item.feature for item in td.feature_comparisons] == FEATURES
    first = td.feature_comparisons[0]
    assert first.value == 21
    assert first.percentile == 50.0
    assert first.position == "within_iqr"
    assert first.q1 == 20.75
    assert first.median == 21.5
    assert first.q3 == 22.25

    asd = next(cohort for cohort in result.cohorts if cohort.group == "ASD")
    assert asd.feature_comparisons[0].position == "above_iqr"
    sli = next(cohort for cohort in result.cohorts if cohort.group == "SLI")
    assert sli.feature_comparisons[0].position == "below_iqr"


def test_missing_feature_returns_missing_position_without_crashing(tmp_path):
    features_path, cohorts_path = _write_reference_csvs(tmp_path)
    engine = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=_missing_clan_path(tmp_path),
    )
    features = _feature_payload(21)
    features.pop("mlu")

    result = engine.compare(features=features, age_months=50, task_type="toyplay")
    td = next(cohort for cohort in result.cohorts if cohort.group == "TD")
    mlu = next(item for item in td.feature_comparisons if item.feature == "mlu")

    assert mlu.value is None
    assert mlu.percentile is None
    assert mlu.position == "missing"


def test_age_band_and_missing_metadata_return_insufficient_data(tmp_path):
    features_path, cohorts_path = _write_reference_csvs(tmp_path)
    engine = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=_missing_clan_path(tmp_path),
    )

    assert age_band_12mo(48) == "48-59"
    assert age_band_12mo(59.9) == "48-59"
    features = _feature_payload(21)
    features.pop("age_months")
    result = engine.compare(features=features, session_type="free_play")

    assert result.status == INSUFFICIENT_REFERENCE_DATA
    assert "missing_age_band" in result.warnings


def test_clan_metric_comparisons_are_separate_and_only_for_ok_cohorts(tmp_path):
    features_path, cohorts_path = _write_reference_csvs(tmp_path)
    clan_features_path = _write_clan_csv(tmp_path)
    engine = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=clan_features_path,
    )
    features = _feature_payload(21)
    features["kideval_mlu_utts"] = 101

    result = engine.compare(features=features, age_months=50, task_type="toyplay")

    td = next(cohort for cohort in result.cohorts if cohort.group == "TD")
    asd = next(cohort for cohort in result.cohorts if cohort.group == "ASD")
    sli = next(cohort for cohort in result.cohorts if cohort.group == "SLI")
    assert asd.clan_metric_comparisons == []
    assert sli.clan_metric_comparisons == []
    assert [item.feature for item in td.feature_comparisons] == FEATURES
    assert "kideval_freq_ttr" not in [item.metric for item in td.clan_metric_comparisons]
    assert "kideval_dss" in [item.metric for item in td.clan_metric_comparisons]

    mlu_utts = next(
        item for item in td.clan_metric_comparisons if item.metric == "kideval_mlu_utts"
    )
    assert mlu_utts.value == 101
    assert mlu_utts.percentile == 50.0
    assert mlu_utts.position == "within_iqr"
    assert mlu_utts.reference_n == 4
    assert mlu_utts.metric_source == "clan_kideval"

    dss = next(item for item in td.clan_metric_comparisons if item.metric == "kideval_dss")
    assert dss.reference_n == 2


def test_clan_metric_comparisons_keep_reference_distribution_when_user_value_missing(tmp_path):
    features_path, cohorts_path = _write_reference_csvs(tmp_path)
    clan_features_path = _write_clan_csv(tmp_path)
    engine = ReferenceEngine(
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=clan_features_path,
    )

    result = engine.compare(features=_feature_payload(21), age_months=50, task_type="toyplay")

    td = next(cohort for cohort in result.cohorts if cohort.group == "TD")
    assert td.clan_metric_comparisons
    first = td.clan_metric_comparisons[0]
    assert first.metric in CLAN_METRICS
    assert first.value is None
    assert first.percentile is None
    assert first.position == "missing"
    assert first.reference_n > 0


def test_smoke_existing_reference_csvs_use_descriptive_wording():
    features_path = Path("data/reference/english_child_reference_features.csv")
    cohorts_path = Path("data/reference/english_child_reference_cohorts.csv")
    if not features_path.exists() or not cohorts_path.exists():
        return

    engine = ReferenceEngine(features_path=features_path, cohorts_path=cohorts_path)
    features = {feature: 1 for feature in FEATURES}
    features["age_months"] = 50
    result = engine.compare(features=features, age_months=50, session_type="free_play")

    assert result.reference_term == "Reference Comparison"
    assert_descriptive_wording(result.to_dict())
