from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
from threading import RLock
from typing import Callable

from app.core.config import Settings, get_settings
from app.repositories.base import ProcessingJobStateConflictError
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import (
    AsrDraftResult,
    AudioFileMetadata,
    AudioProcessRequest,
    AudioQualityReport,
    AudioUploadCompleteRequest,
    AudioUploadRequest,
    JobStatus,
    ProcessingJob,
    ReviewStatus,
    Transcript,
    utc_now,
    TranscriptionJobRequest,
    Utterance,
    QaIssue,
    QaStatus,
)
from app.services.cha_service import build_cha_text
from app.services.consent_service import ensure_session_consent_active
from app.services.storage_service import get_storage_adapter
from app.services.audio_media_service import (
    AudioIntakeError,
    get_decoder_capability_registry,
    verified_configured_audio_formats,
)
from app.services.asr_providers.registry import asr_provider_registry
from app.services.asr_profiles import (
    AsrProfileLoadError,
    PinnedAsrProfile,
    load_pinned_asr_profile,
)
from app.services.asr_providers.base import (
    SpeechDetectionEvidence,
    TranscriptionInput,
    VerifiedNormalizedAudioHandle,
)
from app.schemas.speech_pipeline import PrivateAsrEvidenceRecord
from app.services.asr_completeness_service import (
    AsrCompletenessResult,
    AsrJobRuntimeProfile,
    AsrSegmentInterval,
    SpeechInterval,
    evaluate_asr_completeness,
)
from app.services.storage_service import StorageProcessingError
from app.tasks.job_queue import (
    AsrExecutionFailure,
    AsrExecutionOutcome,
    AsrExecutionTimeout,
    AsrExecutionUnavailable,
    LocalAsrExecutionRequest,
    execute_local_asr_with_evidence_timeout,
)



V170_AUDIO_CONTENT_TYPES = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
}


class TranscriptionJobContractError(ValueError):
    """Typed upload-first job contract failure."""

    def __init__(
        self,
        code: str,
        *,
        remediation: str,
    ) -> None:
        self.code = code
        self.remediation = remediation
        super().__init__(code)


class RuntimeProfileResolutionError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        remediation: str,
    ) -> None:
        self.code = code
        self.remediation = remediation
        super().__init__(code)


_job_creation_lock = RLock()


def _canonical_json_sha256(material: dict[str, object]) -> str:
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def build_transcription_idempotency_key(
    *,
    audio_file_id: str,
    source_asset_version: int,
    normalized_asset_version: int,
    normalized_checksum_sha256: str,
    provider_id: str,
    asr_profile_checksum_sha256: str,
    runtime_profile_checksum_sha256: str,
) -> str:
    return _canonical_json_sha256(
        {
            "audio_file_id": audio_file_id,
            "source_asset_version": source_asset_version,
            "normalized_asset_version": normalized_asset_version,
            "normalized_checksum": normalized_checksum_sha256,
            "provider_id": provider_id,
            "asr_profile_checksum": asr_profile_checksum_sha256,
            "runtime_profile_checksum": runtime_profile_checksum_sha256,
        }
    )




def validate_audio_upload(
    payload: AudioUploadRequest,
    *,
    settings: Settings | None = None,
) -> None:
    runtime_settings = settings or get_settings()
    decoder_registry = get_decoder_capability_registry()
    supported_formats = verified_configured_audio_formats(
        runtime_settings,
        registry=decoder_registry,
    )
    if not payload.filename.strip() or "/" in payload.filename or "\\" in payload.filename or ".." in payload.filename:
        raise ValueError("unsafe filename")
    declared_format = V170_AUDIO_CONTENT_TYPES.get(payload.content_type.lower())
    if not supported_formats:
        raise AudioIntakeError(
            "decoder_capability_unavailable",
            actual_value=decoder_registry.runtime.soundfile_version,
            unit="decoder_runtime",
            supported_formats=(),
            remediation=(
                "Install the pinned audio runtime and verify the committed "
                "WAV/MP3 decoder fixtures before upload."
            ),
        )
    if (
        declared_format is None
        or declared_format not in supported_formats
    ):
        raise AudioIntakeError(
            "audio_format_unavailable",
            actual_value=payload.content_type,
            unit="declared_content_type",
            supported_formats=supported_formats,
            remediation="Choose a WAV or MP3 file; the server will verify its decoded format.",
        )
    limit_bytes = runtime_settings.max_audio_file_size_mb * 1024 * 1024
    if payload.size_bytes <= 0:
        raise AudioIntakeError(
            "audio_size_invalid",
            actual_value=payload.size_bytes,
            configured_limit=limit_bytes,
            unit="bytes",
            supported_formats=supported_formats,
            remediation="Choose a non-empty WAV or MP3 file.",
        )
    if payload.size_bytes > limit_bytes:
        raise AudioIntakeError(
            "audio_size_limit_exceeded",
            actual_value=payload.size_bytes,
            configured_limit=limit_bytes,
            unit="bytes",
            supported_formats=supported_formats,
            remediation=(
                f"Choose a file no larger than "
                f"{runtime_settings.max_audio_file_size_mb} MiB."
            ),
        )


