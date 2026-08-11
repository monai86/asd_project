from __future__ import annotations

from app.schemas.clinical import Utterance
from app.services.providers.descriptive_v170_provider import compute_descriptive_metrics


def test_non_token_metrics_are_deterministic_and_overlap_is_counted_once() -> None:
    utterances = [
        Utterance(utterance_id="u1", speaker="SPK_01", text="สวัสดี", start_ms=0, end_ms=1000, review_status="reviewed"),
        Utterance(utterance_id="u2", speaker="SPK_01", text="หนูชอบรถ", start_ms=900, end_ms=1600, review_status="reviewed"),
        Utterance(utterance_id="u3", speaker="SPK_02", text="ครับ", start_ms=1700, end_ms=2000, review_status="reviewed"),
    ]
    metrics = compute_descriptive_metrics(
        utterances,
        role_by_utterance={"u1": "target_child", "u2": "target_child", "u3": "therapist"},
        audio_duration_ms=2500,
    )

    assert metrics["total_utterance_count"].value == 3
    assert metrics["child_utterance_count"].value == 2
    assert metrics["therapist_utterance_count"].value == 1
    assert metrics["turn_count"].value == 2
    assert metrics["timestamp_coverage"].numerator == 1900
    assert metrics["timestamp_coverage"].denominator == 2500
    assert metrics["timestamp_coverage"].value == 0.76


def test_token_metrics_use_thai_profile_and_never_zero_fill_insufficient_results() -> None:
    utterances = [
        Utterance(utterance_id="u1", speaker="SPK_01", text="หนูชอบ blue car", review_status="reviewed"),
        Utterance(utterance_id="u2", speaker="SPK_01", text="หนูชอบรถ", review_status="reviewed"),
    ]
    metrics = compute_descriptive_metrics(
        utterances,
        role_by_utterance={"u1": "target_child", "u2": "target_child"},
        audio_duration_ms=2000,
    )

    assert metrics["target_token_count"].value == 7
    assert metrics["number_of_different_words"].value == 5
    assert metrics["type_token_ratio"].status == "insufficient_data"
    assert metrics["type_token_ratio"].value is None
    assert metrics["mean_length_of_utterance_words"].status == "insufficient_data"
    assert metrics["mean_length_of_utterance_words"].value is None
