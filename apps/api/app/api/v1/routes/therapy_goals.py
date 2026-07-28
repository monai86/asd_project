from fastapi import APIRouter, Depends

from app.auth.authorization import assert_clinical_mutation_allowed, require_case
from app.api.v1.dependencies import get_repository
from app.core.errors import bad_request, not_found
from app.core.security import CurrentUser, get_current_user
from app.repositories.mock_repository import MockRepository
from app.schemas.clinical import TherapyGoal, TherapyGoalCreate, TherapyGoalUpdate
from app.services.consent_service import (
    active_case_consent_fence,
    ensure_case_consent_active,
)
from app.services.therapy_goal_service import create_goal, list_goals, update_goal

router = APIRouter(tags=["therapy-goals"])


@router.get("/cases/{case_id}/goals", response_model=list[TherapyGoal])
def get_case_goals(
    case_id: str,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    require_case(repo, case_id, user)
    try:
        ensure_case_consent_active(repo, case_id)
        return list_goals(repo, case_id)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.post("/cases/{case_id}/goals", response_model=TherapyGoal)
def create_case_goal(
    case_id: str,
    payload: TherapyGoalCreate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if case_id not in repo.cases:
        raise not_found("Case not found.")
    require_case(repo, case_id, user)
    assert_clinical_mutation_allowed(user)
    try:
        with active_case_consent_fence(repo, case_id):
            require_case(repo, case_id, user)
            return create_goal(repo, case_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc


@router.patch("/goals/{goal_id}", response_model=TherapyGoal)
def patch_goal(
    goal_id: str,
    payload: TherapyGoalUpdate,
    repo: MockRepository = Depends(get_repository),
    user: CurrentUser = Depends(get_current_user),
):
    if goal_id not in repo.therapy_goals:
        raise not_found("Therapy goal not found.")
    case_id = repo.therapy_goals[goal_id].case_id
    try:
        require_case(repo, case_id, user)
        assert_clinical_mutation_allowed(user)
        with active_case_consent_fence(repo, case_id):
            require_case(repo, case_id, user)
            return update_goal(repo, goal_id, payload)
    except ValueError as exc:
        raise bad_request(str(exc)) from exc
