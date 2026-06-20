from pathlib import Path
import hashlib
import hmac
import re
import sys

import pandas as pd
import pandas.testing as pdt
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.ml.reference_dataset import (  # noqa: E402
    CANONICAL_FEATURE_COLUMNS,
    CANONICAL_METADATA,
    build_canonical_reference_rows as _build_canonical_reference_rows,
)
from src.feature_schema import FEATURES  # noqa: E402

TEST_PSEUDONYMIZATION_KEY = b"test-only-reference-dataset-key!"


def build_canonical_reference_rows(
    combined,
    curated,
    *,
    pseudonymization_key=TEST_PSEUDONYMIZATION_KEY,
    pseudonymization_key_version="test-v1",
):
    return _build_canonical_reference_rows(
        combined,
        curated,
        pseudonymization_key=pseudonymization_key,
        pseudonymization_key_version=pseudonymization_key_version,
    )


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
    assert result.rows["participant_key"].nunique() == 2
    assert all(
        re.fullmatch(r"(eigsti|rescorla):participant-[0-9a-f]{64}", value)
        for value in result.rows["participant_key"]
    )


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
    assert CANONICAL_FEATURE_COLUMNS == [
        feature for feature in FEATURES if feature not in CANONICAL_METADATA
    ]
    assert list(result.rows.columns) == (
        CANONICAL_METADATA + CANONICAL_FEATURE_COLUMNS
    )
    assert result.rows.columns.is_unique
    assert result.rows.columns.tolist().count("age_months") == 1
    assert isinstance(result.rows["age_months"], pd.Series)
    assert set(FEATURES).issubset(result.rows.columns)
    feature_values = result.rows.iloc[0, len(CANONICAL_METADATA) :]
    assert feature_values.index.tolist() == CANONICAL_FEATURE_COLUMNS
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
    assert result.pseudonymization_key_version == "test-v1"


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


def test_child_fallback_is_pseudonymized_across_repeated_sessions():
    combined = pd.DataFrame(
        [
            {
                "child": "Jane Doe",
                "corpus": "PrivateCorpus",
                "group": "TD",
                "age_months": 40,
            },
            {
                "child": " jane   doe ",
                "corpus": "PrivateCorpus",
                "group": "TD",
                "age_months": 41,
            },
        ]
    )

    result = build_canonical_reference_rows(combined, pd.DataFrame())

    expected_digest = hmac.new(
        TEST_PSEUDONYMIZATION_KEY,
        b"participant\x00child\x00jane doe",
        hashlib.sha256,
    ).hexdigest()
    assert result.rows["participant_key"].nunique() == 1
    assert result.rows["participant_key"].iloc[0] == (
        f"privatecorpus:participant-{expected_digest}"
    )
    assert result.rows["session_key"].nunique() == 2

    serialized = "\n".join(
        [
            result.rows.to_csv(index=False),
            result.audit.to_csv(index=False),
            result.dataset_hash,
        ]
    ).lower()
    assert "jane" not in serialized
    assert "doe" not in serialized


def test_blank_child_without_public_corpus_id_is_audited_as_missing_participant():
    combined = pd.DataFrame(
        [{"child": "  ", "corpus": "PrivateCorpus", "group": "TD"}]
    )

    result = build_canonical_reference_rows(combined, pd.DataFrame())

    assert result.rows.empty
    assert result.audit["reason_code"].tolist() == ["missing_participant_key"]


