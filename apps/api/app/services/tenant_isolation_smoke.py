from __future__ import annotations

import time

from fastapi import HTTPException, status

from app.auth.authorization import require_case
from app.core.security import CurrentUser
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import ChildCase, TenantIsolationSmokeCheck, TenantIsolationSmokeReport


def run_tenant_isolation_smoke(user: CurrentUser) -> TenantIsolationSmokeReport:
    repo = _synthetic_repository()
    checks = [
        _expect_http_error(
            key="cross_org_case_read",
            label="Cross-organization clinical case read is hidden",
            expected_status=status.HTTP_404_NOT_FOUND,
            action=lambda: require_case(repo, "case_smoke_org_b", _user("therapist_a", "therapist", "org_a")),
        ),
        _expect_http_error(
            key="care_team_guard",
            label="Unassigned therapist cannot read same-organization case",
            expected_status=status.HTTP_403_FORBIDDEN,
            action=lambda: require_case(repo, "case_smoke_org_a", _user("therapist_unassigned", "therapist", "org_a")),
        ),
        _expect_http_error(
            key="org_admin_clinical_grant",
            label="Org admin needs explicit care-team grant for clinical case access",
            expected_status=status.HTTP_403_FORBIDDEN,
            action=lambda: require_case(repo, "case_smoke_org_a", _user("admin_unassigned", "org_admin", "org_a")),
        ),
        _expect_success(
            key="explicit_care_team_access",
            label="Assigned therapist can read assigned organization case",
            action=lambda: require_case(repo, "case_smoke_org_a", _user("therapist_a", "therapist", "org_a")),
            evidence="assigned therapist read allowed for case_smoke_org_a",
        ),
        _expect_success(
            key="org_admin_explicit_grant",
            label="Org admin with explicit care-team grant can read clinical case",
            action=lambda: require_case(repo, "case_smoke_admin_grant", _user("admin_a", "org_admin", "org_a")),
            evidence="org admin read allowed only when listed in care_team_user_ids",
        ),
        _expect_success(
            key="break_glass_scope",
            label="Platform break-glass access is scoped and audited",
            action=lambda: _break_glass_case_access(
                repo,
                "case_smoke_org_a",
                _user(
                    "platform_a",
                    "platform_operator",
                    "org_a",
                    break_glass_case_id="case_smoke_org_a",
                    break_glass_category="incident_response",
                    break_glass_reason="Synthetic smoke verification.",
                    break_glass_expires_at=int(time.time()) + 600,
                ),
            ),
            evidence="scoped break-glass access writes break_glass.case_access audit event",
        ),
        _expect_http_error(
            key="break_glass_wrong_scope",
            label="Platform break-glass access rejects an unscoped case",
            expected_status=status.HTTP_403_FORBIDDEN,
            action=lambda: _break_glass_case_access(
                repo,
                "case_smoke_org_b",
                _user(
                    "platform_a",
                    "platform_operator",
                    "org_a",
                    break_glass_case_id="case_smoke_org_a",
                    break_glass_category="incident_response",
                    break_glass_reason="Synthetic smoke verification.",
                    break_glass_expires_at=int(time.time()) + 600,
                ),
            ),
        ),
    ]
    return TenantIsolationSmokeReport(
        status="passed" if all(check.passed for check in checks) else "failed",
        checked_by=user.user_id,
        organization_id=user.organization_id,
        checks=checks,
    )


def _synthetic_repository() -> MockRepository:
    repo = MockRepository()
    repo.cases.clear()
    repo.sessions.clear()
    repo.transcripts.clear()
    repo.reports.clear()
    repo.audit_log.clear()
    repo.cases["case_smoke_org_a"] = ChildCase(
        case_id="case_smoke_org_a",
        organization_id="org_a",
        care_team_user_ids=["therapist_a"],
        primary_therapist_user_id="therapist_a",
        child_code="SMOKE-A",
        age_months=60,
    )
    repo.cases["case_smoke_org_b"] = ChildCase(
        case_id="case_smoke_org_b",
        organization_id="org_b",
        care_team_user_ids=["therapist_b"],
        primary_therapist_user_id="therapist_b",
        child_code="SMOKE-B",
        age_months=61,
    )
    repo.cases["case_smoke_admin_grant"] = ChildCase(
        case_id="case_smoke_admin_grant",
        organization_id="org_a",
        care_team_user_ids=["admin_a"],
        primary_therapist_user_id=None,
        child_code="SMOKE-ADMIN",
        age_months=62,
    )
    return repo


def _expect_http_error(
    *,
    key: str,
    label: str,
    expected_status: int,
    action,
) -> TenantIsolationSmokeCheck:
    try:
        action()
    except HTTPException as exc:
        passed = exc.status_code == expected_status
        return TenantIsolationSmokeCheck(
            key=key,
            label=label,
            passed=passed,
            evidence=f"blocked_with_status={exc.status_code}; expected_status={expected_status}",
        )
    return TenantIsolationSmokeCheck(
        key=key,
        label=label,
        passed=False,
        evidence=f"access_allowed_unexpectedly; expected_status={expected_status}",
    )


def _expect_success(*, key: str, label: str, action, evidence: str) -> TenantIsolationSmokeCheck:
    try:
        action()
    except HTTPException as exc:
        return TenantIsolationSmokeCheck(
            key=key,
            label=label,
            passed=False,
            evidence=f"blocked_with_status={exc.status_code}; expected_success=true",
        )
    return TenantIsolationSmokeCheck(key=key, label=label, passed=True, evidence=evidence)


def _break_glass_case_access(repo: MockRepository, case_id: str, user: CurrentUser) -> ChildCase:
    if user.role != "platform_operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform operator role required.")
    if not user.break_glass_category:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access requires a category.")
    if not user.break_glass_reason:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access requires a reason.")
    if not user.break_glass_case_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access requires a scoped case.")
    if user.break_glass_case_id != case_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access is limited to the scoped case.")
    if not user.break_glass_expires_at or user.break_glass_expires_at <= int(time.time()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Break-glass access is expired.")
    case = repo.cases.get(case_id)
    if case is None or case.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    repo.audit_break_glass_case_access(user.organization_id, case_id, actor_id=user.user_id)
    if not any(event["action"] == "break_glass.case_access" for event in repo.audit_log):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Break-glass audit missing.")
    return repo.clone(case)


def _user(
    user_id: str,
    role: str,
    organization_id: str,
    *,
    break_glass_case_id: str | None = None,
    break_glass_category: str | None = None,
    break_glass_reason: str | None = None,
    break_glass_expires_at: int | None = None,
) -> CurrentUser:
    return CurrentUser(
        user_id=user_id,
        role=role,
        organization_id=organization_id,
        break_glass_case_id=break_glass_case_id,
        break_glass_category=break_glass_category,
        break_glass_reason=break_glass_reason,
        break_glass_expires_at=break_glass_expires_at,
    )
