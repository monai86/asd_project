"""
Abstract base classes for ASR (Automatic Speech Recognition) providers.

Adding a new provider:
  1. Subclass BaseTranscriptionProvider
  2. Implement all abstract methods
  3. Register with asr_provider_registry.register(MyProvider())
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal, Mapping, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.asr_profiles import (
    AsrRuntimeVersions,
    PinnedAsrProfile,
    PinnedVadParameters,
)


@dataclass
class ProviderAvailability:
    """Result of a provider's availability check."""

    available: bool
    reason: str = ""
    reason_code: str | None = None
    remediation: str | None = None
    missing_dependencies: tuple[str, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:
        return self.available


@dataclass
class TranscriptLine:
    """One utterance line from an ASR provider."""

    line_id: str
    speaker: str  # "CHI" | "THER" | "UNK"
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    confidence: float | None = None
    source: str = "asr"  # "asr" | "mock" | "manual"
    unclear: bool = False


@dataclass
class TranscriptionResult:
    """Structured output from a provider's transcribe() call."""

    status: str  # "completed" | "failed" | "unavailable"
    provider_id: str
    provider_name: str
    provider_version: str
    transcript_lines: list[TranscriptLine]
    language: str = "en"
    confidence_available: bool = False
    word_timestamps_available: bool = False
    speaker_segments_available: bool = False
    warnings: list[str] = field(default_factory=list)
    error_message: str = ""
    provider_metadata: dict = field(default_factory=dict)
    raw_artifact_refs: list[str] = field(default_factory=list)
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FrozenAsrContract(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
    )

    def revalidated(self) -> Self:
        values = {
            field_name: getattr(self, field_name)
            for field_name in type(self).model_fields
        }
        return type(self).model_validate(values)

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
        if deep:
            values = deepcopy(values)
        if update:
            values.update(update)
        return type(self).model_validate(values)


class VerifiedNormalizedAudioHandle(FrozenAsrContract):
    """Exact, server-verified working asset allowed to cross the ASR boundary."""

    source_audio_file_id: str = Field(min_length=1)
    source_asset_version: int = Field(ge=1)
    source_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    normalized_asset_version: int = Field(ge=1)
    normalized_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    normalized_object_key: str = Field(min_length=1)
    local_processing_path: Path
    verification_status: Literal["verified", "unverified"]
    is_current: bool


class TranscriptionInput(FrozenAsrContract):
    normalized_audio: VerifiedNormalizedAudioHandle | None
    profile: PinnedAsrProfile | None
    placeholder_profile_id: str | None = None

    @classmethod
    def unverified_placeholder(cls, *, profile_id: str) -> "TranscriptionInput":
        return cls(
            normalized_audio=None,
            profile=None,
            placeholder_profile_id=profile_id,
        )


class AsrUnavailability(FrozenAsrContract):
    code: str
    message: str
    remediation: str
    missing_dependencies: tuple[str, ...] = Field(default_factory=tuple)


class CanonicalAsrWarning(FrozenAsrContract):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: Literal["info", "warning", "limitation"]
    remediation: str = Field(min_length=1)


class CanonicalTranscriptionSegment(FrozenAsrContract):
    segment_id: str
    temporary_speaker_id: str = Field(pattern=r"^(SPK_[0-9]{2}|UNK)$")
    source_speaker_label: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "CanonicalTranscriptionSegment":
        if self.end_ms < self.start_ms:
            raise ValueError("segment end_ms must be greater than or equal to start_ms")
        return self


class RawProviderWord(FrozenAsrContract):
    start_seconds: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    end_seconds: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    text: str
    probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "RawProviderWord":
        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds < self.start_seconds
        ):
            raise ValueError(
                "raw word end_seconds must be greater than or equal to start_seconds"
            )
        return self


class RawProviderSegment(FrozenAsrContract):
    provider_segment_id: str
    seek: int | None = Field(default=None, ge=0)
    start_seconds: float = Field(ge=0.0, allow_inf_nan=False)
    end_seconds: float = Field(ge=0.0, allow_inf_nan=False)
    text: str
    token_ids: tuple[int, ...]
    temperature: float | None = Field(default=None, allow_inf_nan=False)
    average_log_probability: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )
    compression_ratio: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    no_speech_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    words: tuple[RawProviderWord, ...]

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "RawProviderSegment":
        if self.end_seconds < self.start_seconds:
            raise ValueError(
                "raw segment end_seconds must be greater than or equal to start_seconds"
            )
        return self


