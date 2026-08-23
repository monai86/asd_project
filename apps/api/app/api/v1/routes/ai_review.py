from fastapi import APIRouter, Depends

from app.auth.authorization import assert_clinical_mutation_allowed, require_session
from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import AiReview, AiReviewPatch
from app.services.consent_service import ensure_session_consent_active
from app.services.ai_review_service import create_ai_review, patch_ai_review

router = APIRouter(tags=["ai-review"])


def _ensure_ai_review_enabled(repo: MockRepository, session_id: str) -> None:
    session = repo.get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    organization_id = session.organization_id
    if hasattr(repo, "is_ai_review_enabled") and not repo.is_ai_review_enabled(organization_id):
        raise ValueError("AI-assisted review is unavailable because this organization has not enabled it.")


@router.post("/sessions/{session_id}/ai-review", response_model=AiReview)
def create_review(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        _ensure_ai_review_enabled(repo, session_id)
        ensure_session_consent_active(repo, session_id)
        return create_ai_review(repo, session_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/ai-review", response_model=AiReview)
def get_review(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    session = require_session(repo, session_id, user)
    try:
        _ensure_ai_review_enabled(repo, session_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
    review_id = session.ai_review_id
    if not review_id:
        raise not_found("AI-assisted review not found.")
    review = repo.get_ai_review(review_id)
    if review is None:
        raise not_found("AI-assisted review not found.")
    return review


@router.patch("/ai-reviews/{ai_review_id}", response_model=AiReview)
def update_review(
    ai_review_id: str,
    payload: AiReviewPatch,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    review = repo.get_ai_review(ai_review_id)
    if review is None:
        raise not_found("AI-assisted review not found.")
    try:
        require_session(repo, review.session_id, user)
        assert_clinical_mutation_allowed(repo, user)
        _ensure_ai_review_enabled(repo, review.session_id)
        ensure_session_consent_active(repo, review.session_id)
        return patch_ai_review(repo, ai_review_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
