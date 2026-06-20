from pathlib import Path
import re
import sys

import pandas as pd
import pandas.testing as pdt
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.ml.reference_dataset import (  # noqa: E402
    CANONICAL_METADATA,
    build_canonical_reference_rows,
)
from src.feature_schema import FEATURES  # noqa: E402


def test_canonical_rows_preserve_original_and_presentation_groups():
    combined = pd.DataFrame(
        [
            {
                "participant_id": "P1",
                "corpus": "Eigsti",
                "group": "ASD",
                "age_months": 50,
                "total_utterances": 10,
            }
        ]
    )
    curated = pd.DataFrame(
        [
            {
                "participant_id": "P2",
                "source_path": "data/lt.cha",
                "corpus": "Rescorla",
                "group": "LT",
                "age_months": 48,
                "total_utterances": 12,
            }
        ]
    )

    result = build_canonical_reference_rows(combined, curated)

    assert set(result.rows["original_group"]) == {"ASD", "LT"}
    assert set(result.rows["presentation_group"]) == {"ASD", "OTHER"}
    assert set(result.rows["participant_key"]) == {"Eigsti:P1", "Rescorla:P2"}


def test_exact_overlap_is_kept_once_and_audited():
    row = {
        "participant_id": "P1",
        "source_path": "data/shared.cha",
        "corpus": "Eigsti",
        "group": "TD",
        "age_months": 42,
        "total_utterances": 10,
    }

    result = build_canonical_reference_rows(
        pd.DataFrame([row]),
        pd.DataFrame([row]),
    )

    assert len(result.rows) == 1
    assert result.rows.iloc[0]["source_dataset"] == "combined"
    assert result.audit["reason_code"].tolist() == ["duplicate_source_row"]


def test_repeated_sessions_share_participant_key_and_have_distinct_session_keys():
    curated = pd.DataFrame(
        [
            {
                "participant_id": "P1",
                "source_path": "a.cha",
                "corpus": "Gillam",
                "group": "TD",
            },
            {
                "participant_id": "P1",
                "source_path": "b.cha",
                "corpus": "Gillam",
                "group": "TD",
            },
        ]
    )

    result = build_canonical_reference_rows(pd.DataFrame(), curated)

    assert result.rows["participant_key"].nunique() == 1
    assert result.rows["session_key"].nunique() == 2


def test_result_and_dataset_hash_are_deterministic_across_input_row_order():
    combined_rows = [
        {
            "participant_id": "P2",
            "corpus": "CorpusB",
            "group": "DD",
            "session_id": "visit-2",
            "mlu": 2.5,
        },
        {
            "participant_id": "P1",
            "corpus": "CorpusA",
            "group": "ASD",
            "session_id": "visit-1",
            "mlu": 1.5,
        },
    ]
    curated_rows = [
        {
            "participant_id": "P3",
            "corpus": "CorpusC",
            "group": "HL",
            "file_id": "file-3",
            "mlu": 3.5,
        }
    ]

    forward = build_canonical_reference_rows(
        pd.DataFrame(combined_rows),
        pd.DataFrame(curated_rows),
    )
    reversed_result = build_canonical_reference_rows(
        pd.DataFrame(list(reversed(combined_rows))),
        pd.DataFrame(list(reversed(curated_rows))),
    )

    pdt.assert_frame_equal(forward.rows, reversed_result.rows)
    pdt.assert_frame_equal(forward.audit, reversed_result.audit)
    assert forward.dataset_hash == reversed_result.dataset_hash


@pytest.mark.parametrize(
    ("row", "reason_code"),
    [
        (
            {"participant_id": " ", "corpus": "Eigsti", "group": "TD"},
            "missing_participant_key",
        ),
        (
            {"participant_id": "P1", "corpus": " ", "group": "TD"},
            "missing_corpus",
        ),
        (
            {"participant_id": "P1", "corpus": "Eigsti", "group": "OTHER"},
            "unsupported_group",
        ),
    ],
)
def test_invalid_source_rows_are_excluded_and_audited(row, reason_code):
    result = build_canonical_reference_rows(pd.DataFrame([row]), pd.DataFrame())

    assert result.rows.empty
    assert result.audit["reason_code"].tolist() == [reason_code]
    assert list(result.audit.columns) == [
        "source_dataset",
        "source_path",
        "source_row_hash",
        "reason_code",
        "detail",
    ]


def test_output_uses_canonical_columns_and_preserves_missing_features_as_null():
    combined = pd.DataFrame(
        [
            {
                "participant_id": "P1",
                "corpus": "Eigsti",
                "group": "ASD",
                "age_months": 50,
                "total_utterances": 10,
            }
        ]
    )

    result = build_canonical_reference_rows(combined, pd.DataFrame())

    assert CANONICAL_METADATA == [
        "source_dataset",
        "source_path",
        "source_row_hash",
        "corpus",
        "participant_key",
        "session_key",
        "original_group",
        "presentation_group",
        "age_months",
        "language",
        "task_type",
        "extractor_version",
        "feature_schema_version",
    ]
    assert list(result.rows.columns) == CANONICAL_METADATA + FEATURES
    feature_values = result.rows.iloc[0, len(CANONICAL_METADATA) :]
    assert feature_values.index.tolist() == FEATURES
    assert feature_values["total_utterances"] == 10
    assert pd.isna(feature_values["mlu"])
    assert feature_values["mlu"] != 0


def test_source_rows_have_auditable_metadata_and_sha256_hashes():
    combined = pd.DataFrame(
        [
            {
                "participant_id": "P1",
                "corpus": "Eigsti",
                "group": "ASD",
                "age_months": 50,
            }
        ]
    )

    result = build_canonical_reference_rows(combined, pd.DataFrame())
    row = result.rows.iloc[0]

    assert set(CANONICAL_METADATA).issubset(result.rows.columns)
    assert row["source_dataset"] == "combined"
    assert row["source_path"] == ""
    assert row["language"] == ""
    assert row["task_type"] == ""
    assert row["extractor_version"] == "legacy-project-extractor"
    assert row["feature_schema_version"] == "reference-core-14-v1"
    assert re.fullmatch(r"[0-9a-f]{64}", row["source_row_hash"])
    assert re.fullmatch(r"[0-9a-f]{64}", result.dataset_hash)


def test_sensitive_source_fields_are_not_copied_to_canonical_rows():
    combined = pd.DataFrame(
        [
            {
                "participant_id": "DIRECT-ID",
                "corpus": "Eigsti",
                "group": "ASD",
                "transcript": "private transcript content",
                "raw_text": "private raw content",
                "utterances": "private utterances",
                "notes": "private notes",
                "storage_key": "private-storage-key",
                "child": "Child Name",
            }
        ]
    )

    result = build_canonical_reference_rows(combined, pd.DataFrame())

    forbidden_columns = {
        "participant_id",
        "child",
        "transcript",
        "raw_text",
        "utterances",
        "notes",
        "storage_key",
    }
    assert forbidden_columns.isdisjoint(result.rows.columns)
    serialized = result.rows.to_csv(index=False)
    assert "private transcript content" not in serialized
    assert "private raw content" not in serialized
    assert "private utterances" not in serialized
    assert "private notes" not in serialized
    assert "private-storage-key" not in serialized
    assert "Child Name" not in serialized