class SpeechDetectionInterval(FrozenAsrContract):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "SpeechDetectionInterval":
        if self.end_ms < self.start_ms:
            raise ValueError(
                "speech detection interval end must not precede start"
            )
        return self


def canonical_vad_config_checksum(
    vad_parameters: PinnedVadParameters,
) -> str:
    encoded = json.dumps(
        vad_parameters.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _speech_evidence_json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return _speech_evidence_json_value(value.model_dump(mode="json"))
    if isinstance(value, Mapping):
        return {
            str(key): _speech_evidence_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_speech_evidence_json_value(item) for item in value]
    return value


def canonical_speech_detection_evidence_checksum(
    evidence: Mapping[str, object],
) -> str:
    material = {
        key: _speech_evidence_json_value(value)
        for key, value in evidence.items()
        if key != "evidence_checksum_sha256"
    }
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class SpeechDetectionEvidence(FrozenAsrContract):
    detector_id: Literal["faster_whisper_silero_vad"]
    detector_version: str = Field(min_length=1, max_length=128)
    sample_rate_hz: Literal[16000]
    normalized_audio_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    vad_parameters: PinnedVadParameters
    vad_config_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    intervals: tuple[SpeechDetectionInterval, ...]
    evidence_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )

    @model_validator(mode="after")
    def validate_checksums(self) -> "SpeechDetectionEvidence":
        if (
            self.vad_config_checksum_sha256
            != canonical_vad_config_checksum(self.vad_parameters)
        ):
            raise ValueError(
                "speech detector VAD configuration checksum mismatch"
            )
        if (
            self.evidence_checksum_sha256
            != canonical_speech_detection_evidence_checksum(
                self.model_dump(mode="json")
            )
        ):
            raise ValueError("speech detection evidence checksum mismatch")
        return self


class RawProviderPayload(FrozenAsrContract):
    provider_id: str
    language: str
    language_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    duration_after_vad_seconds: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    speech_detection_evidence: SpeechDetectionEvidence
    segments: tuple[RawProviderSegment, ...]


