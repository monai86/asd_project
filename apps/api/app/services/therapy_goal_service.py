from __future__ import annotations

from datetime import timezone, datetime

from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import TherapyGoal, TherapyGoalCreate, TherapyGoalUpdate


ALLOWED_GOAL_STATUSES = {"active", "paused", "completed", "withdrawn"}


def list_goals(repo: MockRepository, case_id: str) -> list[TherapyGoal]:
    return [repo.clone(goal) for goal in repo.therapy_goals.values() if goal.case_id == case_id]


def create_goal(repo: MockRepository, case_id: str, payload: TherapyGoalCreate) -> TherapyGoal:
    status = _validate_status(payload.status)
    goal = TherapyGoal(
        goal_id=new_id("goal"),
        case_id=case_id,
        title=payload.title.strip(),
        target=payload.target.strip(),
        status=status,
        notes=payload.notes.strip(),
    )
    if not goal.title:
        raise ValueError("Therapy goal title is required.")
    repo.therapy_goals[goal.goal_id] = goal
    repo.add_audit("therapy_goal.create", goal.goal_id, "Therapy goal created for case.")
    return repo.clone(goal)


def update_goal(repo: MockRepository, goal_id: str, payload: TherapyGoalUpdate) -> TherapyGoal:
    goal = repo.therapy_goals[goal_id]
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = _validate_status(updates["status"])
    if "title" in updates and updates["title"] is not None:
        updates["title"] = updates["title"].strip()
        if not updates["title"]:
            raise ValueError("Therapy goal title is required.")
    for key, value in updates.items():
        setattr(goal, key, value)
    goal.updated_at = datetime.now(timezone.utc)
    repo.add_audit("therapy_goal.patch", goal_id, "Therapy goal updated.")
    return repo.clone(goal)


def _validate_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized not in ALLOWED_GOAL_STATUSES:
        raise ValueError("Therapy goal status must be active, paused, completed, or withdrawn.")
    return normalized
