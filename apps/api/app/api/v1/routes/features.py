from fastapi import APIRouter, Depends

from app.auth.authorization import assert_clinical_mutation_allowed, require_session, require_transcript
from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import FeatureExtractionRequest, FeatureSet
from app.schemas.speech_pipeline import FindingsProjection
from app.services.consent_service import (
    active_case_consent_fence,
    ensure_session_consent_active,
)
from app.services.feature_service import extract_features, get_feature_definitions, get_providers

router = APIRouter(tags=["features"])


@router.post("/transcripts/{transcript_id}/extract-features", response_model=FeatureSet)
def extract(
    transcript_id: str,
    payload: FeatureExtractionRequest | None = None,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    require_transcript(repo, transcript_id, user)
    assert_clinical_mutation_allowed(user)
    case_id = repo.transcripts[transcript_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_transcript(repo, transcript_id, user)
            return extract_features(
                repo,
                transcript_id,
                payload or FeatureExtractionRequest(),
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/features", response_model=FeatureSet)
def get_features(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    require_session(repo, session_id, user)
    try:
        ensure_session_consent_active(repo, session_id)
        feature_set_id = repo.sessions[session_id].feature_set_id
        if not feature_set_id or feature_set_id not in repo.features:
            raise not_found("Feature set not found.")
        return repo.clone(repo.features[feature_set_id])
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/features/providers", response_model=list[dict], tags=["features"])
def list_providers(user: CurrentUser = Depends(get_current_user)):
    """Return metadata and live availability status for all registered feature providers."""
    return get_providers()


@router.get("/features/definitions", response_model=list[dict], tags=["features"])
def list_feature_definitions(user: CurrentUser = Depends(get_current_user)):
    """Return the full feature definition catalogue from all registered providers."""
    return get_feature_definitions()


@router.post("/sessions/{session_id}/findings", response_model=FindingsProjection)
def project_findings(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        ensure_session_consent_active(repo, session_id)
        from app.services.findings_service import project_findings_for_session
        return project_findings_for_session(repo, session_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/sessions/{session_id}/findings", response_model=FindingsProjection)
def get_findings(
    session_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    require_session(repo, session_id, user)
    try:
        ensure_session_consent_active(repo, session_id)
        from app.services.findings_service import get_current_findings_for_session
        findings = get_current_findings_for_session(repo, session_id)
        if findings is None:
            raise not_found("Findings projection not found.")
        return findings
    except ValueError as exc:
        raise bad_request(str(exc)) from exc

