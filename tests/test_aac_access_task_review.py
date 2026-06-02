from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.review_aac_access_task import (  # noqa: E402
    REVIEW_COLUMNS,
    build_aac_review_row,
    write_aac_review,
)


def test_default_aac_review_row_records_access_and_task_boundary():
    row = build_aac_review_row()

    assert row["corpus"] == "AAC"
    assert row["official_participant_count"] == 18
    assert row["official_video_subset_count"] == 14
    assert row["access_requirement"] == "restricted_to_faculty_slps_or_postdocs"
    assert row["age_eligibility_raw"] == "over_30_months"
    assert row["task_fit_for_toyplay"] == "not_direct_match"
    assert row["recommended_task_type"] == "aac_intervention"
    assert row["review_status"] == "separate_task_candidate_requires_access"
    assert "nonspoken_modalities" in str(row["mor_gra_warning"])


def test_write_aac_review_creates_expected_csv(tmp_path):
    output_path = tmp_path / "aac_review.csv"

    rows = write_aac_review(output_path=output_path)

    assert len(rows) == 1
    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert list(reader.fieldnames or []) == REVIEW_COLUMNS
        written_rows = list(reader)
    assert written_rows[0]["review_status"] == "separate_task_candidate_requires_access"
