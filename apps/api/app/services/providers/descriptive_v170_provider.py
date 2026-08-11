"""Deterministic descriptive speech metrics for the v1.7.0 testbed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256

from app.schemas.clinical import Utterance
from app.schemas.speech_pipeline import FeatureResult, FeatureResultStatus, TokenizerProfileReference
from app.services.tokenizer_service import TokenizerUnavailable, load_tokenizer_profile, tokenize_v170


FEATURE_SCHEMA_VERSION = "descriptive-features-v1.7.0"
ALGORITHM_VERSION = "descriptive-feature-algorithm-v1.7.0"
CONFIGURATION_VERSION = "descriptive-feature-config-v1.7.0"


@dataclass(frozen=True)
class MetricDraft:
    status: FeatureResultStatus
    value: float | int | None
    unit: str
    numerator: float | int | None = None
    denominator: float | int | None = None
    minimum_sample: int | None = None
    reason_code: str | None = None
    remediation: str | None = None
    excluded_item_counts: dict[str, int] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()


def _covered_duration(intervals: list[tuple[int, int]]) -> int:
    if not intervals:
        return 0
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if start < 0 or end <= start:
            continue
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)


def compute_descriptive_metrics(
    utterances: list[Utterance],
    *,
    role_by_utterance: dict[str, str],
    audio_duration_ms: int,
) -> dict[str, MetricDraft]:
    reviewed = [item for item in utterances if str(item.review_status).lower() in {"reviewed", "attested"}]
    target = [item for item in reviewed if role_by_utterance.get(item.utterance_id) in {"target", "target_child", "child"}]
    therapist = [item for item in reviewed if role_by_utterance.get(item.utterance_id) in {"therapist", "investigator"}]
    roles = [role_by_utterance.get(item.utterance_id, "unknown") for item in reviewed]
    turns = sum(1 for index, role in enumerate(roles) if index == 0 or role != roles[index - 1])
    intervals = [
        (item.start_ms, item.end_ms)
        for item in reviewed
        if item.start_ms is not None and item.end_ms is not None
    ]
    covered_ms = min(_covered_duration(intervals), audio_duration_ms)
    eligible_intelligibility = len(reviewed)
    unintelligible = sum(1 for item in reviewed if item.unintelligible)
    metrics = {
        "total_utterance_count": MetricDraft(FeatureResultStatus.available, len(reviewed), "utterances", len(reviewed), len(reviewed)),
        "child_utterance_count": MetricDraft(FeatureResultStatus.available, len(target), "utterances", len(target), len(reviewed)),
        "therapist_utterance_count": MetricDraft(FeatureResultStatus.available, len(therapist), "utterances", len(therapist), len(reviewed)),
        "turn_count": MetricDraft(FeatureResultStatus.available, turns, "turns", turns, len(reviewed)),
        "audio_duration_ms": MetricDraft(FeatureResultStatus.available, audio_duration_ms, "milliseconds", audio_duration_ms, audio_duration_ms),
        "timestamp_coverage": MetricDraft(FeatureResultStatus.available, round(covered_ms / audio_duration_ms, 6), "ratio", covered_ms, audio_duration_ms),
        "unintelligible_ratio": MetricDraft(
            FeatureResultStatus.available,
            round(unintelligible / eligible_intelligibility, 6) if eligible_intelligibility else 0,
            "ratio",
            unintelligible,
            eligible_intelligibility,
            limitations=("Uses therapist-reviewed intelligibility annotations, never ASR confidence.",),
        ),
    }
    try:
        token_lists = [tokenize_v170(item.text) for item in target if not item.unintelligible]
        tokens = [token for item in token_lists for token in item]
        unique = set(tokens)
        complete_target_count = len(token_lists)
        metrics.update(
            {
                "target_token_count": MetricDraft(FeatureResultStatus.available, len(tokens), "tokens", len(tokens), len(tokens)),
                "number_of_different_words": MetricDraft(FeatureResultStatus.available, len(unique), "tokens", len(unique), len(tokens)),
                "type_token_ratio": MetricDraft(
                    FeatureResultStatus.available if len(tokens) >= 50 else FeatureResultStatus.insufficient_data,
                    round(len(unique) / len(tokens), 6) if len(tokens) >= 50 else None,
                    "ratio", len(unique), len(tokens), 50,
                    None if len(tokens) >= 50 else "MINIMUM_TARGET_TOKENS_NOT_MET",
                    None if len(tokens) >= 50 else "Collect or review a larger target-speaker language sample.",
                ),
                "mean_length_of_utterance_words": MetricDraft(
                    FeatureResultStatus.available if complete_target_count >= 50 else FeatureResultStatus.insufficient_data,
                    round(len(tokens) / complete_target_count, 6) if complete_target_count >= 50 else None,
                    "tokens per utterance", len(tokens), complete_target_count, 50,
                    None if complete_target_count >= 50 else "MINIMUM_COMPLETE_TARGET_UTTERANCES_NOT_MET",
                    None if complete_target_count >= 50 else "Collect or review at least 50 complete target-speaker utterances.",
                ),
            }
        )
    except TokenizerUnavailable:
        for feature_id, unit in (
            ("target_token_count", "tokens"),
            ("number_of_different_words", "tokens"),
            ("type_token_ratio", "ratio"),
            ("mean_length_of_utterance_words", "tokens per utterance"),
        ):
            metrics[feature_id] = MetricDraft(
                FeatureResultStatus.unavailable,
                None,
                unit,
                reason_code="TOKENIZER_PROFILE_UNAVAILABLE",
                remediation="Install and verify the tokenizer profile recorded for this feature schema.",
            )
    return metrics


def extract_descriptive_feature_results(repo, transcript_id: str) -> list[FeatureResult]:
    transcript = repo.transcripts[transcript_id]
    mapping = repo.get_current_speaker_mapping(transcript_id)
    attestation = repo.get_current_transcript_attestation(transcript_id)
    chat_export = repo.get_current_chat_export(transcript_id)
    if mapping is None or mapping.transcript_version != transcript.version:
        raise ValueError("SPEAKER_MAPPING_STALE: deterministic features require current mapping.")
    if attestation is None or attestation.transcript_version != transcript.version:
        raise ValueError("ATTESTATION_VERSION_STALE: deterministic features require current attestation.")
    if chat_export is None or chat_export.transcript_version != transcript.version or chat_export.round_trip.status.value != "verified":
        raise ValueError("CHAT_ROUND_TRIP_FAILED: deterministic features require a current verified CHAT export.")
    audio = next(
        (
            item for item in repo.audio_files.values()
            if item.audio_file_id == chat_export.source_audio_file_id
            and item.source_asset_version == chat_export.source_asset_version
        ),
        None,
    )
    normalized = repo.get_current_normalized_audio_asset(chat_export.source_audio_file_id)
    if audio is None or normalized is None or normalized.asset_version != chat_export.normalized_asset_version:
        raise ValueError("AUDIO_LINEAGE_MISMATCH: deterministic feature inputs are not current.")
    role_by_utterance: dict[str, str] = {}
    for entry in mapping.entries:
        for utterance_id in entry.affected_utterance_ids:
            role_by_utterance[utterance_id] = entry.participant_role
    metrics = compute_descriptive_metrics(
        transcript.utterances,
        role_by_utterance=role_by_utterance,
        audio_duration_ms=normalized.duration_ms,
    )
    try:
        profile = load_tokenizer_profile()
        tokenizer_reference = TokenizerProfileReference(
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            profile_checksum_sha256=profile.profile_checksum_sha256,
            engine=profile.engine,
            package_version=profile.package_version,
            artifact_id=profile.artifact_id,
            artifact_checksum_sha256=profile.artifact_checksum_sha256,
            custom_vocabulary_version=profile.custom_vocabulary_version,
            custom_vocabulary_checksum_sha256=profile.custom_vocabulary_checksum_sha256,
        )
    except TokenizerUnavailable:
        tokenizer_reference = None
    generated_at = datetime.now(timezone.utc)
    algorithm_checksum = sha256(f"{ALGORITHM_VERSION}:{CONFIGURATION_VERSION}".encode()).hexdigest()
    return [
        FeatureResult(
            feature_id=feature_id,
            feature_version=1,
            status=metric.status,
            value=metric.value,
            unit=metric.unit,
            numerator=metric.numerator,
            denominator=metric.denominator,
            minimum_sample=metric.minimum_sample,
            excluded_item_counts=metric.excluded_item_counts,
            required_inputs=["reviewed_transcript", "confirmed_speaker_mapping", "verified_normalized_audio", "verified_chat_round_trip"],
            reason_code=metric.reason_code,
            remediation=metric.remediation,
            limitations=list(metric.limitations),
            clinical_caution="Descriptive engineering-testbed value; it is not diagnostic or normative.",
            transcript_id=transcript.transcript_id,
            transcript_version=transcript.version,
            speaker_mapping_id=mapping.mapping_id,
            speaker_mapping_version=mapping.mapping_version,
            source_audio_file_id=audio.audio_file_id,
            source_asset_version=audio.source_asset_version,
            source_checksum_sha256=audio.checksum_sha256,
            normalized_asset_version=normalized.asset_version,
            normalized_checksum_sha256=normalized.normalized_checksum_sha256,
            attestation_id=attestation.attestation_id,
            attestation_version=attestation.attestation_version,
            chat_export_id=chat_export.export_id,
            chat_export_version=chat_export.export_version,
            chat_export_checksum_sha256=chat_export.round_trip.deterministic_export_checksum_sha256 or "",
            parser_version=chat_export.parser_version,
            serializer_version=chat_export.serializer_version,
            tokenizer_profile=tokenizer_reference if feature_id in {"target_token_count", "number_of_different_words", "type_token_ratio", "mean_length_of_utterance_words"} else None,
            algorithm_version=ALGORITHM_VERSION,
            algorithm_checksum_sha256=algorithm_checksum,
            generated_at=generated_at,
        )
        for feature_id, metric in metrics.items()
    ]
