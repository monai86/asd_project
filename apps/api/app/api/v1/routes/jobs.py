from copy import deepcopy
import tempfile
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_repository
from app.auth.authorization import assert_clinical_mutation_allowed, assert_sensitive_clinical_export_allowed, require_case, require_session
from app.core.config import JSON_SAFE_INTEGER_MAX, Settings, get_settings
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AudioFileMetadata, AudioProcessRequest, AudioUploadCompleteRequest, AudioUploadRequest, JobStatus, ProcessingJob, TranscriptionJobRequest
from app.schemas.speech_pipeline import AudioNormalizationProvenance
from app.services.audio_job_service import complete_audio_upload, create_audio_upload_job, process_audio as process_audio_job
from app.services.audio_media_service import (
    AudioIntakeError,
    audio_intake_error_from_storage,
    get_decoder_capability_registry,
    verified_configured_audio_formats,
    verify_and_normalize_audio,
)
from app.services.consent_service import ensure_audio_file_consent_active, ensure_session_consent_active
from app.services.storage_service import (
    BaseStorageAdapter,
    StorageProcessingError,
    get_storage_adapter,
)
from app.tasks.job_queue import get_job_queue

router = APIRouter(tags=["jobs"])


JsonSafePositiveInteger = Annotated[
    int,
    Field(gt=0, le=JSON_SAFE_INTEGER_MAX),
]


class AudioNormalizationCapabilities(BaseModel):
    channels: Literal[1]
    sample_rate_hz: JsonSafePositiveInteger
    format: Literal["wav_pcm_s16le"]
    source_min_sample_rate_hz: JsonSafePositiveInteger
    source_max_sample_rate_hz: JsonSafePositiveInteger
    source_max_channels: JsonSafePositiveInteger
    max_rational_factor: JsonSafePositiveInteger
    max_filter_taps: JsonSafePositiveInteger
    max_working_bytes: JsonSafePositiveInteger


class BrowserRecordingCapabilities(BaseModel):
    state: Literal["experimental_unavailable"]
    blocks_milestone: Literal[False]


class AudioCapabilitiesResponse(BaseModel):
    milestone: Literal["v1.7.0-testbed"]
    max_size_bytes: JsonSafePositiveInteger
    max_duration_seconds: JsonSafePositiveInteger
    supported_formats: Annotated[
        list[Literal["wav", "mp3"]],
        Field(max_length=2),
    ]
    processing_state: Literal["available", "unavailable"]
    unavailable_reason: str | None = None
    normalization: AudioNormalizationCapabilities
    browser_recording: BrowserRecordingCapabilities


class AudioNormalizationVerificationResponse(BaseModel):
    source_audio_file_id: str
    source_asset_version: JsonSafePositiveInteger
    normalized_asset_version: JsonSafePositiveInteger
    source_checksum_sha256: str
    normalized_checksum_sha256: str
    duration_ms: JsonSafePositiveInteger
    frame_count: JsonSafePositiveInteger
    sample_rate_hz: JsonSafePositiveInteger
    channels: Literal[1]
    format: Literal["wav_pcm_s16le"]
    verification_status: Literal["verified"]
    provenance: AudioNormalizationProvenance


@router.get("/audio/capabilities", response_model=AudioCapabilitiesResponse)
def get_audio_capabilities(
    settings: Settings = Depends(get_settings),
) -> AudioCapabilitiesResponse:
    registry = get_decoder_capability_registry()
    supported_formats = verified_configured_audio_formats(
        settings,
        registry=registry,
    )
    unavailable_reason = None
    if not supported_formats:
        initialization_failed = any(
            capability.reason_code
            == "decoder_registry_initialization_failed"
            for capability in registry.capabilities.values()
        )
        unavailable_reason = (
            "decoder_registry_initialization_failed"
            if initialization_failed
            else (
                "decoder_runtime_unavailable"
                if not registry.verified_formats
                else "no_configured_verified_format"
            )
        )
    return AudioCapabilitiesResponse(
        milestone="v1.7.0-testbed",
        max_size_bytes=settings.max_audio_file_size_mb * 1024 * 1024,
        max_duration_seconds=settings.max_audio_duration_seconds,
        supported_formats=list(supported_formats),
        processing_state="available" if supported_formats else "unavailable",
        unavailable_reason=unavailable_reason,
        normalization=AudioNormalizationCapabilities(
            channels=settings.audio_normalization_channels,
            sample_rate_hz=settings.audio_normalization_sample_rate_hz,
            format=settings.audio_normalization_format,
            source_min_sample_rate_hz=settings.audio_source_min_sample_rate_hz,
            source_max_sample_rate_hz=settings.audio_source_max_sample_rate_hz,
            source_max_channels=settings.audio_source_max_channels,
            max_rational_factor=(
                settings.audio_normalization_max_rational_factor
            ),
            max_filter_taps=settings.audio_normalization_max_filter_taps,
            max_working_bytes=settings.audio_normalization_max_working_bytes,
        ),
        browser_recording=BrowserRecordingCapabilities(
            state="experimental_unavailable",
            blocks_milestone=False,
        ),
    )


