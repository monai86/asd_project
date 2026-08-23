from __future__ import annotations

from fastapi import HTTPException, status

from app.core.errors import not_found
from app.core.security import CurrentUser
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ChildCase, Report, TherapySession, Transcript


PILOT_ORG_ID = "pilot_org_001"
PILOT_THERAPIST_ID = "therapist-demo"
ORG_MANAGEMENT_ROLES = {"org_admin"}
CLINICAL_OVERSIGHT_ROLES = {"clinical_supervisor"}
CARE_TEAM_ASSIGNMENT_ROLES = {*ORG_MANAGEMENT_ROLES, *CLINICAL_OVERSIGHT_ROLES}
CLINICAL_ROLES = {"therapist", *CLINICAL_OVERSIGHT_ROLES}
CASE_CREATION_ROLES = {"therapist", *CLINICAL_OVERSIGHT_ROLES}
CLINICAL_MUTATION_ROLES = {"therapist", *CLINICAL_OVERSIGHT_ROLES}
SENSITIVE_CLINICAL_EXPORT_ROLES = {"therapist", *CLINICAL_OVERSIGHT_ROLES}


def assert_case_creation_allowed(user: CurrentUser) -> None:
    if user.role not in CASE_CREATION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Case creation requires therapist or clinical supervisor role.",
        )


def assert_clinical_mutation_allowed(user: CurrentUser) -> None:
    if user.role not in CLINICAL_MUTATION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinical mutation requires therapist or clinical supervisor role.",
        )


def assert_sensitive_clinical_export_allowed(user: CurrentUser) -> None:
    if user.role not in SENSITIVE_CLINICAL_EXPORT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sensitive clinical export requires therapist or clinical supervisor role.",
        )


def assert_case_access(case: ChildCase, user: CurrentUser) -> None:
    if user.role == "platform_operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical content access denied.")
    if case.organization_id != user.organization_id:
        raise not_found("Case not found.")
    if user.role in CLINICAL_OVERSIGHT_ROLES:
        return
    if user.role == "org_admin":
        if user.user_id not in case.care_team_user_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Care-team assignment required.")
        return
    if user.role not in CLINICAL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical content access denied.")
    if user.user_id not in case.care_team_user_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Care-team assignment required.")


def filter_cases_for_user(cases: list[ChildCase], user: CurrentUser) -> list[ChildCase]:
    visible = []
    for case in cases:
        try:
            assert_case_access(case, user)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                continue
            if exc.status_code == status.HTTP_403_FORBIDDEN:
                continue
            raise
        visible.append(case)
    return visible


def require_case(repo: MockRepository, case_id: str, user: CurrentUser) -> ChildCase:
    case = require_org_case(repo, case_id, user)
    assert_case_access(case, user)
    return case


def require_org_case(repo: MockRepository, case_id: str, user: CurrentUser) -> ChildCase:
    case = repo.get_case(case_id)
    if case is None:
        raise not_found("Case not found.")
    if case.organization_id != user.organization_id:
        raise not_found("Case not found.")
    return case


def require_session(repo: MockRepository, session_id: str, user: CurrentUser) -> TherapySession:
    session = repo.get_session(session_id)
    if session is None:
        raise not_found("Session not found.")
    require_case(repo, session.case_id, user)
    return session


def require_transcript(repo: MockRepository, transcript_id: str, user: CurrentUser) -> Transcript:
    transcript = repo.get_transcript(transcript_id)
    if transcript is None:
        raise not_found("Transcript not found.")
    require_case(repo, transcript.case_id, user)
    return transcript


def require_report(repo: MockRepository, report_id: str, user: CurrentUser) -> Report:
    report = repo.get_report(report_id)
    if report is None:
        raise not_found("Report not found.")
    require_case(repo, report.case_id, user)
    return report
