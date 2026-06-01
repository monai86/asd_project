from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.build_reference_coverage_report import (  # noqa: E402
    COVERAGE_COLUMNS,
    build_coverage_rows,
    build_markdown,
    write_coverage_outputs,
)


def test_coverage_rows_use_union_of_feature_cohort_and_clan_cells():
    features_df = pd.DataFrame(
        [
            _feature_row("eng", "24-35", "toyplay", "TD", corpus="Ambrose"),
            _feature_row("eng", "24-35", "toyplay", "TD", corpus="Ambrose"),
            _feature_row("eng", "", "narrative", "TD", corpus="ENNI"),
        ]
    )
    cohorts_df = pd.DataFrame([_cohort_row("24-35", "toyplay", "TD", cohort_n=20)])
    clan_df = pd.DataFrame(
        [
            _feature_row("eng", "24-35", "toyplay", "TD", corpus="Ambrose"),
            _feature_row("eng", "24-35", "toyplay", "TD", corpus="Ambrose"),
            _feature_row("eng", "", "narrative", "TD", corpus="ENNI"),
            _feature_row("eng", "36-47", "toyplay", "ASD", corpus="Rollins"),
        ]
    )

    rows = build_coverage_rows(features_df, cohorts_df, clan_df)

    assert len(rows) == 3
    assert list(rows[0]) == COVERAGE_COLUMNS
    by_key = {(row["age_band_12mo"], row["task_type"], row["group"]): row for row in rows}
    assert by_key[("24-35", "toyplay", "TD")]["coverage_status"] == "ok"
    assert by_key[("24-35", "toyplay", "TD")]["feature_row_count"] == 2
    assert by_key[("24-35", "toyplay", "TD")]["clan_row_count"] == 2
    assert by_key[("UNASSIGNED", "narrative", "TD")]["coverage_status"] == "not_cohort_ready"
    assert by_key[("36-47", "toyplay", "ASD")]["clan_coverage_status"] == "clan_only"


def test_coverage_rows_preserve_low_n_threshold_from_reference_cohorts():
    features_df = pd.DataFrame([_feature_row("eng", "24-35", "toyplay", "HL") for _ in range(19)])
    cohorts_df = pd.DataFrame([_cohort_row("24-35", "toyplay", "HL", cohort_n=19)])
    clan_df = features_df.copy()

    rows = build_coverage_rows(features_df, cohorts_df, clan_df)

    assert rows[0]["cohort_n"] == 19
    assert rows[0]["confidence_flag"] == "low_n"
    assert rows[0]["coverage_status"] == "low_n"


def test_coverage_rows_mark_partial_clan_when_new_feature_rows_are_unparsed():
    features_df = pd.DataFrame(
        [
            _feature_row("eng", "84-95", "narrative", "TD", corpus="ENNI"),
            _feature_row("eng", "84-95", "narrative", "TD", corpus="Gillam"),
        ]
    )
    cohorts_df = pd.DataFrame([_cohort_row("84-95", "narrative", "TD", cohort_n=20)])
    clan_df = pd.DataFrame([_feature_row("eng", "84-95", "narrative", "TD", corpus="ENNI")])

    rows = build_coverage_rows(features_df, cohorts_df, clan_df)

    assert rows[0]["feature_row_count"] == 2
    assert rows[0]["clan_row_count"] == 1
    assert rows[0]["clan_coverage_status"] == "partial_clan"
    assert rows[0]["coverage_status"] == "missing_clan"
    assert rows[0]["phase2_recommendation"].startswith("Run CLAN check/kideval")


def test_markdown_summary_avoids_safety_sensitive_shortcuts():
    coverage_df = pd.DataFrame(
        [
            {
                "language": "eng",
                "age_band_12mo": "24-35",
                "task_type": "toyplay",
                "group": "TD",
                "feature_row_count": 20,
                "cohort_ready_row_count": 20,
                "cohort_n": 20,
                "confidence_flag": "ok",
                "clan_row_count": 20,
                "clan_coverage_status": "matched",
                "corpus_count": 1,
                "corpora": "Ambrose",
                "design_types": "long",
                "coverage_status": "ok",
                "phase2_recommendation": "",
            }
        ],
        columns=COVERAGE_COLUMNS,
    )

    markdown = build_markdown(coverage_df, pd.DataFrame())

    for blocked in ["diagnostic norm", "benchmark", "ground truth", "validated score"]:
        assert blocked not in markdown.lower()
    assert "Reference Cohort Coverage Report" in markdown
    assert "CLAN-Derived Metrics" in markdown


def test_write_coverage_outputs_creates_csv_and_markdown(tmp_path):
    features_path = tmp_path / "features.csv"
    cohorts_path = tmp_path / "cohorts.csv"
    clan_path = tmp_path / "clan.csv"
    qc_path = tmp_path / "qc.csv"
    coverage_path = tmp_path / "coverage.csv"
    markdown_path = tmp_path / "coverage.md"

    pd.DataFrame([_feature_row("eng", "24-35", "toyplay", "TD")]).to_csv(features_path, index=False)
    pd.DataFrame([_cohort_row("24-35", "toyplay", "TD", cohort_n=1)]).to_csv(
        cohorts_path,
        index=False,
    )
    pd.DataFrame([_feature_row("eng", "24-35", "toyplay", "TD")]).to_csv(clan_path, index=False)
    pd.DataFrame(
        [
            {
                "qc_scope": "transcript",
                "source_path": "x.cha",
                "cohort_key": "",
                "qc_status": "warn",
                "reason": "missing_age_months",
                "detail": "Feature row retained.",
            }
        ]
    ).to_csv(qc_path, index=False)

    coverage_df, markdown = write_coverage_outputs(
        coverage_path=coverage_path,
        markdown_path=markdown_path,
        features_path=features_path,
        cohorts_path=cohorts_path,
        clan_features_path=clan_path,
        qc_path=qc_path,
    )

    assert coverage_path.exists()
    assert markdown_path.exists()
    assert list(pd.read_csv(coverage_path).columns) == COVERAGE_COLUMNS
    assert len(coverage_df) == 1
    assert "QC missing_age_months rows" in markdown
    assert markdown_path.read_text(encoding="utf-8") == markdown


def _feature_row(
    language: str,
    age_band: str,
    task_type: str,
    group: str,
    *,
    corpus: str = "Synthetic",
) -> dict[str, object]:
    return {
        "language": language,
        "age_band_12mo": age_band,
        "task_type": task_type,
        "group": group,
        "corpus": corpus,
        "design_type": "long",
    }


def _cohort_row(age_band: str, task_type: str, group: str, *, cohort_n: int) -> dict[str, object]:
    return {
        "age_band_12mo": age_band,
        "task_type": task_type,
        "group": group,
        "cohort_n": cohort_n,
        "confidence_flag": "ok" if cohort_n >= 20 else "low_n",
        "corpus_count": 1,
        "corpora": "Synthetic",
        "design_types": "long",
    }
