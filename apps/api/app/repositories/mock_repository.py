from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from uuid import uuid4

from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    ArtifactStatus,
    CareTeamAssignment,
    CareTeamAssignmentCreate,
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    FindingsProjection,
    LimitationAcknowledgment,
    MappingStatus,
    MLResult,
    NormalizedAudioAsset,
    OrganizationMembership,
    OrganizationMembershipCreate,
    OrganizationInvitation,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    PrivacyOperation,
    ProcessingJob,
    QaDisposition,
    Report,
    ReviewedSpeakerMapping,
    ReviewStatus,
    RoundTripStatus,
    StalenessCause,
    TherapyGoal,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    TranscriptAttestation,
    ChatExport,
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
        self.normalized_audio_assets: dict[tuple[str, int], NormalizedAudioAsset] = {}
        self.speaker_mappings: dict[tuple[str, int], ReviewedSpeakerMapping] = {}
        self.limitation_acknowledgments: dict[tuple[str, int], LimitationAcknowledgment] = {}
        self.transcript_attestations: dict[tuple[str, int], TranscriptAttestation] = {}
        self.chat_exports: dict[tuple[str, int], ChatExport] = {}
        self.findings_results: dict[tuple[str, int], FindingsProjection] = {}
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
        previous_version = expected_version if expected_version is not None else current.version
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
        if invalidate_downstream and previous_version != transcript.version:
            self.mark_downstream_stale(
                transcript.transcript_id,
                [
                    StalenessCause(
                        code="TRANSCRIPT_VERSION_CHANGED",
                        affected_resource_id=transcript.transcript_id,
                        affected_resource_version=str(transcript.version),
                        validator_or_rule_version="speech-lineage-v1.7.0",
                    )
                ],
            )
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

    def _speech_pipeline_changed(self) -> None:
        """Persistence hook for durable repository implementations."""

    def _persist_speech_pipeline_mutation(self) -> None:
        """Publish an accepted in-memory speech mutation to durable storage."""
        self._speech_pipeline_changed()

    def _validate_speech_ownership(
        self,
        *,
        organization_id: str,
        session_id: str,
        transcript_id: str | None = None,
        audio_file_id: str | None = None,
    ) -> None:
        session = self.sessions.get(session_id)
        if session is None or session.organization_id != organization_id:
            raise KeyError(session_id)
        if transcript_id is not None:
            transcript = self.transcripts.get(transcript_id)
            if (
                transcript is None
                or transcript.organization_id != organization_id
                or transcript.session_id != session_id
            ):
                raise KeyError(transcript_id)
        if audio_file_id is not None:
            audio = self.audio_files.get(audio_file_id)
            if (
                audio is None
                or audio.organization_id != organization_id
                or audio.session_id != session_id
            ):
                raise KeyError(audio_file_id)

    @staticmethod
    def _reject_duplicate(store: dict, key: tuple[str, int]) -> None:
        if key in store:
            raise ValueError(f"Duplicate immutable version {key[0]} version {key[1]}.")

    def _validate_transcript_version(self, transcript_id: str, transcript_version: int) -> Transcript:
        transcript = self.transcripts[transcript_id]
        if transcript.version != transcript_version:
            raise ValueError(
                f"Expected current transcript version {transcript.version}, "
                f"received transcript version {transcript_version}."
            )
        return transcript

    def _validate_acknowledgment_refs(
        self,
        transcript_id: str,
        transcript_version: int,
        refs: list[tuple[str, int]],
        *,
        validator_version: str | None = None,
    ) -> None:
        for acknowledgment_id, acknowledgment_version in refs:
            acknowledgment = self.limitation_acknowledgments.get(
                (acknowledgment_id, acknowledgment_version)
            )
            if acknowledgment is None:
                raise KeyError(f"acknowledgment {acknowledgment_id} version {acknowledgment_version}")
            if (
                acknowledgment.status is not ArtifactStatus.current
                or acknowledgment.transcript_id != transcript_id
                or acknowledgment.transcript_version != transcript_version
                or acknowledgment.disposition
                is not QaDisposition.acknowledgeable_limitation
            ):
                raise ValueError(
                    f"acknowledgment {acknowledgment_id} version {acknowledgment_version} "
                    "is not a current acknowledgeable_limitation for the exact transcript version."
                )
            if validator_version and acknowledgment.validator_version != validator_version:
                raise ValueError(
                    f"acknowledgment {acknowledgment_id} validator version "
                    f"{acknowledgment.validator_version} does not match {validator_version}."
                )

    def _require_current_mapping(
        self,
        transcript_id: str,
        transcript_version: int,
        mapping_id: str,
        mapping_version: int,
    ) -> ReviewedSpeakerMapping:
        mapping = self.speaker_mappings.get((mapping_id, mapping_version))
        if (
            mapping is None
            or mapping.transcript_id != transcript_id
            or mapping.status is not MappingStatus.confirmed
        ):
            raise KeyError(f"current mapping {mapping_id} version {mapping_version}")
        current = self.get_current_speaker_mapping(transcript_id)
        if (
            current is None
            or current.mapping_id != mapping_id
            or current.mapping_version != mapping_version
        ):
            raise ValueError(
                f"mapping {mapping_id} version {mapping_version} is not the current confirmed mapping."
            )
        if mapping.transcript_version != transcript_version:
            raise ValueError(
                f"mapping {mapping_id} transcript version {mapping.transcript_version} "
                f"does not match transcript version {transcript_version}."
            )
        return mapping

    def _require_current_attestation(
        self,
        transcript_id: str,
        transcript_version: int,
        attestation_id: str,
        attestation_version: int,
    ) -> TranscriptAttestation:
        attestation = self.transcript_attestations.get((attestation_id, attestation_version))
        if (
            attestation is None
            or attestation.transcript_id != transcript_id
        ):
            raise KeyError(f"current attestation {attestation_id} version {attestation_version}")
        if attestation.transcript_version != transcript_version:
            raise ValueError(
                f"attestation {attestation_id} transcript version {attestation.transcript_version} "
                f"does not match transcript version {transcript_version}."
            )
        if attestation.status is not ArtifactStatus.current:
            raise KeyError(f"current attestation {attestation_id} version {attestation_version}")
        current = self.get_current_transcript_attestation(transcript_id)
        if (
            current is None
            or current.attestation_id != attestation_id
            or current.attestation_version != attestation_version
        ):
            raise ValueError(
                f"attestation {attestation_id} version {attestation_version} is not current."
            )
        return attestation

    def _require_current_chat_export(
        self,
        transcript_id: str,
        transcript_version: int,
        export_id: str,
        export_version: int,
    ) -> ChatExport:
        export = self.chat_exports.get((export_id, export_version))
        if (
            export is None
            or export.transcript_id != transcript_id
        ):
            raise KeyError(f"current CHAT export {export_id} version {export_version}")
        if export.transcript_version != transcript_version:
            raise ValueError(
                f"CHAT export {export_id} transcript version {export.transcript_version} "
                f"does not match transcript version {transcript_version}."
            )
        if export.status is not ArtifactStatus.current:
            raise KeyError(f"current CHAT export {export_id} version {export_version}")
        current = self.get_current_chat_export(transcript_id)
        if (
            current is None
            or current.export_id != export_id
            or current.export_version != export_version
        ):
            raise ValueError(f"CHAT export {export_id} version {export_version} is not current.")
        if export.round_trip.status is not RoundTripStatus.verified:
            raise ValueError(f"CHAT export {export_id} does not have verified round-trip status.")
        return export

    def complete_audio_upload(
        self,
        audio_file_id: str,
        *,
        checksum_sha256: str,
        size_bytes: int,
        uploaded_at,
        actor_id: str = "system",
    ) -> AudioFileMetadata:
        audio_file = self.audio_files.get(audio_file_id)
        if audio_file is None:
            raise ValueError("Audio file not found.")
        if not audio_file.retained:
            raise ValueError("Audio file is no longer retained.")
        if audio_file.upload_status != "pending_verification":
            raise ValueError(
                "Audio upload must be re-issued with a new upload intent "
                "before completion verification."
            )
        audio_file.size_bytes = size_bytes
        audio_file.checksum_sha256 = checksum_sha256
        audio_file.uploaded_at = uploaded_at
        audio_file.upload_status = "uploaded"
        self.add_audit(
            "audio.upload_complete",
            audio_file.audio_file_id,
            "Audio upload bytes verified and marked complete.",
            actor_id=actor_id,
            organization_id=audio_file.organization_id,
        )
        return self.clone(audio_file)

    def has_durable_normalized_audio_reference(
        self,
        *,
        source_audio_file_id: str,
        asset_version: int,
        object_key: str,
        normalized_checksum_sha256: str,
    ) -> bool:
        record = self.normalized_audio_assets.get(
            (source_audio_file_id, asset_version)
        )
        return bool(
            record is not None
            and record.object_key == object_key
            and record.normalized_checksum_sha256 == normalized_checksum_sha256
        )

    def create_normalized_audio_asset(self, record: NormalizedAudioAsset) -> NormalizedAudioAsset:
        self._validate_speech_ownership(
            organization_id=record.organization_id,
            session_id=record.session_id,
            audio_file_id=record.source_audio_file_id,
        )
        audio = self.audio_files[record.source_audio_file_id]
        if audio.source_asset_version != record.source_asset_version:
            raise ValueError(
                f"source asset version {record.source_asset_version} does not match "
                f"audio source version {audio.source_asset_version}."
            )
        if audio.checksum_sha256 != record.source_checksum_sha256:
            raise ValueError("source checksum does not match the source audio record.")
        key = (record.source_audio_file_id, record.asset_version)
        self._reject_duplicate(self.normalized_audio_assets, key)
        stored = record
        current = next(
            (
                item
                for item in self.normalized_audio_assets.values()
                if item.source_audio_file_id == record.source_audio_file_id
                and item.status is ArtifactStatus.current
            ),
            None,
        )
        if record.status is ArtifactStatus.current:
            if current is not None and record.asset_version <= current.asset_version:
                stored = record.model_copy(update={"status": ArtifactStatus.stale})
            else:
                for existing_key, existing in list(self.normalized_audio_assets.items()):
                    if (
                        existing.source_audio_file_id == record.source_audio_file_id
                        and existing.status is ArtifactStatus.current
                    ):
                        self.normalized_audio_assets[existing_key] = existing.model_copy(
                            update={"status": ArtifactStatus.stale}
                        )
                audio.current_normalized_asset_version = record.asset_version
                audio.current_normalized_checksum_sha256 = record.normalized_checksum_sha256
                if record.provenance is not None:
                    audio.duration_seconds = (
                        record.provenance.source_frame_count
                        / record.provenance.source_sample_rate_hz
                    )
                    audio.sample_rate_hz = (
                        record.provenance.source_sample_rate_hz
                    )
                    audio.channels = record.provenance.source_channels
        self.normalized_audio_assets[key] = stored
        if (
            current is not None
            and stored.status is ArtifactStatus.current
            and stored.asset_version > current.asset_version
        ):
            transcript_id = self.sessions[record.session_id].transcript_id
            if transcript_id is not None:
                self._apply_upstream_replacement_invalidation(
                    transcript_id,
                    replacement_kind="normalization",
                    resource_id=record.source_audio_file_id,
                    resource_version=record.asset_version,
                )
        self._persist_speech_pipeline_mutation()
        return self.clone(stored)

    def get_current_normalized_audio_asset(self, audio_file_id: str) -> NormalizedAudioAsset | None:
        if audio_file_id not in self.audio_files:
            raise KeyError(audio_file_id)
        matches = [
            item
            for item in self.normalized_audio_assets.values()
            if item.source_audio_file_id == audio_file_id and item.status is ArtifactStatus.current
        ]
        return self.clone(max(matches, key=lambda item: item.asset_version)) if matches else None

    def create_speaker_mapping(self, record: ReviewedSpeakerMapping) -> ReviewedSpeakerMapping:
        self._validate_speech_ownership(
            organization_id=record.organization_id,
            session_id=record.session_id,
            transcript_id=record.transcript_id,
        )
        self._validate_transcript_version(record.transcript_id, record.transcript_version)
        key = (record.mapping_id, record.mapping_version)
        self._reject_duplicate(self.speaker_mappings, key)
        stored = record
        current = None
        if record.status is MappingStatus.confirmed:
            current = self.get_current_speaker_mapping(record.transcript_id)
            if current is not None and record.mapping_version <= current.mapping_version:
                stored = record.model_copy(update={"status": MappingStatus.stale})
            else:
                for existing_key, existing in list(self.speaker_mappings.items()):
                    if (
                        existing.transcript_id == record.transcript_id
                        and existing.status is MappingStatus.confirmed
                    ):
                        self.speaker_mappings[existing_key] = existing.model_copy(
                            update={"status": MappingStatus.stale}
                        )
        self.speaker_mappings[key] = stored
        if (
            record.status is MappingStatus.confirmed
            and current is not None
            and stored.status is MappingStatus.confirmed
            and stored.mapping_version > current.mapping_version
        ):
            self._apply_upstream_replacement_invalidation(
                record.transcript_id,
                replacement_kind="mapping",
                resource_id=record.mapping_id,
                resource_version=record.mapping_version,
            )
        self._persist_speech_pipeline_mutation()
        return self.clone(stored)

    def get_current_speaker_mapping(self, transcript_id: str) -> ReviewedSpeakerMapping | None:
        if transcript_id not in self.transcripts:
            raise KeyError(transcript_id)
        matches = [
            item
            for item in self.speaker_mappings.values()
            if item.transcript_id == transcript_id and item.status is MappingStatus.confirmed
        ]
        return self.clone(max(matches, key=lambda item: item.mapping_version)) if matches else None

    def list_speaker_mapping_history(self, transcript_id: str) -> list[ReviewedSpeakerMapping]:
        if transcript_id not in self.transcripts:
            raise KeyError(transcript_id)
        return [
            self.clone(item)
            for item in sorted(
                (item for item in self.speaker_mappings.values() if item.transcript_id == transcript_id),
                key=lambda item: (item.mapping_id, item.mapping_version),
            )
        ]

    def create_limitation_acknowledgment(
        self,
        record: LimitationAcknowledgment,
    ) -> LimitationAcknowledgment:
        if record.disposition is not QaDisposition.acknowledgeable_limitation:
            raise ValueError(
                "limitation acknowledgments require acknowledgeable_limitation disposition"
            )
        self._validate_speech_ownership(
            organization_id=record.organization_id,
            session_id=record.session_id,
            transcript_id=record.transcript_id,
        )
        self._validate_transcript_version(record.transcript_id, record.transcript_version)
        if (
            record.affected_resource_id == record.transcript_id
            and record.affected_resource_version != str(record.transcript_version)
        ):
            raise ValueError("acknowledgment affected resource version does not match transcript version.")
        key = (record.acknowledgment_id, record.acknowledgment_version)
        self._reject_duplicate(self.limitation_acknowledgments, key)
        stored = record
        current = max(
            (
                item
                for item in self.limitation_acknowledgments.values()
                if item.acknowledgment_id == record.acknowledgment_id
                and item.status is ArtifactStatus.current
            ),
            key=lambda item: item.acknowledgment_version,
            default=None,
        )
        if record.status is ArtifactStatus.current:
            if current is not None and record.acknowledgment_version <= current.acknowledgment_version:
                stored = record.model_copy(update={"status": ArtifactStatus.stale})
            else:
                for existing_key, existing in list(self.limitation_acknowledgments.items()):
                    if (
                        existing.acknowledgment_id == record.acknowledgment_id
                        and existing.status is ArtifactStatus.current
                    ):
                        self.limitation_acknowledgments[existing_key] = existing.model_copy(
                            update={"status": ArtifactStatus.stale}
                        )
        self.limitation_acknowledgments[key] = stored
        if (
            current is not None
            and stored.status is ArtifactStatus.current
            and stored.acknowledgment_version > current.acknowledgment_version
        ):
            self._apply_upstream_replacement_invalidation(
                record.transcript_id,
                replacement_kind="acknowledgment",
                resource_id=record.acknowledgment_id,
                resource_version=record.acknowledgment_version,
            )
        self._persist_speech_pipeline_mutation()
        return self.clone(stored)

    def list_current_acknowledgments(self, transcript_id: str) -> list[LimitationAcknowledgment]:
        if transcript_id not in self.transcripts:
            raise KeyError(transcript_id)
        return [
            self.clone(item)
            for item in sorted(
                (
                    item
                    for item in self.limitation_acknowledgments.values()
                    if item.transcript_id == transcript_id and item.status is ArtifactStatus.current
                ),
                key=lambda item: (item.acknowledgment_id, item.acknowledgment_version),
            )
        ]

    def create_transcript_attestation(self, record: TranscriptAttestation) -> TranscriptAttestation:
        self._validate_speech_ownership(
            organization_id=record.organization_id,
            session_id=record.session_id,
            transcript_id=record.transcript_id,
        )
        self._validate_transcript_version(record.transcript_id, record.transcript_version)
        self._require_current_mapping(
            record.transcript_id,
            record.transcript_version,
            record.speaker_mapping_id,
            record.speaker_mapping_version,
        )
        self._validate_acknowledgment_refs(
            record.transcript_id,
            record.transcript_version,
            record.acknowledgment_refs,
            validator_version=record.qa_validator_version,
        )
        key = (record.attestation_id, record.attestation_version)
        self._reject_duplicate(self.transcript_attestations, key)
        stored = record
        current = None
        if record.status is ArtifactStatus.current:
            current = self.get_current_transcript_attestation(record.transcript_id)
            if current is not None and record.attestation_version <= current.attestation_version:
                stored = record.model_copy(update={"status": ArtifactStatus.stale})
            else:
                self._stale_current_artifacts(self.transcript_attestations, record.transcript_id)
        self.transcript_attestations[key] = stored
        if (
            current is not None
            and stored.status is ArtifactStatus.current
            and stored.attestation_version > current.attestation_version
        ):
            self._apply_upstream_replacement_invalidation(
                record.transcript_id,
                replacement_kind="attestation",
                resource_id=record.attestation_id,
                resource_version=record.attestation_version,
            )
        self._persist_speech_pipeline_mutation()
        return self.clone(stored)

    def get_current_transcript_attestation(self, transcript_id: str) -> TranscriptAttestation | None:
        return self._get_current_transcript_artifact(
            self.transcript_attestations,
            transcript_id,
            "attestation_version",
        )

    def create_chat_export(self, record: ChatExport) -> ChatExport:
        self._validate_speech_ownership(
            organization_id=record.organization_id,
            session_id=record.session_id,
            transcript_id=record.transcript_id,
        )
        self._validate_transcript_version(record.transcript_id, record.transcript_version)
        mapping = self._require_current_mapping(
            record.transcript_id,
            record.transcript_version,
            record.speaker_mapping_id,
            record.speaker_mapping_version,
        )
        attestation = self._require_current_attestation(
            record.transcript_id,
            record.transcript_version,
            record.attestation_id,
            record.attestation_version,
        )
        if (
            attestation.speaker_mapping_id != mapping.mapping_id
            or attestation.speaker_mapping_version != mapping.mapping_version
        ):
            raise ValueError("attestation mapping relation does not match CHAT export lineage.")
        if (
            record.round_trip.parser_version != record.parser_version
            or record.round_trip.serializer_version != record.serializer_version
            or record.round_trip.subset_version != record.subset_version
        ):
            raise ValueError("CHAT round-trip parser/serializer/subset versions do not match export.")
        if record.status is ArtifactStatus.current and record.round_trip.status is not RoundTripStatus.verified:
            raise ValueError("current CHAT exports require verified round-trip status.")
        if record.round_trip.status is RoundTripStatus.verified:
            if (
                record.round_trip.input_semantic_checksum_sha256
                != record.round_trip.output_semantic_checksum_sha256
            ):
                raise ValueError("verified CHAT semantic checksum values must match.")
            if (
                record.canonical_checksum_sha256
                != record.round_trip.deterministic_export_checksum_sha256
            ):
                raise ValueError("verified CHAT export checksum values must match.")
            if record.round_trip.errors:
                raise ValueError("verified CHAT exports cannot contain verification errors.")
        elif not record.round_trip.errors:
            raise ValueError("nonverified CHAT exports require structured errors.")
        audio = self.audio_files.get(record.source_audio_file_id)
        if audio is None:
            raise KeyError(record.source_audio_file_id)
        if (
            audio.source_asset_version != record.source_asset_version
            or audio.checksum_sha256 != record.source_checksum_sha256
        ):
            raise ValueError("CHAT source audio version/checksum mismatch.")
        normalized = self.get_current_normalized_audio_asset(record.source_audio_file_id)
        if (
            normalized is None
            or normalized.asset_version != record.normalized_asset_version
            or normalized.normalized_checksum_sha256 != record.normalized_checksum_sha256
        ):
            raise ValueError("CHAT normalized asset version/checksum mismatch.")
        if record.asr_provenance is not None:
            provenance = record.asr_provenance
            if (
                provenance.source_audio_file_id != record.source_audio_file_id
                or provenance.source_asset_version != record.source_asset_version
                or provenance.source_checksum_sha256 != record.source_checksum_sha256
                or provenance.normalized_asset_version != record.normalized_asset_version
                or provenance.normalized_checksum_sha256 != record.normalized_checksum_sha256
            ):
                raise ValueError("CHAT ASR provenance does not match export audio lineage.")
            audio = self.audio_files.get(provenance.source_audio_file_id)
            if audio is None:
                raise KeyError(provenance.source_audio_file_id)
            if (
                audio.source_asset_version != provenance.source_asset_version
                or audio.checksum_sha256 != provenance.source_checksum_sha256
            ):
                raise ValueError("CHAT ASR provenance source audio version/checksum mismatch.")
            normalized = self.get_current_normalized_audio_asset(provenance.source_audio_file_id)
            if (
                normalized is None
                or normalized.asset_version != provenance.normalized_asset_version
                or normalized.normalized_checksum_sha256 != provenance.normalized_checksum_sha256
            ):
                raise ValueError("CHAT ASR provenance normalized asset version/checksum mismatch.")
        key = (record.export_id, record.export_version)
        self._reject_duplicate(self.chat_exports, key)
        stored = record
        current = None
        if record.status is ArtifactStatus.current:
            current = self.get_current_chat_export(record.transcript_id)
            if current is not None and record.export_version <= current.export_version:
                stored = record.model_copy(update={"status": ArtifactStatus.stale})
            else:
                self._stale_current_artifacts(self.chat_exports, record.transcript_id)
        self.chat_exports[key] = stored
        if (
            current is not None
            and stored.status is ArtifactStatus.current
            and stored.export_version > current.export_version
        ):
            self._apply_upstream_replacement_invalidation(
                record.transcript_id,
                replacement_kind="chat",
                resource_id=record.export_id,
                resource_version=record.export_version,
            )
        self._persist_speech_pipeline_mutation()
        return self.clone(stored)

    def get_current_chat_export(self, transcript_id: str) -> ChatExport | None:
        return self._get_current_transcript_artifact(
            self.chat_exports,
            transcript_id,
            "export_version",
        )

    def create_findings_result(self, record: FindingsProjection) -> FindingsProjection:
        self._validate_speech_ownership(
            organization_id=record.organization_id,
            session_id=record.session_id,
            transcript_id=record.transcript_id,
            audio_file_id=record.source_audio_file_id,
        )
        self._validate_transcript_version(record.transcript_id, record.transcript_version)
        mapping = self._require_current_mapping(
            record.transcript_id,
            record.transcript_version,
            record.speaker_mapping_id,
            record.speaker_mapping_version,
        )
        attestation = self._require_current_attestation(
            record.transcript_id,
            record.transcript_version,
            record.attestation_id,
            record.attestation_version,
        )
        export = self._require_current_chat_export(
            record.transcript_id,
            record.transcript_version,
            record.chat_export_id,
            record.chat_export_version,
        )
        if (
            export.canonical_checksum_sha256 != record.chat_export_checksum_sha256
            or export.parser_version != record.parser_version
            or export.serializer_version != record.serializer_version
        ):
            raise ValueError("Findings CHAT export checksum/parser/serializer lineage mismatch.")
        if (
            export.source_audio_file_id != record.source_audio_file_id
            or export.source_asset_version != record.source_asset_version
            or export.source_checksum_sha256 != record.source_checksum_sha256
        ):
            raise ValueError("Findings source audio lineage does not match the current CHAT export.")
        if export.normalized_asset_version != record.normalized_asset_version:
            raise ValueError("Findings normalized asset version does not match the current CHAT export.")
        if export.normalized_checksum_sha256 != record.normalized_checksum_sha256:
            raise ValueError("Findings normalized checksum does not match the current CHAT export.")
        if (
            export.speaker_mapping_id != mapping.mapping_id
            or export.speaker_mapping_version != mapping.mapping_version
            or export.attestation_id != attestation.attestation_id
            or export.attestation_version != attestation.attestation_version
        ):
            raise ValueError("Findings mapping/attestation relation does not match CHAT export.")
        audio = self.audio_files[record.source_audio_file_id]
        if (
            audio.source_asset_version != record.source_asset_version
            or audio.checksum_sha256 != record.source_checksum_sha256
        ):
            raise ValueError("Findings source audio version/checksum mismatch.")
        normalized = self.get_current_normalized_audio_asset(record.source_audio_file_id)
        if normalized is None or normalized.asset_version != record.normalized_asset_version:
            raise ValueError("Findings normalized asset version does not match current lineage.")
        if normalized.normalized_checksum_sha256 != record.normalized_checksum_sha256:
            raise ValueError("Findings normalized checksum does not match current lineage.")
        self._validate_acknowledgment_refs(
            record.transcript_id,
            record.transcript_version,
            record.acknowledgment_refs,
            validator_version=attestation.qa_validator_version,
        )
        if sorted(record.acknowledgment_refs) != sorted(attestation.acknowledgment_refs):
            raise ValueError("Findings acknowledgment refs do not match the current attestation.")
        for feature in record.features:
            expected_pairs = {
                "transcript version": (feature.transcript_version, record.transcript_version),
                "mapping ID": (feature.speaker_mapping_id, record.speaker_mapping_id),
                "mapping version": (feature.speaker_mapping_version, record.speaker_mapping_version),
                "source audio ID": (feature.source_audio_file_id, record.source_audio_file_id),
                "source audio version": (feature.source_asset_version, record.source_asset_version),
                "source checksum": (feature.source_checksum_sha256, record.source_checksum_sha256),
                "normalized version": (feature.normalized_asset_version, record.normalized_asset_version),
                "normalized checksum": (
                    feature.normalized_checksum_sha256,
                    record.normalized_checksum_sha256,
                ),
                "attestation ID": (feature.attestation_id, record.attestation_id),
                "attestation version": (feature.attestation_version, record.attestation_version),
                "CHAT export ID": (feature.chat_export_id, record.chat_export_id),
                "CHAT export version": (feature.chat_export_version, record.chat_export_version),
                "CHAT export checksum": (
                    feature.chat_export_checksum_sha256,
                    record.chat_export_checksum_sha256,
                ),
                "parser version": (feature.parser_version, record.parser_version),
                "serializer version": (feature.serializer_version, record.serializer_version),
                "algorithm version": (feature.algorithm_version, record.algorithm_version),
                "algorithm checksum": (
                    feature.algorithm_checksum_sha256,
                    record.algorithm_checksum_sha256,
                ),
            }
            for label, (actual, expected) in expected_pairs.items():
                if actual != expected:
                    raise ValueError(f"feature {feature.feature_id} {label} does not match Findings.")
            if feature.transcript_id != record.transcript_id:
                raise ValueError(f"feature {feature.feature_id} transcript ID does not match Findings.")
            if feature.tokenizer_profile != record.tokenizer_profile:
                raise ValueError(f"feature {feature.feature_id} tokenizer profile does not match Findings.")
        key = (record.findings_id, record.findings_version)
        self._reject_duplicate(self.findings_results, key)
        stored = record
        if record.status is ArtifactStatus.current:
            current = self.get_current_findings_result(record.transcript_id)
            if current is not None and record.findings_version <= current.findings_version:
                stored = record.model_copy(update={"status": ArtifactStatus.stale})
            else:
                self._stale_current_artifacts(self.findings_results, record.transcript_id)
        self.findings_results[key] = stored
        self._persist_speech_pipeline_mutation()
        return self.clone(stored)

    def get_current_findings_result(self, transcript_id: str) -> FindingsProjection | None:
        return self._get_current_transcript_artifact(
            self.findings_results,
            transcript_id,
            "findings_version",
        )

    def list_findings_history(self, transcript_id: str) -> list[FindingsProjection]:
        if transcript_id not in self.transcripts:
            raise KeyError(transcript_id)
        return [
            self.clone(item)
            for item in sorted(
                (item for item in self.findings_results.values() if item.transcript_id == transcript_id),
                key=lambda item: (item.findings_id, item.findings_version),
            )
        ]

    @staticmethod
    def _stale_current_artifacts(store: dict, transcript_id: str) -> None:
        for key, existing in list(store.items()):
            if existing.transcript_id == transcript_id and existing.status is ArtifactStatus.current:
                store[key] = existing.model_copy(update={"status": ArtifactStatus.stale})

    def _get_current_transcript_artifact(self, store: dict, transcript_id: str, version_field: str):
        if transcript_id not in self.transcripts:
            raise KeyError(transcript_id)
        matches = [
            item
            for item in store.values()
            if item.transcript_id == transcript_id and item.status is ArtifactStatus.current
        ]
        return self.clone(max(matches, key=lambda item: getattr(item, version_field))) if matches else None

    def _apply_upstream_replacement_invalidation(
        self,
        transcript_id: str,
        *,
        replacement_kind: str,
        resource_id: str,
        resource_version: int,
    ) -> None:
        cause = StalenessCause(
            code=f"{replacement_kind.upper()}_LINEAGE_CHANGED",
            affected_resource_id=resource_id,
            affected_resource_version=str(resource_version),
            validator_or_rule_version="speech-lineage-v1.7.0",
        )
        if replacement_kind == "normalization":
            for key, acknowledgment in list(self.limitation_acknowledgments.items()):
                if (
                    acknowledgment.transcript_id == transcript_id
                    and acknowledgment.status is ArtifactStatus.current
                ):
                    self.limitation_acknowledgments[key] = self._stale_speech_record(
                        acknowledgment,
                        cause,
                    )
            for key, attestation in list(self.transcript_attestations.items()):
                if (
                    attestation.transcript_id == transcript_id
                    and attestation.status is ArtifactStatus.current
                ):
                    self.transcript_attestations[key] = self._stale_speech_record(
                        attestation,
                        cause,
                    )
        self._enforce_speech_dependency_closure(transcript_id, cause)

    @staticmethod
    def _stale_speech_record(record, cause: StalenessCause):
        causes = list(record.stale_causes)
        if cause not in causes:
            causes.append(cause)
        return record.model_copy(
            update={"status": ArtifactStatus.stale, "stale_causes": causes}
        )

    def _acknowledgment_ref_is_current(
        self,
        transcript_id: str,
        transcript_version: int,
        acknowledgment_id: str,
        acknowledgment_version: int,
        validator_version: str,
    ) -> bool:
        acknowledgment = self.limitation_acknowledgments.get(
            (acknowledgment_id, acknowledgment_version)
        )
        return bool(
            acknowledgment is not None
            and acknowledgment.status is ArtifactStatus.current
            and acknowledgment.transcript_id == transcript_id
            and acknowledgment.transcript_version == transcript_version
            and acknowledgment.validator_version == validator_version
            and acknowledgment.disposition
            is QaDisposition.acknowledgeable_limitation
        )

    def _enforce_speech_dependency_closure(
        self,
        transcript_id: str,
        cause: StalenessCause,
    ) -> None:
        for key, attestation in list(self.transcript_attestations.items()):
            if (
                attestation.transcript_id != transcript_id
                or attestation.status is not ArtifactStatus.current
            ):
                continue
            mapping = self.speaker_mappings.get(
                (attestation.speaker_mapping_id, attestation.speaker_mapping_version)
            )
            acknowledgments_current = all(
                self._acknowledgment_ref_is_current(
                    transcript_id,
                    attestation.transcript_version,
                    acknowledgment_id,
                    acknowledgment_version,
                    attestation.qa_validator_version,
                )
                for acknowledgment_id, acknowledgment_version in attestation.acknowledgment_refs
            )
            if (
                mapping is None
                or mapping.status is not MappingStatus.confirmed
                or mapping.transcript_version != attestation.transcript_version
                or not acknowledgments_current
            ):
                self.transcript_attestations[key] = self._stale_speech_record(
                    attestation,
                    cause,
                )

        for key, export in list(self.chat_exports.items()):
            if export.transcript_id != transcript_id or export.status is not ArtifactStatus.current:
                continue
            mapping = self.speaker_mappings.get(
                (export.speaker_mapping_id, export.speaker_mapping_version)
            )
            attestation = self.transcript_attestations.get(
                (export.attestation_id, export.attestation_version)
            )
            normalized = self.normalized_audio_assets.get(
                (export.source_audio_file_id, export.normalized_asset_version)
            )
            if (
                mapping is None
                or mapping.status is not MappingStatus.confirmed
                or attestation is None
                or attestation.status is not ArtifactStatus.current
                or normalized is None
                or normalized.status is not ArtifactStatus.current
                or normalized.normalized_checksum_sha256
                != export.normalized_checksum_sha256
            ):
                self.chat_exports[key] = self._stale_speech_record(export, cause)

        for key, findings in list(self.findings_results.items()):
            if (
                findings.transcript_id != transcript_id
                or findings.status is not ArtifactStatus.current
            ):
                continue
            mapping = self.speaker_mappings.get(
                (findings.speaker_mapping_id, findings.speaker_mapping_version)
            )
            attestation = self.transcript_attestations.get(
                (findings.attestation_id, findings.attestation_version)
            )
            export = self.chat_exports.get(
                (findings.chat_export_id, findings.chat_export_version)
            )
            normalized = self.normalized_audio_assets.get(
                (findings.source_audio_file_id, findings.normalized_asset_version)
            )
            if (
                mapping is None
                or mapping.status is not MappingStatus.confirmed
                or attestation is None
                or attestation.status is not ArtifactStatus.current
                or export is None
                or export.status is not ArtifactStatus.current
                or normalized is None
                or normalized.status is not ArtifactStatus.current
                or normalized.normalized_checksum_sha256
                != findings.normalized_checksum_sha256
            ):
                self.findings_results[key] = self._stale_speech_record(
                    findings,
                    cause,
                )

    def mark_downstream_stale(
        self,
        transcript_id: str,
        causes: list[StalenessCause | dict[str, object]],
    ) -> None:
        if transcript_id not in self.transcripts:
            raise KeyError(transcript_id)
        structured_causes = [
            cause if isinstance(cause, StalenessCause) else StalenessCause.model_validate(cause)
            for cause in causes
        ]
        for key, mapping in list(self.speaker_mappings.items()):
            if mapping.transcript_id == transcript_id and mapping.status is MappingStatus.confirmed:
                self.speaker_mappings[key] = mapping.model_copy(
                    update={"status": MappingStatus.stale, "stale_causes": structured_causes}
                )
        for store in (
            self.transcript_attestations,
            self.limitation_acknowledgments,
            self.chat_exports,
        ):
            for key, record in list(store.items()):
                if record.transcript_id == transcript_id and record.status is ArtifactStatus.current:
                    store[key] = record.model_copy(
                        update={"status": ArtifactStatus.stale, "stale_causes": structured_causes}
                    )
        for key, findings in list(self.findings_results.items()):
            if findings.transcript_id != transcript_id or findings.status is not ArtifactStatus.current:
                continue
            self.findings_results[key] = findings.model_copy(
                update={
                    "status": ArtifactStatus.stale,
                    "stale_causes": structured_causes,
                }
            )
        self._persist_speech_pipeline_mutation()

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
            "normalized_audio_assets": [
                value.model_dump(mode="json") for value in self.normalized_audio_assets.values()
            ],
            "speaker_mappings": [
                value.model_dump(mode="json") for value in self.speaker_mappings.values()
            ],
            "limitation_acknowledgments": [
                value.model_dump(mode="json") for value in self.limitation_acknowledgments.values()
            ],
            "transcript_attestations": [
                value.model_dump(mode="json") for value in self.transcript_attestations.values()
            ],
            "chat_exports": [value.model_dump(mode="json") for value in self.chat_exports.values()],
            "findings_results": [
                value.model_dump(mode="json") for value in self.findings_results.values()
            ],
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
        normalized_assets = [
            NormalizedAudioAsset.model_validate(value)
            for value in data.get("normalized_audio_assets", [])
        ]
        self.normalized_audio_assets = {
            (item.source_audio_file_id, item.asset_version): item for item in normalized_assets
        }
        mappings = [
            ReviewedSpeakerMapping.model_validate(value)
            for value in data.get("speaker_mappings", [])
        ]
        self.speaker_mappings = {
            (item.mapping_id, item.mapping_version): item for item in mappings
        }
        acknowledgments = [
            LimitationAcknowledgment.model_validate(value)
            for value in data.get("limitation_acknowledgments", [])
        ]
        self.limitation_acknowledgments = {
            (item.acknowledgment_id, item.acknowledgment_version): item
            for item in acknowledgments
        }
        attestations = [
            TranscriptAttestation.model_validate(value)
            for value in data.get("transcript_attestations", [])
        ]
        self.transcript_attestations = {
            (item.attestation_id, item.attestation_version): item for item in attestations
        }
        exports = [ChatExport.model_validate(value) for value in data.get("chat_exports", [])]
        self.chat_exports = {(item.export_id, item.export_version): item for item in exports}
        findings = [
            FindingsProjection.model_validate(value)
            for value in data.get("findings_results", [])
        ]
        self.findings_results = {
            (item.findings_id, item.findings_version): item for item in findings
        }
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

    def _speech_pipeline_changed(self) -> None:
        self.save()

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
