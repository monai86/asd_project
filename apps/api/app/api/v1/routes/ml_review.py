from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.v1.dependencies import get_repository
from app.core.errors import not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    EvidenceReviewPatch,
    MLReadiness,
    MLResult,
    MLReviewRequest,
    ReviewCuePatch,
)
from app.services.consent_service import ensure_session_consent_active, ensure_transcript_consent_active
from app.services.ml_providers.registry import ml_provider_registry
from app.services.ml_review_service import (
    MLReadinessError,
    check_ml_readiness,
    create_ml_review,
    get_current_ml_review,
    get_ml_result,
    patch_cue_state,
    patch_profile_evidence_state,
)

router = APIRouter(tags=["ml-review"])


@router.get("/ml/providers", response_model=list[dict])
def list_ml_providers():
    return ml_provider_registry.list_providers()


@router.get("/transcripts/{transcript_id}/ml-readiness", response_model=MLReadiness)
def readiness(transcript_id: str, provider_id: str | None = None, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    ensure_transcript_consent_active(repo, transcript_id)
    return check_ml_readiness(repo, transcript_id, provider_id)


@router.post("/transcripts/{transcript_id}/ml-review", response_model=MLResult)
def generate(transcript_id: str, payload: MLReviewRequest | None = None, repo: MockRepository = Depends(get_repository)):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    ensure_transcript_consent_active(repo, transcript_id)
    try:
        return create_ml_review(repo, transcript_id, payload or MLReviewRequest())
    except MLReadinessError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.readiness.model_dump(mode="json")) from exc


@router.post("/sessions/{session_id}/ml-decision-support", response_model=MLResult)
def compatibility_generate(session_id: str, response: Response, payload: MLReviewRequest | None = None, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    ensure_session_consent_active(repo, session_id)
    transcript_id = repo.sessions[session_id].transcript_id
    if not transcript_id:
        raise not_found("Transcript not found.")
    response.headers["Deprecation"] = "true"
    try:
        return create_ml_review(repo, transcript_id, payload or MLReviewRequest())
    except MLReadinessError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.readiness.model_dump(mode="json")) from exc


@router.get("/sessions/{session_id}/ml-review", response_model=MLResult)
def current(session_id: str, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    ensure_session_consent_active(repo, session_id)
    try:
        return get_current_ml_review(repo, session_id)
    except KeyError as exc:
        raise not_found("ML review result not found.") from exc


@router.get("/ml-results/{result_id}", response_model=MLResult)
def result(result_id: str, repo: MockRepository = Depends(get_repository)):
    if result_id not in repo.ml_results:
        raise not_found("ML review result not found.")
    ensure_session_consent_active(repo, repo.ml_results[result_id].session_id)
    return get_ml_result(repo, result_id)


@router.patch("/ml-results/{result_id}/cues/{cue_code}", response_model=MLResult)
def update_cue(result_id: str, cue_code: str, payload: ReviewCuePatch, repo: MockRepository = Depends(get_repository), user: CurrentUser = Depends(get_current_user)):
    if result_id not in repo.ml_results:
        raise not_found("ML review result not found.")
    ensure_session_consent_active(repo, repo.ml_results[result_id].session_id)
    try:
        return patch_cue_state(repo, result_id, cue_code, payload, user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise not_found(str(exc)) from exc


@router.patch(
    "/ml-results/{result_id}/profiles/{profile_code}/review-state",
    response_model=MLResult,
)
def update_profile_evidence(
    result_id: str,
    profile_code: str,
    payload: EvidenceReviewPatch,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if result_id not in repo.ml_results:
        raise not_found("ML review result not found.")
    ensure_session_consent_active(repo, repo.ml_results[result_id].session_id)
    try:
        return patch_profile_evidence_state(
            repo,
            result_id,
            profile_code,
            payload,
            user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise not_found(str(exc)) from exc