def build_opaque_audio_object_key(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    safe_suffix = suffix if suffix and len(suffix) <= 10 else ""
    return f"audio/{new_id('obj')}{safe_suffix}"


def create_audio_upload_job(
    repo: MockRepository,
    session_id: str,
    payload: AudioUploadRequest,
    *,
    storage_adapter=None,
) -> ProcessingJob:
    storage_adapter = storage_adapter or get_storage_adapter()
    storage_adapter.ensure_available()
    validate_audio_upload(payload)
    initial_session = repo.sessions[session_id]
    with repo.case_consent_fence(initial_session.case_id):
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        session = repo.sessions[session_id]
        ensure_session_consent_active(repo, session_id)
        audio_file = AudioFileMetadata(
            audio_file_id=new_id("aud"),
            organization_id=session.organization_id,
            session_id=session_id,
            case_id=session.case_id,
            original_filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            storage_mode=storage_adapter.storage_mode,
            storage_backend_identity_sha256=(
                storage_adapter.storage_backend_identity_sha256
            ),
            object_key=build_opaque_audio_object_key(payload.filename),
            duration_seconds=payload.duration_seconds,
            sample_rate_hz=payload.sample_rate_hz,
            channels=payload.channels,
            estimated_noise_level=payload.estimated_noise_level,
            silence_ratio=payload.silence_ratio,
        )
        upload_intent = storage_adapter.create_upload_intent(audio_file)
        repo.audio_files[audio_file.audio_file_id] = audio_file
        quality = analyze_audio_quality(
            duration_seconds=payload.duration_seconds,
            sample_rate_hz=payload.sample_rate_hz,
            channels=payload.channels,
            estimated_noise_level=payload.estimated_noise_level,
            silence_ratio=payload.silence_ratio,
        )
        job = ProcessingJob(
            job_id=new_id("job"),
            organization_id=session.organization_id,
            session_id=session_id,
            status=JobStatus.queued,
            message=(
                "Audio metadata accepted. Processing is experimental and "
                "requires therapist transcript review."
            ),
            details={
                "quality": quality.model_dump(mode="json"),
                "audio_file": audio_file.model_dump(mode="json"),
                "upload_intent": upload_intent.model_dump(mode="json"),
                "status_history": [JobStatus.queued.value],
            },
        )
        repo.jobs[job.job_id] = job
        repo.add_audit(
            "audio.upload",
            job.job_id,
            "Experimental audio processing job queued.",
        )
        return repo.clone(job)


def complete_audio_upload(
    repo: MockRepository,
    audio_file_id: str,
    payload: AudioUploadCompleteRequest,
    *,
    storage_adapter=None,
    settings: Settings | None = None,
    actor_id: str = "system",
) -> AudioFileMetadata:
    initial_audio = repo.audio_files.get(audio_file_id)
    if initial_audio is None:
        raise ValueError("Audio file not found.")
    with repo.case_audio_fence(initial_audio.case_id, audio_file_id):
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        return _complete_audio_upload_locked(
            repo,
            audio_file_id,
            payload,
            storage_adapter=storage_adapter,
            settings=settings,
            actor_id=actor_id,
        )


def _complete_audio_upload_locked(
    repo: MockRepository,
    audio_file_id: str,
    payload: AudioUploadCompleteRequest,
    *,
    storage_adapter=None,
    settings: Settings | None = None,
    actor_id: str = "system",
) -> AudioFileMetadata:
    if audio_file_id not in repo.audio_files:
        raise ValueError("Audio file not found.")
    audio_file = repo.audio_files[audio_file_id]
    if not audio_file.retained:
        raise ValueError("Audio file is no longer retained.")
    if audio_file.upload_status != "pending_verification":
        raise ValueError("Audio upload must be re-issued with a new upload intent before completion verification.")
    adapter = storage_adapter or get_storage_adapter()
    if adapter.storage_mode != audio_file.storage_mode:
        raise AudioIntakeError(
            "source_storage_mismatch",
            actual_value=audio_file.storage_mode,
            unit="storage_mode",
            remediation=(
                "Retry with the private storage adapter linked to this source asset."
            ),
        )
    runtime_settings = settings or get_settings()
    with adapter.open_source_for_processing(audio_file) as source:
        source.seek(0, 2)
        actual_size_bytes = source.tell()
        source.seek(0)
        digest = sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
        source.seek(0)
    limit_bytes = runtime_settings.max_audio_file_size_mb * 1024 * 1024
    if actual_size_bytes <= 0:
        raise AudioIntakeError(
            "audio_content_empty",
            actual_value=actual_size_bytes,
            configured_limit=limit_bytes,
            unit="bytes",
            remediation="Upload a non-empty WAV or MP3 source asset.",
        )
    if actual_size_bytes > limit_bytes:
        raise AudioIntakeError(
            "audio_size_limit_exceeded",
            actual_value=actual_size_bytes,
            configured_limit=limit_bytes,
            unit="bytes",
            remediation=(
                f"Upload a file no larger than "
                f"{runtime_settings.max_audio_file_size_mb} MiB."
            ),
        )
    return repo.complete_audio_upload(
        audio_file_id,
        checksum_sha256=digest.hexdigest(),
        size_bytes=actual_size_bytes,
        uploaded_at=utc_now(),
        actor_id=actor_id,
    )


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _configured_profile_path(settings: Settings) -> Path:
    path = Path(settings.asr_runtime_profile_path)
    return path if path.is_absolute() else _repository_root() / path


def load_job_runtime_profile(path: Path) -> AsrJobRuntimeProfile:
    if not path.is_file() or path.is_symlink():
        raise RuntimeProfileResolutionError(
            "runtime_profile_unavailable",
            remediation=(
                "Run the versioned v1.7.0 benchmark and install its verified "
                "runtime profile before retrying."
            ),
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError("runtime profile must be an object")
        job_runtime = payload.get("job_runtime")
        if not isinstance(job_runtime, dict):
            raise KeyError("job_runtime")
        return AsrJobRuntimeProfile.model_validate(job_runtime)
    except (OSError, TypeError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeProfileResolutionError(
            "runtime_profile_unverified",
            remediation=(
                "Regenerate and verify the immutable benchmark-derived "
                "runtime profile before retrying."
            ),
        ) from exc


def _provider_id(payload: object) -> str:
    return str(
        getattr(payload, "provider_id", None)
        or getattr(payload, "provider", "")
    )


def _resolve_audio_file_id_for_job(
    repo: MockRepository,
    session_id: str,
    payload: AudioProcessRequest | TranscriptionJobRequest,
) -> str:
    requested = (
        getattr(payload, "audio_file_id", None)
        or getattr(payload, "audio_id", None)
    )
    if requested is None:
        uploaded = [
            item.audio_file_id
            for item in repo.audio_files.values()
            if item.session_id == session_id
            and item.retained
            and item.upload_status == "uploaded"
        ]
        if len(uploaded) != 1:
            raise AudioIntakeError(
                "source_audio_missing",
                remediation="Select one verified uploaded source audio file.",
            )
        requested = uploaded[0]
    if requested not in repo.audio_files:
        raise AudioIntakeError(
            "source_audio_missing",
            remediation="Select one verified uploaded source audio file.",
        )
    audio = repo.audio_files[requested]
    if (
        audio.session_id != session_id
        or not audio.retained
        or audio.upload_status != "uploaded"
        or not audio.checksum_sha256
    ):
        raise AudioIntakeError(
            "source_audio_unverified",
            remediation=(
                "Complete server-side source verification before transcription."
            ),
        )
    return requested


def _verified_job_lineage(
    repo: MockRepository,
    session_id: str,
    payload: AudioProcessRequest | TranscriptionJobRequest,
):
    audio_file_id = _resolve_audio_file_id_for_job(
        repo,
        session_id,
        payload,
    )
    audio = repo.audio_files[audio_file_id]
    normalized = repo.get_current_normalized_audio_asset(audio_file_id)
    if (
        normalized is None
        or normalized.verification_status != "verified"
        or normalized.status.value != "current"
        or normalized.source_asset_version != audio.source_asset_version
        or normalized.source_checksum_sha256 != audio.checksum_sha256
        or audio.current_normalized_asset_version
        != normalized.asset_version
        or audio.current_normalized_checksum_sha256
        != normalized.normalized_checksum_sha256
    ):
        raise AudioIntakeError(
            "audio_normalization_required",
            actual_value=(
                normalized.verification_status
                if normalized is not None
                else "missing"
            ),
            unit="normalization_status",
            remediation=(
                "Verify and normalize the current source audio before "
                "creating a transcription job."
            ),
        )
    expected_source = getattr(
        payload,
        "expected_source_asset_version",
        audio.source_asset_version,
    )
    expected_normalized = getattr(
        payload,
        "expected_normalized_asset_version",
        normalized.asset_version,
    )
    if (
        expected_source != audio.source_asset_version
        or expected_normalized != normalized.asset_version
    ):
        raise TranscriptionJobContractError(
            "expected_audio_version_mismatch",
            remediation=(
                "Refresh the current source and normalized asset versions."
            ),
        )
    return audio, normalized


def _resolve_profiles(
    *,
    settings: Settings,
    asr_profile: PinnedAsrProfile | None,
    runtime_profile: AsrJobRuntimeProfile | None,
) -> tuple[PinnedAsrProfile | None, AsrJobRuntimeProfile | None, str | None]:
    path = _configured_profile_path(settings)
    try:
        selected_asr = (
            asr_profile.revalidated()
            if asr_profile is not None
            else load_pinned_asr_profile(path)
        )
    except AsrProfileLoadError as exc:
        return None, None, exc.code
    try:
        selected_runtime = (
            AsrJobRuntimeProfile.model_validate(
                runtime_profile.model_dump(mode="json")
            )
            if runtime_profile is not None
            else load_job_runtime_profile(path)
        )
    except RuntimeProfileResolutionError as exc:
        return selected_asr, None, exc.code
    if (
        selected_runtime.asr_profile_checksum_sha256
        != selected_asr.profile_checksum_sha256
    ):
        return selected_asr, selected_runtime, "runtime_profile_mismatch"
    return selected_asr, selected_runtime, None


def _find_idempotent_job(
    repo: MockRepository,
    *,
    idempotency_key: str,
) -> ProcessingJob | None:
    return repo.find_processing_job_by_idempotency_key(
        idempotency_key
    )


def _job_lineage_details(
    *,
    audio,
    normalized,
    provider_id: str,
    asr_profile: PinnedAsrProfile | None,
    runtime_profile: AsrJobRuntimeProfile | None,
    idempotency_key: str | None,
    attempt_number: int,
    previous_attempt_job_id: str | None,
) -> dict[str, object]:
    return {
        "audio_file_id": audio.audio_file_id,
        "source_asset_version": audio.source_asset_version,
        "source_checksum_sha256": audio.checksum_sha256,
        "normalized_asset_version": normalized.asset_version,
        "normalized_checksum_sha256": (
            normalized.normalized_checksum_sha256
        ),
        "provider_id": provider_id,
        "asr_profile_id": (
            asr_profile.profile_id if asr_profile is not None else None
        ),
        "asr_profile_version": (
            asr_profile.profile_version if asr_profile is not None else None
        ),
        "asr_profile_checksum_sha256": (
            asr_profile.profile_checksum_sha256
            if asr_profile is not None
            else None
        ),
        "runtime_profile_id": (
            runtime_profile.profile_id
            if runtime_profile is not None
            else None
        ),
        "runtime_profile_version": (
            runtime_profile.profile_version
            if runtime_profile is not None
            else None
        ),
        "runtime_profile_checksum_sha256": (
            runtime_profile.profile_checksum_sha256
            if runtime_profile is not None
            else None
        ),
        "idempotency_key": idempotency_key,
        "attempt_number": attempt_number,
        "previous_attempt_job_id": previous_attempt_job_id,
        "retry_allowed": True,
    }


def _record_job(
    repo: MockRepository,
    job: ProcessingJob,
    *,
    audit_action: str,
    audit_message: str,
) -> ProcessingJob:
    recorded, _ = repo.create_processing_job(
        job,
        audit_action=audit_action,
        audit_message=audit_message,
    )
    return recorded


def _failed_creation_job(
    repo: MockRepository,
    *,
    session_id: str,
    audio,
    normalized,
    provider_id: str,
    asr_profile: PinnedAsrProfile | None,
    runtime_profile: AsrJobRuntimeProfile | None,
    idempotency_key: str | None,
    attempt_number: int,
    previous_attempt_job_id: str | None,
    error_code: str,
    provider_reason_code: str | None = None,
    provider_remediation: str | None = None,
    missing_dependencies: tuple[str, ...] = (),
) -> ProcessingJob:
    session = repo.sessions[session_id]
    details = _job_lineage_details(
        audio=audio,
        normalized=normalized,
        provider_id=provider_id,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
        idempotency_key=idempotency_key,
        attempt_number=attempt_number,
        previous_attempt_job_id=previous_attempt_job_id,
    )
    details.update(
        {
            "provider_reason_code": provider_reason_code,
            "provider_remediation": provider_remediation,
            "missing_dependencies": list(missing_dependencies),
            "status_history": [JobStatus.failed.value],
        }
    )
    if error_code in {
        "runtime_profile_unavailable",
        "runtime_profile_unverified",
    }:
        details["retry_allowed"] = False
        details["remediation"] = (
            "Restore or select a verified versioned runtime profile, then "
            "create a fresh transcription job."
        )
    return _record_job(
        repo,
        ProcessingJob(
            job_id=new_id("job"),
            organization_id=session.organization_id,
            session_id=session_id,
            status=JobStatus.failed,
            message=(
                "Transcription capability is unavailable for the exact "
                "requested lineage."
            ),
            error_code=error_code,
            details=details,
        ),
        audit_action="transcription.job_unavailable",
        audit_message=(
            "Transcription attempt failed before provider execution."
        ),
    )


def process_audio(
    repo: MockRepository,
    session_id: str,
    payload: TranscriptionJobRequest,
) -> ProcessingJob:
    return create_audio_processing_job(repo, session_id, payload)


def create_audio_processing_job(
    repo: MockRepository,
    session_id: str,
    payload: AudioProcessRequest | TranscriptionJobRequest,
    *,
    provider_registry=None,
    settings: Settings | None = None,
    asr_profile: PinnedAsrProfile | None = None,
    runtime_profile: AsrJobRuntimeProfile | None = None,
    attempt_number: int = 1,
    previous_attempt_job_id: str | None = None,
    force_new_attempt: bool = False,
) -> ProcessingJob:
    initial_session = repo.sessions.get(session_id)
    if initial_session is None:
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        initial_session = repo.sessions.get(session_id)
    if initial_session is None:
        raise KeyError(session_id)
    with repo.case_consent_fence(initial_session.case_id):
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        ensure_session_consent_active(repo, session_id)
        if repo.sessions[session_id].status is ReviewStatus.withdrawn:
            raise ValueError(
                "Session is withdrawn; audio processing is blocked."
            )
        return _create_audio_processing_job_locked(
            repo,
            session_id,
            payload,
            provider_registry=provider_registry,
            settings=settings,
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
            attempt_number=attempt_number,
            previous_attempt_job_id=previous_attempt_job_id,
            force_new_attempt=force_new_attempt,
        )


def _create_audio_processing_job_locked(
    repo: MockRepository,
    session_id: str,
    payload: AudioProcessRequest | TranscriptionJobRequest,
    *,
    provider_registry=None,
    settings: Settings | None = None,
    asr_profile: PinnedAsrProfile | None = None,
    runtime_profile: AsrJobRuntimeProfile | None = None,
    attempt_number: int = 1,
    previous_attempt_job_id: str | None = None,
    force_new_attempt: bool = False,
) -> ProcessingJob:
    runtime_settings = settings or get_settings()
    registry = provider_registry or asr_provider_registry
    provider_id = _provider_id(payload)
    if provider_id != "local_faster_whisper":
        raise TranscriptionJobContractError(
            "provider_not_allowed",
            remediation=(
                "Use local_faster_whisper for normal audio upload or use "
                "the separate manual transcript endpoint."
            ),
        )
    with _job_creation_lock:
        audio, normalized = _verified_job_lineage(
            repo,
            session_id,
            payload,
        )
        selected_asr, selected_runtime, profile_error = _resolve_profiles(
            settings=runtime_settings,
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
        )
        idempotency_key = (
            build_transcription_idempotency_key(
                audio_file_id=audio.audio_file_id,
                source_asset_version=audio.source_asset_version,
                normalized_asset_version=normalized.asset_version,
                normalized_checksum_sha256=(
                    normalized.normalized_checksum_sha256
                ),
                provider_id=provider_id,
                asr_profile_checksum_sha256=(
                    selected_asr.profile_checksum_sha256
                ),
                runtime_profile_checksum_sha256=(
                    selected_runtime.profile_checksum_sha256
                ),
            )
            if selected_asr is not None and selected_runtime is not None
            else None
        )
        if idempotency_key and not force_new_attempt:
            existing = _find_idempotent_job(
                repo,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                return repo.clone(existing)
        if profile_error is not None:
            return _failed_creation_job(
                repo,
                session_id=session_id,
                audio=audio,
                normalized=normalized,
                provider_id=provider_id,
                asr_profile=selected_asr,
                runtime_profile=selected_runtime,
                idempotency_key=idempotency_key,
                attempt_number=attempt_number,
                previous_attempt_job_id=previous_attempt_job_id,
                error_code=profile_error,
            )
        assert selected_asr is not None
        assert selected_runtime is not None
        try:
            provider = registry.get(provider_id)
        except KeyError:
            return _failed_creation_job(
                repo,
                session_id=session_id,
                audio=audio,
                normalized=normalized,
                provider_id=provider_id,
                asr_profile=selected_asr,
                runtime_profile=selected_runtime,
                idempotency_key=idempotency_key,
                attempt_number=attempt_number,
                previous_attempt_job_id=previous_attempt_job_id,
                error_code="provider_unavailable",
                provider_reason_code="provider_not_registered",
            )
        availability = provider.check_availability()
        if not availability:
            return _failed_creation_job(
                repo,
                session_id=session_id,
                audio=audio,
                normalized=normalized,
                provider_id=provider_id,
                asr_profile=selected_asr,
                runtime_profile=selected_runtime,
                idempotency_key=idempotency_key,
                attempt_number=attempt_number,
                previous_attempt_job_id=previous_attempt_job_id,
                error_code="provider_unavailable",
                provider_reason_code=availability.reason_code,
                provider_remediation=availability.remediation,
                missing_dependencies=availability.missing_dependencies,
            )
        details = _job_lineage_details(
            audio=audio,
            normalized=normalized,
            provider_id=provider_id,
            asr_profile=selected_asr,
            runtime_profile=selected_runtime,
            idempotency_key=idempotency_key,
            attempt_number=attempt_number,
            previous_attempt_job_id=previous_attempt_job_id,
        )
        details["status_history"] = [JobStatus.queued.value]
        session = repo.sessions[session_id]
        return _record_job(
            repo,
            ProcessingJob(
                job_id=new_id("job"),
                organization_id=session.organization_id,
                session_id=session_id,
                status=JobStatus.queued,
                message="Real local transcription job queued.",
                details=details,
            ),
            audit_action="transcription.job_queued",
            audit_message="Real local transcription attempt queued.",
        )


def retry_audio_processing_job(
    repo: MockRepository,
    job_id: str,
    *,
    provider_registry=None,
    settings: Settings | None = None,
    asr_profile: PinnedAsrProfile | None = None,
    runtime_profile: AsrJobRuntimeProfile | None = None,
) -> ProcessingJob:
    initial_job = repo.get_processing_job(job_id)
    if initial_job is None:
        raise ValueError("Job not found.")
    initial_session = repo.sessions.get(initial_job.session_id)
    if initial_session is None:
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        initial_session = repo.sessions.get(initial_job.session_id)
    if initial_session is None:
        raise KeyError(initial_job.session_id)
    with repo.case_consent_fence(initial_session.case_id):
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        current = repo.get_processing_job(job_id)
        if current is None:
            raise ValueError("Job not found.")
        ensure_session_consent_active(repo, current.session_id)
        if repo.sessions[current.session_id].status is ReviewStatus.withdrawn:
            raise ValueError(
                "Session is withdrawn; audio processing retry is blocked."
            )
        return _retry_audio_processing_job_locked(
            repo,
            job_id,
            provider_registry=provider_registry,
            settings=settings,
            asr_profile=asr_profile,
            runtime_profile=runtime_profile,
        )


def _retry_audio_processing_job_locked(
    repo: MockRepository,
    job_id: str,
    *,
    provider_registry=None,
    settings: Settings | None = None,
    asr_profile: PinnedAsrProfile | None = None,
    runtime_profile: AsrJobRuntimeProfile | None = None,
) -> ProcessingJob:
    failed = repo.get_processing_job(job_id)
    if failed is None:
        raise ValueError("Job not found.")
    if failed.status is not JobStatus.failed:
        raise TranscriptionJobContractError(
            "job_not_retryable",
            remediation="Retry only an explicitly failed ASR attempt.",
        )
    if not bool(failed.details.get("retry_allowed", False)):
        if failed.error_code in {
            "runtime_profile_unavailable",
            "runtime_profile_unverified",
        }:
            raise TranscriptionJobContractError(
                "runtime_profile_retry_not_allowed",
                remediation=(
                    "Restore or select a verified versioned runtime profile, "
                    "then create a fresh transcription job."
                ),
            )
        raise TranscriptionJobContractError(
            "job_not_retryable",
            remediation=(
                "Remediate the failed capability and create a fresh "
                "transcription job."
            ),
        )
    audio_id = str(failed.details["audio_file_id"])
    audio = repo.audio_files.get(audio_id)
    normalized = repo.get_current_normalized_audio_asset(audio_id)
    if (
        audio is None
        or normalized is None
        or audio.source_asset_version
        != failed.details.get("source_asset_version")
        or audio.checksum_sha256
        != failed.details.get("source_checksum_sha256")
        or normalized.asset_version
        != failed.details.get("normalized_asset_version")
        or normalized.normalized_checksum_sha256
        != failed.details.get("normalized_checksum_sha256")
    ):
        raise TranscriptionJobContractError(
            "job_lineage_stale",
            remediation=(
                "Create a new job for the new source/normalized lineage; "
                "do not retry the older attempt."
            ),
        )
    selected_asr, selected_runtime, profile_error = _resolve_profiles(
        settings=settings or get_settings(),
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    if (
        profile_error is not None
        or selected_asr is None
        or selected_runtime is None
        or selected_asr.profile_checksum_sha256
        != failed.details.get("asr_profile_checksum_sha256")
        or selected_runtime.profile_checksum_sha256
        != failed.details.get("runtime_profile_checksum_sha256")
    ):
        raise TranscriptionJobContractError(
            "retry_profile_lineage_mismatch",
            remediation=(
                "Retry only with the exact ASR and job-runtime profiles from "
                "the failed attempt; create a fresh job identity for changed "
                "profiles."
            ),
        )
    registry = provider_registry or asr_provider_registry
    try:
        provider = registry.get(str(failed.details["provider_id"]))
    except KeyError:
        provider = None
    if provider is not None:
        try:
            provider.prepare_for_retry(profile=selected_asr)
        except Exception as exc:
            raise TranscriptionJobContractError(
                "provider_retry_refresh_failed",
                remediation=(
                    "Restore the exact provider capability for the pinned "
                    "profile before retrying."
                ),
            ) from exc
    payload = TranscriptionJobRequest(
        audio_file_id=audio_id,
        provider_id=str(failed.details["provider_id"]),
        expected_source_asset_version=int(
            failed.details["source_asset_version"]
        ),
        expected_normalized_asset_version=int(
            failed.details["normalized_asset_version"]
        ),
    )
    return _create_audio_processing_job_locked(
        repo,
        failed.session_id,
        payload,
        provider_registry=registry,
        settings=settings,
        asr_profile=selected_asr,
        runtime_profile=selected_runtime,
        attempt_number=int(failed.details.get("attempt_number", 1)) + 1,
        previous_attempt_job_id=failed.job_id,
        force_new_attempt=True,
    )


def _fail_running_job(
    repo: MockRepository,
    job,
    *,
    error_code: str,
    execution_provenance: dict[str, object] | None = None,
    completeness: AsrCompletenessResult | None = None,
) -> ProcessingJob:
    expected_status = job.status
    job.status = JobStatus.failed
    job.error_code = error_code
    job.message = "Transcription attempt failed; remediation and retry required."
    details = dict(job.details)
    details["retry_allowed"] = True
    if execution_provenance is not None:
        details["execution_provenance"] = execution_provenance
    if completeness is not None:
        details["completeness"] = completeness.model_dump(mode="json")
    job.details = details
    append_job_status(job, JobStatus.failed)
    try:
        return repo.update_processing_job(
            job,
            expected_status=expected_status,
            audit_action="transcription.job_failed",
            audit_message=(
                "Transcription attempt failed without creating a "
                "review draft."
            ),
        )
    except ProcessingJobStateConflictError as exc:
        return repo.clone(exc.job)


def _cancel_running_job_for_withdrawn_consent(
    repo: MockRepository,
    job: ProcessingJob,
) -> ProcessingJob:
    if job.status not in {JobStatus.queued, JobStatus.processing}:
        return repo.clone(job)
    expected_status = job.status
    job.status = JobStatus.cancelled
    job.error_code = "consent_withdrawn"
    job.message = "Audio processing cancelled because consent is inactive."
    job.details = {
        **job.details,
        "consent_withdrawn": True,
        "retry_allowed": False,
    }
    append_job_status(job, JobStatus.cancelled)
    try:
        return repo.update_processing_job(
            job,
            expected_status=expected_status,
            audit_action="transcription.job_cancelled",
            audit_message=(
                "Transcription attempt cancelled because consent was "
                "withdrawn."
            ),
        )
    except ProcessingJobStateConflictError as exc:
        return repo.clone(exc.job)


def _assert_job_lineage_current(repo: MockRepository, job):
    audio_id = str(job.details["audio_file_id"])
    if audio_id not in repo.audio_files:
        raise TranscriptionJobContractError(
            "job_lineage_stale",
            remediation="Restore the exact verified source asset.",
        )
    audio = repo.audio_files[audio_id]
    normalized = repo.get_current_normalized_audio_asset(audio_id)
    if (
        normalized is None
        or audio.source_asset_version
        != job.details["source_asset_version"]
        or audio.checksum_sha256
        != job.details["source_checksum_sha256"]
        or normalized.asset_version
        != job.details["normalized_asset_version"]
        or normalized.normalized_checksum_sha256
        != job.details["normalized_checksum_sha256"]
        or normalized.verification_status != "verified"
    ):
        raise TranscriptionJobContractError(
            "job_lineage_stale",
            remediation="Create a new job for the current verified lineage.",
        )
    return audio, normalized


def _extract_segments(result) -> tuple[object, ...]:
    segments = getattr(result, "segments", None)
    return tuple(segments or ())


def _detected_speech_intervals(
    result,
) -> tuple[SpeechInterval, ...]:
    evidence = getattr(result, "speech_detection_evidence", None)
    if not isinstance(evidence, SpeechDetectionEvidence):
        return ()
    evidence = evidence.revalidated()
    return tuple(
        SpeechInterval(
            start_ms=item.start_ms,
            end_ms=item.end_ms,
        )
        for item in evidence.intervals
    )


def _public_provider_provenance(result) -> dict[str, object]:
    provenance = getattr(result, "provenance", None)
    if provenance is None:
        return {}
    return provenance.model_dump(mode="json")


def run_audio_processing_job(
    repo: MockRepository,
    job_id: str,
    *,
    provider_registry=None,
    settings: Settings | None = None,
    asr_profile: PinnedAsrProfile | None = None,
    runtime_profile: AsrJobRuntimeProfile | None = None,
    storage_adapter=None,
    test_execution_runner: Callable[..., AsrExecutionOutcome] | None = None,
    allow_test_execution_runner: bool = False,
) -> ProcessingJob:
    job = repo.get_processing_job(job_id)
    if job is None:
        raise ValueError("Job not found.")
    if job.status is not JobStatus.queued:
        return repo.clone(job)
    try:
        ensure_session_consent_active(repo, job.session_id)
    except ValueError:
        job.status = JobStatus.cancelled
        job.error_code = "consent_withdrawn"
        job.message = "Audio processing cancelled because consent is inactive."
        job.details = {**job.details, "consent_withdrawn": True}
        append_job_status(job, JobStatus.cancelled)
        try:
            return repo.update_processing_job(
                job,
                expected_status=JobStatus.queued,
                audit_action="transcription.job_cancelled",
                audit_message=(
                    "Transcription attempt cancelled before provider "
                    "execution."
                ),
            )
        except ProcessingJobStateConflictError as exc:
            return repo.clone(exc.job)

    try:
        audio, normalized = _assert_job_lineage_current(repo, job)
    except TranscriptionJobContractError:
        return _fail_running_job(
            repo,
            job,
            error_code="job_lineage_stale",
        )
    runtime_settings = settings or get_settings()
    selected_asr, selected_runtime, profile_error = _resolve_profiles(
        settings=runtime_settings,
        asr_profile=asr_profile,
        runtime_profile=runtime_profile,
    )
    if (
        profile_error is not None
        or selected_asr is None
        or selected_runtime is None
        or selected_asr.profile_checksum_sha256
        != job.details.get("asr_profile_checksum_sha256")
        or selected_runtime.profile_checksum_sha256
        != job.details.get("runtime_profile_checksum_sha256")
    ):
        return _fail_running_job(
            repo,
            job,
            error_code=profile_error or "runtime_profile_mismatch",
        )
    registry = provider_registry or asr_provider_registry
    try:
        provider = registry.get("local_faster_whisper")
    except KeyError:
        return _fail_running_job(
            repo,
            job,
            error_code="provider_unavailable",
        )
    availability = provider.check_availability()
    if not availability:
        return _fail_running_job(
            repo,
            job,
            error_code="provider_unavailable",
        )

    job.status = JobStatus.processing
    job.message = "Real local transcription is running."
    append_job_status(job, JobStatus.processing)
    try:
        job = repo.update_processing_job(
            job,
            expected_status=JobStatus.queued,
            audit_action="transcription.job_started",
            audit_message="Real local transcription attempt started.",
        )
    except ProcessingJobStateConflictError as exc:
        return repo.clone(exc.job)
    adapter = storage_adapter or get_storage_adapter()
    max_size_bytes = (
        runtime_settings.max_audio_file_size_mb * 1024 * 1024
    )
    staged_path: Path | None = None
    try:
        if adapter.storage_mode != audio.storage_mode:
            raise StorageProcessingError(
                "source_storage_mismatch",
                remediation=(
                    "Retry with the private storage adapter linked to "
                    "the source audio lineage."
                ),
            )
        # Normalized assets are durably linked to their source audio record;
        # that source metadata binds every normalized-byte read to one
        # hashed backend namespace.
        adapter.validate_storage_backend_identity(
            audio.storage_backend_identity_sha256
        )
        with adapter.open_normalized_for_processing(
            normalized.object_key,
            max_size_bytes=max_size_bytes,
        ) as source:
            digest = sha256()
            with tempfile.NamedTemporaryFile(
                mode="w+b",
                prefix=f"lingualens-asr-{job.job_id}-",
                suffix=".wav",
                delete=False,
            ) as staged:
                staged_path = Path(staged.name)
                total = 0
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    total += len(chunk)
                    if total > max_size_bytes:
                        raise StorageProcessingError(
                            "storage_download_size_exceeded",
                            actual_value=total,
                            configured_limit=max_size_bytes,
                            unit="bytes",
                            remediation=(
                                "Regenerate the bounded normalized asset."
                            ),
                        )
                    digest.update(chunk)
                    staged.write(chunk)
                staged.flush()
        if digest.hexdigest() != normalized.normalized_checksum_sha256:
            return _fail_running_job(
                repo,
                job,
                error_code="normalized_checksum_mismatch",
            )
        transcription_input = TranscriptionInput(
            normalized_audio=VerifiedNormalizedAudioHandle(
                source_audio_file_id=audio.audio_file_id,
                source_asset_version=audio.source_asset_version,
                source_checksum_sha256=str(audio.checksum_sha256),
                normalized_asset_version=normalized.asset_version,
                normalized_checksum_sha256=(
                    normalized.normalized_checksum_sha256
                ),
                normalized_object_key=normalized.object_key,
                local_processing_path=staged_path,
                verification_status="verified",
                is_current=True,
            ),
            profile=selected_asr,
        )
        try:
            if test_execution_runner is not None:
                if not allow_test_execution_runner:
                    return _fail_running_job(
                        repo,
                        job,
                        error_code="test_execution_runner_forbidden",
                    )
                outcome = test_execution_runner(
                    lambda: provider.transcribe(transcription_input),
                    timeout_seconds=selected_runtime.timeout_seconds,
                    timeout_profile_checksum_sha256=(
                        selected_runtime.profile_checksum_sha256
                    ),
                )
            else:
                outcome = execute_local_asr_with_evidence_timeout(
                    LocalAsrExecutionRequest(
                        transcription_input=transcription_input
                    ),
                    timeout_seconds=selected_runtime.timeout_seconds,
                    timeout_profile_checksum_sha256=(
                        selected_runtime.profile_checksum_sha256
                    ),
                )
        except AsrExecutionTimeout as exc:
            return _fail_running_job(
                repo,
                job,
                error_code="asr_timeout",
                execution_provenance=exc.metrics.model_dump(mode="json"),
            )
        except AsrExecutionUnavailable as exc:
            return _fail_running_job(
                repo,
                job,
                error_code="runtime_timeout_capability_unavailable",
                execution_provenance=exc.metrics.model_dump(mode="json"),
            )
        except AsrExecutionFailure as exc:
            return _fail_running_job(
                repo,
                job,
                error_code="asr_failed",
                execution_provenance=exc.metrics.model_dump(mode="json"),
            )
        result = outcome.value
        execution_provenance = outcome.metrics.model_dump(mode="json")
    except StorageProcessingError:
        return _fail_running_job(
            repo,
            job,
            error_code="normalized_asset_unavailable",
        )
    finally:
        if staged_path is not None:
            try:
                staged_path.unlink(missing_ok=True)
            except OSError:
                pass

    status = str(getattr(result, "status", "failed"))
    metadata = getattr(result, "provider_metadata", {}) or {}
    provider_partial = bool(metadata.get("partial_result", False))
    if status != "completed":
        error_code = str(
            getattr(result, "error_code", None)
            or (
                getattr(getattr(result, "unavailability", None), "code", None)
            )
            or "asr_failed"
        )
        if provider_partial:
            error_code = "provider_partial_result"
        return _fail_running_job(
            repo,
            job,
            error_code=error_code,
            execution_provenance=execution_provenance,
        )
    try:
        segments = _extract_segments(result)
        segment_intervals = tuple(
            AsrSegmentInterval(
                segment_id=str(segment.segment_id),
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
            )
            for segment in segments
        )
        completeness = evaluate_asr_completeness(
            audio_duration_ms=normalized.duration_ms,
            detected_speech_intervals=_detected_speech_intervals(result),
            segment_intervals=segment_intervals,
            profile=selected_runtime,
            provider_reported_partial=provider_partial,
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return _fail_running_job(
            repo,
            job,
            error_code="asr_result_invalid",
            execution_provenance=execution_provenance,
        )
    if completeness.status == "blocked":
        blocker = next(
            issue
            for issue in completeness.issues
            if issue.disposition == "integrity_blocker"
        )
        return _fail_running_job(
            repo,
            job,
            error_code=blocker.code,
            execution_provenance=execution_provenance,
            completeness=completeness,
        )

    try:
        transcript = create_draft_transcript_from_result(
            repo,
            job=job,
            result=result,
            audio=audio,
            normalized=normalized,
            asr_profile=selected_asr,
            runtime_profile=selected_runtime,
            completeness=completeness,
        )
        private_record = result.to_private_record()
        provenance = result.provenance
        evidence = PrivateAsrEvidenceRecord(
            job_id=job.job_id,
            transcript_id=transcript.transcript_id,
            raw_provider_payload_checksum_sha256=(
                provenance.raw_provider_payload_checksum_sha256
            ),
            speech_detection_evidence_checksum_sha256=(
                provenance.speech_detection_evidence_checksum_sha256
            ),
            canonical_private_record_checksum_sha256=sha256(
                json.dumps(
                    private_record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            private_record=private_record,
            created_at=utc_now(),
        )
    except Exception:  # noqa: BLE001
        return _fail_running_job(
            repo,
            job,
            error_code="draft_persistence_failed",
            execution_provenance=execution_provenance,
            completeness=completeness,
        )
    warnings = [
        getattr(item, "message", str(item))
        for item in getattr(result, "warnings", ())
    ]
    warnings.extend(
        issue.code
        for issue in completeness.issues
        if issue.disposition == "acknowledgeable_limitation"
    )
    asr_draft_result = AsrDraftResult(
        provider="local_faster_whisper",
        transcript_id=transcript.transcript_id,
        utterance_count=len(transcript.utterances),
        confidence_available=bool(
            getattr(result, "confidence_available", False)
        ),
        timestamps_available=bool(
            getattr(result, "word_timestamps_available", True)
        ),
        diarization_available=bool(
            getattr(result, "speaker_segments_available", False)
        ),
        warnings=warnings,
        quality=analyze_audio_quality(
            duration_seconds=normalized.duration_ms / 1000,
            sample_rate_hz=normalized.sample_rate_hz,
            channels=normalized.channels,
            estimated_noise_level=None,
            silence_ratio=None,
        ),
    )
    job.status = JobStatus.needs_review
    job.error_code = None
    job.message = (
        "Draft transcript generated; therapist review and speaker mapping "
        "confirmation are required."
    )
    job.details = {
        **job.details,
        "execution_provenance": execution_provenance,
        "completeness": completeness.model_dump(mode="json"),
        "asr_draft": asr_draft_result.model_dump(mode="json"),
        "private_evidence_ref": {
            "job_id": evidence.job_id,
            "transcript_id": evidence.transcript_id,
            "raw_provider_payload_checksum_sha256": (
                evidence.raw_provider_payload_checksum_sha256
            ),
            "speech_detection_evidence_checksum_sha256": (
                evidence.speech_detection_evidence_checksum_sha256
            ),
        },
        "retry_allowed": False,
    }
    append_job_status(job, JobStatus.needs_review)
    with repo.case_consent_fence(audio.case_id):
        load = getattr(repo, "load", None)
        if callable(load):
            load()
        current_job = repo.get_processing_job(job.job_id)
        if current_job is None:
            raise KeyError(job.job_id)
        try:
            ensure_session_consent_active(repo, current_job.session_id)
            if (
                repo.sessions[current_job.session_id].status
                is ReviewStatus.withdrawn
            ):
                raise ValueError("Session is withdrawn.")
        except ValueError:
            return _cancel_running_job_for_withdrawn_consent(
                repo,
                current_job,
            )
        if current_job.status is not JobStatus.processing:
            return repo.clone(current_job)
        try:
            _assert_job_lineage_current(repo, current_job)
        except TranscriptionJobContractError:
            return _fail_running_job(
                repo,
                current_job,
                error_code="job_lineage_stale",
                execution_provenance=execution_provenance,
                completeness=completeness,
            )
        try:
            return repo.finalize_transcription_draft(
                job=job,
                expected_status=JobStatus.processing,
                transcript=transcript,
                evidence=evidence,
            )
        except ProcessingJobStateConflictError as exc:
            return repo.clone(exc.job)
        except Exception:  # noqa: BLE001 - atomic repository rollback required
            latest_job = repo.get_processing_job(job.job_id)
            if latest_job is None:
                raise
            return _fail_running_job(
                repo,
                latest_job,
                error_code="draft_persistence_failed",
                execution_provenance=execution_provenance,
                completeness=completeness,
            )


def create_draft_transcript_from_result(
    repo: MockRepository,
    *,
    job: ProcessingJob,
    result,
    audio,
    normalized,
    asr_profile: PinnedAsrProfile,
    runtime_profile: AsrJobRuntimeProfile,
    completeness: AsrCompletenessResult,
) -> Transcript:
    session = repo.sessions[job.session_id]
    segments = _extract_segments(result)
    utterances = [
        Utterance(
            utterance_id=str(segment.segment_id),
            speaker=str(segment.temporary_speaker_id),
            temporary_speaker_id=str(segment.temporary_speaker_id),
            source_speaker_label=str(segment.source_speaker_label),
            text=str(segment.text),
            start_ms=int(segment.start_ms),
            end_ms=int(segment.end_ms),
            confidence=segment.confidence,
            unintelligible=False,
            source="asr",
            notes="ASR draft — therapist review required.",
            review_status="draft",
        )
        for segment in segments
    ]
    raw_labels = list(
        dict.fromkeys(
            str(segment.source_speaker_label)
            for segment in segments
        )
    )
    qa_issues = [
        QaIssue(
            code="ASR_DRAFT_REVIEW_REQUIRED",
            severity="warning",
            message=(
                "Therapist review and correction are required before QA."
            ),
            blocking=False,
            fix_suggestion=(
                "Review every utterance and confirm speaker mapping."
            ),
            source="asr_pipeline",
            validation_version=(
                runtime_profile.completeness_rules.rule_version
            ),
        )
    ]
    qa_issues.extend(
        QaIssue(
            code=issue.code,
            severity=issue.severity,
            message=issue.code,
            blocking=False,
            fix_suggestion=issue.remediation,
            source="asr_completeness",
            validation_version=issue.rule_version,
        )
        for issue in completeness.issues
        if issue.disposition == "acknowledgeable_limitation"
    )
    provider_provenance = _public_provider_provenance(result)
    asr_provenance = {
        **provider_provenance,
        "job_id": job.job_id,
        "source_audio_file_id": audio.audio_file_id,
        "source_asset_version": audio.source_asset_version,
        "source_checksum_sha256": audio.checksum_sha256,
        "normalized_asset_version": normalized.asset_version,
        "normalized_checksum_sha256": (
            normalized.normalized_checksum_sha256
        ),
        "asr_profile_checksum_sha256": (
            asr_profile.profile_checksum_sha256
        ),
        "runtime_profile_checksum_sha256": (
            runtime_profile.profile_checksum_sha256
        ),
        "runtime_profile_version": runtime_profile.profile_version,
        "completeness_rule_version": (
            runtime_profile.completeness_rules.rule_version
        ),
    }
    raw_text = build_cha_text(
        utterances,
        media_name=f"{job.session_id}_audio",
    )
    transcript = Transcript(
        transcript_id=new_id("tr"),
        session_id=job.session_id,
        case_id=session.case_id,
        organization_id=session.organization_id,
        source="asr_draft:local_faster_whisper",
        raw_text=raw_text,
        utterances=utterances,
        review_status=ReviewStatus.needs_review,
        therapist_attested=False,
        qa_status=QaStatus.not_run,
        qa_issues=qa_issues,
        asr_profile={
            "profile_id": asr_profile.profile_id,
            "profile_version": asr_profile.profile_version,
            "profile_checksum_sha256": (
                asr_profile.profile_checksum_sha256
            ),
            "model_identifier": asr_profile.model_identifier,
            "model_revision": asr_profile.model_revision,
            "model_checksum_sha256": (
                asr_profile.model_checksum_sha256
            ),
        },
        asr_provenance=asr_provenance,
        raw_speaker_labels=raw_labels,
        chat_metadata={
            "asr_provider": "local_faster_whisper",
            "asr_provider_version": getattr(
                result,
                "provider_version",
                "v1.7.0",
            ),
            "audio_file_id": audio.audio_file_id,
            "source_asset_version": audio.source_asset_version,
            "normalized_asset_version": normalized.asset_version,
            "word_timestamps_available": bool(
                getattr(result, "word_timestamps_available", True)
            ),
            "speaker_mapping_status": "incomplete",
            "qa_status": "incomplete",
            "attestation_status": "incomplete",
            "provider_warnings": [
                getattr(item, "message", str(item))
                for item in getattr(result, "warnings", ())
            ],
        },
    )
    return transcript



def analyze_audio_quality(
    *,
    duration_seconds: float | None,
    sample_rate_hz: int | None,
    channels: int | None,
    estimated_noise_level: float | None,
    silence_ratio: float | None,
) -> AudioQualityReport:
    warnings: list[str] = []
    status = "pass"
    if duration_seconds is not None and duration_seconds > 3600:
        warnings.append("audio too long")
        status = "failed"
    if sample_rate_hz is not None and sample_rate_hz < 16000:
        warnings.append("sample rate below 16 kHz")
        status = "warning" if status == "pass" else status
    if channels is not None and channels < 1:
        warnings.append("missing audio channel")
        status = "failed"
    if estimated_noise_level is not None and estimated_noise_level > 0.7:
        warnings.append("audio too noisy")
        status = "warning" if status == "pass" else status
    if silence_ratio is not None and silence_ratio > 0.8:
        warnings.append("high silence ratio")
        status = "warning" if status == "pass" else status
    return AudioQualityReport(
        duration_seconds=duration_seconds,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        estimated_noise_level=estimated_noise_level,
        silence_ratio=silence_ratio,
        status=status,
        warnings=warnings,
    )







def append_job_status(job: ProcessingJob, status: JobStatus) -> None:
    history = list(job.details.get("status_history", []))
    if not history or history[-1] != status.value:
        history.append(status.value)
    job.details = {**job.details, "status_history": history}