def _ensure_audio_file_verified_for_read(audio_file: AudioFileMetadata) -> None:
    if audio_file.upload_status != "uploaded":
        raise bad_request("Audio file is not verified yet. Complete upload verification first.")


def _public_audio_metadata(audio_file: AudioFileMetadata) -> AudioFileMetadata:
    return audio_file.model_copy(update={"object_key": None})


def _public_processing_job(job: ProcessingJob) -> ProcessingJob:
    clone = job.model_copy(deep=True)
    audio_file = clone.details.get("audio_file")
    if isinstance(audio_file, dict):
        redacted = deepcopy(audio_file)
        redacted["object_key"] = None
        clone.details["audio_file"] = redacted
    return clone


@router.post("/sessions/{session_id}/audio/upload", response_model=ProcessingJob)
def upload_audio(
    session_id: str,
    payload: AudioUploadRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
    storage_adapter: BaseStorageAdapter = Depends(get_storage_adapter),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_session_consent_active(repo, session_id)
        return _public_processing_job(
            create_audio_upload_job(
                repo,
                session_id,
                payload,
                storage_adapter=storage_adapter,
            )
        )
    except AudioIntakeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.as_detail(),
        ) from exc
    except StorageProcessingError as exc:
        intake_error = audio_intake_error_from_storage(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=intake_error.as_detail(),
        ) from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/audio/{audio_file_id}", response_model=AudioFileMetadata)
def get_audio_file(
    audio_file_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file not found.")
    require_case(repo, repo.audio_files[audio_file_id].case_id, user)
    assert_sensitive_clinical_export_allowed(user)
    return _public_audio_metadata(repo.clone(repo.audio_files[audio_file_id]))


@router.post("/audio/{audio_file_id}/complete-upload", response_model=AudioFileMetadata)
def complete_upload(
    audio_file_id: str,
    payload: AudioUploadCompleteRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    storage_adapter: BaseStorageAdapter = Depends(get_storage_adapter),
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file not found.")
    require_case(repo, repo.audio_files[audio_file_id].case_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_audio_file_consent_active(repo, audio_file_id)
        return _public_audio_metadata(
            complete_audio_upload(
                repo,
                audio_file_id,
                payload,
                storage_adapter=storage_adapter,
                settings=settings,
                actor_id=user.user_id,
            )
        )
    except AudioIntakeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.as_detail(),
        ) from exc
    except StorageProcessingError as exc:
        intake_error = audio_intake_error_from_storage(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=intake_error.as_detail(),
        ) from exc
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise not_found(str(exc)) from exc
        raise bad_request(str(exc)) from exc


@router.post(
    "/audio/{audio_file_id}/verify-and-normalize",
    response_model=AudioNormalizationVerificationResponse,
)
def verify_and_normalize_uploaded_audio(
    audio_file_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    storage_adapter: BaseStorageAdapter = Depends(get_storage_adapter),
) -> AudioNormalizationVerificationResponse:
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file not found.")
    audio_file = repo.audio_files[audio_file_id]
    require_case(repo, audio_file.case_id, user)
    assert_clinical_mutation_allowed(user)
    ensure_audio_file_consent_active(repo, audio_file_id)
    try:
        asset = verify_and_normalize_audio(
            repo,
            audio_file_id,
            storage_adapter=storage_adapter,
            settings=settings,
        )
    except AudioIntakeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.as_detail(),
        ) from exc
    return AudioNormalizationVerificationResponse(
        source_audio_file_id=asset.source_audio_file_id,
        source_asset_version=asset.source_asset_version,
        normalized_asset_version=asset.asset_version,
        source_checksum_sha256=asset.source_checksum_sha256,
        normalized_checksum_sha256=asset.normalized_checksum_sha256,
        duration_ms=asset.duration_ms,
        frame_count=asset.frame_count,
        sample_rate_hz=asset.sample_rate_hz,
        channels=asset.channels,
        format=asset.format,
        verification_status=asset.verification_status,
        provenance=asset.provenance,
    )


@router.post("/sessions/{session_id}/audio/process", response_model=ProcessingJob)
def process_audio(
    session_id: str,
    payload: AudioProcessRequest | TranscriptionJobRequest | None = None,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_session_consent_active(repo, session_id)
        job = process_audio_job(repo, session_id, payload or AudioProcessRequest())
        get_job_queue().enqueue(job.job_id)
        return job
    except AudioIntakeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.as_detail(),
        ) from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=ProcessingJob)
