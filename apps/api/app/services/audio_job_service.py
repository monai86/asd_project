from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
from app.services.cha_service import build_cha_text, manual_text_to_utterances
from app.services.consent_service import ensure_session_consent_active
from app.services.storage_service import get_storage_adapter
from app.services.asr_providers.registry import asr_provider_registry
from app.services.asr_providers.base import TranscriptionResult



ALLOWED_AUDIO_TYPES = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/x-m4a", "video/mp4", "video/quicktime"}
MAX_AUDIO_BYTES = 250 * 1024 * 1024


@dataclass(frozen=True)
class ProviderDraft:
    provider: str
    text: str
    confidence_available: bool = False
    timestamps_available: bool = False
    diarization_available: bool = False


class AsrProviderError(RuntimeError):
    pass





def validate_audio_upload(payload: AudioUploadRequest) -> None:
    if not payload.filename.strip() or "/" in payload.filename or "\\" in payload.filename or ".." in payload.filename:
        raise ValueError("unsafe filename")
    if payload.content_type not in ALLOWED_AUDIO_TYPES:
        raise ValueError("unsupported file")
    if payload.size_bytes > MAX_AUDIO_BYTES:
        raise ValueError("audio too long or too large")


def build_opaque_audio_object_key(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    safe_suffix = suffix if suffix and len(suffix) <= 10 else ""
    return f"audio/{new_id('obj')}{safe_suffix}"


def create_audio_upload_job(repo: MockRepository, session_id: str, payload: AudioUploadRequest) -> ProcessingJob:
    validate_audio_upload(payload)
    session = repo.sessions[session_id]
    storage_adapter = get_storage_adapter()
    audio_file = AudioFileMetadata(
        audio_file_id=new_id("aud"),
        organization_id=session.organization_id,
        session_id=session_id,
        case_id=session.case_id,
        original_filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        storage_mode=storage_adapter.storage_mode,
        object_key=build_opaque_audio_object_key(payload.filename),
        duration_seconds=payload.duration_seconds,
        sample_rate_hz=payload.sample_rate_hz,
        channels=payload.channels,
        estimated_noise_level=payload.estimated_noise_level,
        silence_ratio=payload.silence_ratio,
    )
    upload_intent = storage_adapter.create_upload_intent(audio_file)
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
        message="Audio metadata accepted. Processing is experimental and requires therapist transcript review.",
        details={
            "quality": quality.model_dump(mode="json"),
            "audio_file": audio_file.model_dump(mode="json"),
            "upload_intent": upload_intent.model_dump(mode="json"),
            "status_history": [JobStatus.queued.value],
        },
    )
    return repo.create_audio_upload(audio_file, job, actor_id="system")


def complete_audio_upload(repo: MockRepository, audio_file_id: str, payload: AudioUploadCompleteRequest) -> AudioFileMetadata:
    if audio_file_id not in repo.audio_files:
        raise ValueError("Audio file not found.")
    audio_file = repo.clone(repo.audio_files[audio_file_id])
    if not audio_file.retained:
        raise ValueError("Audio file is no longer retained.")
    storage_adapter = get_storage_adapter()
    if audio_file.upload_status == "pending" and audio_file.storage_mode == "supabase_private":
        if storage_adapter.storage_mode != audio_file.storage_mode:
            raise ValueError("Audio upload storage mode no longer matches the configured adapter.")
        if not storage_adapter.verify_upload_completion(audio_file, payload.size_bytes):
            raise ValueError("Uploaded audio object could not be verified.")
        audio_file.upload_status = "pending_verification"
    if audio_file.upload_status != "pending_verification":
        raise ValueError("Audio upload must be re-issued with a new upload intent before completion verification.")
    if payload.size_bytes is not None and payload.size_bytes != audio_file.size_bytes:
        raise ValueError("Uploaded audio size does not match upload intent metadata.")
    audio_file.checksum_sha256 = payload.checksum_sha256
    audio_file.uploaded_at = utc_now()
    audio_file.upload_status = "uploaded"
    return repo.update_audio_file_metadata(
        audio_file,
        actor_id="system",
        audit_action="audio.upload_complete",
        audit_message="Audio upload metadata marked complete.",
    )


def process_audio(repo: MockRepository, session_id: str, payload: AudioProcessRequest | TranscriptionJobRequest) -> ProcessingJob:
    job = create_audio_processing_job(repo, session_id, payload)
    return repo.clone(job)


