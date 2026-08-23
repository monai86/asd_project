from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.dependencies import get_repository
from app.auth.authorization import (
    assert_case_creation_allowed,
    authoritative_org_user,
    filter_cases_for_user,
    require_case,
)
from app.core.errors import not_found
from app.core.config import get_settings
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import ChildCase, ChildCaseCreate, ChildCaseUpdate, ConsentWithdrawalRequest, ConsentWithdrawalResult, TimelineEvent
from app.services.consent_service import withdraw_consent

router = APIRouter(prefix="/cases", tags=["cases"])


def _resolve_case_creation_payload(payload: ChildCaseCreate, repo: MockRepository, user: CurrentUser) -> ChildCaseCreate:
    actor_membership = repo.get_membership(user.organization_id, user.user_id)
    if (
        actor_membership is None and not get_settings().mock_mode
    ) or (
        actor_membership is not None and not actor_membership.active
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active organization membership required.",
        )
    if actor_membership is not None:
        user = authoritative_org_user(repo, user)
        assert_case_creation_allowed(repo, user)
    elif user.role not in {"therapist", "clinical_supervisor"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Case creation requires therapist or clinical supervisor role.",
        )

    if user.role == "therapist":
        if payload.primary_therapist_user_id and payload.primary_therapist_user_id != user.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Therapist-created cases must keep the authenticated therapist as primary.",
            )
        extra_care_team = [user_id for user_id in payload.care_team_user_ids if user_id != user.user_id]
        if extra_care_team:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Additional care-team members must be assigned through the care-team route.",
            )
        return payload.model_copy(
            update={
                "organization_id": user.organization_id,
                "care_team_user_ids": [user.user_id],
                "primary_therapist_user_id": user.user_id,
            }
        )

    primary_therapist_user_id = payload.primary_therapist_user_id
    if primary_therapist_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primary therapist assignment required at case creation.",
        )
    membership = repo.get_membership(user.organization_id, primary_therapist_user_id)
    if membership is not None and (membership.role != "therapist" or not membership.active):
        membership = None
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primary therapist assignment must be an active therapist membership.",
        )
    extra_care_team = [
        user_id
        for user_id in payload.care_team_user_ids
        if user_id not in {user.user_id, primary_therapist_user_id}
    ]
    if extra_care_team:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Additional care-team members must be assigned through the care-team route.",
        )
    return payload.model_copy(
        update={
            "organization_id": user.organization_id,
            "care_team_user_ids": [primary_therapist_user_id],
            "primary_therapist_user_id": primary_therapist_user_id,
        }
    )


@router.get("", response_model=list[ChildCase])
def list_cases(user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    cases = repo.list_cases_for_user(user.user_id, user.organization_id)
    return [repo.clone(item) for item in filter_cases_for_user(repo, cases, user)]


@router.post("", response_model=ChildCase)
def create_case(
    payload: ChildCaseCreate,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    scoped_payload = _resolve_case_creation_payload(payload, repo, user)
    return repo.create_case(
        scoped_payload,
        actor_id="system",
        allow_membership_bootstrap=get_settings().mock_mode,
    )


@router.get("/{case_id}", response_model=ChildCase)
def get_case(case_id: str, user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    return repo.clone(require_case(repo, case_id, user))


@router.patch("/{case_id}", response_model=ChildCase)
def update_case(
    case_id: str,
    payload: ChildCaseUpdate,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    case = require_case(repo, case_id, user)
    return repo.update_case(case_id, payload, expected_version=case.version, actor_id="system")


@router.get("/{case_id}/timeline", response_model=list[TimelineEvent])
def case_timeline(case_id: str, user: CurrentUser = Depends(get_current_user), repo: MockRepository = Depends(get_repository)):
    require_case(repo, case_id, user)
    events = []
    for session in repo.list_sessions(case_id):
        events.append(TimelineEvent(event_id=new_id("evt"), label=f"Session {session.session_date}", status=session.status, occurred_at=session.created_at, target_id=session.session_id))
    return events


@router.post("/{case_id}/withdraw-consent", response_model=ConsentWithdrawalResult)
def withdraw_case_consent(
    case_id: str,
    payload: ConsentWithdrawalRequest,
    user: CurrentUser = Depends(get_current_user),
    repo: MockRepository = Depends(get_repository),
):
    require_case(repo, case_id, user)
    return withdraw_consent(repo, case_id, payload.reason, payload.redact_notes)
