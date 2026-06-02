from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.review_asd_addon_candidates import (  # noqa: E402
    REPORT_COLUMNS,
    build_markdown,
    build_review_rows,
    write_review_outputs,
)


def test_review_rows_assign_expected_current_gate_statuses():
    rows = build_review_rows(
        _matrix_rows(),
        _coverage_rows(),
        _source_audit_rows(),
        _official_refresh_rows(),
    )
    by_corpus = {row["candidate_corpus"]: row for row in rows}

    assert by_corpus["AAC"]["review_status"] == "needs_access_and_task_review"
    assert by_corpus["NYU-Emerson"]["review_status"] == "no_official_refresh_available"
    assert by_corpus["NYU-Emerson"]["official_refresh_status"] == "no_official_refresh_available"
    assert by_corpus["Rollins"]["review_status"] == "keep_low_confidence"
    assert by_corpus["QuigleyMcNally"]["review_status"] == "blocked_known_limitation"
    assert by_corpus["Eigsti"]["review_status"] == "blocked_known_limitation"
    assert by_corpus["Rollins"]["source_audit_summary"] == (
        "no_local_target_source_keep_low_confidence:1;"
        "policy_exhausted_keep_low_confidence:1"
    )


def test_review_rows_include_asd_toyplay_low_n_summary():
    rows = build_review_rows(
        _matrix_rows(),
        _coverage_rows(),
        _source_audit_rows(),
        _official_refresh_rows(),
    )

    assert {row["asd_toyplay_low_n_cell_count"] for row in rows} == {2}
    assert {row["asd_toyplay_low_n_row_gap_to_20"] for row in rows} == {26}


def test_review_markdown_avoids_safety_sensitive_claims():
    markdown = build_markdown(
        build_review_rows(
            _matrix_rows(),
            _coverage_rows(),
            _source_audit_rows(),
            _official_refresh_rows(),
        )
    )

    for blocked in ["diagnostic norm", "clinical validation", "model benchmark", "validated score"]:
        assert blocked not in markdown.lower()
    assert "ASD Add-on Review" in markdown
    assert "download_candidate" in markdown


def test_write_review_outputs_creates_csv_and_markdown(tmp_path):
    matrix_path = tmp_path / "matrix.csv"
    coverage_path = tmp_path / "coverage.csv"
    audit_path = tmp_path / "audit.csv"
    official_refresh_path = tmp_path / "official_refresh.csv"
    report_path = tmp_path / "review.csv"
    markdown_path = tmp_path / "review.md"

    pd.DataFrame(_matrix_rows()).to_csv(matrix_path, index=False)
    pd.DataFrame(_coverage_rows()).to_csv(coverage_path, index=False)
    pd.DataFrame(_source_audit_rows()).to_csv(audit_path, index=False)
    pd.DataFrame(_official_refresh_rows()).to_csv(official_refresh_path, index=False)

    rows, markdown = write_review_outputs(
        matrix_path=matrix_path,
        coverage_path=coverage_path,
        source_audit_path=audit_path,
        official_refresh_path=official_refresh_path,
        report_path=report_path,
        markdown_path=markdown_path,
    )

    assert report_path.exists()
    assert markdown_path.exists()
    with report_path.open(newline="", encoding="utf-8") as handle:
        assert list(csv.DictReader(handle).fieldnames or []) == REPORT_COLUMNS
    assert len(rows) == 5
    assert markdown_path.read_text(encoding="utf-8") == markdown


def test_review_rows_leave_nyu_open_when_refresh_artifact_is_absent():
    rows = build_review_rows(
        _matrix_rows(),
        _coverage_rows(),
        _source_audit_rows(),
    )
    by_corpus = {row["candidate_corpus"]: row for row in rows}

    assert by_corpus["NYU-Emerson"]["review_status"] == "needs_official_refresh_check"
    assert by_corpus["NYU-Emerson"]["official_refresh_status"] == ""


def _matrix_rows() -> list[dict[str, str]]:
    return [
        _matrix_row("AAC", "review_access_and_task_fit"),
        _matrix_row("Eigsti", "already_ingested_or_known_limitation"),
        _matrix_row("NYU-Emerson", "review_source_refresh"),
        _matrix_row("QuigleyMcNally", "known_task_mismatch"),
        _matrix_row("Rollins", "source_audit_then_keep_low_confidence"),
    ]


def _matrix_row(corpus: str, decision: str) -> dict[str, str]:
    return {
        "candidate_corpus": corpus,
        "bank": "ASDBank",
        "official_url": f"https://talkbank.org/asd/access/English/{corpus}.html",
        "access_level": "restricted_to_faculty_slps_or_postdocs" if corpus == "AAC" else "registration_required",
        "language": "eng",
        "target_groups": "ASD",
        "age_range_months_raw": "36_to_71",
        "task_match": "toyplay_like",
        "media_or_transcript_status": "transcripts_available",
        "expected_gap_cells": "ASD_toyplay_low_n",
        "license_access_notes": "TalkBank rules apply",
        "decision": decision,
        "decision_reason": "Fixture decision.",
    }


def _coverage_rows() -> list[dict[str, str]]:
    return [
        _coverage_row("24-35", 10, "low_n"),
        _coverage_row("108-119", 4, "low_n"),
        _coverage_row("36-47", 33, "ok"),
    ]


def _coverage_row(age_band: str, cohort_n: int, status: str) -> dict[str, str]:
    return {
        "language": "eng",
        "age_band_12mo": age_band,
        "task_type": "toyplay",
        "group": "ASD",
        "cohort_n": str(cohort_n),
        "coverage_status": status,
    }


def _source_audit_rows() -> list[dict[str, str]]:
    return [
        {
            "target_corpus": "Rollins",
            "audit_status": "policy_exhausted_keep_low_confidence",
        },
        {
            "target_corpus": "Rollins",
            "audit_status": "no_local_target_source_keep_low_confidence",
        },
        {
            "target_corpus": "Gillam",
            "audit_status": "policy_exhausted_keep_low_confidence",
        },
    ]


def _official_refresh_rows() -> list[dict[str, str]]:
    return [
        {
            "corpus": "NYU-Emerson",
            "refresh_status": "no_official_refresh_available",
        }
    ]