def _resolve_audio_file_id_for_job(
    repo: MockRepository,
    session_id: str,
    payload: AudioProcessRequest | TranscriptionJobRequest,
) -> str | None:
    audio_file_id = getattr(payload, "audio_id", None)
    if audio_file_id:
        if audio_file_id not in repo.audio_files:
            raise ValueError("Audio file not found.")
        audio_file = repo.audio_files[audio_file_id]
        if audio_file.session_id != session_id or not audio_file.retained:
            raise ValueError("Audio file is not available for this session.")
        if audio_file.upload_status != "uploaded":
            raise ValueError("Audio processing requires a verified uploaded audio artifact.")
        return audio_file_id
    uploaded_files = [
        audio_file.audio_file_id
        for audio_file in repo.audio_files.values()
        if audio_file.session_id == session_id
        and audio_file.retained
        and audio_file.upload_status == "uploaded"
    ]
    if len(uploaded_files) == 1:
        return uploaded_files[0]
    return None


def _ensure_no_active_job_for_audio_artifact(
    repo: MockRepository,
    *,
    session_id: str,
    audio_file_id: str | None,
) -> None:
    if not audio_file_id:
        return
    active_statuses = {
        JobStatus.queued.value,
        JobStatus.processing.value,
        JobStatus.transcription_completed.value,
    }
    for job in repo.jobs.values():
        if job.session_id != session_id:
            continue
        if job.details.get("audio_file_id") != audio_file_id:
            continue
        status_value = job.status.value if hasattr(job.status, "value") else str(job.status)
        if status_value in active_statuses:
            raise ValueError("Only one active processing job is allowed per audio artifact.")


def create_audio_processing_job(repo: MockRepository, session_id: str, payload: AudioProcessRequest | TranscriptionJobRequest) -> ProcessingJob:
    session = repo.sessions[session_id]
    audio_file_id = _resolve_audio_file_id_for_job(repo, session_id, payload)
    _ensure_no_active_job_for_audio_artifact(
        repo,
        session_id=session_id,
        audio_file_id=audio_file_id,
    )
    try:
        provider = asr_provider_registry.get(payload.provider)
    except KeyError:
        raise ValueError(f"ASR provider '{payload.provider}' is not registered.")
    
    avail = provider.check_availability()
    
    # Fallback logic — explicit, never silent
    actual_provider = payload.provider
    fallback_reason = None
    
    allow_fallback = False
    if hasattr(payload, "config") and payload.config is not None:
        allow_fallback = getattr(payload.config, "allow_fallback_to_mock", False)
    else:
        allow_fallback = getattr(payload, "allow_fallback_to_mock", False)
        
    if not avail:
        if allow_fallback:
            actual_provider = "mock"
            fallback_reason = f"Provider '{payload.provider}' unavailable: {avail.reason}. Fell back to mock."
        else:
            job = ProcessingJob(
                job_id=new_id("job"),
                organization_id=session.organization_id,
                session_id=session_id,
                status=JobStatus.failed,
                message=f"Provider '{payload.provider}' is unavailable: {avail.reason}",
                error_code="provider_unavailable",
                details={
                    "audio_file_id": audio_file_id,
                    "requested_provider": payload.provider,
                    "actual_provider": None,
                    "fallback_reason": None,
                    "provider_error": avail.reason,
                    "status_history": [JobStatus.failed.value],
                },
            )
            return repo.create_processing_job(
                job,
                actor_id="system",
                audit_action="transcription.provider_unavailable",
                audit_message=f"Provider '{payload.provider}' unavailable; job failed immediately.",
            )

    job = ProcessingJob(
        job_id=new_id("job"),
        organization_id=session.organization_id,
        session_id=session_id,
        status=JobStatus.queued,
        message="Transcription job queued.",
        details={
            "queued_payload": payload.model_dump(mode="json"),
            "audio_file_id": audio_file_id,
            "requested_provider": payload.provider,
            "actual_provider": actual_provider,
            "fallback_reason": fallback_reason,
            "status_history": [JobStatus.queued.value],
        },
    )
    return repo.create_processing_job(
        job,
        actor_id="system",
        audit_action="audio.process_queued",
        audit_message="Experimental audio processing job queued.",
    )


