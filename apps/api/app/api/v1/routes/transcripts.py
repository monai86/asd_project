from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    AttestationRequest,
    QaReport,
    Transcript,
    TranscriptExport,
    TranscriptManualCreate,
    TranscriptMergeRequest,
    TranscriptPatch,
    TranscriptSplitRequest,
    TranscriptUploadCha,
)
from app.services.consent_service import ensure_session_consent_active, ensure_transcript_consent_active
from app.services import transcript_service

router = APIRouter(tags=["transcripts"])


@router.post("/sessions/{session_id}/transcripts/upload-cha", response_model=Transcript)
def upload_cha(session_id: str, payload: TranscriptUploadCha, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    try:
        ensure_session_consent_active(repo, session_id)
        return transcript_service.create_from_cha(repo, session_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/sessions/{session_id}/transcripts/manual", response_model=Transcript)
def manual_transcript(session_id: str, payload: TranscriptManualCreate, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    try:
        ensure_session_consent_active(repo, session_id)
        return transcript_service.create_from_manual(repo, session_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/transcript", response_model=Transcript)
def get_session_transcript(session_id: str, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    transcript_id = repo.sessions[session_id].transcript_id
    if not transcript_id:
        raise not_found("Transcript not found.")
    return repo.clone(repo.transcripts[transcript_id])


@router.get("/transcripts/{transcript_id}", response_model=Transcript)
def get_transcript(transcript_id: str, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return repo.clone(repo.transcripts[transcript_id])
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.patch("/transcripts/{transcript_id}", response_model=Transcript)
def patch_transcript(transcript_id: str, payload: TranscriptPatch, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.patch_transcript(repo, transcript_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/split", response_model=Transcript)
def split_transcript_utterance(transcript_id: str, payload: TranscriptSplitRequest, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.split_utterance(repo, transcript_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/merge", response_model=Transcript)
def merge_transcript_utterances(transcript_id: str, payload: TranscriptMergeRequest, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.merge_utterances(repo, transcript_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/transcripts/{transcript_id}/export-cha", response_model=TranscriptExport)
def export_transcript_cha(transcript_id: str, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.export_cha(repo, transcript_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/qa", response_model=QaReport)
def qa_transcript(transcript_id: str, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.run_qa(repo, transcript_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/transcripts/{transcript_id}/attest", response_model=Transcript)
def attest_transcript(transcript_id: str, payload: AttestationRequest, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    try:
        ensure_transcript_consent_active(repo, transcript_id)
        return transcript_service.attest(repo, transcript_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
