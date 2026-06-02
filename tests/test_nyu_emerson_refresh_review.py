from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.review_nyu_emerson_refresh import (  # noqa: E402
    REVIEW_COLUMNS,
    build_refresh_review_row,
    write_refresh_review,
)


def test_nyu_refresh_review_marks_no_official_refresh_when_counts_match():
    row = build_refresh_review_row(
        transcript_manifest_rows=_manifest_rows(total=30, analysis_ready=26),
        feature_rows=_feature_rows(26),
        clan_rows=_feature_rows(26),
        official_published_transcript_sets=30,
    )

    assert row["official_participant_count"] == 30
    assert row["official_published_transcript_sets"] == 30
    assert row["local_transcript_count"] == 30
    assert row["local_analysis_ready_count"] == 26
    assert row["local_feature_row_count"] == 26
    assert row["local_clan_row_count"] == 26
    assert row["local_excluded_count"] == 4
    assert row["refresh_status"] == "no_official_refresh_available"


def test_nyu_refresh_review_marks_download_candidate_when_official_count_exceeds_local():
    row = build_refresh_review_row(
        transcript_manifest_rows=_manifest_rows(total=30, analysis_ready=26),
        feature_rows=_feature_rows(26),
        clan_rows=_feature_rows(26),
        official_published_transcript_sets=31,
    )

    assert row["refresh_status"] == "download_candidate"


def test_nyu_refresh_review_marks_local_rebuild_when_features_lag_ready_manifest():
    row = build_refresh_review_row(
        transcript_manifest_rows=_manifest_rows(total=30, analysis_ready=26),
        feature_rows=_feature_rows(25),
        clan_rows=_feature_rows(25),
        official_published_transcript_sets=30,
    )

    assert row["refresh_status"] == "needs_local_artifact_rebuild"


def test_write_refresh_review_creates_csv(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    features_path = tmp_path / "features.csv"
    clan_path = tmp_path / "clan.csv"
    output_path = tmp_path / "review.csv"

    pd.DataFrame(_manifest_rows(total=30, analysis_ready=26)).to_csv(manifest_path, index=False)
    pd.DataFrame(_feature_rows(26)).to_csv(features_path, index=False)
    pd.DataFrame(_feature_rows(26)).to_csv(clan_path, index=False)

    rows = write_refresh_review(
        transcript_manifest_path=manifest_path,
        features_path=features_path,
        clan_features_path=clan_path,
        output_path=output_path,
    )

    assert output_path.exists()
    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert list(reader.fieldnames or []) == REVIEW_COLUMNS
        written_rows = list(reader)
    assert rows[0]["refresh_status"] == "no_official_refresh_available"
    assert written_rows[0]["refresh_status"] == "no_official_refresh_available"


def _manifest_rows(*, total: int, analysis_ready: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(total):
        ready = index < analysis_ready
        rows.append(
            {
                "source_path": f"data/NYU-Emerson/{2001 + index}.cha",
                "corpus": "NYU-Emerson",
                "analysis_ready": ready,
                "qc_status": "pass" if ready else "eligible_short_sample",
            }
        )
    return rows


def _feature_rows(total: int) -> list[dict[str, object]]:
    return [
        {
            "source_path": f"data/NYU-Emerson/{2001 + index}.cha",
            "corpus": "NYU-Emerson",
        }
        for index in range(total)
    ]
