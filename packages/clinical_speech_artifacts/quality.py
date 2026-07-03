"""Engineering quality metrics for ASR draft versus reviewed CHAT files."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from packages.cha.parser import ParsedChaTranscript
from packages.features import extract_transcript_features


QUALITY_SCHEMA_VERSION = "clinical-speech-quality-v1"


def build_quality_report(
    *,
    asr_draft: ParsedChaTranscript,
    reviewed: ParsedChaTranscript,
) -> dict[str, Any]:
    """Compare an ASR draft with a reviewed transcript.

    These metrics are engineering QA signals only. They measure review burden
    and drift, not clinical validity.
    """
    draft_tokens = _transcript_tokens(asr_draft)
    reviewed_tokens = _transcript_tokens(reviewed)
    draft_chars = list(_transcript_text(asr_draft).replace(" ", ""))
    reviewed_chars = list(_transcript_text(reviewed).replace(" ", ""))
    draft_speakers = [utterance.speaker_code for utterance in asr_draft.utterances]
    reviewed_speakers = [utterance.speaker_code for utterance in reviewed.utterances]
    line_edits = _line_edit_summary(asr_draft, reviewed)

    draft_features = extract_transcript_features(asr_draft)["canonical_features"]
    reviewed_features = extract_transcript_features(reviewed)["canonical_features"]
    feature_drift = _feature_drift(draft_features, reviewed_features)

    return {
        "schema_version": QUALITY_SCHEMA_VERSION,
        "source": "asr_draft_vs_reviewed_transcript",
        "safety_labels": [
            "engineering quality assurance only",
            "does not diagnose ASD",
            "reviewed transcript remains source of truth",
        ],
        "summary": {
            "wer": _error_rate(draft_tokens, reviewed_tokens),
            "cer": _error_rate(draft_chars, reviewed_chars),
            "speaker_label_accuracy": _speaker_accuracy(draft_speakers, reviewed_speakers),
            "utterance_count_draft": len(asr_draft.utterances),
            "utterance_count_reviewed": len(reviewed.utterances),
            "utterance_count_delta": len(asr_draft.utterances) - len(reviewed.utterances),
            "feature_drift_mean_abs": _mean_abs_feature_drift(feature_drift),
            "line_edit_rate": line_edits["line_edit_rate"],
        },
        "line_edit_summary": line_edits,
        "feature_drift": feature_drift,
        "warnings": _quality_warnings(
            asr_draft=asr_draft,
            reviewed=reviewed,
            speaker_count_compared=min(len(draft_speakers), len(reviewed_speakers)),
        ),
    }


def _line_edit_summary(
    asr_draft: ParsedChaTranscript,
    reviewed: ParsedChaTranscript,
) -> dict[str, Any]:
    comparable = min(len(asr_draft.utterances), len(reviewed.utterances))
    text_changed = 0
    speaker_changed = 0
    timing_changed = 0
    changed_lines: list[dict[str, Any]] = []

    for index in range(comparable):
        draft = asr_draft.utterances[index]
        review = reviewed.utterances[index]
        text_is_changed = draft.normalized_text != review.normalized_text
        speaker_is_changed = draft.speaker_code != review.speaker_code
        timing_is_changed = (
            draft.start_ms != review.start_ms
            or draft.end_ms != review.end_ms
        )
        if text_is_changed:
            text_changed += 1
        if speaker_is_changed:
            speaker_changed += 1
        if timing_is_changed:
            timing_changed += 1
        if text_is_changed or speaker_is_changed or timing_is_changed:
            changed_lines.append(
                {
                    "position": index + 1,
                    "draft_line_number": draft.line_number,
                    "reviewed_line_number": review.line_number,
                    "speaker_changed": speaker_is_changed,
                    "text_changed": text_is_changed,
                    "timing_changed": timing_is_changed,
                    "draft_speaker": draft.speaker_code,
                    "reviewed_speaker": review.speaker_code,
                    "draft_text": draft.normalized_text,
                    "reviewed_text": review.normalized_text,
                }
            )

    inserted_or_deleted = abs(len(asr_draft.utterances) - len(reviewed.utterances))
    changed_count = len(changed_lines) + inserted_or_deleted
    denominator = max(len(reviewed.utterances), 1)
    return {
        "comparable_line_count": comparable,
        "draft_line_count": len(asr_draft.utterances),
        "reviewed_line_count": len(reviewed.utterances),
        "changed_line_count": changed_count,
        "line_edit_rate": round(changed_count / denominator, 4),
        "text_changed_count": text_changed,
        "speaker_changed_count": speaker_changed,
        "timing_changed_count": timing_changed,
        "inserted_or_deleted_line_count": inserted_or_deleted,
        "changed_lines": changed_lines,
    }


def _transcript_text(transcript: ParsedChaTranscript) -> str:
    return " ".join(utterance.normalized_text for utterance in transcript.utterances)


def _transcript_tokens(transcript: ParsedChaTranscript) -> list[str]:
    tokens: list[str] = []
    for utterance in transcript.utterances:
        tokens.extend(utterance.tokens)
    return tokens


def _error_rate(hypothesis: Sequence[str], reference: Sequence[str]) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return round(_levenshtein(hypothesis, reference) / len(reference), 4)


def _levenshtein(left: Sequence[str], right: Sequence[str]) -> int:
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for left_index, left_item in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_item in enumerate(right, start=1):
            substitution_cost = 0 if left_item == right_item else 1
            current.append(
                min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]


def _speaker_accuracy(draft: Sequence[str], reviewed: Sequence[str]) -> float | None:
    compared = min(len(draft), len(reviewed))
    if compared == 0:
        return None
    matches = sum(1 for index in range(compared) if draft[index] == reviewed[index])
    return round(matches / compared, 4)


def _feature_drift(
    draft_features: dict[str, Any],
    reviewed_features: dict[str, Any],
) -> dict[str, dict[str, float | int]]:
    drift: dict[str, dict[str, float | int]] = {}
    for name in sorted(set(draft_features) | set(reviewed_features)):
        draft_value = _to_float(draft_features.get(name))
        reviewed_value = _to_float(reviewed_features.get(name))
        absolute_delta = round(draft_value - reviewed_value, 4)
        relative_delta = (
            round(absolute_delta / reviewed_value, 4)
            if reviewed_value not in {0.0, -0.0}
            else 0.0
        )
        drift[name] = {
            "draft": draft_value,
            "reviewed": reviewed_value,
            "absolute_delta": absolute_delta,
            "relative_delta": relative_delta,
        }
    return drift


def _mean_abs_feature_drift(feature_drift: dict[str, dict[str, float | int]]) -> float:
    values = [abs(float(row["absolute_delta"])) for row in feature_drift.values()]
    return round(sum(values) / len(values), 4) if values else 0.0


def _to_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if number != number:
        return 0.0
    return round(number, 4)


def _quality_warnings(
    *,
    asr_draft: ParsedChaTranscript,
    reviewed: ParsedChaTranscript,
    speaker_count_compared: int,
) -> list[str]:
    warnings: list[str] = []
    if len(asr_draft.utterances) != len(reviewed.utterances):
        warnings.append(
            "Utterance counts differ; speaker accuracy is position-aligned and approximate."
        )
    if speaker_count_compared == 0:
        warnings.append("No comparable speaker labels were available.")
    return warnings
