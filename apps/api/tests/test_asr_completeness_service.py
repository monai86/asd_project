from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.services.asr_completeness_service import (
    AsrCompletenessRules,
    AsrJobRuntimeProfile,
    AsrSegmentInterval,
    SpeechInterval,
    canonical_job_runtime_profile_checksum,
    evaluate_asr_completeness,
)


ASR_PROFILE_CHECKSUM = "1" * 64
BENCHMARK_CHECKSUM = "2" * 64
FIXTURE_CHECKSUM = "3" * 64


def _runtime_profile(**overrides: object) -> AsrJobRuntimeProfile:
    values: dict[str, object] = {
        "profile_id": "synthetic-runtime-v1",
        "profile_version": 1,
        "asr_profile_checksum_sha256": ASR_PROFILE_CHECKSUM,
        "benchmark_result_checksum_sha256": BENCHMARK_CHECKSUM,
        "fixture_manifest_checksum_sha256": FIXTURE_CHECKSUM,
        "timeout_seconds": 42,
        "completeness_rules": {
            "rule_version": "speech-completeness-v1.7.0",
            "beginning_anchor_max_delay_ms": 250,
            "ending_anchor_max_gap_ms": 250,
            "limitation_unexplained_gap_ms": 500,
            "blocker_unexplained_gap_ms": 1_500,
            "minimum_integrity_coverage_ratio": 0.75,
            "recommended_coverage_ratio": 0.90,
            "maximum_allowed_overlap_ms": 0,
        },
        "verified": True,
    }
    values.update(overrides)
    values["profile_checksum_sha256"] = (
        canonical_job_runtime_profile_checksum(values)
    )
    return AsrJobRuntimeProfile.model_validate(values)


def test_runtime_profile_requires_exact_canonical_checksum() -> None:
    profile = _runtime_profile()
    payload = profile.model_dump(mode="json")
    payload["timeout_seconds"] = 43

    with pytest.raises(
        ValidationError,
        match="runtime profile checksum does not match",
    ):
        AsrJobRuntimeProfile.model_validate(payload)


def test_runtime_profile_has_no_default_timeout_or_completeness_thresholds() -> None:
    fields = AsrJobRuntimeProfile.model_fields
    rules = AsrCompletenessRules.model_fields

    assert fields["timeout_seconds"].is_required()
    assert fields["completeness_rules"].is_required()
    for field_name in (
        "beginning_anchor_max_delay_ms",
        "ending_anchor_max_gap_ms",
        "limitation_unexplained_gap_ms",
        "blocker_unexplained_gap_ms",
        "minimum_integrity_coverage_ratio",
        "recommended_coverage_ratio",
        "maximum_allowed_overlap_ms",
    ):
        assert rules[field_name].is_required()


def test_complete_segments_report_exact_coverage_metrics() -> None:
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=100, end_ms=2_000),
            SpeechInterval(start_ms=8_000, end_ms=9_900),
        ),
        segment_intervals=(
            AsrSegmentInterval(
                segment_id="seg-1",
                start_ms=100,
                end_ms=2_000,
            ),
            AsrSegmentInterval(
                segment_id="seg-2",
                start_ms=8_000,
                end_ms=9_900,
            ),
        ),
        profile=_runtime_profile(),
    )

    assert result.status == "pass"
    assert result.rule_version == "speech-completeness-v1.7.0"
    assert result.beginning_coverage is True
    assert result.ending_coverage is True
    assert result.detected_speech_duration_ms == 3_800
    assert result.covered_speech_duration_ms == 3_800
    assert result.uncovered_speech_duration_ms == 0
    assert result.timestamp_coverage_ratio == 1.0
    assert result.unexplained_gaps == ()
    assert result.overlap_duration_ms == 0
    assert result.issues == ()


