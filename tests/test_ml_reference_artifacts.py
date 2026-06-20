from pathlib import Path
import json
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.ml.reference_contracts import (
    MIN_CORPORA_PER_CELL,
    MIN_PARTICIPANTS_PER_CELL,
    SUPPORTED_LANGUAGE,
    evaluate_support,
    original_group,
    presentation_group,
)  # noqa: E402
from packages.ml.reference_artifacts import (  # noqa: E402
    build_reference_cells,
    sha256_file,
    write_reference_artifacts,
)
from packages.ml.reference_dataset import CanonicalDatasetResult  # noqa: E402
from scripts.build_ml_reference_evidence import (  # noqa: E402
    _pseudonymization_key,
)


def _canonical_rows(
    *,
    participants: int,
    sessions_each: int,
    corpora: list[str],
    language: str = "eng",
    age_months: float = 50,
    task_type: str = "toyplay",
    group: str = "TD",
) -> pd.DataFrame:
    rows = []
    for index in range(participants):
        corpus = corpora[index % len(corpora)]
        for session in range(sessions_each):
            rows.append(
                {
                    "language": language,
                    "age_months": age_months,
                    "task_type": task_type,
                    "original_group": group,
                    "participant_key": f"{corpus}:participant-{index}",
                    "session_key": f"session-{index}-{session}",
                    "corpus": corpus,
                    "mlu": float(index + session),
                }
            )
    return pd.DataFrame(rows)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("TD", "TD"),
        ("TYP", "TD"),
        ("CONTROL", "TD"),
        ("DD", "DD"),
        ("ASD", "ASD"),
        ("LT", "OTHER"),
        ("SLI", "OTHER"),
        ("STI", "OTHER"),
        ("DLD", "OTHER"),
        ("HL", "OTHER"),
        (" td ", "TD"),
        (" typ ", "TD"),
        (" control ", "TD"),
        (" dd ", "DD"),
        (" asd ", "ASD"),
        (" lt ", "OTHER"),
        (" sli ", "OTHER"),
        (" sti ", "OTHER"),
        (" dld ", "OTHER"),
        (" hl ", "OTHER"),
    ],
)
def test_other_is_presentation_only(value, expected):
    assert presentation_group(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("TD", "TD"),
        ("TYP", "TD"),
        ("CONTROL", "TD"),
        ("DD", "DD"),
        ("ASD", "ASD"),
        ("LT", "LT"),
        ("SLI", "STI"),
        ("STI", "STI"),
        ("DLD", "STI"),
        ("HL", "HL"),
    ],
)
def test_original_group_aliases_preserve_research_labels(value, expected):
    assert original_group(value) == expected


def test_reference_support_thresholds_are_preregistered():
    assert MIN_PARTICIPANTS_PER_CELL == 20
    assert MIN_CORPORA_PER_CELL == 2
    assert SUPPORTED_LANGUAGE == "eng"


def test_support_requires_minimum_participants_first():
    decision = evaluate_support(participant_count=19, corpus_count=1)

    assert decision.supported is False
    assert decision.participant_count == 19
    assert decision.corpus_count == 1
    assert decision.reason_code == "insufficient_participants"


def test_support_requires_corpus_diversity():
    decision = evaluate_support(participant_count=20, corpus_count=1)

    assert decision.supported is False
    assert decision.participant_count == 20
    assert decision.corpus_count == 1
    assert decision.reason_code == "insufficient_corpus_diversity"


def test_support_meets_preregistered_thresholds():
    decision = evaluate_support(participant_count=20, corpus_count=2)

    assert decision.supported is True
    assert decision.participant_count == 20
    assert decision.corpus_count == 2
    assert decision.reason_code is None


def test_unsupported_original_group_raises_value_error():
    with pytest.raises(ValueError):
        original_group("OTHER")


def test_unhashable_unsupported_original_group_raises_value_error():
    with pytest.raises(ValueError):
        original_group([])


def test_twenty_sessions_from_one_participant_do_not_support_a_cell():
    cells = build_reference_cells(
        _canonical_rows(
            participants=1,
            sessions_each=20,
            corpora=["CorpusA"],
        )
    )

    cell = cells.iloc[0]
    assert cell["participant_count"] == 1
    assert cell["session_count"] == 20
    assert bool(cell["supported"]) is False
    assert cell["reason_code"] == "insufficient_participants"
    assert cell["mlu_n"] == 0
    assert pd.isna(cell["mlu_median"])


def test_twenty_participants_from_one_corpus_still_abstain():
    cell = build_reference_cells(
        _canonical_rows(
            participants=20,
            sessions_each=1,
            corpora=["CorpusA"],
        )
    ).iloc[0]

    assert cell["participant_count"] == 20
    assert cell["corpus_count"] == 1
    assert bool(cell["supported"]) is False
    assert cell["reason_code"] == "insufficient_corpus_diversity"
    assert cell["mlu_n"] == 0


