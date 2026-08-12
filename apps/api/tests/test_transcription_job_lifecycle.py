from __future__ import annotations

from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import multiprocessing
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.routes.jobs import _public_processing_job, retry_job
from app.core.security import CurrentUser
from app.core.config import Settings
from app.main import app
from app.repositories.base import ProcessingJobStateConflictError
from app.repositories.mock_repository import JsonFileRepository, MockRepository
from app.schemas.clinical import (
    AudioFileMetadata,
    JobStatus,
    ProcessingJob,
    ReviewStatus,
    Transcript,
    TranscriptionJobRequest,
)
from app.schemas.speech_pipeline import (
    ArtifactStatus,
    AudioNormalizationProvenance,
    NormalizedAudioAsset,
)
from app.services.asr_completeness_service import (
    AsrJobRuntimeProfile,
    canonical_job_runtime_profile_checksum,
)
from app.services.asr_profiles import (
    AsrRuntimeVersions,
    PinnedAsrProfile,
    PinnedVadParameters,
    canonical_profile_checksum,
    hash_model_artifact,
)
from app.services.asr_providers.base import (
    AsrProfileProvenanceProjection,
    CanonicalAsrProvenance,
    CanonicalTranscriptionDraft,
    CanonicalTranscriptionSegment,
    ProviderAvailability,
    RawProviderPayload,
    RawProviderSegment,
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
from app.services.asr_providers.local_whisper_provider import (
    LocalWhisperProvider,
)
from app.services.audio_job_service import (
    AudioIntakeError,
    TranscriptionJobContractError,
    build_transcription_idempotency_key,
    create_audio_processing_job,
    load_job_runtime_profile,
    retry_audio_processing_job,
    run_audio_processing_job,
)
from app.services.consent_service import withdraw_consent
from app.tasks.job_queue import (
    AsrExecutionMetrics,
    AsrExecutionOutcome,
    AsrExecutionTimeout,
)


SOURCE_BYTES = b"source-audio"
NORMALIZED_BYTES = b"normalized-audio"
SOURCE_CHECKSUM = sha256(SOURCE_BYTES).hexdigest()
NORMALIZED_CHECKSUM = sha256(NORMALIZED_BYTES).hexdigest()
STORAGE_BACKEND_IDENTITY = "f" * 64


def _asr_profile(**overrides: object) -> PinnedAsrProfile:
    values: dict[str, object] = {
        "profile_id": "v170-job-test-profile",
        "profile_version": 1,
        "model_identifier": "synthetic-whisper",
        "model_revision": "fixture-revision-001",
        "model_artifact_path": Path("/synthetic/model"),
        "model_checksum_sha256": "a" * 64,
        "faster_whisper_version": "1.2.1",
        "ctranslate2_version": "4.8.1",
        "decoder_name": "soundfile",
        "decoder_version": "0.14.0",
        "device": "cpu",
        "device_index": 0,
        "compute_type": "int8",
        "cpu_threads": 2,
        "num_workers": 1,
        "language_mode": "th",
        "task": "transcribe",
        "log_progress": False,
        "beam_size": 5,
        "best_of": 5,
        "patience": 1.0,
        "length_penalty": 1.0,
        "repetition_penalty": 1.0,
        "no_repeat_ngram_size": 0,
        "temperature": 0.0,
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "vad_filter": True,
        "vad_parameters": {
            "threshold": 0.5,
            "neg_threshold": 0.35,
            "min_speech_duration_ms": 250,
            "max_speech_duration_s": 30.0,
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 100,
        },
        "word_timestamps": True,
        "condition_on_previous_text": False,
        "prompt_reset_on_temperature": 0.5,
        "initial_prompt": None,
        "prefix": None,
        "suppress_blank": True,
        "suppress_tokens": [-1],
        "without_timestamps": False,
        "max_initial_timestamp": 1.0,
        "prepend_punctuations": "\"'“¿([{-",
        "append_punctuations": "\"'.。,，!！?？:：”)]}、",
        "multilingual": False,
        "max_new_tokens": None,
        "chunk_length": None,
        "clip_timestamps": "0",
        "hallucination_silence_threshold": None,
        "hotwords": None,
        "language_detection_threshold": 0.5,
        "language_detection_segments": 1,
    }
    values.update(overrides)
    values["profile_checksum_sha256"] = canonical_profile_checksum(values)
    return PinnedAsrProfile.model_validate(values)


def _runtime_profile(
    asr_profile: PinnedAsrProfile,
    **overrides: object,
) -> AsrJobRuntimeProfile:
    values: dict[str, object] = {
        "profile_id": "synthetic-runtime-v1",
        "profile_version": 1,
        "asr_profile_checksum_sha256": (
            asr_profile.profile_checksum_sha256
        ),
        "benchmark_result_checksum_sha256": "b" * 64,
        "fixture_manifest_checksum_sha256": "c" * 64,
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


def _speech_detection_evidence(
    *,
    normalized_checksum_sha256: str = NORMALIZED_CHECKSUM,
) -> SpeechDetectionEvidence:
    vad_parameters = PinnedVadParameters(
        threshold=0.5,
        neg_threshold=0.35,
        min_speech_duration_ms=250,
        max_speech_duration_s=30.0,
        min_silence_duration_ms=500,
        speech_pad_ms=100,
    )
    values: dict[str, object] = {
        "detector_id": "faster_whisper_silero_vad",
        "detector_version": "faster-whisper:1.2.1",
        "sample_rate_hz": 16_000,
        "normalized_audio_checksum_sha256": normalized_checksum_sha256,
        "vad_parameters": vad_parameters,
        "vad_config_checksum_sha256": canonical_vad_config_checksum(
            vad_parameters
        ),
        "intervals": (
            SpeechDetectionInterval(start_ms=100, end_ms=9_900),
        ),
    }
    values["evidence_checksum_sha256"] = (
        canonical_speech_detection_evidence_checksum(values)
    )
    return SpeechDetectionEvidence.model_validate(values)


def _normalization_provenance() -> AudioNormalizationProvenance:
    profile_name = "v170-test-normalization"
    return AudioNormalizationProvenance(
        source_size_bytes=len(SOURCE_BYTES),
        source_detected_format="wav",
        source_duration_ms=10_000,
        source_frame_count=160_000,
        source_sample_rate_hz=16_000,
        source_channels=1,
        normalized_size_bytes=len(NORMALIZED_BYTES),
        boundary_frames_verified=True,
        decoder_library_name="soundfile",
        decoder_library_version="0.14.0",
        mixer_name="numpy.mean",
        mixer_version="2.4.4",
        resampler_name="scipy.signal.resample_poly",
        resampler_version="1.17.1",
        writer_name="soundfile.write",
        writer_version="0.14.0",
        writer_library_name="libsndfile",
        writer_library_version="1.2.2",
        processing_dtype="float32",
        streaming_block_frames=4_096,
        overlap_frames=0,
        resample_window="kaiser-5.0",
        filter_profile="scipy-default-v1",
        padding_policy="constant-zero",
        normalization_profile=profile_name,
        profile_checksum_sha256=sha256(
            profile_name.encode("utf-8")
        ).hexdigest(),
    )


def _repo_with_verified_audio() -> tuple[MockRepository, str]:
    repo = MockRepository()
    audio = AudioFileMetadata(
        audio_file_id="audio-synthetic-001",
        organization_id="pilot_org_001",
        session_id="session_demo_001",
        case_id="case_demo_001",
        original_filename="synthetic.wav",
        content_type="audio/wav",
        size_bytes=len(SOURCE_BYTES),
        storage_mode="local_private",
        storage_backend_identity_sha256=STORAGE_BACKEND_IDENTITY,
        object_key="audio/source.wav",
        upload_status="uploaded",
        duration_seconds=10.0,
        sample_rate_hz=16_000,
        channels=1,
        checksum_sha256=SOURCE_CHECKSUM,
        source_asset_version=1,
        uploaded_at=datetime.now(timezone.utc),
    )
    repo.audio_files[audio.audio_file_id] = audio
    repo.create_normalized_audio_asset(
        NormalizedAudioAsset(
            organization_id=audio.organization_id,
            session_id=audio.session_id,
            asset_version=1,
            object_key="normalized/audio.wav",
            source_checksum_sha256=SOURCE_CHECKSUM,
            normalized_checksum_sha256=NORMALIZED_CHECKSUM,
            format="wav_pcm_s16le",
            duration_ms=10_000,
            sample_rate_hz=16_000,
            channels=1,
            frame_count=160_000,
            decoder_name="soundfile",
            decoder_version="0.14.0",
            conversion_command_profile="v170-test-normalization",
            verification_status="verified",
            provenance=_normalization_provenance(),
            source_audio_file_id=audio.audio_file_id,
            source_asset_version=1,
            created_at=datetime.now(timezone.utc),
            status=ArtifactStatus.current,
        )
    )
    return repo, audio.audio_file_id


def _seed_durable_repo(repo) -> str:
    template, audio_file_id = _repo_with_verified_audio()
    repo.audio_files[audio_file_id] = repo.clone(
        template.audio_files[audio_file_id]
    )
    for key, normalized in template.normalized_audio_assets.items():
        repo.normalized_audio_assets[key] = repo.clone(normalized)
    repo.save()
    return audio_file_id


def _durable_repo_factory(tmp_path: Path, backend: str):
    if backend == "json":
        path = tmp_path / "repository.json"
        seed = JsonFileRepository(path)
        audio_file_id = _seed_durable_repo(seed)
        return lambda: JsonFileRepository(path), audio_file_id

    from app.repositories.sqlalchemy_repository import SqlAlchemyRepository

    database_url = f"sqlite:///{tmp_path / 'repository.db'}"
    seed = SqlAlchemyRepository(database_url)
    audio_file_id = _seed_durable_repo(seed)
    return lambda: SqlAlchemyRepository(database_url), audio_file_id


def _json_process_cas_candidate(
    repository_path: str,
    job_id: str,
    target_status: str,
    start_event,
    result_queue,
) -> None:
    repo = JsonFileRepository(Path(repository_path))
    candidate = repo.get_processing_job(job_id)
    assert candidate is not None
    candidate.status = JobStatus(target_status)
    candidate.message = f"cross-process candidate {target_status}"
    start_event.wait()
    try:
        repo.update_processing_job(
            candidate,
            expected_status=JobStatus.queued,
            audit_action=f"test.json.cas.{target_status}",
            audit_message="Cross-process JSON CAS candidate.",
        )
    except ProcessingJobStateConflictError:
        result_queue.put("conflict")
    else:
        result_queue.put(target_status)


def _request(audio_file_id: str) -> TranscriptionJobRequest:
    return TranscriptionJobRequest(
        audio_file_id=audio_file_id,
        expected_source_asset_version=1,
        expected_normalized_asset_version=1,
    )


class FakeStorage:
    storage_mode = "local_private"

    def validate_storage_backend_identity(self, expected_identity):
        assert expected_identity == STORAGE_BACKEND_IDENTITY

    @contextmanager
    def open_normalized_for_processing(
        self,
        object_key: str,
        *,
        max_size_bytes: int,
    ):
        assert object_key == "normalized/audio.wav"
        assert len(NORMALIZED_BYTES) <= max_size_bytes
        yield BytesIO(NORMALIZED_BYTES)


class ConsentCleanupStorage:
    def validate_storage_backend_identity(self, expected_identity):
        assert expected_identity == STORAGE_BACKEND_IDENTITY

    def delete_object(self, object_key):
        return SimpleNamespace(status="deleted")


class FakeCanonicalProvider:
    provider_id = "local_faster_whisper"
    provider_name = "FakeLocalFasterWhisper"
    provider_version = "v1.7.0-test"

    def __init__(
        self,
        *,
        available: bool = True,
        result_status: str = "completed",
        empty: bool = False,
        partial: bool = False,
        include_speech_evidence: bool = True,
    ) -> None:
        self.available = available
        self.result_status = result_status
        self.empty = empty
        self.partial = partial
        self.include_speech_evidence = include_speech_evidence
        self.availability_calls = 0
        self.prepare_for_retry_calls: list[str] = []
        self.transcribe_calls = 0
        self.last_input: TranscriptionInput | None = None

    def check_availability(self) -> ProviderAvailability:
        self.availability_calls += 1
        return ProviderAvailability(
            available=self.available,
            reason="" if self.available else "synthetic model missing",
            reason_code=None if self.available else "model_artifact_missing",
            remediation=(
                None
                if self.available
                else "Restore the exact immutable model artifact."
            ),
            missing_dependencies=(
                ()
                if self.available
                else ("synthetic-model",)
            ),
        )

    def prepare_for_retry(self, *, profile: PinnedAsrProfile) -> None:
        self.prepare_for_retry_calls.append(
            profile.profile_checksum_sha256
        )

    def transcribe(self, transcription_input: TranscriptionInput):
        self.transcribe_calls += 1
        self.last_input = transcription_input
        assert transcription_input.normalized_audio is not None
        assert (
            transcription_input.normalized_audio.local_processing_path.read_bytes()
            == NORMALIZED_BYTES
        )
        if self.result_status != "completed":
            return SimpleNamespace(
                status=self.result_status,
                provider_id=self.provider_id,
                segments=(),
                transcript_lines=[],
                warnings=(),
                error_code="provider_partial_result",
                error_message="Provider reported a partial result.",
                unavailability=None,
                provider_metadata={"partial_result": self.partial},
                computed_at=datetime.now(timezone.utc),
            )
        if self.empty:
            return SimpleNamespace(
                status="completed",
                provider_id=self.provider_id,
                segments=(),
                transcript_lines=[],
                warnings=(),
                provider_metadata={"partial_result": self.partial},
                speech_detection_evidence=_speech_detection_evidence(),
            )
        provider_metadata = {"partial_result": self.partial}
        speech_detection_evidence = (
            _speech_detection_evidence()
            if self.include_speech_evidence
            else None
        )
        if speech_detection_evidence is None:
            return SimpleNamespace(
                status="completed",
                provider_id=self.provider_id,
                segments=(
                    SimpleNamespace(
                        segment_id="segment-001",
                        temporary_speaker_id="UNK",
                        source_speaker_label="UNK",
                        start_ms=100,
                        end_ms=4_000,
                        text="สวัสดี blue cup",
                        confidence=None,
                    ),
                ),
                warnings=(),
                provider_metadata=provider_metadata,
                speech_detection_evidence=None,
            )
        assert speech_detection_evidence is not None
        assert transcription_input.profile is not None
        assert transcription_input.normalized_audio is not None
        raw_segments = (
            RawProviderSegment(
                provider_segment_id="segment-001",
                seek=0,
                start_seconds=0.1,
                end_seconds=4.0,
                text="สวัสดี blue cup",
                token_ids=(1, 2),
                words=(),
            ),
            RawProviderSegment(
                provider_segment_id="segment-002",
                seek=0,
                start_seconds=4.0,
                end_seconds=9.9,
                text="จบหนึ่งเจ็ดศูนย์",
                token_ids=(3, 4),
                words=(),
            ),
        )
        raw_payload = RawProviderPayload(
            provider_id=self.provider_id,
            language="th",
            language_probability=0.99,
            duration_seconds=10.0,
            duration_after_vad_seconds=9.8,
            speech_detection_evidence=speech_detection_evidence,
            segments=raw_segments,
        )
        raw_checksum = canonical_raw_provider_payload_checksum(raw_payload)
        runtime = AsrRuntimeVersions(
            faster_whisper_version="1.2.1",
            ctranslate2_version="4.8.1",
            decoder_name="soundfile",
            decoder_version="0.14.0",
            decoder_available=True,
        )
        projection = AsrProfileProvenanceProjection.from_pinned_profile(
            transcription_input.profile,
            runtime,
        )
        normalized = transcription_input.normalized_audio
        provenance = CanonicalAsrProvenance(
            **projection.model_dump(mode="python"),
            provider_id=self.provider_id,
            provider_version=self.provider_version,
            detected_language="th",
            detected_language_probability=0.99,
            source_audio_file_id=normalized.source_audio_file_id,
            source_audio_asset_version=normalized.source_asset_version,
            source_audio_checksum_sha256=normalized.source_checksum_sha256,
            normalized_audio_asset_version=normalized.normalized_asset_version,
            normalized_audio_checksum_sha256=(
                normalized.normalized_checksum_sha256
            ),
            normalized_audio_object_key=normalized.normalized_object_key,
            raw_provider_payload_checksum_sha256=raw_checksum,
            speech_detection_evidence_checksum_sha256=(
                speech_detection_evidence.evidence_checksum_sha256
            ),
            input_lineage_checksum_sha256=canonical_input_lineage_checksum(
                provider_id=self.provider_id,
                source_audio_file_id=normalized.source_audio_file_id,
                source_audio_asset_version=normalized.source_asset_version,
                source_audio_checksum_sha256=normalized.source_checksum_sha256,
                normalized_audio_asset_version=normalized.normalized_asset_version,
                normalized_audio_checksum_sha256=normalized.normalized_checksum_sha256,
                profile_id=transcription_input.profile.profile_id,
                profile_version=transcription_input.profile.profile_version,
                profile_checksum_sha256=transcription_input.profile.profile_checksum_sha256,
            ),
            decoding_provenance_checksum_sha256=(
                canonical_decoding_provenance_checksum(projection)
            ),
        )
        segments = tuple(
            CanonicalTranscriptionSegment(
                segment_id=canonical_asr_segment_id(
                    normalized_audio_checksum_sha256=(
                        normalized.normalized_checksum_sha256
                    ),
                    ordinal=ordinal,
                    start_ms=int(round(raw.start_seconds * 1000)),
                    end_ms=int(round(raw.end_seconds * 1000)),
                    text=raw.text.strip(),
                ),
                temporary_speaker_id="UNK",
                source_speaker_label="UNK",
                start_ms=int(round(raw.start_seconds * 1000)),
                end_ms=int(round(raw.end_seconds * 1000)),
                text=raw.text.strip(),
            )
            for ordinal, raw in enumerate(raw_segments, start=1)
        )
        draft = CanonicalTranscriptionDraft(
            status="completed",
            provider_id=self.provider_id,
            segments=segments,
            language="th",
            provenance=provenance,
            speech_detection_evidence=speech_detection_evidence,
            raw_provider_payload=raw_payload,
        )
        if self.partial:
            return _mutable_provider_result(
                draft,
                provider_metadata={"partial_result": True},
            )
        return draft


def _mutable_provider_result(result, **overrides):
    values = {
        "status": result.status,
        "provider_id": result.provider_id,
        "provider_name": result.provider_name,
        "provider_version": result.provider_version,
        "segments": result.segments,
        "transcript_lines": result.transcript_lines,
        "language": result.language,
        "confidence_available": result.confidence_available,
        "word_timestamps_available": result.word_timestamps_available,
        "speaker_segments_available": result.speaker_segments_available,
        "warnings": result.warnings,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "unavailability": result.unavailability,
        "provider_metadata": result.provider_metadata,
        "speech_detection_evidence": result.speech_detection_evidence,
        "provenance": result.provenance,
        "to_private_record": result.to_private_record,
        "raw_provider_payload": result.raw_provider_payload,
        "computed_at": result.computed_at,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeRegistry:
    def __init__(self, provider: FakeCanonicalProvider) -> None:
        self.provider = provider
        self.requested_ids: list[str] = []

    def get(self, provider_id: str) -> FakeCanonicalProvider:
        self.requested_ids.append(provider_id)
        if provider_id != "local_faster_whisper":
            raise AssertionError("normal jobs must never resolve another provider")
        return self.provider


def _fixed_execution_runner(operation, **kwargs):
    return AsrExecutionOutcome(
        value=operation(),
        metrics=AsrExecutionMetrics(
            cold_warm_mode="cold",
            execution_isolation_mode="one_shot_isolated_process",
            warm_reuse_capability=(
                "unavailable_one_shot_isolation"
            ),
            started_monotonic_seconds=10.0,
            ended_monotonic_seconds=12.5,
            wall_time_seconds=2.5,
            cpu_time_seconds=1.25,
            peak_resident_memory_bytes=123_456,
            timeout_seconds=kwargs["timeout_seconds"],
            timeout_profile_checksum_sha256=kwargs[
                "timeout_profile_checksum_sha256"
            ],
            termination_reason="completed",
        ),
    )


def test_normal_job_request_has_only_upload_first_fields() -> None:
    fields = set(TranscriptionJobRequest.model_fields)
    assert fields == {
        "audio_file_id",
        "provider_id",
        "expected_source_asset_version",
        "expected_normalized_asset_version",
    }
    request = TranscriptionJobRequest(
        audio_file_id="audio-1",
        expected_source_asset_version=1,
        expected_normalized_asset_version=1,
    )
    assert request.provider_id == "local_faster_whisper"

    for legacy in (
        {"audio_id": "audio-1"},
        {"provider": "mock"},
        {"draft_text": "fabricated"},
        {"allow_fallback_to_mock": True},
        {"config": {"allow_fallback_to_mock": True}},
    ):
        with pytest.raises(ValidationError):
            TranscriptionJobRequest.model_validate(
                {
                    "audio_file_id": "audio-1",
                    "expected_source_asset_version": 1,
                    "expected_normalized_asset_version": 1,
                    **legacy,
                }
            )


def test_openapi_exposes_only_strict_process_contract_and_typed_retry() -> None:
    schema = app.openapi()
    process = schema["paths"][
        "/api/v1/sessions/{session_id}/audio/process"
    ]["post"]
    request_schema = process["requestBody"]["content"][
        "application/json"
    ]["schema"]

    assert request_schema == {
        "$ref": "#/components/schemas/TranscriptionJobRequest"
    }
    properties = schema["components"]["schemas"][
        "TranscriptionJobRequest"
    ]["properties"]
    assert set(properties) == {
        "audio_file_id",
        "provider_id",
        "expected_source_asset_version",
        "expected_normalized_asset_version",
    }
    retry = schema["paths"]["/api/v1/jobs/{job_id}/retry"]["post"]
    assert "requestBody" not in retry


def test_idempotency_key_binds_exact_audio_provider_and_both_profiles() -> None:
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    key = build_transcription_idempotency_key(
        audio_file_id="audio-synthetic-001",
        source_asset_version=1,
        normalized_asset_version=2,
        normalized_checksum_sha256=NORMALIZED_CHECKSUM,
        provider_id="local_faster_whisper",
        asr_profile_checksum_sha256=(
            asr_profile.profile_checksum_sha256
        ),
        runtime_profile_checksum_sha256=(
            runtime_profile.profile_checksum_sha256
        ),
    )

    assert key == (
        "c2a8eadbc207ee23ff4999d277d7ec863e35c3c8251a2c7b190cdae43df9a732"
    )
    changed = build_transcription_idempotency_key(
        audio_file_id="audio-synthetic-001",
        source_asset_version=1,
        normalized_asset_version=2,
        normalized_checksum_sha256="d" * 64,
        provider_id="local_faster_whisper",
        asr_profile_checksum_sha256=(
            asr_profile.profile_checksum_sha256
        ),
        runtime_profile_checksum_sha256=(
            runtime_profile.profile_checksum_sha256
        ),
    )
    assert changed != key
    changed_runtime = build_transcription_idempotency_key(
        audio_file_id="audio-synthetic-001",
        source_asset_version=1,
        normalized_asset_version=2,
        normalized_checksum_sha256=NORMALIZED_CHECKSUM,
        provider_id="local_faster_whisper",
        asr_profile_checksum_sha256=(
            asr_profile.profile_checksum_sha256
        ),
        runtime_profile_checksum_sha256=(
            _runtime_profile(
                asr_profile,
                timeout_seconds=43,
            ).profile_checksum_sha256
        ),
    )
    assert changed_runtime != key


def test_no_job_is_created_without_current_verified_normalization() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    repo.normalized_audio_assets.clear()
    provider = FakeCanonicalProvider()

    with pytest.raises(
        AudioIntakeError,
        match="audio_normalization_required",
    ):
        create_audio_processing_job(
            repo,
            "session_demo_001",
            _request(audio_file_id),
            provider_registry=FakeRegistry(provider),
            asr_profile=_asr_profile(),
            runtime_profile=_runtime_profile(_asr_profile()),
        )

    assert repo.jobs == {}
    assert provider.availability_calls == 0
    assert provider.transcribe_calls == 0


def test_no_job_is_created_for_source_marked_uploaded_but_unverified() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    repo.audio_files[audio_file_id].checksum_sha256 = None
    provider = FakeCanonicalProvider()
    asr_profile = _asr_profile()

    with pytest.raises(
        AudioIntakeError,
        match="source_audio_unverified",
    ):
        create_audio_processing_job(
            repo,
            "session_demo_001",
            _request(audio_file_id),
            provider_registry=FakeRegistry(provider),
            asr_profile=asr_profile,
            runtime_profile=_runtime_profile(asr_profile),
        )

    assert repo.jobs == {}
    assert provider.availability_calls == 0
    assert provider.transcribe_calls == 0


@pytest.mark.parametrize(
    "provider_id",
    ["mock", "manual", "whisper", "cloud-asr"],
)
def test_normal_job_never_invokes_mock_manual_or_cloud_provider(
    provider_id: str,
) -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider()
    registry = FakeRegistry(provider)
    payload = _request(audio_file_id).model_copy(
        update={"provider_id": provider_id}
    )

    with pytest.raises(
        TranscriptionJobContractError,
        match="provider_not_allowed",
    ):
        create_audio_processing_job(
            repo,
            "session_demo_001",
            payload,
            provider_registry=registry,
            asr_profile=_asr_profile(),
            runtime_profile=_runtime_profile(_asr_profile()),
        )

    assert registry.requested_ids == []
    assert repo.jobs == {}


@pytest.mark.parametrize(
    ("profile_state", "expected_error"),
    [
        ("missing", "runtime_profile_unavailable"),
        ("unverified", "runtime_profile_unverified"),
    ],
)
def test_unbound_runtime_profile_is_nonretryable_and_fresh_create_is_new(
    tmp_path: Path,
    profile_state: str,
    expected_error: str,
) -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider()
    asr_profile = _asr_profile()

    runtime_profile_path = tmp_path / "runtime-profile.json"
    if profile_state == "unverified":
        runtime_profile_path.write_text(
            '{"job_runtime":{"verified":false}}',
            encoding="utf-8",
        )
    job = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        settings=Settings(
            asr_runtime_profile_path=str(runtime_profile_path)
        ),
        asr_profile=asr_profile,
    )

    assert job.status is JobStatus.failed
    assert job.error_code == expected_error
    assert job.details["retry_allowed"] is False
    assert job.details["remediation"] == (
        "Restore or select a verified versioned runtime profile, then create "
        "a fresh transcription job."
    )
    assert job.details["attempt_number"] == 1
    assert provider.availability_calls == 0
    assert provider.transcribe_calls == 0

    original_failed_record = repo.clone(job)
    runtime_profile = _runtime_profile(asr_profile)
    with pytest.raises(
        TranscriptionJobContractError,
        match="runtime_profile_retry_not_allowed",
    ) as service_error:
        retry_audio_processing_job(
            repo,
            job.job_id,
            provider_registry=FakeRegistry(provider),
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
        )
    assert service_error.value.code == "runtime_profile_retry_not_allowed"
    assert "fresh transcription job" in service_error.value.remediation

    with pytest.raises(HTTPException) as endpoint_error:
        retry_job(
            job.job_id,
            repo=repo,
            user=CurrentUser(),
        )
    assert endpoint_error.value.status_code == 409
    assert endpoint_error.value.detail["error_code"] == (
        "runtime_profile_retry_not_allowed"
    )

    fresh = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    assert fresh.job_id != job.job_id
    assert fresh.status is JobStatus.queued
    assert fresh.details["idempotency_key"]
    assert repo.jobs[job.job_id] == original_failed_record
    assert len(repo.jobs) == 2


def test_one_composite_artifact_loads_decoding_and_job_runtime_profiles(
    tmp_path: Path,
) -> None:
    from app.services.asr_profiles import load_pinned_asr_profile

    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    artifact_path = tmp_path / "asr-runtime-profile.json"
    artifact_path.write_text(
        __import__("json").dumps(
            {
                "asr_profile": asr_profile.model_dump(mode="json"),
                "job_runtime": runtime_profile.model_dump(mode="json"),
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    assert load_pinned_asr_profile(artifact_path) == asr_profile
    assert load_job_runtime_profile(artifact_path) == runtime_profile


def test_unavailable_provider_creates_failed_job_and_preserves_assets() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    audio_before = repo.clone(repo.audio_files[audio_file_id])
    normalized_before = repo.get_current_normalized_audio_asset(audio_file_id)
    provider = FakeCanonicalProvider(available=False)
    asr_profile = _asr_profile()

    job = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=_runtime_profile(asr_profile),
    )

    assert job.status is JobStatus.failed
    assert job.error_code == "provider_unavailable"
    assert job.details["provider_reason_code"] == "model_artifact_missing"
    assert job.details["retry_allowed"] is True
    assert repo.audio_files[audio_file_id] == audio_before
    assert (
        repo.get_current_normalized_audio_asset(audio_file_id)
        == normalized_before
    )
    assert provider.transcribe_calls == 0


def test_repeated_create_returns_same_job_for_exact_identity() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)

    first = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    repeated = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    assert repeated.job_id == first.job_id
    assert repeated.details["idempotency_key"] == (
        first.details["idempotency_key"]
    )
    assert repeated.details["attempt_number"] == 1
    assert len(repo.jobs) == 1
    assert provider.prepare_for_retry_calls == []


def test_retry_creates_next_attempt_linked_to_failed_job() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider(available=False)
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    failed = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    retried = retry_audio_processing_job(
        repo,
        failed.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    assert retried.job_id != failed.job_id
    assert retried.status is JobStatus.failed
    assert retried.details["attempt_number"] == 2
    assert retried.details["previous_attempt_job_id"] == failed.job_id
    assert (
        retried.details["idempotency_key"]
        == failed.details["idempotency_key"]
    )
    assert provider.prepare_for_retry_calls == [
        asr_profile.profile_checksum_sha256
    ]


def test_retry_rejects_changed_normalized_lineage() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider(available=False)
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    failed = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    old = repo.normalized_audio_assets[(audio_file_id, 1)]
    repo.normalized_audio_assets[(audio_file_id, 1)] = old.model_copy(
        update={"status": ArtifactStatus.stale}
    )
    repo.normalized_audio_assets[(audio_file_id, 2)] = old.model_copy(
        update={
            "asset_version": 2,
            "normalized_checksum_sha256": "e" * 64,
            "status": ArtifactStatus.current,
        }
    )

    with pytest.raises(
        TranscriptionJobContractError,
        match="job_lineage_stale",
    ):
        retry_audio_processing_job(
            repo,
            failed.job_id,
            provider_registry=registry,
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
        )

    assert len(repo.jobs) == 1


@pytest.mark.parametrize("backend", ["json", "sql"])
@pytest.mark.parametrize("changed_profile", ["asr", "runtime"])
def test_retry_rejects_changed_profile_lineage(
    tmp_path: Path,
    backend: str,
    changed_profile: str,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
    seed = factory()
    provider = FakeCanonicalProvider(available=False)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    failed = create_audio_processing_job(
        seed,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    retry_repo = factory()
    if changed_profile == "asr":
        selected_asr = _asr_profile(beam_size=3)
        selected_runtime = _runtime_profile(selected_asr)
    else:
        selected_asr = asr_profile
        selected_runtime = _runtime_profile(
            asr_profile,
            timeout_seconds=43,
        )

    with pytest.raises(
        TranscriptionJobContractError,
        match="retry_profile_lineage_mismatch",
    ) as exc_info:
        retry_audio_processing_job(
            retry_repo,
            failed.job_id,
            provider_registry=FakeRegistry(provider),
            asr_profile=selected_asr,
            runtime_profile=selected_runtime,
        )

    assert exc_info.value.code == "retry_profile_lineage_mismatch"
    assert provider.prepare_for_retry_calls == []
    assert len(factory().jobs) == 1


@pytest.mark.parametrize("backend", ["json", "sql"])
def test_two_repository_instances_create_one_idempotent_attempt(
    tmp_path: Path,
    backend: str,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
    first = factory()
    second = factory()
    provider = FakeCanonicalProvider()
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)

    def create(repo):
        return create_audio_processing_job(
            repo,
            "session_demo_001",
            _request(audio_file_id),
            provider_registry=FakeRegistry(provider),
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        jobs = list(executor.map(create, (first, second)))

    assert jobs[0].job_id == jobs[1].job_id
    durable = factory()
    assert list(durable.jobs) == [jobs[0].job_id]
    assert durable.jobs[jobs[0].job_id].details["attempt_number"] == 1


@pytest.mark.parametrize("backend", ["json", "sql"])
def test_two_repository_instances_create_one_retry_attempt(
    tmp_path: Path,
    backend: str,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
    seed = factory()
    unavailable = FakeCanonicalProvider(available=False)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    failed = create_audio_processing_job(
        seed,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(unavailable),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    first = factory()
    second = factory()

    def retry(repo):
        return retry_audio_processing_job(
            repo,
            failed.job_id,
            provider_registry=FakeRegistry(unavailable),
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        retries = list(executor.map(retry, (first, second)))

    assert retries[0].job_id == retries[1].job_id
    durable = factory()
    assert len(durable.jobs) == 2
    retry_job = durable.jobs[retries[0].job_id]
    assert retry_job.details["attempt_number"] == 2
    assert retry_job.details["previous_attempt_job_id"] == failed.job_id


@pytest.mark.parametrize("backend", ["json", "sql"])
def test_two_workers_execute_one_attempt_and_persist_one_draft(
    tmp_path: Path,
    backend: str,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
    seed = factory()
    provider = FakeCanonicalProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        seed,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    first = factory()
    second = factory()

    def run(repo):
        return run_audio_processing_job(
            repo,
            queued.job_id,
            provider_registry=registry,
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
            storage_adapter=FakeStorage(),
            test_execution_runner=_fixed_execution_runner,
            allow_test_execution_runner=True,
            settings=Settings(),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(run, (first, second)))

    durable = factory()
    assert provider.transcribe_calls == 1
    assert durable.jobs[queued.job_id].status is JobStatus.needs_review
    assert len(durable.transcripts) == 1
    transcript = next(iter(durable.transcripts.values()))
    assert transcript.asr_provenance["job_id"] == queued.job_id
    assert durable.sessions["session_demo_001"].transcript_id == (
        transcript.transcript_id
    )


@pytest.mark.parametrize("backend", ["json", "sql"])
@pytest.mark.parametrize(
    "tamper",
    [
        "raw_payload",
        "outer_transcript_id",
        "job_evidence_ref",
        "transcript_provenance_job",
    ],
)
def test_private_asr_evidence_survives_reload_and_tampering_is_rejected(
    tmp_path: Path,
    backend: str,
    tamper: str,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
    repo = factory()
    provider = FakeCanonicalProvider()
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    completed = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    reloaded = factory()
    evidence = reloaded.get_private_asr_evidence(completed.job_id)
    assert evidence is not None
    assert evidence.transcript_id == completed.details["asr_draft"][
        "transcript_id"
    ]
    assert evidence.private_record["raw_provider_payload"][
        "provider_id"
    ] == "local_faster_whisper"

    if backend == "json":
        path = tmp_path / "repository.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if tamper == "raw_payload":
            payload["private_asr_evidence"][completed.job_id][
                "private_record"
            ]["raw_provider_payload"]["segments"][0]["text"] = "tampered"
        elif tamper == "outer_transcript_id":
            payload["private_asr_evidence"][completed.job_id][
                "transcript_id"
            ] = "tr_missing"
        elif tamper == "job_evidence_ref":
            payload["jobs"][completed.job_id]["details"][
                "private_evidence_ref"
            ]["transcript_id"] = "tr_missing"
        else:
            transcript_id = completed.details["asr_draft"]["transcript_id"]
            payload["transcripts"][transcript_id]["asr_provenance"][
                "job_id"
            ] = "job_different"
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        from app.db.models import (
            AsrPrivateEvidenceRecord,
            ProcessingJobRecord,
            TranscriptRecord,
        )

        with reloaded.SessionLocal() as db:
            if tamper in {"raw_payload", "outer_transcript_id"}:
                row = db.get(AsrPrivateEvidenceRecord, completed.job_id)
                assert row is not None
                if tamper == "raw_payload":
                    private_record = json.loads(
                        json.dumps(row.private_record)
                    )
                    private_record["raw_provider_payload"]["segments"][0][
                        "text"
                    ] = "tampered"
                    row.private_record = private_record
                else:
                    row.transcript_id = "tr_missing"
            elif tamper == "job_evidence_ref":
                row = db.get(ProcessingJobRecord, completed.job_id)
                assert row is not None
                details = json.loads(json.dumps(row.details))
                details["private_evidence_ref"][
                    "transcript_id"
                ] = "tr_missing"
                row.details = details
            else:
                transcript_id = completed.details["asr_draft"][
                    "transcript_id"
                ]
                row = db.get(TranscriptRecord, transcript_id)
                assert row is not None
                provenance = dict(row.asr_provenance)
                provenance["job_id"] = "job_different"
                row.asr_provenance = provenance
            db.commit()

    with pytest.raises((ValidationError, ValueError)):
        factory()


def test_json_repository_interrupted_replace_preserves_previous_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "atomic-repository.json"
    repo = JsonFileRepository(path)
    previous_bytes = path.read_bytes()
    repo.jobs["job_unsaved"] = ProcessingJob(
        job_id="job_unsaved",
        session_id="session_demo_001",
        status=JobStatus.queued,
        message="must not appear in durable snapshot",
        details={"attempt_number": 1},
    )

    def interrupted_replace(_source, _destination) -> None:
        raise OSError("synthetic replace interruption")

    monkeypatch.setattr(
        "app.repositories.mock_repository.os.replace",
        interrupted_replace,
    )
    with pytest.raises(OSError, match="replace interruption"):
        repo.save()

    assert path.read_bytes() == previous_bytes
    assert not list(tmp_path.glob(f".{path.name}.*.tmp"))
    durable = JsonFileRepository(path)
    assert "job_unsaved" not in durable.jobs
    assert repo.snapshot() == durable.snapshot()


def test_json_processing_job_cas_is_locked_across_processes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "cross-process-repository.json"
    repo = JsonFileRepository(path)
    queued = ProcessingJob(
        job_id="job_cross_process",
        session_id="session_demo_001",
        status=JobStatus.queued,
        message="cross-process fixture",
        details={"attempt_number": 1},
    )
    repo.create_processing_job(
        queued,
        audit_action="transcription.job_queued",
        audit_message="Cross-process JSON fixture queued.",
    )
    context = multiprocessing.get_context("fork")
    start_event = context.Event()
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_json_process_cas_candidate,
            args=(
                str(path),
                queued.job_id,
                target.value,
                start_event,
                result_queue,
            ),
        )
        for target in (JobStatus.processing, JobStatus.cancelled)
    ]
    for process in processes:
        process.start()
    start_event.set()
    for process in processes:
        process.join(timeout=10)
        assert process.exitcode == 0
        process.close()

    outcomes = [result_queue.get(timeout=2) for _ in processes]
    result_queue.close()
    result_queue.join_thread()
    assert outcomes.count("conflict") == 1
    winner = next(item for item in outcomes if item != "conflict")
    durable = JsonFileRepository(path)
    assert durable.jobs[queued.job_id].status.value == winner


@pytest.mark.parametrize("backend", ["json", "sql"])
def test_cancel_wins_atomic_race_with_transcription_finalization(
    tmp_path: Path,
    backend: str,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
    worker_repo = factory()
    provider = FakeCanonicalProvider()
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        worker_repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    finalization_entered = Event()
    release_finalization = Event()
    atomic_finalize = worker_repo.finalize_transcription_draft

    def paused_finalize(**kwargs):
        finalization_entered.set()
        if not release_finalization.wait(timeout=10):
            raise TimeoutError("synthetic finalization barrier timed out")
        return atomic_finalize(**kwargs)

    worker_repo.finalize_transcription_draft = paused_finalize

    def run_worker():
        return run_audio_processing_job(
            worker_repo,
            queued.job_id,
            provider_registry=FakeRegistry(provider),
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
            storage_adapter=FakeStorage(),
            test_execution_runner=_fixed_execution_runner,
            allow_test_execution_runner=True,
            settings=Settings(),
        )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_worker)
        assert finalization_entered.wait(timeout=10)
        cancelling_repo = factory()
        processing = cancelling_repo.get_processing_job(queued.job_id)
        assert processing is not None
        assert processing.status is JobStatus.processing
        processing.status = JobStatus.cancelled
        processing.message = "cancelled during finalization race"
        processing.details = {
            **processing.details,
            "status_history": [
                *processing.details["status_history"],
                JobStatus.cancelled.value,
            ],
        }
        cancelling_repo.update_processing_job(
            processing,
            expected_status=JobStatus.processing,
            audit_action="job.cancel",
            audit_message="Synthetic cancellation won finalization race.",
        )
        release_finalization.set()
        result = future.result(timeout=15)

    assert result.status is JobStatus.cancelled
    durable = factory()
    assert durable.transcripts == {}
    assert durable.private_asr_evidence == {}
    assert durable.sessions["session_demo_001"].transcript_id is None


@pytest.mark.parametrize("backend", ["mock", "json", "sql"])
def test_repository_finalizer_rejects_durable_withdrawal_from_stale_snapshot(
    tmp_path: Path,
    backend: str,
) -> None:
    if backend == "mock":
        worker_repo, audio_file_id = _repo_with_verified_audio()
        factory = lambda: worker_repo
    else:
        factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
        worker_repo = factory()
    provider = FakeCanonicalProvider()
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        worker_repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    captured: dict[str, object] = {}
    atomic_finalize = worker_repo.finalize_transcription_draft

    def capture_finalization(**kwargs):
        captured.update(kwargs)
        return kwargs["job"]

    worker_repo.finalize_transcription_draft = capture_finalization
    prepared = run_audio_processing_job(
        worker_repo,
        queued.job_id,
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )
    assert prepared.status is JobStatus.needs_review
    assert captured
    stale_finalizer_repo = factory()
    if backend == "mock":
        stale_finalizer_repo.finalize_transcription_draft = atomic_finalize

    if backend == "sql":
        from app.db.models import ChildCaseRecord, SessionRecord

        external = factory()
        with external.SessionLocal() as db:
            case_row = db.get(ChildCaseRecord, "case_demo_001")
            session_row = db.get(SessionRecord, "session_demo_001")
            assert case_row is not None
            assert session_row is not None
            case_row.consent_status = "withdrawn"
            session_row.status = ReviewStatus.withdrawn.value
            db.commit()
    else:
        external = factory()
        external.cases["case_demo_001"].consent_status = "withdrawn"
        external.sessions["session_demo_001"].status = ReviewStatus.withdrawn
        save = getattr(external, "save", None)
        if callable(save):
            save()

    result = stale_finalizer_repo.finalize_transcription_draft(
        **captured,
    )
    durable = factory()
    durable_job = durable.get_processing_job(queued.job_id)
    assert result.status is JobStatus.cancelled
    assert durable_job is not None
    assert durable_job.status is JobStatus.cancelled
    assert durable_job.error_code == "consent_withdrawn"
    assert durable.transcripts == {}
    assert durable.private_asr_evidence == {}
    assert durable.sessions["session_demo_001"].status is ReviewStatus.withdrawn
    assert durable.sessions["session_demo_001"].transcript_id is None


@pytest.mark.parametrize("backend", ["mock", "json", "sql"])
def test_consent_withdrawal_during_provider_cancels_without_draft(
    tmp_path: Path,
    backend: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if backend == "mock":
        repo, audio_file_id = _repo_with_verified_audio()
        factory = lambda: repo
    else:
        factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
        repo = factory()

    provider_entered = Event()
    release_provider = Event()

    class PausedProvider(FakeCanonicalProvider):
        def transcribe(self, transcription_input: TranscriptionInput):
            provider_entered.set()
            if not release_provider.wait(timeout=10):
                raise TimeoutError("synthetic provider barrier timed out")
            return super().transcribe(transcription_input)

    provider = PausedProvider()
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: ConsentCleanupStorage(),
    )

    def run_worker():
        return run_audio_processing_job(
            repo,
            queued.job_id,
            provider_registry=FakeRegistry(provider),
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
            storage_adapter=FakeStorage(),
            test_execution_runner=_fixed_execution_runner,
            allow_test_execution_runner=True,
            settings=Settings(),
        )

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_worker)
        assert provider_entered.wait(timeout=10)
        withdraw_consent(
            factory(),
            "case_demo_001",
            "Synthetic withdrawal while provider is running.",
        )
        release_provider.set()
        result = future.result(timeout=15)

    durable = factory()
    durable_job = durable.get_processing_job(queued.job_id)
    assert result.status is JobStatus.cancelled
    assert durable_job is not None
    assert durable_job.status is JobStatus.cancelled
    assert durable_job.error_code == "consent_withdrawn"
    assert durable.transcripts == {}
    assert durable.private_asr_evidence == {}
    assert durable.sessions["session_demo_001"].status is ReviewStatus.withdrawn
    assert durable.sessions["session_demo_001"].transcript_id is None


@pytest.mark.parametrize("backend", ["json", "sql"])
def test_stale_repository_cannot_create_job_after_durable_withdrawal(
    tmp_path: Path,
    backend: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
    stale_repo = factory()
    external = factory()
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: ConsentCleanupStorage(),
    )
    withdraw_consent(
        external,
        "case_demo_001",
        "Synthetic external withdrawal.",
    )

    asr_profile = _asr_profile()
    with pytest.raises((ValueError, TranscriptionJobContractError)):
        create_audio_processing_job(
            stale_repo,
            "session_demo_001",
            _request(audio_file_id),
            provider_registry=FakeRegistry(FakeCanonicalProvider()),
            asr_profile=asr_profile,
            runtime_profile=_runtime_profile(asr_profile),
        )

    assert factory().jobs == {}


@pytest.mark.parametrize("backend", ["json", "sql"])
def test_stale_repository_cannot_retry_job_after_durable_withdrawal(
    tmp_path: Path,
    backend: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
    setup_repo = factory()
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    failed = create_audio_processing_job(
        setup_repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(
            FakeCanonicalProvider(available=False)
        ),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    assert failed.status is JobStatus.failed
    assert failed.details["retry_allowed"] is True

    stale_repo = factory()
    external = factory()
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: ConsentCleanupStorage(),
    )
    withdraw_consent(
        external,
        "case_demo_001",
        "Synthetic external withdrawal.",
    )

    with pytest.raises((ValueError, TranscriptionJobContractError)):
        retry_audio_processing_job(
            stale_repo,
            failed.job_id,
            provider_registry=FakeRegistry(FakeCanonicalProvider()),
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
        )

    durable_jobs = factory().jobs
    assert set(durable_jobs) == {failed.job_id}
    assert durable_jobs[failed.job_id].status is JobStatus.failed


def test_successful_job_records_evidence_and_creates_neutral_review_draft() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    finished = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    assert finished.status is JobStatus.needs_review
    assert finished.error_code is None
    assert finished.details["status_history"] == [
        "queued",
        "processing",
        "needs_review",
    ]
    execution = finished.details["execution_provenance"]
    assert execution == {
        "cold_warm_mode": "cold",
        "execution_isolation_mode": "one_shot_isolated_process",
        "warm_reuse_capability": (
            "unavailable_one_shot_isolation"
        ),
        "started_monotonic_seconds": 10.0,
        "ended_monotonic_seconds": 12.5,
        "wall_time_seconds": 2.5,
        "cpu_time_seconds": 1.25,
        "peak_resident_memory_bytes": 123_456,
        "timeout_seconds": 42,
        "timeout_profile_checksum_sha256": (
            runtime_profile.profile_checksum_sha256
        ),
        "termination_reason": "completed",
    }
    completeness = finished.details["completeness"]
    assert completeness["status"] == "pass"
    assert completeness["beginning_coverage"] is True
    assert completeness["ending_coverage"] is True
    transcript_id = finished.details["asr_draft"]["transcript_id"]
    transcript = repo.transcripts[transcript_id]
    assert repo.sessions["session_demo_001"].transcript_id == transcript_id
    assert repo.sessions["session_demo_001"].version == 2
    assert "session_transcript_selection_conflict" not in finished.details
    assert len({item.utterance_id for item in transcript.utterances}) == 2
    assert [item.speaker for item in transcript.utterances] == [
        "UNK",
        "UNK",
    ]
    assert [
        item.temporary_speaker_id for item in transcript.utterances
    ] == ["UNK", "UNK"]
    assert [
        item.source_speaker_label for item in transcript.utterances
    ] == ["UNK", "UNK"]
    assert transcript.raw_speaker_labels == ["UNK"]
    assert transcript.therapist_attested is False
    assert transcript.qa_status.value == "NOT_RUN"
    assert transcript.chat_metadata["speaker_mapping_status"] == "incomplete"
    assert transcript.chat_metadata["qa_status"] == "incomplete"
    assert transcript.chat_metadata["attestation_status"] == "incomplete"
    private_evidence = repo.get_private_asr_evidence(finished.job_id)
    assert private_evidence is not None
    assert private_evidence.private_record["raw_provider_payload"][
        "provider_id"
    ] == "local_faster_whisper"
    public_payload = _public_processing_job(finished).model_dump(
        mode="json"
    )
    assert "raw_provider_payload" not in public_payload["details"][
        "private_evidence_ref"
    ]
    assert '"token_ids"' not in json.dumps(
        public_payload,
        ensure_ascii=False,
    )


def test_sql_withdrawal_deletes_persisted_private_asr_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, audio_file_id = _durable_repo_factory(tmp_path, "sql")
    repo = factory()
    provider = FakeCanonicalProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    finished = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )
    assert factory().get_private_asr_evidence(finished.job_id) is not None
    monkeypatch.setattr(
        "app.services.consent_service.get_storage_adapter",
        lambda: ConsentCleanupStorage(),
    )

    withdraw_consent(
        factory(),
        "case_demo_001",
        "Synthetic withdrawal after completed ASR evidence.",
    )

    durable = factory()
    assert durable.get_private_asr_evidence(finished.job_id) is None
    transcript_id = finished.details["asr_draft"]["transcript_id"]
    assert (
        durable.transcripts[transcript_id].review_status
        is ReviewStatus.withdrawn
    )
    durable_job = durable.get_processing_job(finished.job_id)
    assert durable_job is not None
    assert durable_job.details["consent_withdrawn"] is True
    assert durable_job.details["storage_unlinked"] is True


@pytest.mark.parametrize("backend", ["mock", "json", "sql"])
def test_asr_finalization_preserves_newer_manual_session_selection(
    tmp_path: Path,
    backend: str,
) -> None:
    if backend == "mock":
        repo, audio_file_id = _repo_with_verified_audio()
        factory = lambda: repo
    else:
        factory, audio_file_id = _durable_repo_factory(tmp_path, backend)
        repo = factory()
    provider = FakeCanonicalProvider()
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    assert queued.details["expected_session_transcript_id"] is None
    assert queued.details["expected_session_version"] == 1

    manual = Transcript(
        transcript_id="tr_manual_newer",
        session_id="session_demo_001",
        case_id="case_demo_001",
        source="manual",
        raw_text="synthetic therapist-selected transcript",
    )
    repo.create_transcript(
        manual,
        session_status=ReviewStatus.needs_review,
        actor_id="therapist-test",
        audit_action="transcript.manual_created",
        audit_message="Synthetic manual transcript selected.",
    )

    worker_repo = factory()
    completed = run_audio_processing_job(
        worker_repo,
        queued.job_id,
        provider_registry=FakeRegistry(provider),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )
    durable = factory()
    durable_job = durable.get_processing_job(completed.job_id)
    assert durable_job is not None
    assert durable_job.status is JobStatus.needs_review
    conflict = durable_job.details[
        "session_transcript_selection_conflict"
    ]
    assert conflict["code"] == "session_transcript_selection_conflict"
    assert conflict["disposition"] == "integrity_blocker"
    assert conflict["requires_therapist_resolution"] is True
    assert durable.sessions["session_demo_001"].transcript_id == (
        manual.transcript_id
    )
    asr_transcript_id = durable_job.details["asr_draft"]["transcript_id"]
    assert asr_transcript_id in durable.transcripts
    assert asr_transcript_id != manual.transcript_id
    assert durable.get_private_asr_evidence(completed.job_id) is not None
    assert durable.transcripts[asr_transcript_id].asr_provenance[
        "session_transcript_selection_conflict"
    ]["code"] == "session_transcript_selection_conflict"


def test_local_faster_whisper_provider_reaches_task6_review_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "pinned-whisper-model"
    model_path.mkdir()
    (model_path / "config.json").write_text(
        '{"model":"synthetic-integration"}',
        encoding="utf-8",
    )
    (model_path / "model.bin").write_bytes(b"pinned-model-weights")
    asr_profile = _asr_profile(
        model_artifact_path=model_path,
        model_checksum_sha256=hash_model_artifact(model_path),
    )
    runtime_profile = _runtime_profile(asr_profile)
    model_load_evidence = tmp_path / "model-loads.bin"
    fake_runtime_root = tmp_path / "spawn-runtime"
    fake_package = fake_runtime_root / "faster_whisper"
    fake_package.mkdir(parents=True)
    (fake_package / "__init__.py").write_text(
        """
import os
from pathlib import Path
from types import SimpleNamespace

class WhisperModel:
    def __init__(self, **kwargs):
        evidence = os.environ["LINGUALENS_TEST_MODEL_LOAD_EVIDENCE"]
        with Path(evidence).open("ab") as evidence_file:
            evidence_file.write(b"1")
            evidence_file.flush()

    def transcribe(self, audio, **kwargs):
        segments = (
            SimpleNamespace(
                id=0, seek=0, start=0.1, end=4.0,
                text=" สวัสดี blue cup ", tokens=[1, 2],
                temperature=0.0, avg_logprob=-0.1,
                compression_ratio=1.0, no_speech_prob=0.01,
                words=(),
            ),
            SimpleNamespace(
                id=1, seek=0, start=4.0, end=9.9,
                text=" จบหนึ่งเจ็ดศูนย์ ", tokens=[3, 4],
                temperature=0.0, avg_logprob=-0.1,
                compression_ratio=1.0, no_speech_prob=0.01,
                words=(),
            ),
        )
        info = SimpleNamespace(
            language="th",
            language_probability=0.99,
            duration=10.0,
            duration_after_vad=9.8,
        )
        return iter(segments), info
""".strip(),
        encoding="utf-8",
    )
    (fake_package / "audio.py").write_text(
        """
def decode_audio(audio, *, sampling_rate, split_stereo):
    return [0.0] * 160000
""".strip(),
        encoding="utf-8",
    )
    (fake_package / "vad.py").write_text(
        """
class VadOptions:
    def __init__(self, **kwargs):
        self.options = kwargs

def get_speech_timestamps(samples, *, vad_options, sampling_rate):
    return [{"start": 1600, "end": 158400}]
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(fake_runtime_root))
    monkeypatch.setenv(
        "LINGUALENS_TEST_MODEL_LOAD_EVIDENCE",
        str(model_load_evidence),
    )

    class InjectedDetector:
        detector_id = "faster_whisper_silero_vad"

        def check_availability(self, *, profile, runtime):
            return None

        def detect(
            self,
            audio_path: Path,
            *,
            normalized_audio_checksum_sha256: str,
            vad_parameters: PinnedVadParameters,
            detector_version: str,
        ) -> SpeechDetectionEvidence:
            assert audio_path.read_bytes() == NORMALIZED_BYTES
            assert vad_parameters == asr_profile.vad_parameters
            assert detector_version == "faster-whisper:1.2.1"
            return _speech_detection_evidence(
                normalized_checksum_sha256=(
                    normalized_audio_checksum_sha256
                )
            )

    class FakeModel:
        def transcribe(self, audio: str, **kwargs):
            assert Path(audio).read_bytes() == NORMALIZED_BYTES
            segments = (
                SimpleNamespace(
                    id=0,
                    seek=0,
                    start=0.1,
                    end=4.0,
                    text=" สวัสดี blue cup ",
                    tokens=[1, 2],
                    temperature=0.0,
                    avg_logprob=-0.1,
                    compression_ratio=1.0,
                    no_speech_prob=0.01,
                    words=(),
                ),
                SimpleNamespace(
                    id=1,
                    seek=0,
                    start=4.0,
                    end=9.9,
                    text=" จบหนึ่งเจ็ดศูนย์ ",
                    tokens=[3, 4],
                    temperature=0.0,
                    avg_logprob=-0.1,
                    compression_ratio=1.0,
                    no_speech_prob=0.01,
                    words=(),
                ),
            )
            info = SimpleNamespace(
                language="th",
                language_probability=0.99,
                duration=10.0,
                duration_after_vad=9.8,
            )
            return iter(segments), info

    def load_model(**_kwargs):
        with model_load_evidence.open("ab") as evidence_file:
            evidence_file.write(b"1")
            evidence_file.flush()
        return FakeModel()

    provider = LocalWhisperProvider(
        profile=asr_profile,
        runtime_inspector=lambda: AsrRuntimeVersions(
            faster_whisper_version="1.2.1",
            ctranslate2_version="4.8.1",
            decoder_name="soundfile",
            decoder_version="0.14.0",
            decoder_available=True,
        ),
        model_factory=load_model,
        speech_detector=InjectedDetector(),
    )
    registry = FakeRegistry(provider)
    repo, audio_file_id = _repo_with_verified_audio()
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    finished = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        settings=Settings(),
    )

    assert finished.status is JobStatus.needs_review
    assert finished.details["completeness"]["status"] == "pass"
    transcript = repo.transcripts[
        finished.details["asr_draft"]["transcript_id"]
    ]
    assert transcript.asr_provenance[
        "speech_detection_evidence_checksum_sha256"
    ] == _speech_detection_evidence().evidence_checksum_sha256
    assert [utterance.speaker for utterance in transcript.utterances] == [
        "UNK",
        "UNK",
    ]
    provenance = transcript.asr_provenance
    assert provenance["job_id"] == queued.job_id
    assert provenance["source_audio_file_id"] == audio_file_id
    assert provenance["source_asset_version"] == 1
    assert provenance["source_checksum_sha256"] == SOURCE_CHECKSUM
    assert provenance["normalized_asset_version"] == 1
    assert (
        provenance["normalized_checksum_sha256"]
        == NORMALIZED_CHECKSUM
    )
    assert (
        provenance["asr_profile_checksum_sha256"]
        == asr_profile.profile_checksum_sha256
    )
    assert (
        provenance["runtime_profile_checksum_sha256"]
        == runtime_profile.profile_checksum_sha256
    )
    second_repo, second_audio_file_id = _repo_with_verified_audio()
    second_queued = create_audio_processing_job(
        second_repo,
        "session_demo_001",
        _request(second_audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    second_finished = run_audio_processing_job(
        second_repo,
        second_queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        settings=Settings(),
    )

    execution_modes = [
        finished.details["execution_provenance"],
        second_finished.details["execution_provenance"],
    ]
    assert [item["cold_warm_mode"] for item in execution_modes] == [
        "cold",
        "cold",
    ]
    assert all(
        item["execution_isolation_mode"]
        == "one_shot_isolated_process"
        for item in execution_modes
    )
    assert all(
        item["warm_reuse_capability"]
        == "unavailable_one_shot_isolation"
        for item in execution_modes
    )
    assert all(
        item["timeout_profile_checksum_sha256"]
        == runtime_profile.profile_checksum_sha256
        for item in execution_modes
    )
    assert all(item["cpu_time_seconds"] >= 0 for item in execution_modes)
    assert all(
        item["peak_resident_memory_bytes"] > 0
        for item in execution_modes
    )
    assert model_load_evidence.read_bytes() == b"11"
    assert provider._loaded_model is None


def test_exact_retry_refreshes_cached_local_provider_capability(
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "retry-whisper-model"
    model_path.mkdir()
    (model_path / "config.json").write_text(
        '{"model":"retry-integration"}',
        encoding="utf-8",
    )
    (model_path / "model.bin").write_bytes(b"retry-model-weights")
    model_checksum = hash_model_artifact(model_path)
    unavailable_model_path = tmp_path / "temporarily-unavailable-model"
    model_path.rename(unavailable_model_path)
    asr_profile = _asr_profile(
        model_artifact_path=model_path,
        model_checksum_sha256=model_checksum,
    )
    runtime_profile = _runtime_profile(asr_profile)

    class RetryDetector:
        detector_id = "faster_whisper_silero_vad"

        def check_availability(self, *, profile, runtime):
            return None

        def detect(
            self,
            audio_path: Path,
            *,
            normalized_audio_checksum_sha256: str,
            vad_parameters: PinnedVadParameters,
            detector_version: str,
        ) -> SpeechDetectionEvidence:
            return _speech_detection_evidence(
                normalized_checksum_sha256=(
                    normalized_audio_checksum_sha256
                )
            )

    class RetryModel:
        def transcribe(self, audio: str, **kwargs):
            return iter(
                (
                    SimpleNamespace(
                        id=0,
                        seek=0,
                        start=0.1,
                        end=4.0,
                        text=" สวัสดี blue cup ",
                        tokens=[1, 2],
                        temperature=0.0,
                        avg_logprob=-0.1,
                        compression_ratio=1.0,
                        no_speech_prob=0.01,
                        words=(),
                    ),
                    SimpleNamespace(
                        id=1,
                        seek=0,
                        start=4.0,
                        end=9.9,
                        text=" จบหนึ่งเจ็ดศูนย์ ",
                        tokens=[3, 4],
                        temperature=0.0,
                        avg_logprob=-0.1,
                        compression_ratio=1.0,
                        no_speech_prob=0.01,
                        words=(),
                    ),
                )
            ), SimpleNamespace(
                language="th",
                language_probability=0.99,
                duration=10.0,
                duration_after_vad=9.8,
            )

    provider = LocalWhisperProvider(
        profile=asr_profile,
        runtime_inspector=lambda: AsrRuntimeVersions(
            faster_whisper_version="1.2.1",
            ctranslate2_version="4.8.1",
            decoder_name="soundfile",
            decoder_version="0.14.0",
            decoder_available=True,
        ),
        model_factory=lambda **_: RetryModel(),
        speech_detector=RetryDetector(),
    )
    registry = FakeRegistry(provider)
    repo, audio_file_id = _repo_with_verified_audio()

    failed = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    assert failed.status is JobStatus.failed
    assert failed.error_code == "provider_unavailable"
    assert failed.details["provider_reason_code"] == "model_artifact_missing"
    assert failed.details["retry_allowed"] is True
    failed_snapshot = repo.clone(failed)
    unavailable_model_path.rename(model_path)

    retried = retry_audio_processing_job(
        repo,
        failed.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    assert retried.status is JobStatus.queued
    assert retried.details["previous_attempt_job_id"] == failed.job_id

    finished = run_audio_processing_job(
        repo,
        retried.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    assert finished.status is JobStatus.needs_review
    assert repo.jobs[failed.job_id] == failed_snapshot
    failed_actions = {
        event["action"]
        for event in repo.audit_log
        if event["target_id"] == failed.job_id
    }
    assert "transcription.job_unavailable" in failed_actions
    retry_actions = {
        event["action"]
        for event in repo.audit_log
        if event["target_id"] == retried.job_id
    }
    assert {
        "transcription.job_queued",
        "transcription.job_started",
        "transcription.draft_created",
    }.issubset(retry_actions)


@pytest.mark.parametrize(
    ("provider", "expected_code"),
    [
        (FakeCanonicalProvider(empty=True), "asr_empty_result"),
        (
            FakeCanonicalProvider(partial=True),
            "provider_partial_result",
        ),
        (
            FakeCanonicalProvider(result_status="failed", partial=True),
            "provider_partial_result",
        ),
    ],
)
def test_empty_or_partial_provider_result_fails_without_transcript(
    provider: FakeCanonicalProvider,
    expected_code: str,
) -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    failed = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    assert failed.status is JobStatus.failed
    assert failed.error_code == expected_code
    assert failed.details["retry_allowed"] is True
    assert repo.sessions["session_demo_001"].transcript_id is None
    assert repo.transcripts == {}


def test_missing_detected_speech_evidence_fails_closed() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider(include_speech_evidence=False)
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    failed = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    assert failed.status is JobStatus.failed
    assert failed.error_code == "speech_detection_evidence_missing"
    assert repo.transcripts == {}


def test_provider_segment_sequence_order_failure_cannot_create_review_draft() -> None:
    class BackwardSequenceProvider(FakeCanonicalProvider):
        def transcribe(self, transcription_input: TranscriptionInput):
            result = super().transcribe(transcription_input)
            return _mutable_provider_result(
                result,
                segments=tuple(reversed(result.segments)),
            )

    repo, audio_file_id = _repo_with_verified_audio()
    provider = BackwardSequenceProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    failed = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    assert failed.status is JobStatus.failed
    assert failed.error_code == "timestamp_sequence_order_invalid"
    assert failed.details["completeness"]["status"] == "blocked"
    assert repo.transcripts == {}
    assert repo.sessions["session_demo_001"].transcript_id is None


def test_malformed_provider_evidence_fails_without_stranding_processing_job() -> None:
    class MalformedEvidenceProvider(FakeCanonicalProvider):
        def transcribe(self, transcription_input: TranscriptionInput):
            result = super().transcribe(transcription_input)
            valid_evidence = _speech_detection_evidence()
            return _mutable_provider_result(
                result,
                speech_detection_evidence=(
                    SpeechDetectionEvidence.model_construct(
                        **{
                            **valid_evidence.model_dump(),
                            "evidence_checksum_sha256": "0" * 64,
                        }
                    )
                ),
            )

    repo, audio_file_id = _repo_with_verified_audio()
    provider = MalformedEvidenceProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    failed = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    assert failed.status is JobStatus.failed
    assert failed.error_code == "asr_result_invalid"
    assert repo.transcripts == {}


def test_draft_persistence_failure_marks_completed_attempt_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    def fail_atomic_finalization(*args, **kwargs):
        raise RuntimeError("synthetic transcript persistence failure")

    monkeypatch.setattr(
        repo,
        "finalize_transcription_draft",
        fail_atomic_finalization,
    )
    failed = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=_fixed_execution_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    assert failed.status is JobStatus.failed
    assert failed.error_code == "draft_persistence_failed"
    assert repo.transcripts == {}
    assert repo.private_asr_evidence == {}
    assert repo.sessions["session_demo_001"].transcript_id is None


def test_execution_timeout_records_typed_termination_and_no_partial_draft() -> None:
    repo, audio_file_id = _repo_with_verified_audio()
    provider = FakeCanonicalProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)
    queued = create_audio_processing_job(
        repo,
        "session_demo_001",
        _request(audio_file_id),
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )

    def timeout_runner(operation, **kwargs):
        raise AsrExecutionTimeout(
            AsrExecutionMetrics(
                cold_warm_mode="cold",
                execution_isolation_mode=(
                    "one_shot_isolated_process"
                ),
                warm_reuse_capability=(
                    "unavailable_one_shot_isolation"
                ),
                started_monotonic_seconds=20.0,
                ended_monotonic_seconds=62.0,
                wall_time_seconds=42.0,
                cpu_time_seconds=40.0,
                peak_resident_memory_bytes=222_222,
                timeout_seconds=kwargs["timeout_seconds"],
                timeout_profile_checksum_sha256=kwargs[
                    "timeout_profile_checksum_sha256"
                ],
                termination_reason="timeout",
            )
        )

    failed = run_audio_processing_job(
        repo,
        queued.job_id,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        storage_adapter=FakeStorage(),
        test_execution_runner=timeout_runner,
        allow_test_execution_runner=True,
        settings=Settings(),
    )

    assert failed.status is JobStatus.failed
    assert failed.error_code == "asr_timeout"
    assert (
        failed.details["execution_provenance"]["termination_reason"]
        == "timeout"
    )
    assert repo.transcripts == {}


def test_worker_transcription_job_lifecycle_and_idle_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks.job_queue import MemoryJobQueue, QueuedJob
    from app.tasks.worker import process_next_job
    import app.tasks.worker as worker_module

    class ClaimingMemoryQueue(MemoryJobQueue):
        def dequeue(self) -> QueuedJob | None:
            queued = super().dequeue()
            if queued is None:
                return None
            return QueuedJob(
                job_id=queued.job_id,
                claim_id="claim-test-123",
                owner_id="worker-test-1",
                lease_expires_at=2000000000.0,
            )

    repo, audio_file_id = _repo_with_verified_audio()
    queue = ClaimingMemoryQueue()
    storage = FakeStorage()

    cleanup_calls = []

    def fake_cleanup(r, s):
        cleanup_calls.append((r, s))
        return {
            "discovered": 1,
            "succeeded": 1,
            "failed": 0,
            "escalated": 0,
        }

    monkeypatch.setattr(worker_module, "get_repository", lambda: repo)
    monkeypatch.setattr(worker_module, "get_job_queue", lambda: queue)
    monkeypatch.setattr(worker_module, "get_storage_adapter", lambda: storage)
    monkeypatch.setattr(
        worker_module,
        "reconcile_due_audio_upload_cleanups",
        fake_cleanup,
    )

    idle_result = process_next_job()
    assert idle_result["status"] == "idle"
    assert idle_result["processed"] == 0
    assert idle_result["cleanup"] == {
        "discovered": 1,
        "succeeded": 1,
        "failed": 0,
        "escalated": 0,
    }
    assert len(cleanup_calls) == 1

    provider = FakeCanonicalProvider()
    registry = FakeRegistry(provider)
    asr_profile = _asr_profile()
    runtime_profile = _runtime_profile(asr_profile)

    job_req = _request(audio_file_id)
    queued_job = create_audio_processing_job(
        repo,
        "session_demo_001",
        job_req,
        provider_registry=registry,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    queue.enqueue(queued_job.job_id)

    real_run_audio_job = run_audio_processing_job

    def patched_run_audio_job(r, j_id):
        return real_run_audio_job(
            r,
            j_id,
            provider_registry=registry,
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
            storage_adapter=storage,
            test_execution_runner=_fixed_execution_runner,
            allow_test_execution_runner=True,
            settings=Settings(),
        )

    monkeypatch.setattr(
        worker_module,
        "run_audio_processing_job",
        patched_run_audio_job,
    )

    active_result = process_next_job()
    assert active_result["status"] == "processed"
    assert active_result["processed"] == 1
    assert active_result["job_id"] == queued_job.job_id
    assert active_result["job_status"] == JobStatus.needs_review.value
    assert queue.size() == 0

    job_after = repo.get_processing_job(queued_job.job_id)
    assert job_after is not None
    assert job_after.status is JobStatus.needs_review
    assert "queue_claim" in job_after.details
    assert job_after.details["queue_claim"]["claim_id"] == "claim-test-123"
    assert job_after.details["queue_claim"]["owner_id"] == "worker-test-1"

    expired_claimed = QueuedJob(
        job_id=queued_job.job_id,
        claim_id="expired-claim-123",
        owner_id="dead-worker",
        lease_expires_at=100.0,
        recovered_from_claim_id="expired-claim-123",
    )
    job_after.status = JobStatus.processing
    repo.jobs[job_after.job_id] = job_after

    worker_module._recover_claimed_job(expired_claimed, repo)
    recovered_job = repo.get_processing_job(queued_job.job_id)
    assert recovered_job is not None
    assert recovered_job.status is JobStatus.failed
    assert recovered_job.error_code == "worker_lease_expired"
    assert (
        recovered_job.details["worker_recovery"]["recovered_from_claim_id"]
        == "expired-claim-123"
    )

