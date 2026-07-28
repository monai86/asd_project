from copy import deepcopy
from hashlib import sha256
import tempfile
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_repository
from app.auth.authorization import assert_clinical_mutation_allowed, assert_sensitive_clinical_export_allowed, require_case, require_session
from app.core.config import JSON_SAFE_INTEGER_MAX, Settings, get_settings
from app.repositories.base import ProcessingJobStateConflictError
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AudioFileMetadata,
    AudioUploadCleanupRemediation,
    AudioUploadCompleteRequest,
    AudioUploadOwnershipReceipt,
    AudioUploadRequest,
    JobStatus,
    ProcessingJob,
    TranscriptionJobRequest,
)
from app.schemas.speech_pipeline import AudioNormalizationProvenance
from app.services.audio_job_service import (
    TranscriptionJobContractError,
    complete_audio_upload,
    create_audio_upload_job,
    process_audio as process_audio_job,
    retry_audio_processing_job,
)
from app.services.audio_media_service import (
    AudioIntakeError,
    audio_intake_error_from_storage,
    get_decoder_capability_registry,
    verified_configured_audio_formats,
    verify_and_normalize_audio,
)
from app.services.consent_service import (
    active_case_consent_fence,
    ensure_audio_file_consent_active,
    ensure_session_consent_active,
)
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
    try:
        ensure_audio_file_consent_active(repo, audio_file_id)
        return _public_audio_metadata(
            repo.clone(repo.audio_files[audio_file_id])
        )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


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
    payload: TranscriptionJobRequest,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_session_consent_active(repo, session_id)
        job = process_audio_job(repo, session_id, payload)
        if job.status is JobStatus.queued:
            get_job_queue().enqueue(job.job_id)
        return _public_processing_job(job)
    except AudioIntakeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.as_detail(),
        ) from exc
    except TranscriptionJobContractError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": exc.code,
                "remediation": exc.remediation,
            },
        ) from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=ProcessingJob)
def get_job(job_id: str, repo: MockRepository = Depends(get_repository), user: CurrentUser = Depends(get_current_user)):
    job = repo.get_processing_job(job_id)
    if job is None:
        raise not_found("Job not found.")
    require_session(repo, job.session_id, user)
    try:
        ensure_session_consent_active(repo, job.session_id)
        return _public_processing_job(job)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/jobs/{job_id}/retry", response_model=ProcessingJob)
