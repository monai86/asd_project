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
        OrganizationReadinessItem(
            key="auth_mode",
            label="Production-capable auth",
            status="ready" if config.auth_mode == "supabase" and not config.mock_mode else "blocked",
            detail=(
                "Supabase auth is active with mock mode disabled."
                if config.auth_mode == "supabase" and not config.mock_mode
                else "Production SaaS requires Supabase auth with mock mode disabled."
            ),
        ),
        OrganizationReadinessItem(
            key="invitation_policy",
            label="Invitation-only access",
            status="ready" if config.supabase_require_invitation else "blocked",
            detail=(
                "Accepted invitation is required before app access."
                if config.supabase_require_invitation
                else "Production access must require accepted invitations."
            ),
        ),
        OrganizationReadinessItem(
            key="mfa_policy",
            label="AAL2 / MFA gate",
            status="ready" if config.supabase_require_mfa else "blocked",
            detail=(
                "AAL2 is required before clinical or admin workflow access."
                if config.supabase_require_mfa
                else "Production access must require MFA before workspace use."
            ),
        ),
        OrganizationReadinessItem(
            key="repository",
            label="Tenant persistence",
            status="ready" if config.repository_mode == "sql" else "attention",
            detail=(
                "SQL repository is configured."
                if config.repository_mode == "sql"
                else f"{config.repository_mode} repository is for local/pilot use, not production SaaS."
            ),
        ),
        OrganizationReadinessItem(
            key="storage",
            label="Private storage",
            status="ready" if config.storage_mode in PRODUCTION_STORAGE_MODES else "attention",
            detail=(
                "Private managed storage mode is configured."
                if config.storage_mode in PRODUCTION_STORAGE_MODES
                else f"{config.storage_mode} storage is acceptable for pilot verification only."
            ),
        ),
        OrganizationReadinessItem(
            key="job_queue",
            label="Durable job queue",
            status="ready" if config.job_queue_mode in PRODUCTION_JOB_QUEUE_MODES else "attention",
            detail=(
                "Durable managed job queue is configured."
                if config.job_queue_mode in PRODUCTION_JOB_QUEUE_MODES
                else f"{config.job_queue_mode} job queue is not production durable."
            ),
        ),
        OrganizationReadinessItem(
            key="observability",
            label="Production observability",
            status=(
                "ready"
                if config.observability_enabled and config.observability_provider in PRODUCTION_OBSERVABILITY_PROVIDERS
                else "blocked"
            ),
            detail=(
                "Approved observability provider is configured."
                if config.observability_enabled and config.observability_provider in PRODUCTION_OBSERVABILITY_PROVIDERS
                else "Production SaaS needs approved observability and critical alert routing."
            ),
        ),
        OrganizationReadinessItem(
            key="secrets",
            label="Managed secrets",
            status="ready" if config.secret_store_provider in PRODUCTION_SECRET_STORE_PROVIDERS else "blocked",
            detail=(
                "Managed secret store provider is configured."
                if config.secret_store_provider in PRODUCTION_SECRET_STORE_PROVIDERS
                else "Production secrets must come from a managed secret store."
            ),
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
