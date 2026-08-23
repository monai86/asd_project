from copy import deepcopy

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.auth.authorization import assert_clinical_mutation_allowed, assert_sensitive_clinical_export_allowed, require_case, require_session
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AudioFileMetadata, AudioProcessRequest, AudioUploadCompleteRequest, AudioUploadRequest, JobStatus, ProcessingJob, TranscriptionJobRequest
from app.services.audio_job_service import complete_audio_upload, create_audio_upload_job, process_audio as process_audio_job
from app.services.consent_service import ensure_audio_file_consent_active, ensure_session_consent_active
from app.tasks.job_queue import get_job_queue

router = APIRouter(tags=["jobs"])


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
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_session_consent_active(repo, session_id)
        return _public_processing_job(create_audio_upload_job(repo, session_id, payload))
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
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file not found.")
    require_case(repo, repo.audio_files[audio_file_id].case_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_audio_file_consent_active(repo, audio_file_id)
        return _public_audio_metadata(complete_audio_upload(repo, audio_file_id, payload))
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise not_found(str(exc)) from exc
        raise bad_request(str(exc)) from exc


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
    job = repo.clone(repo.jobs[job_id])
    require_session(repo, job.session_id, user)
    assert_clinical_mutation_allowed(user)
    terminal_statuses = {"failed", "cancelled", "needs_review"}
    if job.status in terminal_statuses or (hasattr(job.status, "value") and job.status.value in terminal_statuses):
        return _public_processing_job(repo.clone(job))  # idempotent
    job.status = JobStatus.cancelled
    job.message = "Job cancelled by therapist."
    from app.services.audio_job_service import append_job_status
    append_job_status(job, JobStatus.cancelled)
    saved = repo.update_processing_job(
        job,
        actor_id=user.user_id,
        audit_action="job.cancel",
        audit_message="Transcription job cancelled by therapist.",
    )
    return _public_processing_job(saved)


from app.services.asr_providers.registry import asr_provider_registry

@router.get("/transcription-providers", response_model=list[dict])
def list_transcription_providers(user: CurrentUser = Depends(get_current_user)):
    """Return all registered ASR providers with live availability status."""
    return asr_provider_registry.list_supported()


from fastapi import Request
from fastapi.responses import FileResponse
from app.core.config import get_settings
from app.services.consent_service import ensure_audio_file_consent_active

@router.put("/audio/{audio_file_id}/upload-file")
async def upload_audio_file_bytes(
    audio_file_id: str,
    request: Request,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file metadata not found.")
    audio_file = repo.clone(repo.audio_files[audio_file_id])
    require_case(repo, audio_file.case_id, user)
    assert_clinical_mutation_allowed(user)
    ensure_audio_file_consent_active(repo, audio_file_id)
    if audio_file.upload_status != "pending":
        raise bad_request("This upload intent is no longer writable. Issue a new upload intent.")
    
    settings = get_settings()
    if settings.storage_mode not in {"local", "local_private"}:
        raise bad_request("Local audio upload route is unavailable for the configured storage mode.")
    if not audio_file.object_key:
        raise bad_request("Audio upload is missing its storage object key.")

    storage_root = settings.resolved_local_storage_root.resolve()
    dest_path = (storage_root / audio_file.object_key).resolve()
    if dest_path == storage_root or storage_root not in dest_path.parents:
        raise bad_request("Invalid audio storage path.")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    body = await request.body()
    dest_path.write_bytes(body)
    
    audio_file.upload_status = "pending_verification"
    repo.update_audio_file_metadata(audio_file, actor_id=user.user_id)
        
    return {"status": "success", "size_bytes": len(body)}


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
