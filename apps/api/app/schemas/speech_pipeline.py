"""Immutable v1.7 speech-pipeline lineage records.

These records describe research/education workflow artifacts. They are
version-bound audit records and do not represent diagnostic conclusions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FeatureResultStatus(str, Enum):
    available = "available"
    unavailable = "unavailable"
    insufficient_data = "insufficient_data"
    experimental = "experimental"
    stale = "stale"
    failed = "failed"


class QaDisposition(str, Enum):
    integrity_blocker = "integrity_blocker"
    acknowledgeable_limitation = "acknowledgeable_limitation"


class ArtifactStatus(str, Enum):
    current = "current"
    stale = "stale"


class MappingStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"
    stale = "stale"


class RoundTripStatus(str, Enum):
    verified = "verified"
    failed = "failed"
    stale = "stale"


class StalenessCause(FrozenRecord):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$")
    affected_resource_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )
    affected_resource_version: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )
    validator_or_rule_version: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9_.:-]+$",
    )


class AudioNormalizationProvenance(FrozenRecord):
    source_size_bytes: int = Field(gt=0)
    source_detected_format: Literal["wav", "mp3"]
    source_duration_ms: int = Field(ge=0)
    source_frame_count: int = Field(gt=0)
    source_sample_rate_hz: int = Field(gt=0)
    source_channels: int = Field(gt=0)
    normalized_size_bytes: int = Field(gt=0)
    boundary_frames_verified: Literal[True]
    decoder_library_name: str
    decoder_library_version: str
    mixer_name: str
    mixer_version: str
    resampler_name: str
    resampler_version: str
    writer_name: str
    writer_version: str
    writer_library_name: str
    writer_library_version: str
    processing_dtype: Literal["float32"]
    streaming_block_frames: int = Field(gt=0)
    overlap_frames: int = Field(ge=0)
    resample_window: str
    filter_profile: str
    padding_policy: str
    normalization_profile: str
    profile_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )


class NormalizedAudioAsset(FrozenRecord):
    organization_id: str
    session_id: str
    asset_version: int = Field(ge=1)
    object_key: str
    source_checksum_sha256: str
    normalized_checksum_sha256: str
    format: Literal["wav_pcm_s16le"]
    duration_ms: int = Field(gt=0)
    sample_rate_hz: int = Field(gt=0)
    channels: Literal[1]
    frame_count: int = Field(gt=0)
    decoder_name: str
    decoder_version: str
    conversion_command_profile: str
    verification_status: Literal["verified", "unverified"] = "unverified"
    provenance: AudioNormalizationProvenance | None = None
    source_audio_file_id: str
    source_asset_version: int = Field(ge=1)
    created_at: datetime
    status: ArtifactStatus = ArtifactStatus.current
    stale_causes: list[StalenessCause] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_verified_provenance(self) -> "NormalizedAudioAsset":
        if self.verification_status != "verified":
            return self
        if self.provenance is None:
            raise ValueError("verified normalized audio requires complete provenance")
        if self.conversion_command_profile != self.provenance.normalization_profile:
            raise ValueError("verified normalization profile fields do not match")
        expected_checksum = sha256(
            self.provenance.normalization_profile.encode("utf-8")
        ).hexdigest()
        if self.provenance.profile_checksum_sha256 != expected_checksum:
            raise ValueError("verified normalization profile checksum does not match")
        return self


class SpeakerMappingEntry(FrozenRecord):
    temporary_speaker_id: str
    confirmed_chat_code: str | None = None
    participant_role: str
    disposition: Literal["target", "non_target", "unknown", "merged"]
    merged_into_temporary_speaker_id: str | None = None
    affected_utterance_ids: list[str] = Field(default_factory=list)


class ReviewedSpeakerMapping(FrozenRecord):
    organization_id: str
    session_id: str
    mapping_id: str
    mapping_version: int = Field(ge=1)
    transcript_id: str
    transcript_version: int = Field(ge=1)
    entries: list[SpeakerMappingEntry]
    confirmed_by_user_id: str
    confirmed_by_role: str
    confirmed_at: datetime
    status: MappingStatus
    stale_causes: list[StalenessCause] = Field(default_factory=list)


class LimitationAcknowledgment(FrozenRecord):
    organization_id: str
    session_id: str
    transcript_id: str
    transcript_version: int = Field(ge=1)
    acknowledgment_id: str
    acknowledgment_version: int = Field(ge=1)
    limitation_code: str
    severity: str
    disposition: QaDisposition
    affected_resource_id: str
    affected_resource_version: str
    affected_stage: str
    affected_feature_id: str | None = None
    therapist_user_id: str
    therapist_role: str
    acknowledged_at: datetime
    structured_reason: str
    note: str = ""
    validator_version: str
    request_audit_id: str
    status: ArtifactStatus
    stale_causes: list[StalenessCause] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_acknowledgeable_limitation(self):
        if self.disposition is not QaDisposition.acknowledgeable_limitation:
            raise ValueError(
                "limitation acknowledgments require acknowledgeable_limitation disposition"
            )
        return self


class AsrProfile(FrozenRecord):
    provider_name: str
    provider_version: str
    model_id: str
    model_version: str
    model_checksum_sha256: str
    language_profile: str
    configuration_checksum_sha256: str | None = None


class AsrProvenance(FrozenRecord):
    job_id: str
    profile: AsrProfile
    source_audio_file_id: str
    source_asset_version: int = Field(ge=1)
    source_checksum_sha256: str
    normalized_asset_version: int = Field(ge=1)
    normalized_checksum_sha256: str
    raw_speaker_labels: list[str] = Field(default_factory=list)
    generated_at: datetime


class TranscriptAttestation(FrozenRecord):
    organization_id: str
    session_id: str
    attestation_id: str
    attestation_version: int = Field(ge=1)
    transcript_id: str
    transcript_version: int = Field(ge=1)
    speaker_mapping_id: str
    speaker_mapping_version: int = Field(ge=1)
    qa_validator_version: str
    acknowledgment_refs: list[tuple[str, int]] = Field(default_factory=list)
    attested_by_user_id: str
    attested_by_role: str
    attested_at: datetime
    request_audit_id: str
    status: ArtifactStatus
    stale_causes: list[StalenessCause] = Field(default_factory=list)


class ChatRoundTripError(FrozenRecord):
    code: str
    field_or_tier: str | None
    utterance_or_segment_id: str | None
    expected: str | int | float | bool | None
    actual: str | int | float | bool | None
    severity: str
    parser_version: str
    serializer_version: str
    subset_version: str
    message: str = ""
    disposition: QaDisposition = QaDisposition.integrity_blocker


class ChatSemanticRoundTripResult(FrozenRecord):
    status: RoundTripStatus
    parser_version: str
    serializer_version: str
    subset_version: str
    input_semantic_checksum_sha256: str
    output_semantic_checksum_sha256: str | None = None
    deterministic_export_checksum_sha256: str | None = None
    errors: list[ChatRoundTripError] = Field(default_factory=list)


class ChatExport(FrozenRecord):
    organization_id: str
    session_id: str
    export_id: str
    export_version: int = Field(ge=1)
    transcript_id: str
    transcript_version: int = Field(ge=1)
    speaker_mapping_id: str
    speaker_mapping_version: int = Field(ge=1)
    attestation_id: str
    attestation_version: int = Field(ge=1)
    parser_version: str
    serializer_version: str
    subset_version: str
    canonical_checksum_sha256: str
    source_audio_file_id: str
    source_asset_version: int = Field(ge=1)
    source_checksum_sha256: str
    normalized_asset_version: int = Field(ge=1)
    normalized_checksum_sha256: str
    asr_provenance: AsrProvenance | None = None
    round_trip: ChatSemanticRoundTripResult
    status: ArtifactStatus
    created_at: datetime
    stale_causes: list[StalenessCause] = Field(default_factory=list)


class TokenizerProfileReference(FrozenRecord):
    profile_id: str
    profile_version: int = Field(ge=1)
    profile_checksum_sha256: str
    engine: str
    package_version: str
    artifact_id: str
    artifact_checksum_sha256: str
    custom_vocabulary_version: str
    custom_vocabulary_checksum_sha256: str


class FeatureResult(FrozenRecord):
    feature_id: str
    feature_version: int = Field(ge=1)
    status: FeatureResultStatus
    value: float | int | None = None
    unit: str
    numerator: float | int | None = None
    denominator: float | int | None = None
    minimum_sample: int | None = None
    excluded_item_counts: dict[str, int] = Field(default_factory=dict)
    required_inputs: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    remediation: str | None = None
    data_quality_notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    clinical_caution: str = "Descriptive research output; therapist review is required."
    transcript_id: str
    transcript_version: int = Field(ge=1)
    speaker_mapping_id: str
    speaker_mapping_version: int = Field(ge=1)
    source_audio_file_id: str
    source_asset_version: int = Field(ge=1)
    source_checksum_sha256: str
    normalized_asset_version: int = Field(ge=1)
    normalized_checksum_sha256: str
    attestation_id: str
    attestation_version: int = Field(ge=1)
    chat_export_id: str
    chat_export_version: int = Field(ge=1)
    chat_export_checksum_sha256: str
    parser_version: str
    serializer_version: str
    tokenizer_profile: TokenizerProfileReference | None = None
    algorithm_version: str
    algorithm_checksum_sha256: str
    generated_at: datetime

    @model_validator(mode="after")
    def enforce_status_value_semantics(self):
        if self.status in {
            FeatureResultStatus.unavailable,
            FeatureResultStatus.insufficient_data,
            FeatureResultStatus.stale,
            FeatureResultStatus.failed,
        } and self.value is not None:
            raise ValueError(f"{self.status.value} feature results must not contain a value")
        if self.status is FeatureResultStatus.available and self.value is None:
            raise ValueError("available feature results must contain a value")
        return self


class FindingsProjection(FrozenRecord):
    organization_id: str
    session_id: str
    findings_id: str
    findings_version: int = Field(ge=1)
    transcript_id: str
    transcript_version: int = Field(ge=1)
    speaker_mapping_id: str
    speaker_mapping_version: int = Field(ge=1)
    source_audio_file_id: str
    source_asset_version: int = Field(ge=1)
    source_checksum_sha256: str
    normalized_asset_version: int = Field(ge=1)
    normalized_checksum_sha256: str
    attestation_id: str
    attestation_version: int = Field(ge=1)
    chat_export_id: str
    chat_export_version: int = Field(ge=1)
    chat_export_checksum_sha256: str
    parser_version: str
    serializer_version: str
    tokenizer_profile: TokenizerProfileReference | None = None
    feature_schema_version: str
    algorithm_version: str
    algorithm_checksum_sha256: str
    features: list[FeatureResult]
    acknowledgment_refs: list[tuple[str, int]] = Field(default_factory=list)
    generation_service_version: str
    generated_at: datetime
    status: ArtifactStatus
    stale_causes: list[StalenessCause] = Field(default_factory=list)