def canonical_raw_provider_payload_checksum(
    payload: RawProviderPayload,
) -> str:
    """Hash private provider output using the one canonical JSON serializer."""

    encoded = json.dumps(
        payload.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def canonical_asr_segment_id(
    *,
    normalized_audio_checksum_sha256: str,
    ordinal: int,
    start_ms: int,
    end_ms: int,
    text: str,
) -> str:
    """Derive the stable canonical segment identity from verified evidence."""

    identity = (
        f"{normalized_audio_checksum_sha256}:{ordinal}:"
        f"{start_ms}:{end_ms}:{text}"
    )
    return (
        f"asrseg-{ordinal:06d}-"
        f"{sha256(identity.encode('utf-8')).hexdigest()[:12]}"
    )


def canonical_input_lineage_checksum(
    *,
    provider_id: str,
    source_audio_file_id: str,
    source_audio_asset_version: int,
    source_audio_checksum_sha256: str,
    normalized_audio_asset_version: int,
    normalized_audio_checksum_sha256: str,
    profile_id: str,
    profile_version: int,
    profile_checksum_sha256: str,
) -> str:
    """Bind the non-secret ASR input lineage with canonical JSON."""

    material = {
        "provider_id": provider_id,
        "source_audio_file_id": source_audio_file_id,
        "source_audio_asset_version": source_audio_asset_version,
        "source_audio_checksum_sha256": source_audio_checksum_sha256,
        "normalized_audio_asset_version": normalized_audio_asset_version,
        "normalized_audio_checksum_sha256": (
            normalized_audio_checksum_sha256
        ),
        "profile_id": profile_id,
        "profile_version": profile_version,
        "profile_checksum_sha256": profile_checksum_sha256,
    }
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class AsrProfileProvenanceProjection(FrozenAsrContract):
    """Validated non-secret model, runtime, and decoding configuration."""

    profile_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    profile_version: int = Field(ge=1)
    profile_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    model_identifier: str = Field(
        min_length=1,
        max_length=256,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$",
    )
    model_revision: str = Field(
        min_length=1,
        max_length=256,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:+-]*$",
    )
    model_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    faster_whisper_version: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$",
    )
    ctranslate2_version: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$",
    )
    decoder_name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$",
    )
    decoder_version: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$",
    )
    device: Literal["cpu", "cuda", "auto"]
    device_index: int = Field(ge=0)
    compute_type: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$",
    )
    cpu_threads: int = Field(ge=0)
    num_workers: int = Field(ge=1)
    language_mode: Literal["th", "auto"]
    task: Literal["transcribe"]
    log_progress: Literal[False]
    beam_size: int = Field(ge=1)
    best_of: int = Field(ge=1)
    patience: float = Field(gt=0, allow_inf_nan=False)
    length_penalty: float = Field(gt=0, allow_inf_nan=False)
    repetition_penalty: float = Field(gt=0, allow_inf_nan=False)
    no_repeat_ngram_size: int = Field(ge=0)
    temperature: Literal[0.0]
    compression_ratio_threshold: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )
    log_prob_threshold: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )
    no_speech_threshold: float | None = Field(
        default=None,
        allow_inf_nan=False,
    )
    vad_filter: bool
    vad_parameters: PinnedVadParameters | None
    word_timestamps: bool
    condition_on_previous_text: bool
    prompt_reset_on_temperature: float = Field(
        ge=0,
        allow_inf_nan=False,
    )
    initial_prompt: str | None
    prefix: str | None
    suppress_blank: bool
    suppress_tokens: tuple[int, ...] | None
    without_timestamps: Literal[False]
    max_initial_timestamp: float = Field(ge=0, allow_inf_nan=False)
    prepend_punctuations: str
    append_punctuations: str
    multilingual: bool
    max_new_tokens: int | None = Field(default=None, ge=1)
    chunk_length: int | None = Field(default=None, ge=1)
    clip_timestamps: str = Field(min_length=1)
    hallucination_silence_threshold: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )
    hotwords: str | None
    language_detection_threshold: float | None = Field(
        default=None,
        ge=0,
        le=1,
        allow_inf_nan=False,
    )
    language_detection_segments: int = Field(ge=1)

    @classmethod
    def from_pinned_profile(
        cls,
        profile: PinnedAsrProfile,
        runtime: AsrRuntimeVersions,
    ) -> "AsrProfileProvenanceProjection":
        """Project one already-validated profile and observed runtime."""

        profile = profile.revalidated()
        values = {
            field_name: getattr(profile, field_name)
            for field_name in cls.model_fields
        }
        values.update(
            faster_whisper_version=runtime.faster_whisper_version,
            ctranslate2_version=runtime.ctranslate2_version,
            decoder_name=runtime.decoder_name,
            decoder_version=runtime.decoder_version,
        )
        return cls.model_validate(values)

    @model_validator(mode="after")
    def validate_deterministic_projection(
        self,
    ) -> "AsrProfileProvenanceProjection":
        if self.model_identifier.strip().lower() in {
            "default",
            "latest",
            "main",
            "master",
        }:
            raise ValueError("model_identifier must be immutable, not floating")
        if self.model_revision.strip().lower() in {
            "default",
            "latest",
            "main",
            "master",
        }:
            raise ValueError("model_revision must be immutable, not floating")
        if (
            self.language_mode == "auto"
            and self.language_detection_threshold is None
        ):
            raise ValueError(
                "language_detection_threshold is required for auto language mode"
            )
        if self.vad_filter and self.vad_parameters is None:
            raise ValueError(
                "vad_parameters are required when vad_filter is enabled"
            )
        if not self.vad_filter and self.vad_parameters is not None:
            raise ValueError(
                "vad_parameters must be null when vad_filter is disabled"
            )
        for field_name in ("initial_prompt", "prefix", "hotwords"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} must be null or non-empty")
        if self.suppress_tokens is not None and len(
            self.suppress_tokens
        ) != len(set(self.suppress_tokens)):
            raise ValueError("suppress_tokens must not contain duplicates")
        return self


