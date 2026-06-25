from __future__ import annotations

from typing import Protocol

from app.schemas.clinical import (
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    ReviewStatus,
    Report,
    TherapyGoal,
)


class CaseVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale clinical record version."""


class SessionVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale session record version."""


class TranscriptVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale transcript record version."""


class ReportVersionConflictError(RuntimeError):
    """Raised when a caller updates a stale report record version."""


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

    def create_session(self, case_id: str, payload: TherapySessionCreate, *, actor_id: str) -> TherapySession: ...

    def update_session(
        self,
        session_id: str,
        patch: TherapySessionUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> TherapySession: ...

    def create_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript: ...

    def update_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript: ...

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report: ...

    def update_report(
        self,
        report: Report,
        *,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report: ...

    def create_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal: ...

    def update_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal: ...
