from pathlib import Path
import sys

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


def test_other_is_presentation_only():
    assert presentation_group("LT") == "OTHER"
    assert presentation_group("STI") == "OTHER"
    assert presentation_group("HL") == "OTHER"
    assert presentation_group("ASD") == "ASD"


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
    decision = evaluate_support(participant_count=19, corpus_count=2)

    assert decision.supported is False
    assert decision.participant_count == 19
    assert decision.corpus_count == 2
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
    assert decision.reason_code == "supported"


def test_unsupported_original_group_raises_value_error():
    try:
        original_group("OTHER")
    except ValueError:
        pass
    else:
        raise AssertionError("original_group should reject unsupported groups")