def canonical_decoding_provenance_checksum(
    projection: AsrProfileProvenanceProjection,
) -> str:
    """Hash every model/runtime/decoding provenance field canonically."""

    encoded = json.dumps(
        projection.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


class CanonicalAsrProvenance(AsrProfileProvenanceProjection):
    provider_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    provider_version: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+:-]*$",
    )
    detected_language: str
    detected_language_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    source_audio_file_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    source_audio_asset_version: int = Field(ge=1)
    source_audio_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    normalized_audio_asset_version: int = Field(ge=1)
    normalized_audio_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    normalized_audio_object_key: str = Field(
        min_length=1,
        exclude=True,
        repr=False,
    )
    raw_provider_payload_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    speech_detection_evidence_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    input_lineage_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    decoding_provenance_checksum_sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )

    @model_validator(mode="after")
    def validate_provenance_checksums(self) -> "CanonicalAsrProvenance":
        expected = canonical_input_lineage_checksum(
            provider_id=self.provider_id,
            source_audio_file_id=self.source_audio_file_id,
            source_audio_asset_version=self.source_audio_asset_version,
            source_audio_checksum_sha256=self.source_audio_checksum_sha256,
            normalized_audio_asset_version=self.normalized_audio_asset_version,
            normalized_audio_checksum_sha256=(
                self.normalized_audio_checksum_sha256
            ),
            profile_id=self.profile_id,
            profile_version=self.profile_version,
            profile_checksum_sha256=self.profile_checksum_sha256,
        )
        if self.input_lineage_checksum_sha256 != expected:
            raise ValueError(
                "input lineage checksum does not match canonical provenance"
            )
        projection = AsrProfileProvenanceProjection.model_validate(
            {
                field_name: getattr(self, field_name)
                for field_name in AsrProfileProvenanceProjection.model_fields
            }
        )
        decoding_checksum = canonical_decoding_provenance_checksum(projection)
        if self.decoding_provenance_checksum_sha256 != decoding_checksum:
            raise ValueError(
                "decoding provenance checksum does not match canonical "
                "model/runtime configuration"
            )
        return self


class PublicCanonicalAsrProvenance(CanonicalAsrProvenance):
    """Canonical provenance projection without the private storage key."""

    normalized_audio_object_key: None = Field(
        default=None,
        exclude=True,
        repr=False,
    )


class PublicCanonicalTranscriptionDraft(FrozenAsrContract):
    """Explicit raw-free projection safe for API and frontend serialization."""

    status: Literal["completed", "failed", "unavailable"]
    provider_id: str
    segments: tuple[CanonicalTranscriptionSegment, ...] = Field(
        default_factory=tuple
    )
    language: str = "und"
    warnings: tuple[CanonicalAsrWarning, ...] = Field(default_factory=tuple)
    provenance: PublicCanonicalAsrProvenance | None = None
    speech_detection_evidence: SpeechDetectionEvidence | None = None
    unavailability: AsrUnavailability | None = None
    error_code: str | None = None
    error_message: str = ""
    computed_at: datetime

    @model_validator(mode="after")
    def validate_public_state(self) -> "PublicCanonicalTranscriptionDraft":
        if self.status == "completed":
            if not self.segments:
                raise ValueError(
                    "completed public canonical draft requires nonempty segments"
                )
            if self.provenance is None:
                raise ValueError(
                    "completed public canonical draft requires provenance"
                )
            if self.speech_detection_evidence is None:
                raise ValueError(
                    "completed public canonical draft requires speech "
                    "detection evidence"
                )
            if (
                self.provenance.speech_detection_evidence_checksum_sha256
                != self.speech_detection_evidence.evidence_checksum_sha256
            ):
                raise ValueError(
                    "public speech detection evidence does not match "
                    "provenance"
                )
            if (
                self.speech_detection_evidence.normalized_audio_checksum_sha256
                != self.provenance.normalized_audio_checksum_sha256
            ):
                raise ValueError(
                    "public speech detection evidence does not match the "
                    "normalized asset provenance"
                )
            if self.provenance.provider_id != self.provider_id:
                raise ValueError(
                    "completed public canonical draft provider does not match "
                    "provenance"
                )
            if (
                self.unavailability is not None
                or self.error_code is not None
                or self.error_message
            ):
                raise ValueError(
                    "completed public canonical draft cannot carry an error state"
                )
            return self
        if (
            self.segments
            or self.provenance is not None
            or self.speech_detection_evidence is not None
        ):
            raise ValueError(
                "failed or unavailable public draft cannot carry partial "
                "completed artifacts"
            )
        if self.status == "unavailable":
            if self.unavailability is None:
                raise ValueError(
                    "unavailable public canonical draft requires typed "
                    "unavailability"
                )
            if (
                self.error_code != self.unavailability.code
                or self.error_message != self.unavailability.message
            ):
                raise ValueError(
                    "unavailable public canonical draft error fields must "
                    "match typed unavailability"
                )
            return self
        if self.unavailability is not None:
            raise ValueError(
                "failed public canonical draft cannot carry unavailability"
            )
        if not self.error_code or not self.error_message:
            raise ValueError(
                "failed public canonical draft requires an error code and message"
            )
        return self


