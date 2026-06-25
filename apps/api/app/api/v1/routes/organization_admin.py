from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_repository
from app.auth.authorization import require_case
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import (
    CareTeamAssignment,
    CareTeamAssignmentCreate,
    OrganizationMembership,
    OrganizationMembershipCreate,
)


router = APIRouter(tags=["organization-admin"])

ORG_MANAGEMENT_ROLES = {"admin", "org_admin"}


def _require_org_admin(user: CurrentUser) -> None:
    if user.role not in ORG_MANAGEMENT_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization admin role required.")


@router.get("/organizations/current/memberships", response_model=list[OrganizationMembership])
def list_current_organization_memberships(
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    _require_org_admin(user)
    return repo.list_memberships(user.organization_id)


@router.post("/organizations/current/memberships", response_model=OrganizationMembership)
def upsert_current_organization_membership(
    payload: OrganizationMembershipCreate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    _require_org_admin(user)
    return repo.upsert_membership(user.organization_id, payload, actor_id=user.user_id)


@router.get("/cases/{case_id}/care-team", response_model=list[CareTeamAssignment])
def list_case_care_team(
    case_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    _require_org_admin(user)
    require_case(repo, case_id, user)
    return repo.list_care_team_assignments(case_id)


@router.post("/cases/{case_id}/care-team", response_model=CareTeamAssignment)
def assign_case_care_team_member(
    case_id: str,
    payload: CareTeamAssignmentCreate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    _require_org_admin(user)
    require_case(repo, case_id, user)
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
    return repo.assign_care_team_member(case_id, payload, actor_id=user.user_id)