def test_all_identifier_and_provenance_outputs_are_opaque_and_stable():
    combined = pd.DataFrame(
        [
            {
                "participant_id": "Participant Alpha",
                "child": "Ignored Child Name",
                "file_id": "File Alpha",
                "session_id": "Session Alpha",
                "source_path": "private/Jane/alpha-session.cha",
                "corpus": "CorpusA",
                "group": "TD",
                "age_months": 40,
            },
            {
                "participant_id": " participant   alpha ",
                "child": "Ignored Child Name",
                "file_id": "File Beta",
                "session_id": "Session Beta",
                "source_path": "private/Jane/beta-session.cha",
                "corpus": "CorpusA",
                "group": "TD",
                "age_months": 41,
            },
            {
                "child": "Child Bravo",
                "session_id": "Child Session",
                "corpus": "CorpusB",
                "group": "TD",
            },
            {
                "file_id": "File Charlie",
                "session_id": "File Session",
                "corpus": "CorpusC",
                "group": "TD",
            },
        ]
    )
    curated = pd.DataFrame(
        [
            {
                "participant_id": "Duplicate Path Person",
                "source_path": "private/Jane/alpha-session.cha",
                "corpus": "CorpusD",
                "group": "TD",
            }
        ]
    )

    result = build_canonical_reference_rows(combined, curated)

    corpus_a = result.rows[result.rows["corpus"] == "corpusa"]
    assert corpus_a["participant_key"].nunique() == 1
    assert result.rows["session_key"].str.fullmatch(
        r"session-[0-9a-f]{64}"
    ).all()
    assert result.rows["source_path"].map(
        lambda value: value == ""
        or re.fullmatch(r"source-[0-9a-f]{64}", value) is not None
    ).all()

    serialized = (
        result.rows.to_csv(index=False) + result.audit.to_csv(index=False)
    ).casefold()
    forbidden_components = [
        "participant alpha",
        "duplicate path person",
        "alpha-session",
        "beta-session",
        "ignored",
        "child bravo",
        "file alpha",
        "file beta",
        "file charlie",
        "session alpha",
        "session beta",
        "child session",
        "file session",
        "private",
        "jane",
        ".cha",
    ]
    for component in forbidden_components:
        assert component not in serialized


def test_identical_cross_source_content_with_blank_paths_deduplicates_by_hash():
    shared_content = {
        "participant_id": "P1",
        "corpus": "Eigsti",
        "group": "TD",
        "age_months": 42,
        "total_utterances": 10,
    }

    result = build_canonical_reference_rows(
        pd.DataFrame([{**shared_content, "group_header": "TD"}]),
        pd.DataFrame([{**shared_content, "notes": "curation metadata"}]),
    )

    assert len(result.rows) == 1
    assert result.rows.iloc[0]["source_dataset"] == "combined"
    assert result.audit["reason_code"].tolist() == ["duplicate_row_hash"]


def test_corpus_case_and_prefixed_public_ids_normalize_before_deduplication():
    combined = pd.DataFrame(
        [{
            "participant_id": "1010",
            "corpus": "eigsti",
            "group": "ASD",
            "age_months": 50,
            "language": "",
            "mlu": 2.5,
        }]
    )
    curated = pd.DataFrame(
        [{
            "participant_id": "Eigsti:ASD:1010",
            "file_id": "Eigsti:1010",
            "corpus": "Eigsti",
            "group": "ASD",
            "age_months": 50,
            "language": "eng",
            "mlu": 2.5,
        }]
    )

    result = build_canonical_reference_rows(combined, curated)

    assert len(result.rows) == 1
    assert result.rows.iloc[0]["corpus"] == "eigsti"
    assert result.rows.iloc[0]["source_dataset"] == "combined"
    assert result.audit["reason_code"].tolist() == ["duplicate_row_hash"]


def test_different_identity_fields_prevent_content_hash_deduplication():
    shared_content = {
        "corpus": "Eigsti",
        "group": "TD",
        "age_months": 42,
        "total_utterances": 10,
    }
    combined = pd.DataFrame(
        [{"participant_id": "P1", "file_id": "F1", **shared_content}]
    )
    curated = pd.DataFrame(
        [{"participant_id": "P2", "file_id": "F2", **shared_content}]
    )

    result = build_canonical_reference_rows(combined, curated)

    assert len(result.rows) == 2
    assert result.rows["source_row_hash"].nunique() == 2
    assert result.audit.empty


@pytest.mark.parametrize("unsupported_value", [{"unordered"}, object()])
def test_unsupported_required_value_is_excluded_with_deterministic_audit(
    unsupported_value,
):
    row = {
        "participant_id": "P1",
        "source_path": "private/rejected.cha",
        "corpus": "Eigsti",
        "group": "TD",
        "mlu": unsupported_value,
    }

    first = build_canonical_reference_rows(pd.DataFrame([row]), pd.DataFrame())
    second = build_canonical_reference_rows(pd.DataFrame([row]), pd.DataFrame())

    assert first.rows.empty
    assert first.audit["reason_code"].tolist() == ["unsupported_value_type"]
    assert re.fullmatch(
        r"source-[0-9a-f]{64}", first.audit.iloc[0]["source_path"]
    )
    assert re.fullmatch(r"[0-9a-f]{64}", first.audit.iloc[0]["source_row_hash"])
    pdt.assert_frame_equal(first.audit, second.audit)
    serialized = first.audit.to_csv(index=False).casefold()
    assert "private" not in serialized
    assert "rejected" not in serialized