def test_supported_cell_reports_participants_corpora_and_distribution():
    cell = build_reference_cells(
        _canonical_rows(
            participants=20,
            sessions_each=1,
            corpora=["CorpusA", "CorpusB"],
        )
    ).iloc[0]

    assert cell["age_band_12mo"] == "48-59"
    assert cell["presentation_group"] == "TD"
    assert cell["participant_count"] == 20
    assert cell["session_count"] == 20
    assert cell["corpus_count"] == 2
    assert cell["corpora"] == "CorpusA;CorpusB"
    assert bool(cell["supported"]) is True
    assert cell["reason_code"] == ""
    assert cell["mlu_n"] == 20
    assert cell["mlu_median"] == pytest.approx(9.5)


def test_other_is_only_a_presentation_rollup_in_reference_cells():
    rows = pd.concat(
        [
            _canonical_rows(
                participants=20,
                sessions_each=1,
                corpora=["CorpusA", "CorpusB"],
                group=group,
            )
            for group in ("LT", "STI", "HL")
        ],
        ignore_index=True,
    )

    cells = build_reference_cells(rows)

    assert set(cells["original_group"]) == {"LT", "STI", "HL"}
    assert set(cells["presentation_group"]) == {"OTHER"}
    assert len(cells) == 3


def test_rows_missing_language_age_or_task_do_not_create_reference_cells():
    rows = pd.concat(
        [
            _canonical_rows(
                participants=20,
                sessions_each=1,
                corpora=["CorpusA", "CorpusB"],
                language="",
            ),
            _canonical_rows(
                participants=20,
                sessions_each=1,
                corpora=["CorpusA", "CorpusB"],
                age_months=float("nan"),
            ),
            _canonical_rows(
                participants=20,
                sessions_each=1,
                corpora=["CorpusA", "CorpusB"],
                task_type="",
            ),
        ],
        ignore_index=True,
    )

    assert build_reference_cells(rows).empty


def _canonical_result() -> CanonicalDatasetResult:
    rows = _canonical_rows(
        participants=20,
        sessions_each=1,
        corpora=["CorpusA", "CorpusB"],
    )
    return CanonicalDatasetResult(
        rows=rows,
        audit=pd.DataFrame(
            columns=[
                "source_dataset",
                "source_path",
                "source_row_hash",
                "reason_code",
                "detail",
            ]
        ),
        dataset_hash="d" * 64,
        pseudonymization_key_version="test-key-v1",
    )


def test_manifest_binds_dataset_schema_support_policy_and_checksums(tmp_path):
    result = _canonical_result()
    paths = write_reference_artifacts(
        result,
        tmp_path / "candidate-v1",
        artifact_version="candidate-v1",
    )

    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    assert manifest["artifact_type"] == "ml_reference_evidence"
    assert manifest["artifact_version"] == "candidate-v1"
    assert manifest["dataset_hash"] == result.dataset_hash
    assert manifest["pseudonymization_key_version"] == "test-key-v1"
    assert manifest["feature_schema_version"] == "reference-core-14-v1"
    assert manifest["support_policy"] == {
        "minimum_unique_participants": 20,
        "minimum_corpora": 2,
    }
    for logical_name, metadata in manifest["files"].items():
        file_path = paths.directory / metadata["filename"]
        assert file_path.exists(), logical_name
        assert metadata["sha256"] == sha256_file(file_path)
        assert metadata["size_bytes"] == file_path.stat().st_size
        assert len(metadata["sha256"]) == 64


def test_artifact_publish_is_fail_closed_when_target_exists(tmp_path):
    target = tmp_path / "candidate-v1"
    target.mkdir()
    marker = target / "keep.txt"
    marker.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_reference_artifacts(
            _canonical_result(),
            target,
            artifact_version="candidate-v1",
        )

    assert marker.read_text(encoding="utf-8") == "existing"


def test_optional_gate1_report_is_checksummed(tmp_path):
    paths = write_reference_artifacts(
        _canonical_result(),
        tmp_path / "candidate-v1",
        artifact_version="candidate-v1",
        gate1_validation={"promotion_gate": {"passed": False}},
    )

    manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    gate = manifest["files"]["gate1_validation"]
    gate_path = paths.directory / gate["filename"]
    assert json.loads(gate_path.read_text())["promotion_gate"]["passed"] is False
    assert gate["sha256"] == sha256_file(gate_path)
    assert manifest["gate1"] == {
        "status": "research_only",
        "report_sha256": gate["sha256"],
    }


def test_pseudonymization_key_loader_requires_secret_environment(
    monkeypatch,
):
    monkeypatch.delenv("TEST_REFERENCE_KEY", raising=False)
    with pytest.raises(ValueError, match="Set TEST_REFERENCE_KEY"):
        _pseudonymization_key("TEST_REFERENCE_KEY")

    monkeypatch.setenv("TEST_REFERENCE_KEY", "too-short")
    with pytest.raises(ValueError, match="at least 32 bytes"):
        _pseudonymization_key("TEST_REFERENCE_KEY")


def test_pseudonymization_key_loader_accepts_raw_and_hex(monkeypatch):
    raw_key = "x" * 32
    monkeypatch.setenv("TEST_REFERENCE_KEY", raw_key)
    assert _pseudonymization_key("TEST_REFERENCE_KEY") == raw_key.encode()

    hex_key = bytes(range(32))
    monkeypatch.setenv("TEST_REFERENCE_KEY", f"hex:{hex_key.hex()}")
    assert _pseudonymization_key("TEST_REFERENCE_KEY") == hex_key