def test_leading_and_trailing_silence_do_not_fail_speech_anchors() -> None:
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=2_000, end_ms=8_000),
        ),
        segment_intervals=(
            AsrSegmentInterval(
                segment_id="speech-only",
                start_ms=2_100,
                end_ms=7_900,
            ),
        ),
        profile=_runtime_profile(),
    )

    assert result.beginning_coverage is True
    assert result.ending_coverage is True
    assert "beginning_speech_anchor_missing" not in {
        item.code for item in result.issues
    }
    assert "ending_speech_anchor_missing" not in {
        item.code for item in result.issues
    }


def test_multi_interval_anchors_use_first_and_last_detected_speech() -> None:
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=2_000, end_ms=3_000),
            SpeechInterval(start_ms=7_000, end_ms=8_000),
        ),
        segment_intervals=(
            AsrSegmentInterval(
                segment_id="first",
                start_ms=2_100,
                end_ms=3_000,
            ),
            AsrSegmentInterval(
                segment_id="last",
                start_ms=7_000,
                end_ms=7_900,
            ),
        ),
        profile=_runtime_profile(),
    )

    assert result.beginning_coverage is True
    assert result.ending_coverage is True


@pytest.mark.parametrize(
    ("segments", "expected_code", "expected_id"),
    [
        (
            (
                AsrSegmentInterval(
                    segment_id="reversed",
                    start_ms=1_000,
                    end_ms=500,
                ),
            ),
            "timestamp_order_invalid",
            "reversed",
        ),
        (
            (
                AsrSegmentInterval(
                    segment_id="out-of-range",
                    start_ms=9_000,
                    end_ms=10_100,
                ),
            ),
            "timestamp_range_invalid",
            "out-of-range",
        ),
        (
            (
                AsrSegmentInterval(
                    segment_id="missing",
                    start_ms=None,
                    end_ms=None,
                ),
            ),
            "timestamp_missing",
            "missing",
        ),
    ],
)
def test_invalid_segment_timestamps_are_integrity_blockers(
    segments: tuple[AsrSegmentInterval, ...],
    expected_code: str,
    expected_id: str,
) -> None:
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=100, end_ms=9_900),
        ),
        segment_intervals=segments,
        profile=_runtime_profile(),
    )

    assert result.status == "blocked"
    issue = next(item for item in result.issues if item.code == expected_code)
    assert issue.disposition == "integrity_blocker"
    assert issue.segment_ids == (expected_id,)


def test_provider_segment_sequence_cannot_move_backward_before_union() -> None:
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=1_000, end_ms=6_000),
        ),
        segment_intervals=(
            AsrSegmentInterval(
                segment_id="listed-first",
                start_ms=5_000,
                end_ms=6_000,
            ),
            AsrSegmentInterval(
                segment_id="moves-backward",
                start_ms=1_000,
                end_ms=5_000,
            ),
        ),
        profile=_runtime_profile(),
    )

    assert result.status == "blocked"
    issue = next(
        item
        for item in result.issues
        if item.code == "timestamp_sequence_order_invalid"
    )
    assert issue.disposition == "integrity_blocker"
    assert issue.segment_ids == ("moves-backward",)
    assert result.overlap_duration_ms == 0


@pytest.mark.parametrize(
    ("segments", "expected_code"),
    [
        (
            (
                AsrSegmentInterval(
                    segment_id="late",
                    start_ms=500,
                    end_ms=9_900,
                ),
            ),
            "beginning_speech_anchor_missing",
        ),
        (
            (
                AsrSegmentInterval(
                    segment_id="early",
                    start_ms=100,
                    end_ms=9_500,
                ),
            ),
            "ending_speech_anchor_missing",
        ),
    ],
)
def test_missing_beginning_or_ending_speech_anchor_is_blocking(
    segments: tuple[AsrSegmentInterval, ...],
    expected_code: str,
) -> None:
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=100, end_ms=9_900),
        ),
        segment_intervals=segments,
        profile=_runtime_profile(),
    )

    assert result.status == "blocked"
    assert expected_code in {item.code for item in result.issues}