def test_unsupported_excluded_values_are_ignored():
    row = {
        "participant_id": "P1",
        "corpus": "Eigsti",
        "group": "TD",
        "notes": object(),
        "raw_text": {"unsupported"},
        "utterances": object(),
    }

    result = build_canonical_reference_rows(pd.DataFrame([row]), pd.DataFrame())

    assert len(result.rows) == 1
    assert result.audit.empty


def test_supported_nested_values_are_normalized_deterministically():
    shared = {
        "participant_id": "P1",
        "corpus": "Eigsti",
        "group": "TD",
    }
    first_mapping = {
        "z": (pd.Timestamp("2026-01-02T03:04:05"), {"b": 2, "a": 1}),
        "a": True,
    }
    second_mapping = {
        "a": True,
        "z": [pd.Timestamp("2026-01-02T03:04:05"), {"a": 1, "b": 2}],
    }

    first = build_canonical_reference_rows(
        pd.DataFrame([{**shared, "mlu": first_mapping}]),
        pd.DataFrame(),
    )
    second = build_canonical_reference_rows(
        pd.DataFrame([{**shared, "mlu": second_mapping}]),
        pd.DataFrame(),
    )

    pdt.assert_frame_equal(first.rows, second.rows)
    assert first.dataset_hash == second.dataset_hash


def test_empty_pseudonymization_key_is_rejected_before_processing():
    with pytest.raises(ValueError, match="pseudonymization_key"):
        _build_canonical_reference_rows(
            pd.DataFrame([{"notes": object()}]),
            pd.DataFrame(),
            pseudonymization_key=b"",
        )


def test_different_keys_change_only_opaque_references_and_hashes():
    row = {
        "participant_id": "P1",
        "source_path": "Data/Session A.cha",
        "corpus": "Eigsti",
        "group": "TD",
        "age_months": 42,
        "mlu": 2.5,
    }

    first = build_canonical_reference_rows(
        pd.DataFrame([row]),
        pd.DataFrame(),
        pseudonymization_key=b"first-test-key-with-32-byte-value!",
        pseudonymization_key_version="key-a",
    )
    second = build_canonical_reference_rows(
        pd.DataFrame([row]),
        pd.DataFrame(),
        pseudonymization_key=b"second-test-key-with-32-byte-value",
        pseudonymization_key_version="key-b",
    )

    opaque_columns = {
        "source_path",
        "source_row_hash",
        "participant_key",
        "session_key",
    }
    assert all(
        first.rows.iloc[0][column] != second.rows.iloc[0][column]
        for column in opaque_columns
    )
    pdt.assert_series_equal(
        first.rows.drop(columns=opaque_columns).iloc[0],
        second.rows.drop(columns=opaque_columns).iloc[0],
    )
    assert first.pseudonymization_key_version == "key-a"
    assert second.pseudonymization_key_version == "key-b"
    assert b"first-test-key" not in repr(first).encode()


def test_same_source_blank_path_duplicate_hash_is_audited():
    row = {
        "participant_id": "P1",
        "corpus": "Eigsti",
        "group": "TD",
        "age_months": 42,
        "mlu": 2.5,
    }

    result = build_canonical_reference_rows(
        pd.DataFrame([row, row]),
        pd.DataFrame(),
    )

    assert len(result.rows) == 1
    assert result.audit["reason_code"].tolist() == ["duplicate_row_hash"]


def test_path_normalization_preserves_case_and_internal_whitespace():
    rows = [
        {
            "participant_id": "P1",
            "source_path": r" folder\A  Session.cha ",
            "corpus": "Eigsti",
            "group": "TD",
        },
        {
            "participant_id": "P1",
            "source_path": "folder/a  Session.cha",
            "corpus": "Eigsti",
            "group": "TD",
        },
    ]

    result = build_canonical_reference_rows(pd.DataFrame(rows), pd.DataFrame())

    assert len(result.rows) == 2
    assert result.rows["source_path"].nunique() == 2
    assert result.rows["source_row_hash"].nunique() == 2
    assert result.audit.empty


