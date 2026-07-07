from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_repository
from app.auth.authorization import CARE_TEAM_ASSIGNMENT_ROLES, require_org_case
from app.core.config import (
    PRODUCTION_JOB_QUEUE_MODES,
    PRODUCTION_OBSERVABILITY_PROVIDERS,
    PRODUCTION_SECRET_STORE_PROVIDERS,
    PRODUCTION_STORAGE_MODES,
    get_settings,
)
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    CareTeamAssignment,
    CareTeamAssignmentCreate,
    OrganizationMembership,
    OrganizationMembershipCreate,
    OrganizationInvitation,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    OrganizationReadiness,
    OrganizationReadinessItem,
)


router = APIRouter(tags=["organization-admin"])

ORG_MANAGEMENT_ROLES = {"org_admin"}


def _require_org_admin(user: CurrentUser) -> None:
    if user.role not in ORG_MANAGEMENT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admin role required.")


def _require_assignment_manager(user: CurrentUser) -> None:
    if user.role not in CARE_TEAM_ASSIGNMENT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Care-team assignment role required.")


def _readiness_item(
    key: str,
    label: str,
    ready: bool,
    ready_detail: str,
    blocked_detail: str,
    ready_evidence: list[str],
    blocked_evidence: list[str],
    next_action: str,
    blocked_status: str = "blocked",
) -> OrganizationReadinessItem:
    return OrganizationReadinessItem(
        key=key,
        label=label,
        status="ready" if ready else blocked_status,
        detail=ready_detail if ready else blocked_detail,
        evidence=ready_evidence if ready else blocked_evidence,
        next_action="" if ready else next_action,
    )


