from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.auth.authorization import assert_clinical_mutation_allowed, require_case, require_session
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import TherapySession, TherapySessionCreate, TherapySessionUpdate
from app.services.consent_service import ensure_case_consent_active, ensure_session_consent_active

router = APIRouter(tags=["sessions"])


@router.post("/cases/{case_id}/sessions", response_model=TherapySession)
def create_session(
    case_id: str,
    payload: TherapySessionCreate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_case(repo, case_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_case_consent_active(repo, case_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    return repo.create_session(case_id, payload, actor_id=user.user_id)


@router.get("/sessions/{session_id}", response_model=TherapySession)
def get_session(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    try:
        ensure_session_consent_active(repo, session_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    return repo.clone(repo.sessions[session_id])


@router.patch("/sessions/{session_id}", response_model=TherapySession)
def update_session(
    session_id: str,
    payload: TherapySessionUpdate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_session_consent_active(repo, session_id)
        return repo.update_session(session_id, payload, expected_version=None, actor_id=user.user_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/status")
def get_session_status(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    session = repo.sessions[session_id]
    return {
        "session_id": session_id,
        "status": session.status,
        "transcript_id": session.transcript_id,
        "feature_set_id": session.feature_set_id,
        "ai_review_id": session.ai_review_id,
        "report_id": session.report_id,
    }
