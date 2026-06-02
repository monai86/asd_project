from __future__ import annotations

import csv
from pathlib import Path


MATRIX_PATH = Path("data/reference/asd_addon_candidate_matrix.csv")

EXPECTED_COLUMNS = [
    "candidate_corpus",
    "bank",
    "official_url",
    "access_level",
    "language",
    "target_groups",
    "age_range_months_raw",
    "task_match",
    "media_or_transcript_status",
    "expected_gap_cells",
    "license_access_notes",
    "decision",
    "decision_reason",
]


def test_asd_addon_candidate_matrix_has_required_schema_and_candidates():
    rows = _read_matrix()

    assert rows
    assert list(rows[0]) == EXPECTED_COLUMNS
    assert {row["candidate_corpus"] for row in rows} == {
        "AAC",
        "Eigsti",
        "Flusberg",
        "Nadig",
        "NYU-Emerson",
        "QuigleyMcNally",
        "Rollins",
    }


def test_aac_is_review_candidate_not_automatic_download():
    rows = {row["candidate_corpus"]: row for row in _read_matrix()}

    assert rows["AAC"]["decision"] == "review_access_and_task_fit"
    assert "restricted" in rows["AAC"]["access_level"]
    assert rows["AAC"]["decision"] != "download_candidate"


def test_matrix_does_not_claim_clinical_validation_or_download_approval():
    rows = _read_matrix()
    text = " ".join(
        str(value).lower()
        for row in rows
        for value in row.values()
    )

    assert "download_candidate" not in {row["decision"] for row in rows}
    for blocked in ["diagnostic norm", "clinical validation", "model benchmark"]:
        assert blocked not in text


def _read_matrix() -> list[dict[str, str]]:
    with MATRIX_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