@router.get("/organizations/current/readiness", response_model=OrganizationReadiness)
def get_current_organization_readiness(
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_org_admin(user)
    config = get_settings()
    active_memberships = sum(1 for item in repo.list_memberships(user.organization_id) if item.active)
    pending_invitations = sum(1 for item in repo.list_invitations(user.organization_id) if item.status == "pending")
    items = [
        _readiness_item(
            key="auth_mode",
            label="Production-capable auth",
            ready=config.auth_mode == "supabase" and not config.mock_mode,
            ready_detail="Supabase auth is active with mock mode disabled.",
            blocked_detail="Production SaaS requires Supabase auth with mock mode disabled.",
            ready_evidence=[f"auth_mode={config.auth_mode}", "mock_mode=false"],
            blocked_evidence=[f"auth_mode={config.auth_mode}", f"mock_mode={str(config.mock_mode).lower()}"],
            next_action="Configure Supabase auth and set LINGUALENS_MOCK_MODE=false for production-like runtime.",
        ),
        _readiness_item(
            key="invitation_policy",
            label="Invitation-only access",
            ready=config.supabase_require_invitation,
            ready_detail="Accepted invitation is required before app access.",
            blocked_detail="Production access must require accepted invitations.",
            ready_evidence=["supabase_require_invitation=true", f"pending_invitations={pending_invitations}"],
            blocked_evidence=["supabase_require_invitation=false"],
            next_action="Enable invitation-only access and verify accepted invitation claims before workspace access.",
        ),
        _readiness_item(
            key="mfa_policy",
            label="AAL2 / MFA gate",
            ready=config.supabase_require_mfa,
            ready_detail="AAL2 is required before clinical or admin workflow access.",
            blocked_detail="Production access must require MFA before workspace use.",
            ready_evidence=["supabase_require_mfa=true", "required_app_aal=aal2"],
            blocked_evidence=["supabase_require_mfa=false"],
            next_action="Require TOTP MFA and verify AAL2 claims before clinical/admin routes render.",
        ),
        _readiness_item(
            key="repository",
            label="Tenant persistence",
            ready=config.repository_mode == "sql",
            ready_detail="SQL repository is configured.",
            blocked_detail=f"{config.repository_mode} repository is for local/pilot use, not production SaaS.",
            ready_evidence=["repository_mode=sql"],
            blocked_evidence=[f"repository_mode={config.repository_mode}"],
            next_action="Switch to SQL repository backed by managed Postgres/Supabase and run migrations to head.",
            blocked_status="attention",
        ),
        _readiness_item(
            key="tenant_isolation",
            label="Tenant isolation verification",
            ready=config.repository_mode == "sql" and config.auth_mode == "supabase" and not config.mock_mode,
            ready_detail="Production-like auth and SQL tenant persistence are configured for tenant isolation verification.",
            blocked_detail="Tenant isolation cannot be production-verified while mock auth or non-SQL persistence is active.",
            ready_evidence=[
                "auth_mode=supabase",
                "repository_mode=sql",
                "api_org_guards=enabled",
                "rls_migration=0009_tenant_rls",
            ],
            blocked_evidence=[
                f"auth_mode={config.auth_mode}",
                f"mock_mode={str(config.mock_mode).lower()}",
                f"repository_mode={config.repository_mode}",
                "api_org_guards=enabled",
                "rls_migration=0009_tenant_rls",
            ],
            next_action="Run production-like tenant isolation smoke tests against Supabase/Postgres with two organizations.",
            blocked_status="attention",
        ),
        _readiness_item(
            key="storage",
            label="Private storage",
            ready=config.storage_mode in PRODUCTION_STORAGE_MODES,
            ready_detail="Private managed storage mode is configured.",
            blocked_detail=f"{config.storage_mode} storage is acceptable for pilot verification only.",
            ready_evidence=[f"storage_mode={config.storage_mode}"],
            blocked_evidence=[f"storage_mode={config.storage_mode}"],
            next_action="Configure private managed storage and signed URL access for clinical uploads.",
            blocked_status="attention",
        ),
        _readiness_item(
            key="job_queue",
            label="Durable job queue",
            ready=config.job_queue_mode in PRODUCTION_JOB_QUEUE_MODES,
            ready_detail="Durable managed job queue is configured.",
            blocked_detail=f"{config.job_queue_mode} job queue is not production durable.",
            ready_evidence=[f"job_queue_mode={config.job_queue_mode}"],
            blocked_evidence=[f"job_queue_mode={config.job_queue_mode}"],
            next_action="Configure Redis/Celery or another durable managed queue for async audio/report work.",
            blocked_status="attention",
        ),
        _readiness_item(
            key="observability",
            label="Production observability",
            ready=config.observability_enabled and config.observability_provider in PRODUCTION_OBSERVABILITY_PROVIDERS,
            ready_detail="Approved observability provider is configured.",
            blocked_detail="Production SaaS needs approved observability and critical alert routing.",
            ready_evidence=[f"observability_provider={config.observability_provider}", "observability_enabled=true"],
            blocked_evidence=[
                f"observability_provider={config.observability_provider}",
                f"observability_enabled={str(config.observability_enabled).lower()}",
            ],
            next_action="Configure Sentry, CloudWatch, or OTLP plus a critical alert route.",
        ),
        _readiness_item(
            key="secrets",
            label="Managed secrets",
            ready=config.secret_store_provider in PRODUCTION_SECRET_STORE_PROVIDERS,
            ready_detail="Managed secret store provider is configured.",
            blocked_detail="Production secrets must come from a managed secret store.",
            ready_evidence=[f"secret_store_provider={config.secret_store_provider}"],
            blocked_evidence=[f"secret_store_provider={config.secret_store_provider}"],
            next_action="Move production credentials into an approved managed secret store and document rotation.",
        ),
    ]
    pilot_ready = (
        config.supabase_require_invitation
        and config.supabase_require_mfa
        and active_memberships > 0
        and all(item.status != "blocked" for item in items if item.key in {"invitation_policy", "mfa_policy"})
    )
    production_ready = all(item.status == "ready" for item in items)
    return OrganizationReadiness(
        organization_id=user.organization_id,
        checked_by=user.user_id,
        role=user.role,
        environment="local_pilot" if config.mock_mode else "production_like",
        pilot_ready=pilot_ready,
        production_ready=production_ready,
        active_memberships=active_memberships,
        pending_invitations=pending_invitations,
        items=items,
    )


@router.get("/organizations/current/memberships", response_model=list[OrganizationMembership])
def list_current_organization_memberships(
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_org_admin(user)
    return repo.list_memberships(user.organization_id)


@router.post("/organizations/current/memberships", response_model=OrganizationMembership)
def upsert_current_organization_membership(
    payload: OrganizationMembershipCreate,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_org_admin(user)
    return repo.upsert_membership(user.organization_id, payload, actor_id=user.user_id)


@router.post("/organizations/current/memberships/{membership_id}/revoke", response_model=OrganizationMembership)
def revoke_current_organization_membership(
    membership_id: str,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_org_admin(user)
    try:
        return repo.revoke_membership(user.organization_id, membership_id, actor_id=user.user_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.") from None


@router.get("/organizations/current/invitations", response_model=list[OrganizationInvitation])
def list_current_organization_invitations(
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_org_admin(user)
    return repo.list_invitations(user.organization_id)


@router.post("/organizations/current/invitations", response_model=OrganizationInvitation)
def create_current_organization_invitation(
    payload: OrganizationInvitationCreate,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_org_admin(user)
    return repo.create_invitation(user.organization_id, payload, actor_id=user.user_id)


@router.post("/organizations/current/invitations/{invitation_id}/accept", response_model=OrganizationInvitation)
def accept_current_organization_invitation(
    invitation_id: str,
    payload: OrganizationInvitationAccept,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_org_admin(user)
    try:
        invitation = repo.accept_invitation(user.organization_id, invitation_id, payload, actor_id=user.user_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.") from None
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if invitation.status != "accepted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation is not accepted.")
    return invitation


@router.get("/cases/{case_id}/care-team", response_model=list[CareTeamAssignment])
def list_case_care_team(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_assignment_manager(user)
    require_org_case(repo, case_id, user)
    return repo.list_care_team_assignments(case_id)


@router.post("/cases/{case_id}/care-team", response_model=CareTeamAssignment)
def assign_case_care_team_member(
    case_id: str,
    payload: CareTeamAssignmentCreate,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    _require_assignment_manager(user)
    require_org_case(repo, case_id, user)
    membership = next(
        (
            item
            for item in repo.memberships.values()
            if item.organization_id == user.organization_id
            and item.user_id == payload.user_id
            and item.active
        ),
        None,
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active organization membership required.")
    try:
        return repo.assign_care_team_member(case_id, payload, actor_id=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/cases/{case_id}/break-glass-access")
def scoped_break_glass_case_access(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
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
    return case
