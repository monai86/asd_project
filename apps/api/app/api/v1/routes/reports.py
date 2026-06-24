from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
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
def create_draft(session_id: str, payload: ReportGenerationRequest | None = None, repo: MockRepository = Depends(get_repository)):
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    try:
        ensure_session_consent_active(repo, session_id)
        request = payload or ReportGenerationRequest()
        return draft_report(repo, session_id, request)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/reports", response_model=list[Report])
def list_reports(repo: MockRepository = Depends(get_repository)):
    return [repo.clone(item) for item in repo.reports.values()]


@router.get("/reports/providers", response_model=list[ReportProviderAvailability])
def list_report_providers():
    from app.services.providers.report_registry import report_provider_registry
    return report_provider_registry.list_available()


@router.patch("/reports/{report_id}", response_model=Report)
def update_report(report_id: str, payload: ReportPatch, repo: MockRepository = Depends(get_repository)):
    if report_id not in repo.reports:
        raise not_found("Report not found.")
    try:
        ensure_report_consent_active(repo, report_id)
        if repo.reports[report_id].status.value == "Signed Off":
            return revise_finalized_report(repo, report_id, payload)
        return patch_report(repo, report_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/reports/{report_id}/sign-off", response_model=Report)
def sign_off(report_id: str, payload: ReportFinalizeRequest, repo: MockRepository = Depends(get_repository)):
    if report_id not in repo.reports:
        raise not_found("Report not found.")
    if payload.confirmation_checked is False:
        raise bad_request("Confirmation check must be accepted by therapist.")
    try:
        ensure_report_consent_active(repo, report_id)
        therapist_name = payload.therapist_name or payload.signed_by or "Demo Therapist"
        return sign_off_report(repo, report_id, therapist_name)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.get("/reports/{report_id}", response_model=Report)
def get_report(report_id: str, repo: MockRepository = Depends(get_repository)):
    if report_id not in repo.reports:
        raise not_found("Report not found.")
    return repo.clone(repo.reports[report_id])


@router.get("/reports/{report_id}/export", response_model=ExportResponse)
def export(report_id: str, format: str = "markdown", repo: MockRepository = Depends(get_repository)):
    if report_id not in repo.reports:
        raise not_found("Report not found.")
    try:
        ensure_report_consent_active(repo, report_id)
        return export_report(repo, report_id, format)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
