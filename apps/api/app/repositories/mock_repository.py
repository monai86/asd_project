from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from uuid import uuid4

from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    CareTeamAssignment,
    CareTeamAssignmentCreate,
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    MLResult,
    OrganizationMembership,
    OrganizationMembershipCreate,
    OrganizationInvitation,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    PrivacyOperation,
    ProcessingJob,
    Report,
    ReviewStatus,
    TherapyGoal,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    utc_now,
)
from app.repositories.base import (
    CaseVersionConflictError,
    ReportVersionConflictError,
    SessionVersionConflictError,
    TranscriptVersionConflictError,
)
from app.services.audit_safety import validate_audit_event


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class MockRepository:
    """In-memory repository for local demo and contract tests."""

    def __init__(self) -> None:
        self.cases: dict[str, ChildCase] = {}
        self.sessions: dict[str, TherapySession] = {}
        self.transcripts: dict[str, Transcript] = {}
        self.features: dict[str, FeatureSet] = {}
        self.ml_results: dict[str, MLResult] = {}
        self.ai_reviews: dict[str, AiReview] = {}
        self.reports: dict[str, Report] = {}
        self.memberships: dict[str, OrganizationMembership] = {}
        self.invitations: dict[str, OrganizationInvitation] = {}
        self.care_team_assignments: dict[str, CareTeamAssignment] = {}
        self.therapy_goals: dict[str, TherapyGoal] = {}
        self.audio_files: dict[str, AudioFileMetadata] = {}
        self.jobs: dict[str, ProcessingJob] = {}
        self.privacy_operations: dict[str, PrivacyOperation] = {}
        self.audit_log: list[dict] = []
        self.seed()

    def seed(self) -> None:
        if self.cases:
            return
        case = ChildCase(
            case_id="case_demo_001",
            organization_id="pilot_org_001",
            care_team_user_ids=["therapist-demo"],
            child_code="C-1024",
            nickname="Demo child",
            age_months=62,
            language="English",
            consent_status="granted",
            review_priority="moderate",
        )
        session = TherapySession(
            session_id="session_demo_001",
            case_id=case.case_id,
            session_date="2026-06-12",
            session_type="therapy_session",
            status=ReviewStatus.needs_review,
        )
        case.latest_session_date = session.session_date
        case.latest_session_status = session.status
        self.cases[case.case_id] = case
        self.sessions[session.session_id] = session

    def clone(self, value):
        return deepcopy(value)

    def add_audit(
        self,
        action: str,
        target_id: str,
        message: str,
        *,
        actor_id: str = "system",
        outcome: str = "success",
        correlation_id: str = "local",
    ) -> None:
        event = validate_audit_event(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            outcome=outcome,
            correlation_id=correlation_id,
            message=message,
        )
        event_data = event.as_dict()
        event_data["organization_id"] = self._organization_for_target(target_id)
        self.audit_log.append(event_data)

    def _organization_for_target(self, target_id: str) -> str:
        if target_id in self.cases:
            return self.cases[target_id].organization_id
        if target_id in self.sessions:
            return self.sessions[target_id].organization_id
        if target_id in self.transcripts:
            return self.transcripts[target_id].organization_id
        if target_id in self.features:
            return self.features[target_id].organization_id
        if target_id in self.ml_results:
            return self.ml_results[target_id].organization_id
        if target_id in self.ai_reviews:
            return self.ai_reviews[target_id].organization_id
        if target_id in self.reports:
            return self.reports[target_id].organization_id
        if target_id in self.memberships:
            return self.memberships[target_id].organization_id
        if target_id in self.invitations:
            return self.invitations[target_id].organization_id
        if target_id in self.care_team_assignments:
            return self.care_team_assignments[target_id].organization_id
        if target_id in self.therapy_goals:
            return self.therapy_goals[target_id].organization_id
        if target_id in self.audio_files:
            return self.audio_files[target_id].organization_id
        if target_id in self.jobs:
            return self.jobs[target_id].organization_id
        if target_id in self.privacy_operations:
            return self.privacy_operations[target_id].organization_id
        return "pilot_org_001"

    def create_case(self, payload: ChildCaseCreate, *, actor_id: str) -> ChildCase:
        case = ChildCase(case_id=new_id("case"), **payload.model_dump())
        if actor_id not in case.care_team_user_ids and actor_id != "system":
            case.care_team_user_ids = [*case.care_team_user_ids, actor_id]
        self.cases[case.case_id] = case
        self.add_audit("case.create", case.case_id, "Case created.", actor_id=actor_id)
        return self.clone(case)

    def update_case(
        self,
        case_id: str,
        patch: ChildCaseUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> ChildCase:
        case = self.cases[case_id]
        if expected_version is not None and case.version != expected_version:
            raise CaseVersionConflictError(
                f"Case {case_id} expected version {expected_version}, found {case.version}."
            )
        for key, value in patch.model_dump(exclude_unset=True).items():
            setattr(case, key, value)
        case.version += 1
        self.add_audit("case.update", case_id, "Case updated.", actor_id=actor_id)
        return self.clone(case)

    def upsert_membership(
        self,
        organization_id: str,
        payload: OrganizationMembershipCreate,
        *,
        actor_id: str,
    ) -> OrganizationMembership:
        existing = next(
            (
                membership
                for membership in self.memberships.values()
                if membership.organization_id == organization_id and membership.user_id == payload.user_id
            ),
            None,
        )
        if existing:
            existing.display_name = payload.display_name
            existing.role = payload.role
            existing.active = payload.active
            membership = existing
        else:
            membership = OrganizationMembership(
                membership_id=new_id("mbr"),
                organization_id=organization_id,
                user_id=payload.user_id,
                display_name=payload.display_name,
                role=payload.role,
                active=payload.active,
            )
            self.memberships[membership.membership_id] = membership
        self.add_audit(
            "membership.upsert",
            membership.membership_id,
            "Organization membership updated.",
            actor_id=actor_id,
        )
        return self.clone(membership)

    def list_memberships(self, organization_id: str) -> list[OrganizationMembership]:
        memberships = [item for item in self.memberships.values() if item.organization_id == organization_id]
        memberships.sort(key=lambda item: item.created_at)
        return [self.clone(item) for item in memberships]

    def revoke_membership(self, organization_id: str, membership_id: str, *, actor_id: str) -> OrganizationMembership:
        membership = self.memberships[membership_id]
        if membership.organization_id != organization_id:
            raise KeyError(membership_id)
        membership.active = False
        for assignment in self.care_team_assignments.values():
            if assignment.organization_id == organization_id and assignment.user_id == membership.user_id:
                assignment.active = False
                if assignment.case_id in self.cases:
                    case = self.cases[assignment.case_id]
                    case.care_team_user_ids = [
                        user_id for user_id in case.care_team_user_ids if user_id != membership.user_id
                    ]
        self.add_audit(
            "membership.revoke",
            membership.membership_id,
            "Organization membership revoked.",
            actor_id=actor_id,
        )
        return self.clone(membership)

    def create_invitation(
        self,
        organization_id: str,
        payload: OrganizationInvitationCreate,
        *,
        actor_id: str,
    ) -> OrganizationInvitation:
        invitation = OrganizationInvitation(
            invitation_id=new_id("inv"),
            organization_id=organization_id,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            invited_by=actor_id,
            expires_at=payload.expires_at or (utc_now() + timedelta(days=7)),
        )
        self.invitations[invitation.invitation_id] = invitation
        self.add_audit(
            "invitation.create",
            invitation.invitation_id,
            "Organization invitation created.",
            actor_id=actor_id,
        )
        return self.clone(invitation)

    def list_invitations(self, organization_id: str) -> list[OrganizationInvitation]:
        invitations = [item for item in self.invitations.values() if item.organization_id == organization_id]
        invitations.sort(key=lambda item: item.created_at)
        return [self.clone(item) for item in invitations]

    def accept_invitation(
        self,
        organization_id: str,
        invitation_id: str,
        payload: OrganizationInvitationAccept,
        *,
        actor_id: str,
    ) -> OrganizationInvitation:
        invitation = self.invitations[invitation_id]
        if invitation.organization_id != organization_id:
            raise KeyError(invitation_id)
        now = utc_now()
        if invitation.expires_at <= now:
            invitation.status = "expired"
            self.add_audit(
                "invitation.accept",
                invitation.invitation_id,
                "Organization invitation acceptance failed.",
                actor_id=actor_id,
                outcome="denied",
            )
            return self.clone(invitation)
        invitation.status = "accepted"
        invitation.accepted_user_id = payload.user_id
        invitation.accepted_at = now
        self.upsert_membership(
            organization_id,
            OrganizationMembershipCreate(
                user_id=payload.user_id,
                display_name=invitation.display_name,
                role=invitation.role,
                active=True,
            ),
            actor_id=actor_id,
        )
        self.add_audit(
            "invitation.accept",
            invitation.invitation_id,
            "Organization invitation accepted.",
            actor_id=actor_id,
        )
        return self.clone(invitation)

    def audit_break_glass_case_access(self, organization_id: str, case_id: str, *, actor_id: str) -> None:
        if case_id not in self.cases or self.cases[case_id].organization_id != organization_id:
            raise KeyError(case_id)
        self.add_audit(
            "break_glass.case_access",
            case_id,
            "Scoped break-glass case access granted.",
            actor_id=actor_id,
        )

    def assign_care_team_member(
        self,
        case_id: str,
        payload: CareTeamAssignmentCreate,
        *,
        actor_id: str,
    ) -> CareTeamAssignment:
        case = self.cases[case_id]
        existing = next(
            (
                assignment
                for assignment in self.care_team_assignments.values()
                if assignment.organization_id == case.organization_id
                and assignment.case_id == case_id
                and assignment.user_id == payload.user_id
            ),
            None,
        )
        if existing:
            existing.role = payload.role
            existing.active = payload.active
            assignment = existing
        else:
            assignment = CareTeamAssignment(
                assignment_id=new_id("team"),
                organization_id=case.organization_id,
                case_id=case_id,
                user_id=payload.user_id,
                role=payload.role,
                active=payload.active,
            )
            self.care_team_assignments[assignment.assignment_id] = assignment
        if payload.active and payload.user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, payload.user_id]
        if not payload.active and payload.user_id in case.care_team_user_ids:
            case.care_team_user_ids = [user_id for user_id in case.care_team_user_ids if user_id != payload.user_id]
        self.add_audit(
            "care_team.assign",
            assignment.assignment_id,
            "Case care-team assignment updated.",
            actor_id=actor_id,
        )
        return self.clone(assignment)

    def list_care_team_assignments(self, case_id: str) -> list[CareTeamAssignment]:
        assignments = [
            item
            for item in self.care_team_assignments.values()
            if item.case_id == case_id and item.active
        ]
        assignments.sort(key=lambda item: item.created_at)
        return [self.clone(item) for item in assignments]

    def create_session(self, case_id: str, payload: TherapySessionCreate, *, actor_id: str) -> TherapySession:
        case = self.cases[case_id]
        session = TherapySession(
            session_id=new_id("session"),
            case_id=case_id,
            organization_id=case.organization_id,
            **payload.model_dump(),
        )
        self.sessions[session.session_id] = session
        case.latest_session_date = session.session_date
        case.latest_session_status = session.status
        self.add_audit("session.create", session.session_id, "Session created.", actor_id=actor_id)
        return self.clone(session)

    def update_session(
        self,
        session_id: str,
        patch: TherapySessionUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> TherapySession:
        session = self.sessions[session_id]
        if expected_version is not None and session.version != expected_version:
            raise SessionVersionConflictError(
                f"Session {session_id} expected version {expected_version}, found {session.version}."
            )
        for key, value in patch.model_dump(exclude_unset=True).items():
            setattr(session, key, value)
        session.version += 1
        self.add_audit("session.patch", session_id, "Session updated.", actor_id=actor_id)
        return self.clone(session)

    def create_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript:
        session = self.sessions[transcript.session_id]
        session.feature_set_id = None
        session.ml_result_id = None
        session.ai_review_id = None
        session.report_id = None
        transcript.organization_id = session.organization_id
        self.transcripts[transcript.transcript_id] = transcript
        session.transcript_id = transcript.transcript_id
        session.status = session_status
        self.add_audit(audit_action, transcript.transcript_id, audit_message, actor_id=actor_id)
        return self.clone(transcript)

    def update_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript:
        current = self.transcripts[transcript.transcript_id]
        if expected_version is not None:
            if current is transcript:
                if transcript.version not in {expected_version, expected_version + 1}:
                    raise TranscriptVersionConflictError(
                        f"Transcript {transcript.transcript_id} expected version {expected_version}."
                    )
            elif current.version != expected_version:
                raise TranscriptVersionConflictError(
                    f"Transcript {transcript.transcript_id} expected version {expected_version}, found {current.version}."
                )
        session = self.sessions[transcript.session_id]
        session.feature_set_id = None
        session.ml_result_id = None
        session.ai_review_id = None
        session.report_id = None
        session.status = session_status
        transcript.organization_id = session.organization_id
        self.transcripts[transcript.transcript_id] = transcript
        self.add_audit(audit_action, transcript.transcript_id, audit_message, actor_id=actor_id)
        return self.clone(transcript)

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        report.organization_id = self.cases[report.case_id].organization_id
        self.reports[report.report_id] = report
        self.sessions[report.session_id].report_id = report.report_id
        self.cases[report.case_id].latest_report_status = report.status
        self.add_audit(audit_action, report.report_id, audit_message, actor_id=actor_id)
        return self.clone(report)

    def update_report(
        self,
        report: Report,
        *,
        expected_version: int | None,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        current = self.reports[report.report_id]
        if expected_version is not None:
            if current is report:
                if report.version not in {expected_version, expected_version + 1}:
                    raise ReportVersionConflictError(f"Report {report.report_id} expected version {expected_version}.")
            elif current.version != expected_version:
                raise ReportVersionConflictError(
                    f"Report {report.report_id} expected version {expected_version}, found {current.version}."
                )
        report.organization_id = self.cases[report.case_id].organization_id
        self.reports[report.report_id] = report
        self.cases[report.case_id].latest_report_status = report.status
        self.add_audit(audit_action, report.report_id, audit_message, actor_id=actor_id)
        return self.clone(report)

    def create_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        goal.organization_id = self.cases[goal.case_id].organization_id
        self.therapy_goals[goal.goal_id] = goal
        self.add_audit(audit_action, goal.goal_id, audit_message, actor_id=actor_id)
        return self.clone(goal)

    def update_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        goal.organization_id = self.cases[goal.case_id].organization_id
        self.therapy_goals[goal.goal_id] = goal
        self.add_audit(audit_action, goal.goal_id, audit_message, actor_id=actor_id)
        return self.clone(goal)

    def create_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        operation.organization_id = self.cases[operation.case_id].organization_id
        self.privacy_operations[operation.privacy_operation_id] = operation
        self.add_audit(audit_action, operation.privacy_operation_id, audit_message, actor_id=actor_id)
        return self.clone(operation)

    def update_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        operation.organization_id = self.cases[operation.case_id].organization_id
        self.privacy_operations[operation.privacy_operation_id] = operation
        self.add_audit(audit_action, operation.privacy_operation_id, audit_message, actor_id=actor_id)
        return self.clone(operation)

    def create_feature_set(
        self,
        feature_set: FeatureSet,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> FeatureSet:
        feature_set.organization_id = self.sessions[feature_set.session_id].organization_id
        self.features[feature_set.feature_set_id] = feature_set
        session = self.sessions[feature_set.session_id]
        session.feature_set_id = feature_set.feature_set_id
        session.ml_result_id = None
        self.add_audit(audit_action, feature_set.feature_set_id, audit_message, actor_id=actor_id)
        return self.clone(feature_set)

    def create_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        review.organization_id = self.sessions[review.session_id].organization_id
        self.ai_reviews[review.ai_review_id] = review
        self.sessions[review.session_id].ai_review_id = review.ai_review_id
        self.cases[self.sessions[review.session_id].case_id].review_priority = review.review_priority
        self.add_audit(audit_action, review.ai_review_id, audit_message, actor_id=actor_id)
        return self.clone(review)

    def update_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        review.organization_id = self.sessions[review.session_id].organization_id
        self.ai_reviews[review.ai_review_id] = review
        self.add_audit(audit_action, review.ai_review_id, audit_message, actor_id=actor_id)
        return self.clone(review)

    def create_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        result.organization_id = self.sessions[result.session_id].organization_id
        self.ml_results[result.result_id] = result
        self.sessions[result.session_id].ml_result_id = result.result_id
        self.add_audit(audit_action, result.result_id, audit_message, actor_id=actor_id)
        return self.clone(result)

    def update_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        result.organization_id = self.sessions[result.session_id].organization_id
        self.ml_results[result.result_id] = result
        self.add_audit(audit_action, result.result_id, audit_message, actor_id=actor_id)
        return self.clone(result)

    def snapshot(self) -> dict:
        return {
            "cases": {key: value.model_dump(mode="json") for key, value in self.cases.items()},
            "sessions": {key: value.model_dump(mode="json") for key, value in self.sessions.items()},
            "transcripts": {key: value.model_dump(mode="json") for key, value in self.transcripts.items()},
            "features": {key: value.model_dump(mode="json") for key, value in self.features.items()},
            "ml_results": {key: value.model_dump(mode="json") for key, value in self.ml_results.items()},
            "ai_reviews": {key: value.model_dump(mode="json") for key, value in self.ai_reviews.items()},
            "reports": {key: value.model_dump(mode="json") for key, value in self.reports.items()},
            "memberships": {key: value.model_dump(mode="json") for key, value in self.memberships.items()},
            "invitations": {key: value.model_dump(mode="json") for key, value in self.invitations.items()},
            "care_team_assignments": {
                key: value.model_dump(mode="json") for key, value in self.care_team_assignments.items()
            },
            "therapy_goals": {key: value.model_dump(mode="json") for key, value in self.therapy_goals.items()},
            "audio_files": {key: value.model_dump(mode="json") for key, value in self.audio_files.items()},
            "jobs": {key: value.model_dump(mode="json") for key, value in self.jobs.items()},
            "privacy_operations": {key: value.model_dump(mode="json") for key, value in self.privacy_operations.items()},
            "audit_log": self.audit_log,
        }


class JsonFileRepository(MockRepository):
    """Durable local demo repository stored as JSON outside browser storage."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        super().__init__()
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.save()
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.cases = {key: ChildCase.model_validate(value) for key, value in data.get("cases", {}).items()}
        self.sessions = {key: TherapySession.model_validate(value) for key, value in data.get("sessions", {}).items()}
        self.transcripts = {key: Transcript.model_validate(value) for key, value in data.get("transcripts", {}).items()}
        self.features = {key: FeatureSet.model_validate(value) for key, value in data.get("features", {}).items()}
        self.ml_results = {key: MLResult.model_validate(value) for key, value in data.get("ml_results", {}).items()}
        self.ai_reviews = {key: AiReview.model_validate(value) for key, value in data.get("ai_reviews", {}).items()}
        self.reports = {key: Report.model_validate(value) for key, value in data.get("reports", {}).items()}
        self.memberships = {
            key: OrganizationMembership.model_validate(value)
            for key, value in data.get("memberships", {}).items()
        }
        self.invitations = {
            key: OrganizationInvitation.model_validate(value)
            for key, value in data.get("invitations", {}).items()
        }
        self.care_team_assignments = {
            key: CareTeamAssignment.model_validate(value)
            for key, value in data.get("care_team_assignments", {}).items()
        }
        self.therapy_goals = {key: TherapyGoal.model_validate(value) for key, value in data.get("therapy_goals", {}).items()}
        self.audio_files = {key: AudioFileMetadata.model_validate(value) for key, value in data.get("audio_files", {}).items()}
        self.jobs = {key: ProcessingJob.model_validate(value) for key, value in data.get("jobs", {}).items()}
        self.privacy_operations = {key: PrivacyOperation.model_validate(value) for key, value in data.get("privacy_operations", {}).items()}
        self.audit_log = list(data.get("audit_log", []))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")

    def add_audit(
        self,
        action: str,
        target_id: str,
        message: str,
        *,
        actor_id: str = "system",
        outcome: str = "success",
        correlation_id: str = "local",
    ) -> None:
        super().add_audit(
            action,
            target_id,
            message,
            actor_id=actor_id,
            outcome=outcome,
            correlation_id=correlation_id,
        )
        self.save()
