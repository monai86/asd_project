from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.auth.authorization import (
    assert_clinical_mutation_allowed,
    assert_sensitive_clinical_export_allowed,
    filter_cases_for_user,
    require_authoritative_therapist,
    require_report,
    require_session,
)
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    ExportResponse,
    Report,
    ReportGenerationRequest,
    ReportPatch,
    ReportFinalizeRequest,
    ReportProviderAvailability,
)
from app.services.consent_service import ensure_report_consent_active, ensure_session_consent_active
from app.services.report_service import draft_report, export_report, patch_report, revise_finalized_report, sign_off_report

router = APIRouter(tags=["reports"])


@router.post("/sessions/{session_id}/reports/draft", response_model=Report)
def create_draft(
    session_id: str,
    payload: ReportGenerationRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    require_session(repo, session_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_session_consent_active(repo, session_id)
        request = payload or ReportGenerationRequest()
        return draft_report(repo, session_id, request)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/reports", response_model=list[Report])
def list_reports(user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    visible_case_ids = {
        case.case_id
        for case in filter_cases_for_user(
            repo, repo.list_cases_for_user(user.user_id, user.organization_id), user
        )
    }
    return [item for item in repo.list_reports(user.organization_id) if item.case_id in visible_case_ids]


@router.get("/reports/providers", response_model=list[ReportProviderAvailability])
def list_report_providers(user: CurrentUser = Depends(get_current_user)):
    from app.services.providers.report_registry import report_provider_registry
    return report_provider_registry.list_available()


@router.patch("/reports/{report_id}", response_model=Report)
def update_report(
    report_id: str,
    payload: ReportPatch,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    report = require_report(repo, report_id, user)
    assert_clinical_mutation_allowed(repo, user)
    try:
        ensure_report_consent_active(repo, report_id)
        if report.status.value == "Signed Off":
            return revise_finalized_report(repo, report_id, payload)
        return patch_report(repo, report_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/reports/{report_id}/sign-off", response_model=Report)
def sign_off(
    report_id: str,
    payload: ReportFinalizeRequest,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    require_report(repo, report_id, user)
    require_authoritative_therapist(repo, user)
    if payload.confirmation_checked is False:
        raise bad_request("Confirmation check must be accepted by therapist.")
    if payload.therapist_name and payload.therapist_name != user.display_name:
        raise bad_request("Report sign-off must use the authenticated therapist identity.")
    if payload.signed_by and payload.signed_by != user.display_name:
        raise bad_request("Report sign-off must use the authenticated therapist identity.")
    try:
        ensure_report_consent_active(repo, report_id)
        therapist_name = user.display_name or payload.therapist_name or payload.signed_by or "Demo Therapist"
        return sign_off_report(repo, report_id, therapist_name, signed_by_user_id=user.user_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str, user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    return require_report(repo, report_id, user)


@router.get("/reports/{report_id}/export", response_model=ExportResponse)
def export(
    report_id: str,
    format: str = "markdown",
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    require_report(repo, report_id, user)
    assert_sensitive_clinical_export_allowed(repo, user)
    try:
        ensure_report_consent_active(repo, report_id)
        return export_report(repo, report_id, format)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