def run_audio_processing_job(repo: MockRepository, job_id: str) -> ProcessingJob:
    if job_id not in repo.jobs:
        raise ValueError("Job not found.")
    job = repo.clone(repo.jobs[job_id])
    
    queued_payload = job.details.get("queued_payload", {})
    if "config" in queued_payload:
        payload = TranscriptionJobRequest.model_validate(queued_payload)
    else:
        payload = AudioProcessRequest.model_validate(queued_payload)
        
    session_id = job.session_id
    if job.details.get("consent_withdrawn"):
        job.status = JobStatus.cancelled
        job.message = "Audio processing cancelled because case consent was withdrawn."
        job.error_code = "consent_withdrawn"
        append_job_status(job, JobStatus.cancelled)
        return repo.update_processing_job(
            job, actor_id="system", audit_action="audio.process_cancelled",
            audit_message="Audio processing cancelled after consent withdrawal.",
        )
        
    try:
        ensure_session_consent_active(repo, session_id)
    except ValueError:
        job.status = JobStatus.cancelled
        job.message = "Audio processing cancelled because case consent was withdrawn."
        job.error_code = "consent_withdrawn"
        job.details = {**job.details, "consent_withdrawn": True}
        append_job_status(job, JobStatus.cancelled)
        return repo.update_processing_job(
            job, actor_id="system", audit_action="audio.process_cancelled",
            audit_message="Audio processing cancelled after consent withdrawal.",
        )
        
    actual_provider_id = job.details.get("actual_provider") or payload.provider
    
    try:
        provider = asr_provider_registry.get(actual_provider_id)
    except KeyError:
        raise ValueError(f"ASR provider '{actual_provider_id}' is not registered.")
        
    job.status = JobStatus.processing
    job.message = "Audio processing job is running."
    append_job_status(job, JobStatus.processing)
    job = repo.update_processing_job(
        job, actor_id="system", audit_action="audio.process_started",
        audit_message="Experimental audio processing job started.",
    )
    
    audio_file_id = job.details.get("audio_file_id") or (payload.audio_id if hasattr(payload, "audio_id") else None)
    audio_file = None
    if audio_file_id and audio_file_id in repo.audio_files:
        audio_file = repo.audio_files[audio_file_id]
        
    duration_seconds = getattr(payload, "duration_seconds", None)
    sample_rate_hz = getattr(payload, "sample_rate_hz", None)
    channels = getattr(payload, "channels", None)
    estimated_noise_level = getattr(payload, "estimated_noise_level", None)
    silence_ratio = getattr(payload, "silence_ratio", None)
    
    if audio_file:
        duration_seconds = duration_seconds or audio_file.duration_seconds
        sample_rate_hz = sample_rate_hz or audio_file.sample_rate_hz
        channels = channels or audio_file.channels
        estimated_noise_level = estimated_noise_level or audio_file.estimated_noise_level
        silence_ratio = silence_ratio or audio_file.silence_ratio
        
    quality = analyze_audio_quality(
        duration_seconds=duration_seconds,
        sample_rate_hz=sample_rate_hz,
        channels=channels,
        estimated_noise_level=estimated_noise_level,
        silence_ratio=silence_ratio,
    )
    
    if quality.status == "failed":
        job.status = JobStatus.failed
        job.message = "Audio quality checks failed before ASR draft generation."
        job.error_code = "audio_quality_failed"
        job.details = {**job.details, "quality": quality.model_dump(mode="json")}
        append_job_status(job, JobStatus.failed)
        return repo.update_processing_job(
            job, actor_id="system", audit_action="audio.process_failed",
            audit_message="Audio processing failed quality checks.",
        )

    try:
        transcribe_config = {}
        if hasattr(payload, "config") and payload.config is not None:
            transcribe_config = payload.config.model_dump()
        if hasattr(payload, "draft_text") and payload.draft_text:
            transcribe_config["draft_text"] = payload.draft_text
            
        result: TranscriptionResult = provider.transcribe(
            audio_ref=audio_file_id or "",
            config=transcribe_config,
        )
    except Exception as exc:
        job.status = JobStatus.failed
        job.message = str(exc)
        job.error_code = "asr_failed"
        job.details = {**job.details, "quality": quality.model_dump(mode="json"), "provider_error": str(exc)}
        append_job_status(job, JobStatus.failed)
        return repo.update_processing_job(
            job, actor_id="system", audit_action="audio.process_failed",
            audit_message="ASR provider failed before draft transcript generation.",
        )
        
    if result.status != "completed":
        job.status = JobStatus.failed
        job.message = result.error_message or "Provider returned non-completed status."
        job.error_code = "asr_failed"
        job.details = {**job.details, "quality": quality.model_dump(mode="json"), "provider_error": result.error_message}
        append_job_status(job, JobStatus.failed)
        return repo.update_processing_job(
            job, actor_id="system", audit_action="audio.process_failed",
            audit_message=f"ASR provider failed: {result.error_message}",
        )
        
    draft_warnings = []
    utterance_count = len(result.transcript_lines)
    if utterance_count < 2:
        draft_warnings.append("transcript too short")
    if not any(line.speaker == "CHI" for line in result.transcript_lines):
        draft_warnings.append("no child speech detected")
    if not result.speaker_segments_available:
        draft_warnings.append("diarization failed")
        
    job.status = JobStatus.transcription_completed
    job.message = "ASR draft transcription completed; preparing reviewable transcript."
    append_job_status(job, JobStatus.transcription_completed)
    
    transcript = create_draft_transcript_from_result(
        repo, session_id, result, audio_file_id=audio_file_id, persist=False
    )
    
    asr_draft_result = AsrDraftResult(
        provider=result.provider_id,
        transcript_id=transcript.transcript_id,
        utterance_count=len(transcript.utterances),
        confidence_available=result.confidence_available,
        timestamps_available=result.word_timestamps_available,
        diarization_available=result.speaker_segments_available,
        warnings=draft_warnings + result.warnings,
        quality=quality,
    )
    
    job.status = JobStatus.needs_review
    job.message = "Draft transcript generated. Therapist correction and attestation are required before features."
    job.details = {**job.details, "asr_draft": asr_draft_result.model_dump(mode="json")}
    append_job_status(job, JobStatus.needs_review)
    return repo.complete_processing_job(
        job,
        transcript,
        actor_id="system",
        audit_action="audio.process",
        audit_message="Experimental audio-to-draft-CHA processing completed.",
    )

