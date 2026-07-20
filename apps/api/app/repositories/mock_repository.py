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

INVITATION_EXPIRY_DAYS = 7


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
        self.organization_settings: dict[str, dict[str, object]] = {}
        self.audit_log: list[dict] = []
        self.seed()

    def seed(self) -> None:
        if self.cases:
            return
        case = ChildCase(
            case_id="case_demo_001",
            organization_id="pilot_org_001",
            care_team_user_ids=["therapist-demo"],
            primary_therapist_user_id="therapist-demo",
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
        self.organization_settings.setdefault(case.organization_id, {"ai_review_enabled": True})

    def clone(self, value):
        return deepcopy(value)

    def is_ai_review_enabled(self, organization_id: str) -> bool:
        settings = self.organization_settings.get(organization_id, {})
        return bool(settings.get("ai_review_enabled", False))

    def set_ai_review_enabled(self, organization_id: str, enabled: bool) -> None:
        settings = dict(self.organization_settings.get(organization_id, {}))
        settings["ai_review_enabled"] = enabled
        self.organization_settings[organization_id] = settings

    def add_audit(
        self,
        action: str,
        target_id: str,
        message: str,
        *,
        actor_id: str = "system",
        outcome: str = "success",
        correlation_id: str = "local",
        organization_id: str | None = None,
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
        event_data["organization_id"] = organization_id or self._organization_for_target(target_id)
        self.audit_log.append(event_data)

    def has_active_org_admin_membership(self, user_id: str, organization_id: str) -> bool:
        return any(
            membership.user_id == user_id
            and membership.organization_id == organization_id
            and membership.role == "org_admin"
            and membership.active
            for membership in self.memberships.values()
        )

    def append_organization_admin_denial_audit(
        self,
        action: str,
        target_id: str,
        message: str,
        *,
        actor_id: str,
        outcome: str,
        correlation_id: str,
        organization_id: str,
    ) -> None:
        self.add_audit(
            action,
            target_id,
            message,
            actor_id=actor_id,
            outcome=outcome,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )

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
        if case.primary_therapist_user_id is None and actor_id != "system":
            case.primary_therapist_user_id = actor_id
        if case.primary_therapist_user_id and case.primary_therapist_user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, case.primary_therapist_user_id]
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
                assignment.is_primary = False
                if assignment.case_id in self.cases:
                    case = self.cases[assignment.case_id]
                    case.care_team_user_ids = [
                        user_id for user_id in case.care_team_user_ids if user_id != membership.user_id
                    ]
                    if case.primary_therapist_user_id == membership.user_id:
                        case.primary_therapist_user_id = None
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
        now = utc_now()
        invitation = OrganizationInvitation(
            invitation_id=new_id("inv"),
            organization_id=organization_id,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            invited_by=actor_id,
            expires_at=now + timedelta(days=INVITATION_EXPIRY_DAYS),
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
        if invitation.status == "accepted":
            raise ValueError("Invitation has already been accepted.")
        if invitation.status == "revoked":
            raise ValueError("Invitation has been revoked.")
        if invitation.expires_at <= now:
            invitation.status = "expired"
            self.add_audit(
                "invitation.accept",
                invitation.invitation_id,
                "Organization invitation acceptance failed.",
                actor_id=actor_id,
                outcome="denied",
            )
            raise ValueError("Expired invitations require a newly issued invitation.")
        for existing in self.invitations.values():
            if existing.invitation_id == invitation.invitation_id:
                continue
            if existing.email != invitation.email:
                continue
            if existing.accepted_user_id and existing.accepted_user_id != payload.user_id:
                self.add_audit(
                    "invitation.accept",
                    invitation.invitation_id,
                    "Organization invitation acceptance failed.",
                    actor_id=actor_id,
                    outcome="denied",
                )
                raise ValueError("Identity email is already bound to a different user.")
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
        if payload.is_primary and (not payload.active or payload.role != "therapist"):
            raise ValueError("Primary therapist assignment must be an active therapist.")
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
            existing.is_primary = payload.is_primary
            assignment = existing
        else:
            assignment = CareTeamAssignment(
                assignment_id=new_id("team"),
                organization_id=case.organization_id,
                case_id=case_id,
                user_id=payload.user_id,
                role=payload.role,
                active=payload.active,
                is_primary=payload.is_primary,
            )
            self.care_team_assignments[assignment.assignment_id] = assignment
        if payload.active and payload.user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, payload.user_id]
        if not payload.active and payload.user_id in case.care_team_user_ids:
            case.care_team_user_ids = [user_id for user_id in case.care_team_user_ids if user_id != payload.user_id]
        if payload.is_primary:
            for other in self.care_team_assignments.values():
                if other.case_id == case_id and other.assignment_id != assignment.assignment_id:
                    other.is_primary = False
            case.primary_therapist_user_id = payload.user_id
        elif case.primary_therapist_user_id == payload.user_id and (not payload.active or payload.role != "therapist"):
            case.primary_therapist_user_id = None
            assignment.is_primary = False
        self.add_audit(
            "care_team.assign",
            assignment.assignment_id,
            "Case care-team assignment updated.",
            actor_id=actor_id,
        )
        return self.clone(assignment)

    def list_care_team_assignments(self, case_id: str) -> list[CareTeamAssignment]:
        case = self.cases[case_id]
        assignments = [
            item.model_copy(update={"is_primary": item.user_id == case.primary_therapist_user_id})
            for item in self.care_team_assignments.values()
            if item.case_id == case_id and item.active
        ]
        assignments.sort(key=lambda item: (not item.is_primary, item.created_at))
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
        invalidated = self._mark_downstream_outputs_stale(session)
        transcript.organization_id = session.organization_id
        self.transcripts[transcript.transcript_id] = transcript
        session.transcript_id = transcript.transcript_id
        session.status = session_status
        self.add_audit(audit_action, transcript.transcript_id, audit_message, actor_id=actor_id)
        if invalidated:
            self.add_audit(
                "workflow.invalidate_downstream",
                transcript.transcript_id,
                "Derived workflow outputs marked stale after transcript change.",
                actor_id=actor_id,
            )
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
        invalidate_downstream: bool = True,
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
        invalidated = self._mark_downstream_outputs_stale(session) if invalidate_downstream else False
        session.status = session_status
        transcript.organization_id = session.organization_id
        self.transcripts[transcript.transcript_id] = transcript
        self.add_audit(audit_action, transcript.transcript_id, audit_message, actor_id=actor_id)
        if invalidated:
            self.add_audit(
                "workflow.invalidate_downstream",
                transcript.transcript_id,
                "Derived workflow outputs marked stale after transcript change.",
                actor_id=actor_id,
            )
        return self.clone(transcript)

    def _mark_downstream_outputs_stale(self, session: TherapySession) -> bool:
        invalidated = False
        feature_set = self.features.get(session.feature_set_id or "")
        if feature_set is not None and feature_set.review_status != ReviewStatus.stale:
            feature_set.review_status = ReviewStatus.stale
            invalidated = True
        ml_result = self.ml_results.get(session.ml_result_id or "")
        if ml_result is not None and ml_result.is_current:
            ml_result.is_current = False
            invalidated = True
        ai_review = self.ai_reviews.get(session.ai_review_id or "")
        if ai_review is not None and ai_review.therapist_review_status != ReviewStatus.stale:
            ai_review.therapist_review_status = ReviewStatus.stale
            invalidated = True
        report = self.reports.get(session.report_id or "")
        if report is not None and report.status not in {ReviewStatus.signed_off, ReviewStatus.stale}:
            report.status = ReviewStatus.stale
            report.version += 1
            report.updated_at = utc_now()
            self.cases[session.case_id].latest_report_status = ReviewStatus.stale
            invalidated = True
        return invalidated

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        session = self.sessions[report.session_id]
        transcript = self.transcripts.get(report.transcript_id or "")
        expected_transcript_version = report.generated_from_versions.get("transcript_version")
        if report.transcript_id and (
            transcript is None
            or session.transcript_id != report.transcript_id
            or expected_transcript_version != str(transcript.version)
        ):
            raise ValueError("Transcript changed during report generation; discard the stale draft and retry.")
        if report.feature_result_id and (
            session.feature_set_id != report.feature_result_id
            or report.feature_result_id not in self.features
            or self.features[report.feature_result_id].review_status == ReviewStatus.stale
            or transcript is None
            or self.features[report.feature_result_id].transcript_version != transcript.version
        ):
            raise ValueError("Findings changed during report generation; discard the stale draft and retry.")
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
        session = self.sessions[feature_set.session_id]
        transcript = self.transcripts.get(feature_set.transcript_id)
        if (
            transcript is None
            or session.transcript_id != feature_set.transcript_id
            or transcript.version != feature_set.transcript_version
        ):
            raise ValueError("Transcript changed during feature extraction; discard the stale result and retry.")
        feature_set.organization_id = session.organization_id
        self.features[feature_set.feature_set_id] = feature_set
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
        session = self.sessions[review.session_id]
        transcript = self.transcripts.get(session.transcript_id or "")
        feature_set = self.features.get(review.feature_set_id or "")
        if transcript is None or transcript.version != review.input_transcript_version:
            raise ValueError("Transcript changed during AI-assisted review generation; discard the stale result and retry.")
        if review.feature_set_id and (
            session.feature_set_id != review.feature_set_id
            or feature_set is None
            or feature_set.review_status == ReviewStatus.stale
            or feature_set.transcript_version != transcript.version
        ):
            raise ValueError("Findings changed during AI-assisted review generation; discard the stale result and retry.")
        review.organization_id = session.organization_id
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
        session = self.sessions[result.session_id]
        transcript = self.transcripts.get(result.transcript_id)
        feature_set = self.features.get(result.feature_result_id)
        if (
            transcript is None
            or session.transcript_id != result.transcript_id
            or session.feature_set_id != result.feature_result_id
            or feature_set is None
            or feature_set.review_status == ReviewStatus.stale
            or feature_set.transcript_id != transcript.transcript_id
            or feature_set.transcript_version != transcript.version
        ):
            raise ValueError("Transcript or findings changed during ML review generation; discard the stale result and retry.")
        result.organization_id = session.organization_id
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
            "organization_settings": self.organization_settings,
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
        self.organization_settings = {
            key: dict(value) for key, value in data.get("organization_settings", {}).items()
        }
        self.organization_settings.setdefault("pilot_org_001", {"ai_review_enabled": True})
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
        organization_id: str | None = None,
    ) -> None:
        super().add_audit(
            action,
            target_id,
            message,
            actor_id=actor_id,
            outcome=outcome,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        self.save()
