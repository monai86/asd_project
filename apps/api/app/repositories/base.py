from __future__ import annotations

from typing import Protocol

from app.schemas.clinical import ChildCase, ChildCaseCreate, ChildCaseUpdate


class CaseVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale clinical record version."""


class ClinicalRepository(Protocol):
    def get_case(self, case_id: str) -> ChildCase | None: ...

    def create_case(self, payload: ChildCaseCreate, *, actor_id: str) -> ChildCase: ...

    def update_case(
        self,
        case_id: str,
        patch: ChildCaseUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> ChildCase: ...

    def list_cases_for_user(self, user_id: str, organization_id: str) -> list[ChildCase]: ...