class CanonicalTranscriptionDraft(FrozenAsrContract):
    status: Literal["completed", "failed", "unavailable"]
    provider_id: str
    segments: tuple[CanonicalTranscriptionSegment, ...] = Field(
        default_factory=tuple
    )
    language: str = "und"
    warnings: tuple[CanonicalAsrWarning, ...] = Field(default_factory=tuple)
    provenance: CanonicalAsrProvenance | None = None
    speech_detection_evidence: SpeechDetectionEvidence | None = None
    unavailability: AsrUnavailability | None = None
    error_code: str | None = None
    error_message: str = ""
    raw_provider_payload: RawProviderPayload | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @model_validator(mode="after")
    def validate_private_payload_lineage(self) -> "CanonicalTranscriptionDraft":
        if self.status == "unavailable":
            if (
                self.segments
                or self.provenance is not None
                or self.raw_provider_payload is not None
                or self.speech_detection_evidence is not None
            ):
                raise ValueError(
                    "failed or unavailable canonical draft cannot carry partial "
                    "completed artifacts"
                )
            if self.unavailability is None:
                raise ValueError(
                    "unavailable canonical draft requires typed unavailability"
                )
            if (
                self.error_code != self.unavailability.code
                or self.error_message != self.unavailability.message
            ):
                raise ValueError(
                    "unavailable canonical draft error fields must match typed "
                    "unavailability"
                )
            return self
        if self.status == "failed":
            if (
                self.segments
                or self.provenance is not None
                or self.raw_provider_payload is not None
                or self.speech_detection_evidence is not None
            ):
                raise ValueError(
                    "failed or unavailable canonical draft cannot carry partial "
                    "completed artifacts"
                )
            if self.unavailability is not None:
                raise ValueError(
                    "failed canonical draft cannot carry unavailability"
                )
            if not self.error_code or not self.error_message:
                raise ValueError(
                    "failed canonical draft requires an error code and message"
                )
            return self
        if not self.segments:
            raise ValueError(
                "completed canonical draft requires nonempty segments"
            )
        if self.raw_provider_payload is None:
            raise ValueError(
                "completed canonical draft requires a private raw provider payload"
            )
        if self.speech_detection_evidence is None:
            raise ValueError(
                "completed canonical draft requires speech detection evidence"
            )
        if (
            self.unavailability is not None
            or self.error_code is not None
            or self.error_message
        ):
            raise ValueError(
                "completed canonical draft cannot carry an error state"
            )
        if self.raw_provider_payload is not None and self.provenance is None:
            raise ValueError("raw provider payload requires provenance")
        if self.provenance is not None and self.raw_provider_payload is None:
            raise ValueError("canonical provenance requires a raw provider payload")
        if self.raw_provider_payload is None:
            return self
        if self.raw_provider_payload.provider_id != self.provider_id:
            raise ValueError(
                "raw provider payload provider does not match canonical draft"
            )
        if self.provenance is None:
            raise ValueError("raw provider payload requires provenance")
        if (
            self.raw_provider_payload.speech_detection_evidence
            != self.speech_detection_evidence
        ):
            raise ValueError(
                "public speech detection evidence does not match private "
                "provider evidence"
            )
        if (
            self.provenance.speech_detection_evidence_checksum_sha256
            != self.speech_detection_evidence.evidence_checksum_sha256
        ):
            raise ValueError(
                "speech detection evidence checksum does not match provenance"
            )
        if (
            self.speech_detection_evidence.normalized_audio_checksum_sha256
            != self.provenance.normalized_audio_checksum_sha256
        ):
            raise ValueError(
                "speech detection evidence does not match the normalized "
                "asset provenance"
            )
        if self.provenance.provider_id != self.provider_id:
            raise ValueError(
                "canonical provenance provider does not match canonical draft"
            )
        actual_checksum = canonical_raw_provider_payload_checksum(
            self.raw_provider_payload
        )
        if (
            actual_checksum
            != self.provenance.raw_provider_payload_checksum_sha256
        ):
            raise ValueError(
                "raw provider payload checksum does not match provenance"
            )
        if self.language != self.raw_provider_payload.language:
            raise ValueError(
                "canonical language does not match raw provider evidence"
            )
        if (
            self.provenance.detected_language
            != self.raw_provider_payload.language
        ):
            raise ValueError(
                "provenance language does not match raw provider evidence"
            )
        if (
            self.provenance.detected_language_probability
            != self.raw_provider_payload.language_probability
        ):
            raise ValueError(
                "provenance language probability does not match raw provider "
                "evidence"
            )
        raw_segments = self.raw_provider_payload.segments
        if len(self.segments) != len(raw_segments):
            raise ValueError(
                "canonical segment count does not match raw provider evidence"
            )
        for ordinal, (canonical, raw) in enumerate(
            zip(self.segments, raw_segments),
            start=1,
        ):
            start_ms = int(round(raw.start_seconds * 1000))
            end_ms = int(round(raw.end_seconds * 1000))
            text = raw.text.strip()
            expected_id = canonical_asr_segment_id(
                normalized_audio_checksum_sha256=(
                    self.provenance.normalized_audio_checksum_sha256
                ),
                ordinal=ordinal,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
            )
            if (
                canonical.segment_id != expected_id
                or canonical.start_ms != start_ms
                or canonical.end_ms != end_ms
                or canonical.text != text
                or canonical.temporary_speaker_id != "UNK"
                or canonical.source_speaker_label != "UNK"
                or canonical.confidence is not None
            ):
                raise ValueError(
                    f"canonical segment {ordinal} does not match raw provider evidence"
                )
        return self

    def model_copy(
        self,
        *,
        update: dict[str, object] | None = None,
        deep: bool = False,
    ) -> "CanonicalTranscriptionDraft":
        """Copy through validation; Pydantic's default update bypass is unsafe."""

        values = {
            field_name: getattr(self, field_name)
            for field_name in type(self).model_fields
        }
        if deep:
            values = deepcopy(values)
        if update:
            values.update(update)
        return type(self).model_validate(values)

    def to_public_projection(self) -> PublicCanonicalTranscriptionDraft:
        """Return the only supported raw-free serialized representation."""

        return PublicCanonicalTranscriptionDraft(
            status=self.status,
            provider_id=self.provider_id,
            segments=self.segments,
            language=self.language,
            warnings=self.warnings,
            provenance=(
                PublicCanonicalAsrProvenance.model_validate(
                    self.provenance.model_dump(mode="json")
                )
                if self.provenance is not None
                else None
            ),
            speech_detection_evidence=self.speech_detection_evidence,
            unavailability=self.unavailability,
            error_code=self.error_code,
            error_message=self.error_message,
            computed_at=self.computed_at,
        )

    def to_private_record(self) -> dict[str, object]:
        """Serialize complete private state for checksum-linked persistence."""

        record = self.model_dump(mode="json")
        if self.provenance is not None:
            provenance = dict(record["provenance"])
            provenance["normalized_audio_object_key"] = (
                self.provenance.normalized_audio_object_key
            )
            record["provenance"] = provenance
        record["raw_provider_payload"] = (
            self.raw_provider_payload.model_dump(mode="json")
            if self.raw_provider_payload is not None
            else None
        )
        return record

    @property
    def provider_name(self) -> str:
        return "LocalFasterWhisperProvider"

    @property
    def provider_version(self) -> str:
        return self.provenance.provider_version if self.provenance else "v1.7.0"

    @property
    def transcript_lines(self) -> list[TranscriptLine]:
        return [
            TranscriptLine(
                line_id=segment.segment_id,
                speaker=segment.temporary_speaker_id,
                text=segment.text,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                confidence=segment.confidence,
                source="asr",
            )
            for segment in self.segments
        ]

    @property
    def confidence_available(self) -> bool:
        return any(segment.confidence is not None for segment in self.segments)

    @property
    def word_timestamps_available(self) -> bool:
        return bool(self.provenance and self.provenance.word_timestamps)

    @property
    def speaker_segments_available(self) -> bool:
        return False

    @property
    def provider_metadata(self) -> dict[str, object]:
        metadata = (
            self.provenance.model_dump(mode="json")
            if self.provenance is not None
            else {}
        )
        if self.speech_detection_evidence is not None:
            metadata["speech_detection_evidence"] = (
                self.speech_detection_evidence.model_dump(mode="json")
            )
        return metadata

    @property
    def raw_artifact_refs(self) -> list[str]:
        return []


class BaseTranscriptionProvider(ABC):
    """Abstract base for all ASR providers."""

    def prepare_for_retry(
        self,
        *,
        profile: PinnedAsrProfile,
    ) -> None:
        """Refresh retry-scoped capability state; stateless providers no-op."""

        profile.revalidated()

    @property
    @abstractmethod
    def provider_id(self) -> str: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def provider_version(self) -> str: ...

    @abstractmethod
    def get_provider_metadata(self) -> dict: ...

    @abstractmethod
    def check_availability(self) -> ProviderAvailability: ...

    @abstractmethod
    def transcribe(
        self,
        transcription_input: TranscriptionInput,
    ) -> CanonicalTranscriptionDraft | TranscriptionResult: ...