def retry_job(
    job_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    job = repo.get_processing_job(job_id)
    if job is None:
        raise not_found("Job not found.")
    require_session(repo, job.session_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_session_consent_active(repo, job.session_id)
        retried = retry_audio_processing_job(repo, job_id)
        if retried.status is JobStatus.queued:
            get_job_queue().enqueue(retried.job_id)
        return _public_processing_job(retried)
    except TranscriptionJobContractError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": exc.code,
                "remediation": exc.remediation,
            },
        ) from exc
    except AudioIntakeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.as_detail(),
        ) from exc
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/jobs/{job_id}/cancel", response_model=ProcessingJob)
def cancel_job(job_id: str, repo: MockRepository = Depends(get_repository), user: CurrentUser = Depends(get_current_user)):
    job = repo.get_processing_job(job_id)
    if job is None:
        raise not_found("Job not found.")
    require_session(repo, job.session_id, user)
    assert_clinical_mutation_allowed(user)
    case_id = repo.sessions[job.session_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            current = repo.get_processing_job(job_id)
            if current is None:
                raise not_found("Job not found.")
            require_session(repo, current.session_id, user)
            terminal_statuses = {"failed", "cancelled", "needs_review"}
            if current.status in terminal_statuses or (
                hasattr(current.status, "value")
                and current.status.value in terminal_statuses
            ):
                return _public_processing_job(repo.clone(current))
            expected_status = current.status
            current.status = JobStatus.cancelled
            current.message = "Job cancelled by therapist."
            from app.services.audio_job_service import append_job_status

            append_job_status(current, JobStatus.cancelled)
            cancelled = repo.update_processing_job(
                current,
                expected_status=expected_status,
                audit_action="job.cancel",
                audit_message="Transcription job cancelled by therapist.",
            )
    except ProcessingJobStateConflictError as exc:
        cancelled = exc.job
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    return _public_processing_job(cancelled)


from app.services.asr_providers.registry import asr_provider_registry

@router.get("/transcription-providers", response_model=list[dict])
def list_transcription_providers(user: CurrentUser = Depends(get_current_user)):
    """Return all registered ASR providers with live availability status."""
    return asr_provider_registry.list_supported()


from fastapi import Request
from fastapi.responses import FileResponse
from app.services.consent_service import ensure_audio_file_consent_active


def _cleanup_failed_upload_attempt(
    *,
    repo: MockRepository,
    storage_adapter: BaseStorageAdapter,
    receipt: AudioUploadOwnershipReceipt,
    actor_id: str,
) -> Literal[
    "exact_cleanup",
    "committed_asset_preserved",
    "ownership_unverified",
]:
    remediation: AudioUploadCleanupRemediation | None = None
    with storage_adapter.upload_attempt_fence(receipt.audio_file_id):
        ownership_verified = True
        load = getattr(repo, "load", None)
        if callable(load):
            try:
                load()
            except Exception:
                ownership_verified = False
        audio_file = repo.audio_files.get(receipt.audio_file_id)
        committed_reference = bool(
            ownership_verified
            and audio_file is not None
            and audio_file.object_key
            == receipt.intended_final_object_key
            and audio_file.upload_status
            in {"pending_verification", "uploaded"}
        )
        try:
            if committed_reference or not ownership_verified:
                staging_cleanup = (
                    storage_adapter.cleanup_upload_staging(receipt)
                )
                cleanup_succeeded = staging_cleanup.status in {
                    "deleted",
                    "object_not_found",
                    "missing_object_key",
                }
            else:
                cleanup = storage_adapter.cleanup_upload_attempt(receipt)
                cleanup_succeeded = cleanup.succeeded
            if not cleanup_succeeded:
                remediation = AudioUploadCleanupRemediation(
                    state="failed",
                    receipt=receipt,
                    error_code="storage_cleanup_incomplete",
                )
        except Exception as exc:
            remediation = AudioUploadCleanupRemediation(
                state="failed",
                receipt=receipt,
                error_code=(
                    exc.code
                    if isinstance(exc, StorageProcessingError)
                    else "storage_cleanup_failed"
                ),
            )
        if not ownership_verified:
            remediation = AudioUploadCleanupRemediation(
                state="failed",
                receipt=receipt,
                error_code="upload_ownership_verification_failed",
            )
        repo.record_audio_upload_cleanup(
            receipt,
            remediation=remediation,
            actor_id=actor_id,
        )
        if committed_reference:
            repo.add_audit(
                "audio.upload_response_retry_required",
                receipt.audio_file_id,
                "Committed audio upload requires a response retry.",
                actor_id=actor_id,
                outcome="denied",
                organization_id=(
                    audio_file.organization_id
                    if audio_file is not None
                    else None
                ),
            )
            return "committed_asset_preserved"
        if not ownership_verified:
            return "ownership_unverified"
        return "exact_cleanup"

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
    digest = sha256()
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
            digest.update(chunk)
        if actual_size_bytes <= 0:
            error = AudioIntakeError(
                "audio_content_empty",
                actual_value=actual_size_bytes,
                configured_limit=limit_bytes,
                unit="bytes",
                supported_formats=settings.parsed_supported_audio_formats,
                remediation="Upload a non-empty WAV or MP3 source asset.",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error.as_detail(),
            )
        source.seek(0)
        with repo.case_audio_fence(audio_file.case_id, audio_file_id):
            load = getattr(repo, "load", None)
            if callable(load):
                load()
            audio_file = repo.audio_files.get(audio_file_id)
            if audio_file is None:
                raise not_found("Audio file metadata not found.")
            require_case(repo, audio_file.case_id, user)
            ensure_audio_file_consent_active(repo, audio_file_id)
            if audio_file.upload_status != "pending":
                raise bad_request(
                    "This upload intent is no longer writable. "
                    "Issue a new upload intent."
                )
            receipt = storage_adapter.build_source_upload_receipt(
                audio_file,
                expected_consent_version=repo.cases[
                    audio_file.case_id
                ].version,
                checksum_sha256=digest.hexdigest(),
                size_bytes=actual_size_bytes,
            )
            try:
                storage_adapter.stage_source_upload(
                    receipt,
                    source,
                    max_size_bytes=limit_bytes,
                    reserve=lambda: repo.reserve_audio_upload_attempt(
                        receipt,
                        actor_id=user.user_id,
                    ),
                )
                repo.finalize_audio_upload_attempt(
                    receipt,
                    promote=lambda: (
                        storage_adapter.promote_source_upload(receipt)
                    ),
                    actor_id=user.user_id,
                )
            except Exception as exc:
                cleanup_resolution = _cleanup_failed_upload_attempt(
                    repo=repo,
                    storage_adapter=storage_adapter,
                    receipt=receipt,
                    actor_id=user.user_id,
                )
                if cleanup_resolution != "exact_cleanup":
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=(
                            "Upload state could not be returned safely. "
                            "Retry the upload status request."
                        ),
                    ) from exc
                if isinstance(exc, StorageProcessingError):
                    intake_error = audio_intake_error_from_storage(exc)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=intake_error.as_detail(),
                    ) from exc
                if isinstance(exc, ValueError):
                    raise bad_request(str(exc)) from exc
                raise

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
    try:
        ensure_session_consent_active(repo, session_id)
        files = [
            f
            for f in repo.audio_files.values()
            if f.session_id == session_id
            and f.retained
            and f.upload_status == "uploaded"
        ]
        return [
            _public_audio_metadata(repo.clone(audio_file))
            for audio_file in files
        ]
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