def test_structurally_safe_gap_is_an_acknowledgeable_limitation() -> None:
    profile = _runtime_profile(
        completeness_rules={
            "rule_version": "speech-completeness-v1.7.0",
            "beginning_anchor_max_delay_ms": 250,
            "ending_anchor_max_gap_ms": 250,
            "limitation_unexplained_gap_ms": 500,
            "blocker_unexplained_gap_ms": 2_000,
            "minimum_integrity_coverage_ratio": 0.70,
            "recommended_coverage_ratio": 0.95,
            "maximum_allowed_overlap_ms": 0,
        }
    )
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=100, end_ms=9_900),
        ),
        segment_intervals=(
            AsrSegmentInterval(
                segment_id="seg-1",
                start_ms=100,
                end_ms=4_400,
            ),
            AsrSegmentInterval(
                segment_id="seg-2",
                start_ms=5_200,
                end_ms=9_900,
            ),
        ),
        profile=profile,
    )

    assert result.status == "limitation"
    assert result.unexplained_gaps == (
        SpeechInterval(start_ms=4_400, end_ms=5_200),
    )
    issue = next(
        item
        for item in result.issues
        if item.code == "timestamp_coverage_below_recommended"
    )
    assert issue.disposition == "acknowledgeable_limitation"
    assert issue.rule_version == profile.completeness_rules.rule_version


def test_gap_or_coverage_below_integrity_minimum_is_blocking() -> None:
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=100, end_ms=9_900),
        ),
        segment_intervals=(
            AsrSegmentInterval(
                segment_id="seg-1",
                start_ms=100,
                end_ms=1_000,
            ),
            AsrSegmentInterval(
                segment_id="seg-2",
                start_ms=4_000,
                end_ms=9_900,
            ),
        ),
        profile=_runtime_profile(),
    )

    assert result.status == "blocked"
    codes = {item.code for item in result.issues}
    assert "unexplained_timestamp_gap_blocking" in codes
    assert "timestamp_coverage_below_integrity_minimum" in codes


def test_overlapping_segments_are_blocked_by_the_selected_rule() -> None:
    result = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=100, end_ms=9_900),
        ),
        segment_intervals=(
            AsrSegmentInterval(
                segment_id="seg-1",
                start_ms=100,
                end_ms=5_100,
            ),
            AsrSegmentInterval(
                segment_id="seg-2",
                start_ms=5_000,
                end_ms=9_900,
            ),
        ),
        profile=_runtime_profile(),
    )

    assert result.status == "blocked"
    assert result.overlap_duration_ms == 100
    assert "timestamp_overlap_invalid" in {
        item.code for item in result.issues
    }


def test_empty_and_provider_reported_partial_results_are_not_complete() -> None:
    empty = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=100, end_ms=9_900),
        ),
        segment_intervals=(),
        profile=_runtime_profile(),
    )
    partial = evaluate_asr_completeness(
        audio_duration_ms=10_000,
        detected_speech_intervals=(
            SpeechInterval(start_ms=100, end_ms=9_900),
        ),
        segment_intervals=(
            AsrSegmentInterval(
                segment_id="seg-1",
                start_ms=100,
                end_ms=9_900,
            ),
        ),
        profile=_runtime_profile(),
        provider_reported_partial=True,
    )

    assert empty.status == "blocked"
    assert empty.issues[0].code == "asr_empty_result"
    assert partial.status == "blocked"
    assert "provider_partial_result" in {
        item.code for item in partial.issues
    }


def test_profile_copy_with_changed_rules_requires_a_new_checksum() -> None:
    payload = _runtime_profile().model_dump(mode="json")
    changed = deepcopy(payload)
    changed["completeness_rules"]["blocker_unexplained_gap_ms"] = 1_501

    with pytest.raises(ValidationError):
        AsrJobRuntimeProfile.model_validate(changed)
