from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AudioFileMetadata, AudioProcessRequest, AudioUploadCompleteRequest, AudioUploadRequest, ProcessingJob
from app.services.audio_job_service import complete_audio_upload, create_audio_upload_job, process_audio as process_audio_job
from app.services.consent_service import ensure_audio_file_consent_active, ensure_session_consent_active
from app.tasks.job_queue import get_job_queue

router = APIRouter(tags=["jobs"])


@router.post("/sessions/{session_id}/audio/upload", response_model=ProcessingJob)
def upload_audio(session_id: str, payload: AudioUploadRequest, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    try:
        ensure_session_consent_active(repo, session_id)
        return create_audio_upload_job(repo, session_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/audio/{audio_file_id}", response_model=AudioFileMetadata)
def get_audio_file(audio_file_id: str, repo: MockRepository = Depends(get_repository)):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file not found.")
    return repo.clone(repo.audio_files[audio_file_id])


@router.post("/audio/{audio_file_id}/complete-upload", response_model=AudioFileMetadata)
def complete_upload(
    audio_file_id: str,
    payload: AudioUploadCompleteRequest,
    repo: MockRepository = Depends(get_repository),
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file not found.")
    try:
        ensure_audio_file_consent_active(repo, audio_file_id)
        return complete_audio_upload(repo, audio_file_id, payload)
    except ValueError as exc:
        if "not found" in str(exc).lower():
            raise not_found(str(exc)) from exc
        raise bad_request(str(exc)) from exc


@router.post("/sessions/{session_id}/audio/process", response_model=ProcessingJob)
def process_audio(session_id: str, payload: AudioProcessRequest | None = None, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    try:
        ensure_session_consent_active(repo, session_id)
        job = process_audio_job(repo, session_id, payload or AudioProcessRequest())
        get_job_queue().enqueue(job.job_id)
        return job
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=ProcessingJob)
def get_job(job_id: str, repo: MockRepository = Depends(get_repository)):
    if job_id not in repo.jobs:
        raise not_found("Job not found.")
    return repo.clone(repo.jobs[job_id])


@router.post("/jobs/{job_id}/cancel", response_model=ProcessingJob)
def cancel_job(job_id: str, repo: MockRepository = Depends(get_repository)):
    if job_id not in repo.jobs:
        raise not_found("Job not found.")
    job = repo.jobs[job_id]
    terminal_statuses = {"failed", "cancelled", "needs_review"}
    if job.status in terminal_statuses or (hasattr(job.status, "value") and job.status.value in terminal_statuses):
        return repo.clone(job)  # idempotent
    job.status = JobStatus.cancelled
    job.message = "Job cancelled by therapist."
    from app.services.audio_job_service import append_job_status
    append_job_status(job, JobStatus.cancelled)
    repo.add_audit("job.cancel", job_id, "Transcription job cancelled by therapist.")
    return repo.clone(job)


from app.services.asr_providers.registry import asr_provider_registry

@router.get("/transcription-providers", response_model=list[dict])
def list_transcription_providers():
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
    repo: MockRepository = Depends(get_repository)
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file metadata not found.")
    audio_file = repo.audio_files[audio_file_id]
    ensure_audio_file_consent_active(repo, audio_file_id)
    
    settings = get_settings()
    dest_path = (settings.resolved_local_storage_root / audio_file.object_key).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    body = await request.body()
    dest_path.write_bytes(body)
    
    audio_file.upload_status = "uploaded"
    if hasattr(repo, "save"):
        repo.save()
        
    return {"status": "success", "size_bytes": len(body)}


@router.get("/audio/{audio_file_id}/file")
def get_audio_file_bytes(
    audio_file_id: str,
    repo: MockRepository = Depends(get_repository)
):
    if audio_file_id not in repo.audio_files:
        raise not_found("Audio file metadata not found.")
    audio_file = repo.audio_files[audio_file_id]
    ensure_audio_file_consent_active(repo, audio_file_id)
    
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
    repo: MockRepository = Depends(get_repository)
):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    files = [
        f for f in repo.audio_files.values()
        if f.session_id == session_id and f.retained and f.upload_status == "uploaded"
    ]
    return files
