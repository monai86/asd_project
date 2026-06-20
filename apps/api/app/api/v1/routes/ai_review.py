from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AiReview, AiReviewPatch
from app.services.consent_service import ensure_session_consent_active
from app.services.ai_review_service import create_ai_review, patch_ai_review

router = APIRouter(tags=["ai-review"])


@router.post("/sessions/{session_id}/ai-review", response_model=AiReview)
def create_review(session_id: str, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    try:
        ensure_session_consent_active(repo, session_id)
        return create_ai_review(repo, session_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/ai-review", response_model=AiReview)
def get_review(session_id: str, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    review_id = repo.sessions[session_id].ai_review_id
    if not review_id:
        raise not_found("AI-assisted review not found.")
    return repo.clone(repo.ai_reviews[review_id])


@router.patch("/ai-reviews/{ai_review_id}", response_model=AiReview)
def update_review(ai_review_id: str, payload: AiReviewPatch, repo: MockRepository = Depends(get_repository)):
    if ai_review_id not in repo.ai_reviews:
        raise not_found("AI-assisted review not found.")
    try:
        ensure_session_consent_active(repo, repo.ai_reviews[ai_review_id].session_id)
        return patch_ai_review(repo, ai_review_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
