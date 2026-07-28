"""Evidence-bound ASR completeness checks for the v1.7.0 testbed.

The module deliberately has no timeout, coverage, gap, or overlap defaults.
Every decision is bound to one immutable benchmark/runtime profile.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Literal, Mapping, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


_SHA256_PATTERN = r"^[a-f0-9]{64}$"


class _FrozenContract(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    def model_copy(
        self,
        *,
        update: Mapping[str, object] | None = None,
        deep: bool = False,
    ) -> Self:
        values = {
            field_name: getattr(self, field_name)
            for field_name in type(self).model_fields
        }
        if update:
            values.update(update)
        return type(self).model_validate(values)


class SpeechInterval(_FrozenContract):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_order(self) -> "SpeechInterval":
        if self.end_ms < self.start_ms:
            raise ValueError("speech interval end must not precede start")
        return self


class AsrSegmentInterval(_FrozenContract):
    """Raw segment timing evidence.

    Ordering is intentionally not validated here because the completeness
    evaluator must classify malformed provider timestamps as typed blockers.
    """

    segment_id: str = Field(min_length=1, max_length=256)
    start_ms: int | None = None
    end_ms: int | None = None


class AsrCompletenessRules(_FrozenContract):
    rule_version: str = Field(min_length=1, max_length=128)
    beginning_anchor_max_delay_ms: int = Field(ge=0)
    ending_anchor_max_gap_ms: int = Field(ge=0)
    limitation_unexplained_gap_ms: int = Field(gt=0)
    blocker_unexplained_gap_ms: int = Field(gt=0)
    minimum_integrity_coverage_ratio: float = Field(
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    recommended_coverage_ratio: float = Field(
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    maximum_allowed_overlap_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_escalation_order(self) -> "AsrCompletenessRules":
        if (
            self.limitation_unexplained_gap_ms
            >= self.blocker_unexplained_gap_ms
        ):
            raise ValueError(
                "limitation gap threshold must be below blocker threshold"
            )
        if (
            self.minimum_integrity_coverage_ratio
            > self.recommended_coverage_ratio
        ):
            raise ValueError(
                "integrity coverage minimum must not exceed recommendation"
            )
        return self


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return _json_value(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def canonical_job_runtime_profile_checksum(
    profile: Mapping[str, object],
) -> str:
    material = {
        key: _json_value(value)
        for key, value in profile.items()
        if key != "profile_checksum_sha256"
    }
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class AsrJobRuntimeProfile(_FrozenContract):
    profile_id: str = Field(min_length=1, max_length=128)
    profile_version: int = Field(ge=1)
    profile_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=_SHA256_PATTERN,
    )
    asr_profile_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=_SHA256_PATTERN,
    )
    benchmark_result_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=_SHA256_PATTERN,
    )
    fixture_manifest_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=_SHA256_PATTERN,
    )
    timeout_seconds: int = Field(gt=0)
    completeness_rules: AsrCompletenessRules
    verified: Literal[True]

    @model_validator(mode="after")
    def validate_checksum(self) -> "AsrJobRuntimeProfile":
        if (
            canonical_job_runtime_profile_checksum(
                self.model_dump(mode="json")
            )
            != self.profile_checksum_sha256
        ):
            raise ValueError(
                "runtime profile checksum does not match canonical profile"
            )
        return self


class AsrCompletenessIssue(_FrozenContract):
    code: str = Field(min_length=1, max_length=128)
    disposition: Literal[
        "integrity_blocker",
        "acknowledgeable_limitation",
    ]
    severity: Literal["error", "warning"]
    rule_version: str
    segment_ids: tuple[str, ...] = ()
    actual_value: int | float | None = None
    configured_threshold: int | float | None = None
    unit: str | None = None
    remediation: str


class AsrCompletenessResult(_FrozenContract):
    status: Literal["pass", "limitation", "blocked"]
    rule_version: str
    detected_speech_intervals: tuple[SpeechInterval, ...]
    segment_intervals: tuple[AsrSegmentInterval, ...]
    beginning_coverage: bool
    ending_coverage: bool
    detected_speech_duration_ms: int
    covered_speech_duration_ms: int
    uncovered_speech_duration_ms: int
    timestamp_coverage_ratio: float | None
    unexplained_gaps: tuple[SpeechInterval, ...]
    overlap_duration_ms: int
    reversed_segment_ids: tuple[str, ...]
    out_of_range_segment_ids: tuple[str, ...]
    missing_timestamp_segment_ids: tuple[str, ...]
    provider_reported_partial: bool
    issues: tuple[AsrCompletenessIssue, ...]


def _merge_intervals(
    intervals: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    if not intervals:
        return []
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _duration(intervals: list[tuple[int, int]]) -> int:
    return sum(end - start for start, end in intervals)


def _intersections(
    left: list[tuple[int, int]],
    right: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    intersections: list[tuple[int, int]] = []
    left_index = 0
    right_index = 0
    while left_index < len(left) and right_index < len(right):
        left_start, left_end = left[left_index]
        right_start, right_end = right[right_index]
        start = max(left_start, right_start)
        end = min(left_end, right_end)
        if end > start:
            intersections.append((start, end))
        if left_end <= right_end:
            left_index += 1
        else:
            right_index += 1
    return _merge_intervals(intersections)


def _subtract_intervals(
    sources: list[tuple[int, int]],
    coverage: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    uncovered: list[tuple[int, int]] = []
    for source_start, source_end in sources:
        cursor = source_start
        for coverage_start, coverage_end in coverage:
            if coverage_end <= cursor:
                continue
            if coverage_start >= source_end:
                break
            if coverage_start > cursor:
                uncovered.append(
                    (cursor, min(coverage_start, source_end))
                )
            cursor = max(cursor, coverage_end)
            if cursor >= source_end:
                break
        if cursor < source_end:
            uncovered.append((cursor, source_end))
    return [
        (start, end)
        for start, end in uncovered
        if end > start
    ]


def _blocker(
    *,
    code: str,
    rule_version: str,
    remediation: str,
    segment_ids: tuple[str, ...] = (),
    actual_value: int | float | None = None,
    threshold: int | float | None = None,
    unit: str | None = None,
) -> AsrCompletenessIssue:
    return AsrCompletenessIssue(
        code=code,
        disposition="integrity_blocker",
        severity="error",
        rule_version=rule_version,
        segment_ids=segment_ids,
        actual_value=actual_value,
        configured_threshold=threshold,
        unit=unit,
        remediation=remediation,
    )


def _limitation(
    *,
    code: str,
    rule_version: str,
    remediation: str,
    actual_value: int | float | None = None,
    threshold: int | float | None = None,
    unit: str | None = None,
) -> AsrCompletenessIssue:
    return AsrCompletenessIssue(
        code=code,
        disposition="acknowledgeable_limitation",
        severity="warning",
        rule_version=rule_version,
        actual_value=actual_value,
        configured_threshold=threshold,
        unit=unit,
        remediation=remediation,
    )


def evaluate_asr_completeness(
    *,
    audio_duration_ms: int,
    detected_speech_intervals: tuple[SpeechInterval, ...],
    segment_intervals: tuple[AsrSegmentInterval, ...],
    profile: AsrJobRuntimeProfile,
    provider_reported_partial: bool = False,
) -> AsrCompletenessResult:
    """Evaluate timestamp integrity without inventing missing evidence."""

    if audio_duration_ms <= 0:
        raise ValueError("audio_duration_ms must be positive")
    profile = AsrJobRuntimeProfile.model_validate(
        profile.model_dump(mode="json")
    )
    rules = profile.completeness_rules
    rule_version = rules.rule_version
    issues: list[AsrCompletenessIssue] = []

    if not segment_intervals:
        issues.append(
            _blocker(
                code="asr_empty_result",
                rule_version=rule_version,
                remediation=(
                    "Retry real transcription after verifying the exact "
                    "audio and runtime profile."
                ),
            )
        )
    if provider_reported_partial:
        issues.append(
            _blocker(
                code="provider_partial_result",
                rule_version=rule_version,
                remediation=(
                    "Retry the failed provider attempt; do not represent a "
                    "provider-reported partial result as complete."
                ),
            )
        )

    missing_ids: list[str] = []
    reversed_ids: list[str] = []
    out_of_range_ids: list[str] = []
    sequence_order_ids: list[str] = []
    valid_segments: list[tuple[int, int]] = []
    previous_sequence_key: tuple[int, int] | None = None
    for segment in segment_intervals:
        if segment.start_ms is None or segment.end_ms is None:
            missing_ids.append(segment.segment_id)
            continue
        if segment.end_ms < segment.start_ms:
            reversed_ids.append(segment.segment_id)
            continue
        if (
            segment.start_ms < 0
            or segment.end_ms > audio_duration_ms
        ):
            out_of_range_ids.append(segment.segment_id)
            continue
        sequence_key = (segment.start_ms, segment.end_ms)
        if (
            previous_sequence_key is not None
            and sequence_key < previous_sequence_key
        ):
            sequence_order_ids.append(segment.segment_id)
        previous_sequence_key = sequence_key
        valid_segments.append((segment.start_ms, segment.end_ms))

    if missing_ids:
        issues.append(
            _blocker(
                code="timestamp_missing",
                rule_version=rule_version,
                segment_ids=tuple(missing_ids),
                remediation="Regenerate or review every segment timestamp.",
            )
        )
    if reversed_ids:
        issues.append(
            _blocker(
                code="timestamp_order_invalid",
                rule_version=rule_version,
                segment_ids=tuple(reversed_ids),
                remediation="Regenerate reversed segment timestamps.",
            )
        )
    if out_of_range_ids:
        issues.append(
            _blocker(
                code="timestamp_range_invalid",
                rule_version=rule_version,
                segment_ids=tuple(out_of_range_ids),
                remediation=(
                    "Regenerate timestamps within the verified audio duration."
                ),
            )
        )
    if sequence_order_ids:
        issues.append(
            _blocker(
                code="timestamp_sequence_order_invalid",
                rule_version=rule_version,
                segment_ids=tuple(sequence_order_ids),
                remediation=(
                    "Regenerate provider segments in canonical chronological "
                    "order before transcript review."
                ),
            )
        )

    detected = _merge_intervals(
        [
            (interval.start_ms, interval.end_ms)
            for interval in detected_speech_intervals
        ]
    )
    segment_union = _merge_intervals(valid_segments)
    detected_duration = _duration(detected)
    covered = _intersections(detected, segment_union)
    covered_duration = _duration(covered)
    uncovered = _subtract_intervals(detected, segment_union)
    uncovered_duration = _duration(uncovered)
    coverage_ratio = (
        covered_duration / detected_duration
        if detected_duration > 0
        else None
    )
    raw_segment_duration = _duration(valid_segments)
    overlap_duration = max(
        0,
        raw_segment_duration - _duration(segment_union),
    )

    if not detected:
        beginning_coverage = False
        ending_coverage = False
        issues.append(
            _blocker(
                code="speech_detection_evidence_missing",
                rule_version=rule_version,
                remediation=(
                    "Provide version-bound detected-speech evidence before "
                    "accepting transcript completeness."
                ),
            )
        )
    elif not segment_union:
        beginning_coverage = False
        ending_coverage = False
    else:
        beginning_coverage = (
            segment_union[0][0] - detected[0][0]
            <= rules.beginning_anchor_max_delay_ms
            and segment_union[0][1] > detected[0][0]
        )
        ending_coverage = (
            detected[-1][1] - segment_union[-1][1]
            <= rules.ending_anchor_max_gap_ms
            and segment_union[-1][0] < detected[-1][1]
        )

    if detected and not beginning_coverage:
        actual_delay = (
            max(0, segment_union[0][0] - detected[0][0])
            if segment_union
            else detected_duration
        )
        issues.append(
            _blocker(
                code="beginning_speech_anchor_missing",
                rule_version=rule_version,
                actual_value=actual_delay,
                threshold=rules.beginning_anchor_max_delay_ms,
                unit="milliseconds",
                remediation=(
                    "Regenerate or review the beginning of the transcript."
                ),
            )
        )
    if detected and not ending_coverage:
        actual_gap = (
            max(0, detected[-1][1] - segment_union[-1][1])
            if segment_union
            else detected_duration
        )
        issues.append(
            _blocker(
                code="ending_speech_anchor_missing",
                rule_version=rule_version,
                actual_value=actual_gap,
                threshold=rules.ending_anchor_max_gap_ms,
                unit="milliseconds",
                remediation="Regenerate or review the end of the transcript.",
            )
        )

    for start, end in uncovered:
        gap_duration = end - start
        if gap_duration >= rules.blocker_unexplained_gap_ms:
            issues.append(
                _blocker(
                    code="unexplained_timestamp_gap_blocking",
                    rule_version=rule_version,
                    actual_value=gap_duration,
                    threshold=rules.blocker_unexplained_gap_ms,
                    unit="milliseconds",
                    remediation=(
                        "Review and repair the uncovered detected-speech interval."
                    ),
                )
            )
        elif gap_duration >= rules.limitation_unexplained_gap_ms:
            issues.append(
                _limitation(
                    code="unexplained_timestamp_gap_limited",
                    rule_version=rule_version,
                    actual_value=gap_duration,
                    threshold=rules.limitation_unexplained_gap_ms,
                    unit="milliseconds",
                    remediation=(
                        "Review the structurally valid uncovered interval and "
                        "acknowledge the version-bound limitation."
                    ),
                )
            )

    if coverage_ratio is not None:
        if coverage_ratio < rules.minimum_integrity_coverage_ratio:
            issues.append(
                _blocker(
                    code="timestamp_coverage_below_integrity_minimum",
                    rule_version=rule_version,
                    actual_value=coverage_ratio,
                    threshold=rules.minimum_integrity_coverage_ratio,
                    unit="ratio",
                    remediation=(
                        "Repair transcript timestamps until source speech can "
                        "be represented reliably."
                    ),
                )
            )
        elif coverage_ratio < rules.recommended_coverage_ratio:
            issues.append(
                _limitation(
                    code="timestamp_coverage_below_recommended",
                    rule_version=rule_version,
                    actual_value=coverage_ratio,
                    threshold=rules.recommended_coverage_ratio,
                    unit="ratio",
                    remediation=(
                        "Review and acknowledge the current version-bound "
                        "coverage limitation."
                    ),
                )
            )

    if overlap_duration > rules.maximum_allowed_overlap_ms:
        issues.append(
            _blocker(
                code="timestamp_overlap_invalid",
                rule_version=rule_version,
                actual_value=overlap_duration,
                threshold=rules.maximum_allowed_overlap_ms,
                unit="milliseconds",
                remediation=(
                    "Repair overlapping ASR segment timestamps before review."
                ),
            )
        )

    if any(
        issue.disposition == "integrity_blocker"
        for issue in issues
    ):
        status: Literal["pass", "limitation", "blocked"] = "blocked"
    elif issues:
        status = "limitation"
    else:
        status = "pass"

    return AsrCompletenessResult(
        status=status,
        rule_version=rule_version,
        detected_speech_intervals=tuple(
            SpeechInterval(start_ms=start, end_ms=end)
            for start, end in detected
        ),
        segment_intervals=segment_intervals,
        beginning_coverage=beginning_coverage,
        ending_coverage=ending_coverage,
        detected_speech_duration_ms=detected_duration,
        covered_speech_duration_ms=covered_duration,
        uncovered_speech_duration_ms=uncovered_duration,
        timestamp_coverage_ratio=coverage_ratio,
        unexplained_gaps=tuple(
            SpeechInterval(start_ms=start, end_ms=end)
            for start, end in uncovered
        ),
        overlap_duration_ms=overlap_duration,
        reversed_segment_ids=tuple(reversed_ids),
        out_of_range_segment_ids=tuple(out_of_range_ids),
        missing_timestamp_segment_ids=tuple(missing_ids),
        provider_reported_partial=provider_reported_partial,
        issues=tuple(issues),
    )
