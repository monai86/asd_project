from __future__ import annotations

from fastapi import HTTPException, status

from app.core.errors import not_found
from app.core.security import CurrentUser
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ChildCase, Report, TherapySession, Transcript


PILOT_ORG_ID = "pilot_org_001"
PILOT_THERAPIST_ID = "therapist-demo"
ORG_ADMIN_ROLES = {"admin", "org_admin", "clinical_supervisor", "supervisor"}
CLINICAL_ROLES = {"therapist", *ORG_ADMIN_ROLES}


def assert_case_access(case: ChildCase, user: CurrentUser) -> None:
    if user.role == "platform_operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clinical content access denied.")
    if case.organization_id != user.organization_id:
        raise not_found("Case not found.")
    if user.role in ORG_ADMIN_ROLES:
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
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    case = repo.cases[case_id]
    assert_case_access(case, user)
    return case


def require_session(repo: MockRepository, session_id: str, user: CurrentUser) -> TherapySession:
    if session_id not in repo.sessions:
        raise not_found("Session not found.")
    session = repo.sessions[session_id]
    require_case(repo, session.case_id, user)
    return session


def require_transcript(repo: MockRepository, transcript_id: str, user: CurrentUser) -> Transcript:
    if transcript_id not in repo.transcripts:
        raise not_found("Transcript not found.")
    transcript = repo.transcripts[transcript_id]
    require_case(repo, transcript.case_id, user)
    return transcript


def require_report(repo: MockRepository, report_id: str, user: CurrentUser) -> Report:
    if report_id not in repo.reports:
        raise not_found("Report not found.")
    report = repo.reports[report_id]
    require_case(repo, report.case_id, user)
    return report
