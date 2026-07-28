"""Pinned local faster-whisper adapter for canonical v1.7.0 draft output."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Callable

from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.services.asr_profiles import (
    ArtifactChangedDuringReadError,
    ArtifactFingerprint,
    ArtifactSnapshot,
    AsrProfileLoadError,
    AsrRuntimeVersions,
    PinnedAsrProfile,
    PinnedVadParameters,
    UnsafeModelArtifactError,
    fingerprint_model_artifact,
    inspect_asr_runtime,
    load_pinned_asr_profile,
    snapshot_model_artifact,
    snapshot_regular_file,
)
from app.services.asr_providers.base import (
    AsrProfileProvenanceProjection,
    AsrUnavailability,
    BaseTranscriptionProvider,
    CanonicalAsrProvenance,
    CanonicalAsrWarning,
    CanonicalTranscriptionDraft,
    CanonicalTranscriptionSegment,
    ProviderAvailability,
    RawProviderPayload,
    RawProviderSegment,
    RawProviderWord,
    SpeechDetectionEvidence,
    SpeechDetectionInterval,
    TranscriptionInput,
    canonical_asr_segment_id,
    canonical_decoding_provenance_checksum,
    canonical_input_lineage_checksum,
    canonical_raw_provider_payload_checksum,
    canonical_speech_detection_evidence_checksum,
    canonical_vad_config_checksum,
)


_CapabilityIssue = tuple[str, str, str, tuple[str, ...]]


class FasterWhisperSileroSpeechDetector:
    """Pinned Silero VAD evidence from faster-whisper on normalized 16 kHz."""

    detector_id = "faster_whisper_silero_vad"

    def check_availability(
        self,
        *,
        profile: PinnedAsrProfile,
        runtime: AsrRuntimeVersions,
    ) -> _CapabilityIssue | None:
        if not profile.vad_filter or profile.vad_parameters is None:
            return (
                "speech_detector_profile_unavailable",
                "The ASR profile does not pin enabled Silero VAD options.",
                "Select a verified profile with explicit Silero VAD options.",
                (),
            )
        try:
            from faster_whisper.audio import decode_audio  # noqa: F401
            from faster_whisper.vad import (  # noqa: F401
                VadOptions,
                get_speech_timestamps,
            )
        except Exception:
            return (
                "speech_detector_unavailable",
                "The pinned faster-whisper Silero VAD runtime is unavailable.",
                "Restore the exact faster-whisper runtime and retry.",
                ("faster-whisper-silero-vad",),
            )
        if runtime.faster_whisper_version is None:
            return (
                "speech_detector_version_unavailable",
                "The Silero VAD runtime version cannot be verified.",
                "Restore the pinned faster-whisper runtime and retry.",
                ("faster-whisper",),
            )
        return None

    def detect(
        self,
        audio_path: Path,
        *,
        normalized_audio_checksum_sha256: str,
        vad_parameters: PinnedVadParameters,
        detector_version: str,
    ) -> SpeechDetectionEvidence:
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import VadOptions, get_speech_timestamps

        samples = decode_audio(
            str(audio_path),
            sampling_rate=16_000,
            split_stereo=False,
        )
        raw_intervals = get_speech_timestamps(
            samples,
            vad_options=VadOptions(**vad_parameters.model_dump()),
            sampling_rate=16_000,
        )
        intervals = tuple(
            SpeechDetectionInterval(
                start_ms=int(round(int(item["start"]) * 1000 / 16_000)),
                end_ms=int(round(int(item["end"]) * 1000 / 16_000)),
            )
            for item in raw_intervals
        )
        values: dict[str, object] = {
            "detector_id": self.detector_id,
            "detector_version": detector_version,
            "sample_rate_hz": 16_000,
            "normalized_audio_checksum_sha256": (
                normalized_audio_checksum_sha256
            ),
            "vad_parameters": vad_parameters,
            "vad_config_checksum_sha256": canonical_vad_config_checksum(
                vad_parameters
            ),
            "intervals": intervals,
        }
        values["evidence_checksum_sha256"] = (
            canonical_speech_detection_evidence_checksum(values)
        )
        return SpeechDetectionEvidence.model_validate(values)


@dataclass(frozen=True, slots=True)
class _VerifiedCapabilityContext:
    profile: PinnedAsrProfile
    runtime: AsrRuntimeVersions
    model_path: Path
    model_snapshot: ArtifactSnapshot
    model_fingerprint: ArtifactFingerprint


@dataclass(frozen=True, slots=True)
class _LoadedModelContext:
    model: object
    profile_checksum_sha256: str
    model_snapshot: ArtifactSnapshot
    model_fingerprint: ArtifactFingerprint


class LocalWhisperProvider(BaseTranscriptionProvider):
    """Use only a checksummed local model and a verified normalized asset."""

    def __init__(
        self,
        *,
        profile: PinnedAsrProfile | None = None,
        profile_path: Path | None = None,
        settings: Settings | None = None,
        runtime_inspector: Callable[[], AsrRuntimeVersions] = inspect_asr_runtime,
        model_factory: Callable[..., object] | None = None,
        speech_detector: object | None = None,
    ) -> None:
        self._settings = settings
        self._profile = profile
        self._profile_path = profile_path
        self._runtime_inspector = runtime_inspector
        self._model_factory = model_factory or self._default_model_factory
        self._speech_detector = (
            speech_detector or FasterWhisperSileroSpeechDetector()
        )
        self._cache_lock = RLock()
        self._capability_checked = False
        self._cached_capability: _VerifiedCapabilityContext | None = None
        self._cached_capability_issue: _CapabilityIssue | None = None
        self._loaded_model: _LoadedModelContext | None = None

    @property
    def provider_id(self) -> str:
        return "local_faster_whisper"

    @property
    def provider_name(self) -> str:
        return "LocalFasterWhisperProvider"

    @property
    def provider_version(self) -> str:
        return "v1.7.0"

    @staticmethod
    def _repository_root() -> Path:
        return Path(__file__).resolve().parents[5]

    def _configured_profile_path(self) -> Path:
        if self._profile_path is not None:
            return self._profile_path
        settings = self._settings or get_settings()
        configured = Path(settings.asr_runtime_profile_path)
        if configured.is_absolute():
            return configured
        return self._repository_root() / configured

    def _load_profile(self) -> PinnedAsrProfile:
        if self._profile is not None:
            try:
                return self._profile.revalidated()
            except ValidationError as exc:
                raise AsrProfileLoadError(
                    "runtime_profile_unverified",
                    "Pinned ASR runtime profile could not be verified.",
                ) from exc
        return load_pinned_asr_profile(self._configured_profile_path())

    def _resolved_model_artifact_path(
        self,
        profile: PinnedAsrProfile,
    ) -> Path:
        if profile.model_artifact_path.is_absolute():
            return profile.model_artifact_path
        repository_root = self._repository_root().resolve()
        resolved = (
            repository_root / profile.model_artifact_path
        ).resolve()
        if resolved != repository_root and repository_root not in resolved.parents:
            raise UnsafeModelArtifactError(
                "relative model artifact path escapes the repository"
            )
        return resolved

    @staticmethod
    def _default_model_factory(**kwargs):
        from faster_whisper import WhisperModel

        return WhisperModel(**kwargs)

    @staticmethod
    def _unavailable(
        code: str,
        message: str,
        remediation: str,
        *,
        missing_dependencies: tuple[str, ...] | None = None,
    ) -> CanonicalTranscriptionDraft:
        return CanonicalTranscriptionDraft(
            status="unavailable",
            provider_id="local_faster_whisper",
            unavailability=AsrUnavailability(
                code=code,
                message=message,
                remediation=remediation,
                missing_dependencies=missing_dependencies or (),
            ),
            error_code=code,
            error_message=message,
            warnings=(
                CanonicalAsrWarning(
                    code=code,
                    message=message,
                    severity="warning",
                    remediation=remediation,
                ),
            ),
        )

    @staticmethod
    def _integrity_failed(
        code: str,
        message: str,
        remediation: str,
    ) -> CanonicalTranscriptionDraft:
        return CanonicalTranscriptionDraft(
            status="failed",
            provider_id="local_faster_whisper",
            error_code=code,
            error_message=message,
            warnings=(
                CanonicalAsrWarning(
                    code=code,
                    message=message,
                    severity="warning",
                    remediation=remediation,
                ),
            ),
        )

    @classmethod
    def _post_execution_integrity_failure(
        cls,
        *,
        capability: _VerifiedCapabilityContext,
        loaded_model: _LoadedModelContext,
        normalized_audio_path: Path,
        normalized_audio_snapshot: ArtifactSnapshot,
    ) -> CanonicalTranscriptionDraft | None:
        try:
            current_model = fingerprint_model_artifact(
                capability.model_path
            )
        except (
            FileNotFoundError,
            OSError,
            UnsafeModelArtifactError,
        ):
            current_model = None
        if current_model != loaded_model.model_fingerprint:
            return cls._integrity_failed(
                "model_artifact_changed_during_transcription",
                "The pinned model artifact changed during transcription.",
                "Restore the exact immutable model artifact and retry the job.",
            )

        try:
            current_audio = snapshot_regular_file(normalized_audio_path)
        except (
            ArtifactChangedDuringReadError,
            FileNotFoundError,
            OSError,
            UnsafeModelArtifactError,
        ):
            current_audio = None
        if current_audio != normalized_audio_snapshot:
            return cls._integrity_failed(
                "normalized_asset_changed_during_transcription",
                "The normalized audio working copy changed during transcription.",
                "Regenerate and verify the normalized asset before retrying.",
            )
        return None

    def _load_verified_model(
        self,
        capability: _VerifiedCapabilityContext,
    ) -> tuple[_LoadedModelContext | None, CanonicalTranscriptionDraft | None]:
        with self._cache_lock:
            if self._loaded_model is not None:
                if (
                    self._loaded_model.profile_checksum_sha256
                    != capability.profile.profile_checksum_sha256
                ):
                    return None, self._unavailable(
                        "asr_profile_mismatch",
                        "Loaded model profile does not match the current profile.",
                        "Invalidate provider capability state and retry.",
                    )
                return self._loaded_model, None

            try:
                fingerprint_before_load = fingerprint_model_artifact(
                    capability.model_path
                )
            except (
                FileNotFoundError,
                OSError,
                UnsafeModelArtifactError,
            ):
                fingerprint_before_load = None
            if fingerprint_before_load != capability.model_fingerprint:
                return None, self._unavailable(
                    "model_artifact_changed_before_transcription",
                    "The pinned model artifact changed before model loading.",
                    "Restore the exact immutable model artifact and retry.",
                )

            snapshot_before_load = capability.model_snapshot

            try:
                model = self._model_factory(
                    model_size_or_path=str(capability.model_path),
                    device=capability.profile.device,
                    device_index=capability.profile.device_index,
                    compute_type=capability.profile.compute_type,
                    cpu_threads=capability.profile.cpu_threads,
                    num_workers=capability.profile.num_workers,
                    local_files_only=True,
                    revision=capability.profile.model_revision,
                )
            except Exception as exc:  # noqa: BLE001 - classify load safely
                try:
                    snapshot_after_failure = snapshot_model_artifact(
                        capability.model_path
                    )
                except (
                    ArtifactChangedDuringReadError,
                    FileNotFoundError,
                    OSError,
                    UnsafeModelArtifactError,
                ):
                    snapshot_after_failure = None
                if snapshot_after_failure != snapshot_before_load:
                    return None, self._integrity_failed(
                        "model_artifact_changed_during_load",
                        "The pinned model artifact changed during model loading.",
                        "Restore the exact immutable model artifact and retry.",
                    )
                return None, CanonicalTranscriptionDraft(
                    status="failed",
                    provider_id=self.provider_id,
                    error_code="provider_model_load_failed",
                    error_message=(
                        "Local faster-whisper model loading failed: "
                        f"{type(exc).__name__}"
                    ),
                )

            try:
                snapshot_after_load = snapshot_model_artifact(
                    capability.model_path
                )
            except (
                ArtifactChangedDuringReadError,
                FileNotFoundError,
                OSError,
                UnsafeModelArtifactError,
            ):
                snapshot_after_load = None
            if snapshot_after_load != snapshot_before_load:
                return None, self._integrity_failed(
                    "model_artifact_changed_during_load",
                    "The pinned model artifact changed during model loading.",
                    "Restore the exact immutable model artifact and retry.",
                )
            loaded = _LoadedModelContext(
                model=model,
                profile_checksum_sha256=(
                    capability.profile.profile_checksum_sha256
                ),
                model_snapshot=snapshot_after_load,
                model_fingerprint=ArtifactFingerprint(
                    entries=snapshot_after_load.entries
                ),
            )
            self._loaded_model = loaded
            return loaded, None

    def _discover_capability_context(
        self,
    ) -> tuple[_VerifiedCapabilityContext | None, _CapabilityIssue | None]:
        try:
            profile = self._load_profile()
        except AsrProfileLoadError as exc:
            return (
                None,
                (
                    exc.code,
                    str(exc),
                    "Create and verify the immutable benchmark-selected ASR profile.",
                    (),
                ),
            )
        except Exception:  # noqa: BLE001 - configuration inspection fails closed
            return (
                None,
                (
                    "runtime_inspection_failed",
                    "ASR runtime configuration could not be inspected safely.",
                    "Repair the typed ASR runtime configuration and retry.",
                    (),
                ),
            )
        try:
            model_path = self._resolved_model_artifact_path(profile)
            model_snapshot = snapshot_model_artifact(model_path)
        except (UnsafeModelArtifactError, ArtifactChangedDuringReadError):
            return (
                None,
                (
                    "model_artifact_unsafe",
                    "Pinned local ASR model artifact contains an unsafe filesystem entry.",
                    "Install a regular-file-only checksummed model artifact tree.",
                    (),
                ),
            )
        except (FileNotFoundError, OSError):
            return (
                None,
                (
                    "model_artifact_missing",
                    "Pinned local ASR model artifact is missing.",
                    "Install the exact checksummed model artifact selected by the benchmark.",
                    ("model_artifact",),
                ),
            )
        if model_snapshot.checksum_sha256 != profile.model_checksum_sha256:
            return (
                None,
                (
                    "model_checksum_mismatch",
                    "Local ASR model artifact checksum does not match the pinned profile.",
                    "Restore the exact model artifact; do not use a floating model download.",
                    (),
                ),
            )
        model_fingerprint = ArtifactFingerprint(entries=model_snapshot.entries)
        try:
            runtime = self._runtime_inspector()
        except Exception:  # noqa: BLE001 - runtime inspection must stay structured
            return (
                None,
                (
                    "runtime_inspection_failed",
                    "The local ASR runtime could not be inspected safely.",
                    "Repair the pinned runtime dependencies and retry.",
                    (),
                ),
            )
        if runtime.faster_whisper_version is None:
            return (
                None,
                (
                    "faster_whisper_unavailable",
                    "The pinned faster-whisper package is unavailable.",
                    "Install the exact faster-whisper version recorded by the ASR profile.",
                    ("faster-whisper",),
                ),
            )
        if runtime.ctranslate2_version is None:
            return (
                None,
                (
                    "ctranslate2_unavailable",
                    "The pinned CTranslate2 runtime is unavailable.",
                    "Install the exact CTranslate2 version recorded by the ASR profile.",
                    ("ctranslate2",),
                ),
            )
        if not runtime.decoder_available:
            return (
                None,
                (
                    "decoder_unavailable",
                    "The verified normalized-audio decoder is unavailable.",
                    "Restore the pinned decoder runtime and pass its committed fixtures.",
                    ("decoder",),
                ),
            )
        actual_versions = (
            runtime.faster_whisper_version,
            runtime.ctranslate2_version,
            runtime.decoder_name,
            runtime.decoder_version,
        )
        expected_versions = (
            profile.faster_whisper_version,
            profile.ctranslate2_version,
            profile.decoder_name,
            profile.decoder_version,
        )
        if actual_versions != expected_versions:
            return (
                None,
                (
                    "runtime_version_mismatch",
                    "Observed ASR runtime versions do not match the pinned profile.",
                    "Use the exact faster-whisper, CTranslate2, and decoder versions.",
                    (),
                ),
            )
        if not profile.vad_filter or profile.vad_parameters is None:
            return (
                None,
                (
                    "speech_detector_profile_unavailable",
                    "The ASR profile does not pin enabled Silero VAD options.",
                    "Select a verified profile with explicit Silero VAD options.",
                    (),
                ),
            )
        try:
            detector_issue = self._speech_detector.check_availability(
                profile=profile,
                runtime=runtime,
            )
        except Exception:
            detector_issue = (
                "speech_detector_unavailable",
                "The pinned speech detector could not be inspected safely.",
                "Restore the exact Silero VAD runtime and retry.",
                ("faster-whisper-silero-vad",),
            )
        if detector_issue is not None:
            return None, detector_issue
        try:
            fingerprint_after_inspection = fingerprint_model_artifact(
                model_path
            )
        except (
            ArtifactChangedDuringReadError,
            FileNotFoundError,
            OSError,
            UnsafeModelArtifactError,
        ):
            fingerprint_after_inspection = None
        if fingerprint_after_inspection != model_fingerprint:
            return (
                None,
                (
                    "model_artifact_changed_before_transcription",
                    "The pinned model artifact changed during runtime inspection.",
                    "Restore the exact immutable model artifact and retry.",
                    (),
                ),
            )
        return (
            _VerifiedCapabilityContext(
                profile=profile,
                runtime=runtime,
                model_path=model_path,
                model_snapshot=model_snapshot,
                model_fingerprint=model_fingerprint,
            ),
            None,
        )

    def _capability_context(
        self,
    ) -> tuple[_VerifiedCapabilityContext | None, _CapabilityIssue | None]:
        with self._cache_lock:
            if self._capability_checked:
                return (
                    self._cached_capability,
                    self._cached_capability_issue,
                )
            capability, issue = self._discover_capability_context()
            self._cached_capability = capability
            self._cached_capability_issue = issue
            self._capability_checked = True
            return capability, issue

    def invalidate_cached_capability(self) -> None:
        """Explicitly clear local capability/model state before a retry."""

        with self._cache_lock:
            self._capability_checked = False
            self._cached_capability = None
            self._cached_capability_issue = None
            self._loaded_model = None

    def prepare_for_retry(
        self,
        *,
        profile: PinnedAsrProfile,
    ) -> None:
        """Recheck retry capability while preserving an exact loaded model."""

        requested_profile = profile.revalidated()
        with self._cache_lock:
            configured_profile = self._load_profile()
            if configured_profile != requested_profile:
                raise ValueError(
                    "retry profile does not match provider configuration"
                )
            if (
                self._loaded_model is not None
                and self._loaded_model.profile_checksum_sha256
                != requested_profile.profile_checksum_sha256
            ):
                raise ValueError(
                    "loaded model profile does not match retry profile"
                )
            self._capability_checked = False
            self._cached_capability = None
            self._cached_capability_issue = None

    def get_provider_metadata(self) -> dict:
        profile: PinnedAsrProfile | None
        try:
            profile = self._load_profile()
        except Exception:  # noqa: BLE001 - metadata discovery remains fail-closed
            profile = None
        return {
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "description": (
                "Pinned local faster-whisper provider for unreviewed testbed drafts."
            ),
            "is_stub": False,
            "is_mock": False,
            "external_dependencies": [
                "faster-whisper",
                "ctranslate2",
                "pinned local model artifact",
            ],
            "profile_id": profile.profile_id if profile else None,
            "profile_checksum_sha256": (
                profile.profile_checksum_sha256 if profile else None
            ),
            "clinical_caution": (
                "Unreviewed ASR draft only; therapist correction, speaker mapping, "
                "QA, and attestation remain mandatory."
            ),
        }

    def check_availability(self) -> ProviderAvailability:
        _, issue = self._capability_context()
        if issue is not None:
            code, message, remediation, missing = issue
            return ProviderAvailability(
                available=False,
                reason=message,
                reason_code=code,
                remediation=remediation,
                missing_dependencies=missing,
            )
        return ProviderAvailability(
            available=True,
            reason="Pinned local faster-whisper model and runtime are verified.",
            reason_code=None,
        )

    def transcribe(
        self,
        transcription_input: TranscriptionInput,
    ) -> CanonicalTranscriptionDraft:
        if not isinstance(transcription_input, TranscriptionInput):
            raise TypeError(
                "LocalFasterWhisperProvider requires a typed TranscriptionInput."
            )
        try:
            transcription_input = transcription_input.revalidated()
        except ValidationError:
            return self._unavailable(
                "transcription_input_unverified",
                "The transcription input failed integrity validation.",
                "Recreate the job from the current verified profile and audio asset.",
            )

        capability, issue = self._capability_context()
        if issue is not None:
            return self._unavailable(*issue[:3], missing_dependencies=issue[3])
        if capability is None:
            raise RuntimeError("verified ASR capability context is incomplete")
        profile = capability.profile
        runtime = capability.runtime
        if (
            transcription_input.profile is None
            or transcription_input.profile != profile
        ):
            return self._unavailable(
                "asr_profile_mismatch",
                "Transcription input does not reference the verified ASR profile.",
                "Recreate the job using the current immutable ASR profile.",
            )
        audio = transcription_input.normalized_audio
        if audio is None or audio.verification_status != "verified":
            return self._unavailable(
                "normalized_asset_unverified",
                "Normalized audio is not server-verified.",
                "Verify and normalize the current source audio before ASR.",
            )
        if not audio.is_current:
            return self._unavailable(
                "normalized_asset_stale",
                "Normalized audio is not the current source-linked asset.",
                "Regenerate the working asset from the current source version.",
            )
        try:
            audio_snapshot = snapshot_regular_file(
                audio.local_processing_path
            )
        except (UnsafeModelArtifactError, ArtifactChangedDuringReadError):
            return self._unavailable(
                "normalized_asset_unsafe",
                "Normalized audio working copy is not a regular file.",
                "Regenerate the working asset in verified private storage.",
            )
        except (FileNotFoundError, OSError):
            return self._unavailable(
                "normalized_asset_missing",
                "Normalized audio working copy is missing.",
                "Restore and reverify the normalized working asset.",
            )
        if (
            audio_snapshot.checksum_sha256
            != audio.normalized_checksum_sha256
        ):
            return self._unavailable(
                "normalized_asset_checksum_mismatch",
                "Normalized audio checksum does not match its verified lineage.",
                "Regenerate the working asset from the unchanged source audio.",
            )
        loaded_model, model_load_failure = self._load_verified_model(
            capability
        )
        if model_load_failure is not None:
            return model_load_failure
        if loaded_model is None:
            raise RuntimeError("verified local ASR model is unavailable")
        try:
            fingerprint_before_inference = fingerprint_model_artifact(
                capability.model_path
            )
        except (
            FileNotFoundError,
            OSError,
            UnsafeModelArtifactError,
        ):
            fingerprint_before_inference = None
        if (
            fingerprint_before_inference
            != loaded_model.model_fingerprint
        ):
            return self._integrity_failed(
                "model_artifact_changed_after_load",
                "The model artifact changed after the verified eager load.",
                "Restore the exact immutable model artifact and retry.",
            )

        if profile.vad_parameters is None:
            return self._unavailable(
                "speech_detector_profile_unavailable",
                "The ASR profile does not pin Silero VAD options.",
                "Select a verified profile with explicit Silero VAD options.",
            )
        detector_version = (
            f"faster-whisper:{runtime.faster_whisper_version}"
        )
        try:
            speech_evidence = self._speech_detector.detect(
                audio.local_processing_path,
                normalized_audio_checksum_sha256=(
                    audio.normalized_checksum_sha256
                ),
                vad_parameters=profile.vad_parameters,
                detector_version=detector_version,
            )
            if not isinstance(
                speech_evidence,
                SpeechDetectionEvidence,
            ):
                raise TypeError(
                    "speech detector returned an untyped result"
                )
            speech_evidence = speech_evidence.revalidated()
        except Exception as exc:
            return CanonicalTranscriptionDraft(
                status="failed",
                provider_id=self.provider_id,
                error_code="speech_detection_failed",
                error_message=(
                    "Pinned speech detection failed: "
                    f"{type(exc).__name__}"
                ),
            )
        if (
            speech_evidence.detector_id
            != self._speech_detector.detector_id
            or speech_evidence.detector_version != detector_version
            or speech_evidence.sample_rate_hz != 16_000
            or speech_evidence.normalized_audio_checksum_sha256
            != audio.normalized_checksum_sha256
            or speech_evidence.vad_parameters != profile.vad_parameters
        ):
            return self._integrity_failed(
                "speech_detection_evidence_invalid",
                "Speech detection evidence does not match the exact runtime, "
                "profile, or normalized asset.",
                "Regenerate speech evidence from the unchanged 16 kHz asset.",
            )

        try:
            segment_iterator, info = loaded_model.model.transcribe(
                str(audio.local_processing_path),
                language=(
                    profile.language_mode
                    if profile.language_mode == "th"
                    else None
                ),
                task=profile.task,
                log_progress=profile.log_progress,
                beam_size=profile.beam_size,
                best_of=profile.best_of,
                patience=profile.patience,
                length_penalty=profile.length_penalty,
                repetition_penalty=profile.repetition_penalty,
                no_repeat_ngram_size=profile.no_repeat_ngram_size,
                temperature=profile.temperature,
                compression_ratio_threshold=profile.compression_ratio_threshold,
                log_prob_threshold=profile.log_prob_threshold,
                no_speech_threshold=profile.no_speech_threshold,
                vad_filter=profile.vad_filter,
                vad_parameters=(
                    profile.vad_parameters.model_dump()
                    if profile.vad_parameters is not None
                    else None
                ),
                word_timestamps=profile.word_timestamps,
                condition_on_previous_text=profile.condition_on_previous_text,
                prompt_reset_on_temperature=profile.prompt_reset_on_temperature,
                initial_prompt=profile.initial_prompt,
                prefix=profile.prefix,
                suppress_blank=profile.suppress_blank,
                suppress_tokens=(
                    list(profile.suppress_tokens)
                    if profile.suppress_tokens is not None
                    else None
                ),
                without_timestamps=profile.without_timestamps,
                max_initial_timestamp=profile.max_initial_timestamp,
                prepend_punctuations=profile.prepend_punctuations,
                append_punctuations=profile.append_punctuations,
                multilingual=profile.multilingual,
                max_new_tokens=profile.max_new_tokens,
                chunk_length=profile.chunk_length,
                clip_timestamps=profile.clip_timestamps,
                hallucination_silence_threshold=(
                    profile.hallucination_silence_threshold
                ),
                hotwords=profile.hotwords,
                language_detection_threshold=(
                    profile.language_detection_threshold
                ),
                language_detection_segments=profile.language_detection_segments,
            )
            raw_segments: list[RawProviderSegment] = []
            canonical_segments: list[CanonicalTranscriptionSegment] = []
            for index, segment in enumerate(segment_iterator, start=1):
                start_ms = int(round(float(segment.start) * 1000))
                end_ms = int(round(float(segment.end) * 1000))
                if start_ms < 0 or end_ms < start_ms:
                    return CanonicalTranscriptionDraft(
                        status="failed",
                        provider_id=self.provider_id,
                        error_code="provider_timestamp_invalid",
                        error_message=(
                            "Provider emitted a negative or reversed segment timestamp."
                        ),
                    )
                text = str(segment.text).strip()
                segment_id = canonical_asr_segment_id(
                    normalized_audio_checksum_sha256=(
                        audio.normalized_checksum_sha256
                    ),
                    ordinal=index,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text,
                )
                canonical_segments.append(
                    CanonicalTranscriptionSegment(
                        segment_id=segment_id,
                        temporary_speaker_id="UNK",
                        source_speaker_label="UNK",
                        start_ms=start_ms,
                        end_ms=end_ms,
                        text=text,
                        confidence=None,
                    )
                )
                words = tuple(
                    RawProviderWord(
                        start_seconds=getattr(word, "start", None),
                        end_seconds=getattr(word, "end", None),
                        text=str(getattr(word, "word", "")),
                        probability=getattr(word, "probability", None),
                    )
                    for word in (getattr(segment, "words", None) or [])
                )
                raw_segments.append(
                    RawProviderSegment(
                        provider_segment_id=str(getattr(segment, "id", index - 1)),
                        seek=getattr(segment, "seek", None),
                        start_seconds=float(segment.start),
                        end_seconds=float(segment.end),
                        text=str(segment.text),
                        token_ids=tuple(
                            getattr(segment, "tokens", []) or []
                        ),
                        temperature=getattr(segment, "temperature", None),
                        average_log_probability=getattr(segment, "avg_logprob", None),
                        compression_ratio=getattr(segment, "compression_ratio", None),
                        no_speech_probability=getattr(segment, "no_speech_prob", None),
                        words=words,
                    )
                )
            integrity_failure = self._post_execution_integrity_failure(
                capability=capability,
                loaded_model=loaded_model,
                normalized_audio_path=audio.local_processing_path,
                normalized_audio_snapshot=audio_snapshot,
            )
            if integrity_failure is not None:
                return integrity_failure
            raw_payload = RawProviderPayload(
                provider_id=self.provider_id,
                language=str(getattr(info, "language", "und") or "und"),
                language_probability=getattr(info, "language_probability", None),
                duration_seconds=getattr(info, "duration", None),
                duration_after_vad_seconds=getattr(
                    info,
                    "duration_after_vad",
                    None,
                ),
                speech_detection_evidence=speech_evidence,
                segments=tuple(raw_segments),
            )
            raw_checksum = canonical_raw_provider_payload_checksum(raw_payload)
            input_lineage_checksum = canonical_input_lineage_checksum(
                provider_id=self.provider_id,
                source_audio_file_id=audio.source_audio_file_id,
                source_audio_asset_version=audio.source_asset_version,
                source_audio_checksum_sha256=audio.source_checksum_sha256,
                normalized_audio_asset_version=(
                    audio.normalized_asset_version
                ),
                normalized_audio_checksum_sha256=(
                    audio.normalized_checksum_sha256
                ),
                profile_id=profile.profile_id,
                profile_version=profile.profile_version,
                profile_checksum_sha256=profile.profile_checksum_sha256,
            )
            decoding_projection = (
                AsrProfileProvenanceProjection.from_pinned_profile(
                    profile,
                    runtime,
                )
            )
            provenance = CanonicalAsrProvenance(
                **decoding_projection.model_dump(),
                provider_id=self.provider_id,
                provider_version=self.provider_version,
                detected_language=raw_payload.language,
                detected_language_probability=(
                    raw_payload.language_probability
                ),
                source_audio_file_id=audio.source_audio_file_id,
                source_audio_asset_version=audio.source_asset_version,
                source_audio_checksum_sha256=audio.source_checksum_sha256,
                normalized_audio_asset_version=audio.normalized_asset_version,
                normalized_audio_checksum_sha256=audio.normalized_checksum_sha256,
                normalized_audio_object_key=audio.normalized_object_key,
                raw_provider_payload_checksum_sha256=raw_checksum,
                speech_detection_evidence_checksum_sha256=(
                    speech_evidence.evidence_checksum_sha256
                ),
                input_lineage_checksum_sha256=input_lineage_checksum,
                decoding_provenance_checksum_sha256=(
                    canonical_decoding_provenance_checksum(
                        decoding_projection
                    )
                ),
            )
            warnings = [
                CanonicalAsrWarning(
                    code="asr_diarization_not_used",
                    message=(
                        "Speaker diarization was not used; all temporary "
                        "speaker labels are UNK."
                    ),
                    severity="limitation",
                    remediation=(
                        "Review every segment and confirm the speaker mapping."
                    ),
                ),
                CanonicalAsrWarning(
                    code="asr_therapist_review_required",
                    message=(
                        "Therapist review and confirmed speaker mapping are required."
                    ),
                    severity="info",
                    remediation=(
                        "Correct the draft and confirm participant-to-speaker roles."
                    ),
                ),
            ]
            if profile.language_mode == "auto":
                language_probability = raw_payload.language_probability
                threshold = profile.language_detection_threshold
                if language_probability is None:
                    warnings.append(
                        CanonicalAsrWarning(
                            code="asr_language_confidence_unavailable",
                            message=(
                                "Automatic language confidence is unavailable."
                            ),
                            severity="warning",
                            remediation=(
                                "Review the detected language before accepting "
                                "the draft."
                            ),
                        )
                    )
                elif (
                    threshold is not None
                    and language_probability < threshold
                ):
                    warnings.append(
                        CanonicalAsrWarning(
                            code=(
                                "asr_language_confidence_below_threshold"
                            ),
                            message=(
                                "Automatic language confidence is below the "
                                "pinned profile threshold."
                            ),
                            severity="warning",
                            remediation=(
                                "Review the detected language before accepting "
                                "the draft."
                            ),
                        )
                    )
            return CanonicalTranscriptionDraft(
                status="completed",
                provider_id=self.provider_id,
                segments=tuple(canonical_segments),
                language=raw_payload.language,
                warnings=tuple(warnings),
                provenance=provenance,
                speech_detection_evidence=speech_evidence,
                raw_provider_payload=raw_payload,
            )
        except Exception as exc:  # noqa: BLE001 - provider failures stay structured
            integrity_failure = self._post_execution_integrity_failure(
                capability=capability,
                loaded_model=loaded_model,
                normalized_audio_path=audio.local_processing_path,
                normalized_audio_snapshot=audio_snapshot,
            )
            if integrity_failure is not None:
                return integrity_failure
            return CanonicalTranscriptionDraft(
                status="failed",
                provider_id=self.provider_id,
                error_code="provider_execution_failed",
                error_message=f"Local faster-whisper execution failed: {type(exc).__name__}",
            )
