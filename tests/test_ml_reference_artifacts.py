from packages.ml.reference_contracts import (
    MIN_CORPORA_PER_CELL,
    MIN_PARTICIPANTS_PER_CELL,
    evaluate_support,
    original_group,
    presentation_group,
)


def test_other_is_presentation_only():
    assert original_group("SLI") == "STI"
    assert presentation_group("LT") == "OTHER"
    assert presentation_group("STI") == "OTHER"
    assert presentation_group("HL") == "OTHER"
    assert presentation_group("ASD") == "ASD"


def test_reference_support_thresholds_are_preregistered():
    assert MIN_PARTICIPANTS_PER_CELL == 20
    assert MIN_CORPORA_PER_CELL == 2


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
