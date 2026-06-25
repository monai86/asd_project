from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import TherapySession, TherapySessionCreate, TherapySessionUpdate
from app.services.consent_service import ensure_case_consent_active, ensure_session_consent_active

router = APIRouter(tags=["sessions"])


@router.post("/cases/{case_id}/sessions", response_model=TherapySession)
def create_session(case_id: str, payload: TherapySessionCreate, repo: MockRepository = Depends(get_repository)):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    try:
        ensure_case_consent_active(repo, case_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    return repo.create_session(case_id, payload, actor_id="system")


@router.get("/sessions/{session_id}", response_model=TherapySession)
def get_session(session_id: str, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    try:
        ensure_session_consent_active(repo, session_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    return repo.clone(repo.sessions[session_id])


@router.patch("/sessions/{session_id}", response_model=TherapySession)
def update_session(session_id: str, payload: TherapySessionUpdate, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    try:
        ensure_session_consent_active(repo, session_id)
        return repo.update_session(session_id, payload, expected_version=None, actor_id="system")
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/status")
def get_session_status(session_id: str, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    session = repo.sessions[session_id]
    return {
        "session_id": session_id,
        "status": session.status,
        "transcript_id": session.transcript_id,
        "feature_set_id": session.feature_set_id,
        "ai_review_id": session.ai_review_id,
        "report_id": session.report_id,
    }
