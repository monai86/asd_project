from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.auth.authorization import (
    assert_clinical_mutation_allowed,
    assert_sensitive_clinical_export_allowed,
    filter_cases_for_user,
    require_report,
    require_session,
)
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user, require_therapist
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    ExportResponse,
    Report,
    ReportGenerationRequest,
    ReportPatch,
    ReportFinalizeRequest,
    ReportProviderAvailability,
)
from app.services.consent_service import (
    active_case_consent_fence,
    ensure_case_consent_active,
    ensure_report_consent_active,
)
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
    assert_clinical_mutation_allowed(user)
    case_id = repo.sessions[session_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_session(repo, session_id, user)
            request = payload or ReportGenerationRequest()
            return draft_report(repo, session_id, request)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/reports", response_model=list[Report])
def list_reports(user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    visible_case_ids = {case.case_id for case in filter_cases_for_user(list(repo.cases.values()), user)}
    active_case_ids = set()
    for case_id in visible_case_ids:
        try:
            ensure_case_consent_active(repo, case_id)
        except ValueError:
            continue
        active_case_ids.add(case_id)
    return [
        repo.clone(item)
        for item in repo.reports.values()
        if item.case_id in active_case_ids
    ]


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
    require_report(repo, report_id, user)
    assert_clinical_mutation_allowed(user)
    case_id = repo.reports[report_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_report(repo, report_id, user)
            if repo.reports[report_id].status.value == "Signed Off":
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
    require_therapist(user)
    if payload.confirmation_checked is False:
        raise bad_request("Confirmation check must be accepted by therapist.")
    if payload.therapist_name and payload.therapist_name != user.display_name:
        raise bad_request("Report sign-off must use the authenticated therapist identity.")
    if payload.signed_by and payload.signed_by != user.display_name:
        raise bad_request("Report sign-off must use the authenticated therapist identity.")
    case_id = repo.reports[report_id].case_id
    try:
        with active_case_consent_fence(repo, case_id):
            require_report(repo, report_id, user)
            therapist_name = (
                user.display_name
                or payload.therapist_name
                or payload.signed_by
                or "Demo Therapist"
            )
            return sign_off_report(
                repo,
                report_id,
                therapist_name,
                signed_by_user_id=user.user_id,
            )
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str, user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    require_report(repo, report_id, user)
    try:
        ensure_report_consent_active(repo, report_id)
        return repo.clone(repo.reports[report_id])
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/reports/{report_id}/export", response_model=ExportResponse)
def export(
    report_id: str,
    format: str = "markdown",
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    require_report(repo, report_id, user)
    assert_sensitive_clinical_export_allowed(user)
    try:
        ensure_report_consent_active(repo, report_id)
        return export_report(repo, report_id, format)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