def test_path_separator_representations_deduplicate():
    shared = {
        "participant_id": "P1",
        "corpus": "Eigsti",
        "group": "TD",
    }
    rows = [
        {**shared, "source_path": r"folder\Session.cha"},
        {**shared, "source_path": "folder/Session.cha"},
    ]

    result = build_canonical_reference_rows(pd.DataFrame(rows), pd.DataFrame())

    assert len(result.rows) == 1
    assert result.audit["reason_code"].tolist() == ["duplicate_source_row"]


@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
def test_non_finite_canonical_numbers_are_audited(value):
    row = {
        "participant_id": "P1",
        "corpus": "Eigsti",
        "group": "TD",
        "mlu": value,
    }

    result = build_canonical_reference_rows(pd.DataFrame([row]), pd.DataFrame())

    assert result.rows.empty
    assert result.audit["reason_code"].tolist() == ["invalid_numeric_value"]
    assert re.fullmatch(r"[0-9a-f]{64}", result.audit.iloc[0]["source_row_hash"])


def test_rejected_row_hashes_are_unique_and_do_not_leak_identifiers():
    rows = [
        {
            "participant_id": "Rejected Alice",
            "source_path": "private/Alice/bad.cha",
            "corpus": "Eigsti",
            "group": "TD",
            "mlu": object(),
        },
        {
            "participant_id": "Rejected Bob",
            "source_path": "private/Bob/bad.cha",
            "corpus": "Eigsti",
            "group": "TD",
            "mlu": object(),
        },
    ]

    result = build_canonical_reference_rows(pd.DataFrame(rows), pd.DataFrame())

    assert result.audit["source_row_hash"].nunique() == 2
    serialized = result.audit.to_csv(index=False).casefold()
    for raw in ["alice", "bob", "rejected", "private", "bad.cha"]:
        assert raw not in serialized


def test_identical_content_at_different_paths_deduplicates_after_path_pass():
    shared = {
        "participant_id": "P1",
        "corpus": "Eigsti",
        "group": "TD",
        "age_months": 42,
        "mlu": 2.5,
    }
    combined = pd.DataFrame(
        [{**shared, "source_path": "combined/P1.cha"}]
    )
    curated = pd.DataFrame(
        [{**shared, "source_path": "curated/P1-copy.cha"}]
    )

    result = build_canonical_reference_rows(combined, curated)

    assert len(result.rows) == 1
    assert result.rows.iloc[0]["source_dataset"] == "combined"
    assert result.audit["reason_code"].tolist() == ["duplicate_row_hash"]


def test_conflicting_same_path_winner_is_independent_of_input_order():
    rows = [
        {
            "participant_id": "P1",
            "source_path": "same/P1.cha",
            "corpus": "Eigsti",
            "group": "TD",
            "mlu": 1.0,
        },
        {
            "participant_id": "P1",
            "source_path": "same/P1.cha",
            "corpus": "Eigsti",
            "group": "TD",
            "mlu": 2.0,
        },
    ]

    forward = build_canonical_reference_rows(
        pd.DataFrame(rows),
        pd.DataFrame(),
    )
    reversed_result = build_canonical_reference_rows(
        pd.DataFrame(list(reversed(rows))),
        pd.DataFrame(),
    )

    pdt.assert_frame_equal(forward.rows, reversed_result.rows)
    pdt.assert_frame_equal(forward.audit, reversed_result.audit)
    assert forward.dataset_hash == reversed_result.dataset_hash
    assert forward.audit["reason_code"].tolist() == ["duplicate_source_row"]


@pytest.mark.parametrize(
    "invalid_key",
    [b"", b"too-short", "not-bytes", None],
)
def test_pseudonymization_key_requires_at_least_32_bytes(invalid_key):
    with pytest.raises(ValueError, match="at least 32 bytes"):
        _build_canonical_reference_rows(
            pd.DataFrame(),
            pd.DataFrame(),
            pseudonymization_key=invalid_key,
        )


@pytest.mark.parametrize(
    "invalid_version",
    ["", "   ", None, 1],
)
def test_pseudonymization_key_version_must_be_nonblank_string(
    invalid_version,
):
    with pytest.raises(ValueError, match="nonblank string"):
        _build_canonical_reference_rows(
            pd.DataFrame(),
            pd.DataFrame(),
            pseudonymization_key=TEST_PSEUDONYMIZATION_KEY,
            pseudonymization_key_version=invalid_version,
        )