def create_draft_transcript_from_result(
    repo: MockRepository,
    session_id: str,
    result: TranscriptionResult,
    audio_file_id: str | None = None,
    persist: bool = True,
) -> Transcript:
    """
    Create a draft Transcript from a TranscriptionResult.
    - Maps TranscriptLine -> Utterance (preserving timestamps)
    - source = "mock_asr_draft:{id}" or "asr_draft:{id}"
    - Adds ASR warning QaIssue
    - therapist_attested=False locks feature extraction
    """
    session = repo.sessions[session_id]

    utterances: list[Utterance] = []
    for line in result.transcript_lines:
        speaker_code = line.speaker
        if speaker_code != "CHI":
            speaker_code = "UNK"
        utt = Utterance(
            utterance_id=new_id("utt"),
            speaker=speaker_code,
            text=line.text,
            start_ms=line.start_ms,
            end_ms=line.end_ms,
            confidence=line.confidence,
            unintelligible=line.unclear,
            temporary_speaker_id=line.temporary_speaker_id,
            source_speaker_label=line.source_speaker_label,
            source=line.source,
            notes="ASR draft — therapist review required." if (line.unclear or speaker_code == "UNK") else "",
            review_status="draft",
        )
        utterances.append(utt)

    is_mock = result.provider_id == "mock"
    source_label = (
        f"mock_asr_draft:{result.provider_id}" if is_mock
        else f"asr_draft:{result.provider_id}"
    )

    asr_warning = QaIssue(
        code="ASR_DRAFT_REVIEW_REQUIRED",
        severity="warning",
        message="ASR draft transcript — therapist must listen to the audio and correct all content before feature extraction.",
        blocking=False,
        fix_suggestion="Review all utterances, correct speaker labels, and attest when satisfied.",
        source="asr_pipeline",
    )
    qa_issues = [asr_warning]
    if is_mock:
        qa_issues.append(QaIssue(
            code="MOCK_ASR_OUTPUT",
            severity="warning",
            message="MOCK PROVIDER: Synthetic placeholder output, not real ASR. Replace all content.",
            blocking=False,
            source="asr_pipeline",
        ))

    raw_text = build_cha_text(utterances, media_name=f"{session_id}_audio")
    transcript = Transcript(
        transcript_id=new_id("tr"),
        session_id=session_id,
        case_id=session.case_id,
        source=source_label,
        raw_text=raw_text,
        utterances=utterances,
        review_status=ReviewStatus.needs_review,
        therapist_attested=False,
        qa_status=QaStatus.warning,
        qa_issues=qa_issues,
        chat_metadata={
            "asr_provider": result.provider_id,
            "asr_provider_version": result.provider_version,
            "is_mock": is_mock,
            "audio_file_id": audio_file_id,
            "word_timestamps_available": result.word_timestamps_available,
        },
    )
    if not persist:
        return transcript
    return repo.create_transcript(
        transcript,
        session_status=ReviewStatus.needs_review,
        actor_id="system",
        audit_action="transcript.create",
        audit_message="ASR draft transcript created for therapist review.",
    )



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


def draft_quality_warnings(draft: ProviderDraft) -> list[str]:
    utterances = manual_text_to_utterances(draft.text)
    warnings: list[str] = []
    if len(utterances) < 2:
        warnings.append("transcript too short")
    if not any(str(utterance.speaker).upper() == "CHI" for utterance in utterances):
        warnings.append("no child speech detected")
    if not draft.diarization_available:
        warnings.append("diarization failed")
    return warnings