def get_job(job_id: str, repo: MockRepository = Depends(get_repository), user: CurrentUser = Depends(get_current_user)):
    if job_id not in repo.jobs:
        raise not_found("Job not found.")
    require_session(repo, repo.jobs[job_id].session_id, user)
    return _public_processing_job(repo.clone(repo.jobs[job_id]))


@router.post("/jobs/{job_id}/cancel", response_model=ProcessingJob)
def cancel_job(job_id: str, repo: MockRepository = Depends(get_repository), user: CurrentUser = Depends(get_current_user)):
    if job_id not in repo.jobs:
        raise not_found("Job not found.")
    job = repo.jobs[job_id]
    require_session(repo, job.session_id, user)
    assert_clinical_mutation_allowed(user)
    terminal_statuses = {"failed", "cancelled", "needs_review"}
    if job.status in terminal_statuses or (hasattr(job.status, "value") and job.status.value in terminal_statuses):
        return _public_processing_job(repo.clone(job))  # idempotent
    job.status = JobStatus.cancelled
    job.message = "Job cancelled by therapist."
    from app.services.audio_job_service import append_job_status
    append_job_status(job, JobStatus.cancelled)
    repo.add_audit("job.cancel", job_id, "Transcription job cancelled by therapist.")
    return _public_processing_job(repo.clone(job))


from app.services.asr_providers.registry import asr_provider_registry

@router.get("/transcription-providers", response_model=list[dict])
def list_transcription_providers(user: CurrentUser = Depends(get_current_user)):
    """Return all registered ASR providers with live availability status."""
    return asr_provider_registry.list_supported()


from fastapi import Request
from fastapi.responses import FileResponse
from app.services.consent_service import ensure_audio_file_consent_active

@router.put("/audio/{audio_file_id}/upload-file")
async def upload_audio_file_bytes(
    audio_file_id: str,
    request: Request,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    storage_adapter: BaseStorageAdapter = Depends(get_storage_adapter),
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file metadata not found.")
    audio_file = repo.audio_files[audio_file_id]
    require_case(repo, audio_file.case_id, user)
    assert_clinical_mutation_allowed(user)
    ensure_audio_file_consent_active(repo, audio_file_id)
    if audio_file.upload_status != "pending":
        raise bad_request("This upload intent is no longer writable. Issue a new upload intent.")

    limit_bytes = settings.max_audio_file_size_mb * 1024 * 1024
    actual_size_bytes = 0
    with tempfile.SpooledTemporaryFile(
        mode="w+b",
        max_size=min(limit_bytes, 16 * 1024 * 1024),
    ) as source:
        async for chunk in request.stream():
            actual_size_bytes += len(chunk)
            if actual_size_bytes > limit_bytes:
                error = AudioIntakeError(
                    "audio_size_limit_exceeded",
                    actual_value=actual_size_bytes,
                    configured_limit=limit_bytes,
                    unit="bytes",
                    supported_formats=settings.parsed_supported_audio_formats,
                    remediation=(
                        f"Upload a file no larger than "
                        f"{settings.max_audio_file_size_mb} MiB."
                    ),
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error.as_detail(),
                )
            source.write(chunk)
        source.seek(0)
        try:
            storage_adapter.persist_source_upload(
                audio_file,
                source,
                max_size_bytes=limit_bytes,
            )
        except StorageProcessingError as exc:
            intake_error = audio_intake_error_from_storage(exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=intake_error.as_detail(),
            ) from exc

    audio_file.upload_status = "pending_verification"
    if hasattr(repo, "save"):
        repo.save()

    return {"status": "success", "size_bytes": actual_size_bytes}


@router.get("/audio/{audio_file_id}/file")
def get_audio_file_bytes(
    audio_file_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file metadata not found.")
    audio_file = repo.audio_files[audio_file_id]
    require_case(repo, audio_file.case_id, user)
    assert_sensitive_clinical_export_allowed(user)
    ensure_audio_file_consent_active(repo, audio_file_id)
    _ensure_audio_file_verified_for_read(audio_file)
    
    settings = get_settings()
    file_path = (settings.resolved_local_storage_root / audio_file.object_key).resolve()
    if not file_path.exists() or file_path.is_dir():
        raise not_found("Physical audio file not found on disk.")
        
    return FileResponse(
        path=str(file_path),
        media_type=audio_file.content_type,
        filename=audio_file.original_filename
    )


@router.get("/sessions/{session_id}/audio", response_model=list[AudioFileMetadata])
def list_session_audio_files(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    assert_sensitive_clinical_export_allowed(user)
    files = [
        f for f in repo.audio_files.values()
        if f.session_id == session_id and f.retained and f.upload_status == "uploaded"
    ]
    return [_public_audio_metadata(repo.clone(audio_file)) for audio_file in files]
