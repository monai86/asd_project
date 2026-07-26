from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db.models import (
    AiReviewRecord,
    AudioFileRecord,
    AuditLogRecord,
    CaseCareTeamAssignmentRecord,
    Base,
    ChildCaseRecord,
    FeatureSetRecord,
    FindingsResultRecord,
    ChatExportRecord,
    LimitationAcknowledgmentRecord,
    MLResultRecord,
    NormalizedAudioAssetRecord,
    OrganizationInvitationRecord,
    OrganizationMembershipRecord,
    OrganizationRecord,
    OrganizationSettingsRecord,
    PrivacyOperationRecord,
    ProcessingJobRecord,
    ReportRecord,
    SessionRecord,
    SpeakerMappingRecord,
    TherapyGoalRecord,
    TranscriptRecord,
    TranscriptAttestationRecord,
    UserProfileRecord,
)
from app.repositories.base import (
    CaseVersionConflictError,
    ReportVersionConflictError,
    SessionVersionConflictError,
    TranscriptVersionConflictError,
)
from app.repositories.mock_repository import MockRepository, new_id
from app.schemas.clinical import (
    AiReview,
    AudioFileMetadata,
    ChatExport,
    CareTeamAssignment,
    CareTeamAssignmentCreate,
    ChildCase,
    ChildCaseCreate,
    ChildCaseUpdate,
    FeatureSet,
    FindingsProjection,
    LimitationAcknowledgment,
    MLResult,
    OrganizationMembership,
    OrganizationMembershipCreate,
    OrganizationInvitation,
    OrganizationInvitationAccept,
    OrganizationInvitationCreate,
    PrivacyOperation,
    ProcessingJob,
    NormalizedAudioAsset,
    Report,
    ReviewStatus,
    ReviewedSpeakerMapping,
    TherapyGoal,
    TherapySession,
    TherapySessionCreate,
    TherapySessionUpdate,
    Transcript,
    TranscriptAttestation,
    utc_now,
)
from app.services.audit_safety import validate_audit_event


class SqlAlchemyRepository(MockRepository):
    """SQLAlchemy-backed local/pilot scaffold using the v2 service contract.

    Services currently mutate repository dictionaries. This adapter loads SQL
    rows into those dictionaries and persists the current snapshot after audit
    events, allowing the API contract to move toward a real SQL repository
    without changing every route at once.
    """

    def __init__(self, database_url: str, *, create_schema: bool = True) -> None:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("SQLAlchemy repository mode requires sqlalchemy to be installed.") from exc

        self.database_url = database_url
        self.engine = create_engine(database_url)
        if create_schema:
            Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        super().__init__()
        self.load()

    def _refresh_speech_pipeline_state(self) -> None:
        """Refresh immutable lineage before a create decision.

        A second repository process may have committed a newer current version
        since this instance loaded. Refreshing here prevents a stale process
        from regressing current selection or audio pointers.
        """
        with self.SessionLocal() as db:
            self.sessions = {
                row.session_id: self._session_from_record(row)
                for row in db.query(SessionRecord).all()
            }
            self.transcripts = {
                row.transcript_id: self._transcript_from_record(row)
                for row in db.query(TranscriptRecord).all()
            }
            self.features = {
                row.feature_set_id: self._feature_from_record(row)
                for row in db.query(FeatureSetRecord).all()
            }
            self.audio_files = {
                row.audio_file_id: self._audio_from_record(row)
                for row in db.query(AudioFileRecord).all()
            }
            normalized_assets = [
                NormalizedAudioAsset.model_validate(row.payload)
                for row in db.query(NormalizedAudioAssetRecord).all()
            ]
            self.normalized_audio_assets = {
                (item.source_audio_file_id, item.asset_version): item
                for item in normalized_assets
            }
            mappings = [
                ReviewedSpeakerMapping.model_validate(row.payload)
                for row in db.query(SpeakerMappingRecord).all()
            ]
            self.speaker_mappings = {
                (item.mapping_id, item.mapping_version): item for item in mappings
            }
            acknowledgments = [
                LimitationAcknowledgment.model_validate(row.payload)
                for row in db.query(LimitationAcknowledgmentRecord).all()
            ]
            self.limitation_acknowledgments = {
                (item.acknowledgment_id, item.acknowledgment_version): item
                for item in acknowledgments
            }
            attestations = [
                TranscriptAttestation.model_validate(row.payload)
                for row in db.query(TranscriptAttestationRecord).all()
            ]
            self.transcript_attestations = {
                (item.attestation_id, item.attestation_version): item
                for item in attestations
            }
            exports = [
                ChatExport.model_validate(row.payload)
                for row in db.query(ChatExportRecord).all()
            ]
            self.chat_exports = {
                (item.export_id, item.export_version): item for item in exports
            }
            findings = [
                FindingsProjection.model_validate(row.payload)
                for row in db.query(FindingsResultRecord).all()
            ]
            self.findings_results = {
                (item.findings_id, item.findings_version): item for item in findings
            }

    def _validate_speech_ownership(
        self,
        *,
        organization_id: str,
        session_id: str,
        transcript_id: str | None = None,
        audio_file_id: str | None = None,
    ) -> None:
        self._refresh_speech_pipeline_state()
        super()._validate_speech_ownership(
            organization_id=organization_id,
            session_id=session_id,
            transcript_id=transcript_id,
            audio_file_id=audio_file_id,
        )

    def get_case(self, case_id: str) -> ChildCase | None:
        with self.SessionLocal() as db:
            row = db.get(ChildCaseRecord, case_id)
            return self._case_from_record(row) if row is not None else None

    def create_case(self, payload: ChildCaseCreate, *, actor_id: str) -> ChildCase:
        now = _utc_now()
        case = ChildCase(
            case_id=new_id("case"),
            **payload.model_dump(),
            created_at=now,
            updated_at=now,
        )
        if actor_id != "system" and actor_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, actor_id]
        if case.primary_therapist_user_id is None and actor_id != "system":
            case.primary_therapist_user_id = actor_id
        if case.primary_therapist_user_id and case.primary_therapist_user_id not in case.care_team_user_ids:
            case.care_team_user_ids = [*case.care_team_user_ids, case.primary_therapist_user_id]
        audit = validate_audit_event(
            actor_id=actor_id,
            action="case.create",
            target_id=case.case_id,
            outcome="success",
            correlation_id=f"case-create-{case.version}",
            message="Case created.",
        )
        with self.SessionLocal() as db:
            db.add(self._case_to_record(case))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
        self.cases[case.case_id] = case
        self.audit_log.append(audit.as_dict())
        return self.clone(case)

    def update_case(
        self,
        case_id: str,
        patch: ChildCaseUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> ChildCase:
        now = _utc_now()
        patch_values = patch.model_dump(exclude_unset=True)
        with self.SessionLocal() as db:
            row = db.get(ChildCaseRecord, case_id)
            if row is None:
                raise KeyError(case_id)
            if expected_version is not None and row.version != expected_version:
                raise CaseVersionConflictError(
                    f"Case {case_id} expected version {expected_version}, found {row.version}."
                )
            for field, value in patch_values.items():
                setattr(row, field, value)
            row.version += 1
            row.updated_at = now
            audit = validate_audit_event(
                actor_id=actor_id,
                action="case.update",
                target_id=case_id,
                outcome="success",
                correlation_id=f"case-update-{row.version}",
                message="Case updated.",
            )
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = self._case_from_record(row)
        self.cases[case_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def list_cases_for_user(self, user_id: str, organization_id: str) -> list[ChildCase]:
        return [self.clone(case) for case in self.cases.values()]

    def upsert_membership(
        self,
        organization_id: str,
        payload: OrganizationMembershipCreate,
        *,
        actor_id: str,
    ) -> OrganizationMembership:
        now = _utc_now()
        with self.SessionLocal() as db:
            organization = db.get(OrganizationRecord, organization_id)
            if organization is None:
                db.add(OrganizationRecord(organization_id=organization_id, name=organization_id, pilot_mode=False, created_at=now))
            profile = db.get(UserProfileRecord, payload.user_id)
            if profile is None:
                db.add(UserProfileRecord(user_id=payload.user_id, display_name=payload.display_name, created_at=now))
            else:
                profile.display_name = payload.display_name

            row = (
                db.query(OrganizationMembershipRecord)
                .filter_by(organization_id=organization_id, user_id=payload.user_id)
                .one_or_none()
            )
            if row is None:
                membership = OrganizationMembership(
                    membership_id=new_id("mbr"),
                    organization_id=organization_id,
                    user_id=payload.user_id,
                    display_name=payload.display_name,
                    role=payload.role,
                    active=payload.active,
                    created_at=now,
                )
                row = self._membership_to_record(membership)
                db.add(row)
            else:
                row.role = payload.role
                row.active = payload.active
                membership = self._membership_from_record(row, display_name=payload.display_name)

            audit = validate_audit_event(
                actor_id=actor_id,
                action="membership.upsert",
                target_id=membership.membership_id,
                outcome="success",
                correlation_id=f"membership-upsert-{membership.membership_id}",
                message="Organization membership updated.",
            ).as_dict()
            audit["organization_id"] = organization_id
            db.add(self._audit_to_record(audit))
            db.commit()

        self.memberships[membership.membership_id] = membership
        self.audit_log.append(audit)
        return self.clone(membership)

    def revoke_membership(self, organization_id: str, membership_id: str, *, actor_id: str) -> OrganizationMembership:
        now = _utc_now()
        with self.SessionLocal() as db:
            row = db.get(OrganizationMembershipRecord, membership_id)
            if row is None or row.organization_id != organization_id:
                raise KeyError(membership_id)
            row.active = False
            care_rows = (
                db.query(CaseCareTeamAssignmentRecord)
                .filter_by(organization_id=organization_id, user_id=row.user_id)
                .all()
            )
            for assignment_row in care_rows:
                assignment_row.active = False
                case_row = db.get(ChildCaseRecord, assignment_row.case_id)
                if case_row is not None:
                    case_row.care_team_user_ids = [
                        user_id for user_id in (case_row.care_team_user_ids or []) if user_id != row.user_id
                    ]
                    if case_row.primary_therapist_user_id == row.user_id:
                        case_row.primary_therapist_user_id = None
                    case_row.updated_at = now
            profile = db.get(UserProfileRecord, row.user_id)
            membership = self._membership_from_record(
                row,
                display_name=profile.display_name if profile is not None else row.user_id,
            )
            audit = validate_audit_event(
                actor_id=actor_id,
                action="membership.revoke",
                target_id=membership.membership_id,
                outcome="success",
                correlation_id=f"membership-revoke-{membership.membership_id}",
                message="Organization membership revoked.",
            ).as_dict()
            audit["organization_id"] = organization_id
            db.add(self._audit_to_record(audit))
            db.commit()

        self.load()
        return self.clone(membership)

    def create_invitation(
        self,
        organization_id: str,
        payload: OrganizationInvitationCreate,
        *,
        actor_id: str,
    ) -> OrganizationInvitation:
        now = _utc_now()
        invitation = OrganizationInvitation(
            invitation_id=new_id("inv"),
            organization_id=organization_id,
            email=payload.email,
            display_name=payload.display_name,
            role=payload.role,
            invited_by=actor_id,
            expires_at=now + timedelta(days=INVITATION_EXPIRY_DAYS),
            created_at=now,
        )
        audit = validate_audit_event(
            actor_id=actor_id,
            action="invitation.create",
            target_id=invitation.invitation_id,
            outcome="success",
            correlation_id=f"invitation-create-{invitation.invitation_id}",
            message="Organization invitation created.",
        ).as_dict()
        audit["organization_id"] = organization_id
        with self.SessionLocal() as db:
            if db.get(OrganizationRecord, organization_id) is None:
                db.add(OrganizationRecord(organization_id=organization_id, name=organization_id, pilot_mode=False, created_at=now))
            db.add(self._invitation_to_record(invitation))
            db.add(self._audit_to_record(audit))
            db.commit()

        self.invitations[invitation.invitation_id] = invitation
        self.audit_log.append(audit)
        return self.clone(invitation)

    def accept_invitation(
        self,
        organization_id: str,
        invitation_id: str,
        payload: OrganizationInvitationAccept,
        *,
        actor_id: str,
    ) -> OrganizationInvitation:
        now = _utc_now()
        with self.SessionLocal() as db:
            row = db.get(OrganizationInvitationRecord, invitation_id)
            if row is None or row.organization_id != organization_id:
                raise KeyError(invitation_id)
            expires_at = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
            if row.status == "accepted":
                raise ValueError("Invitation has already been accepted.")
            if row.status == "revoked":
                raise ValueError("Invitation has been revoked.")
            if expires_at <= now:
                row.status = "expired"
                outcome = "denied"
                message = "Organization invitation acceptance failed."
                invitation = self._invitation_from_record(row)
                error_detail = "Expired invitations require a newly issued invitation."
            else:
                conflicting_identity = (
                    db.query(OrganizationInvitationRecord)
                    .filter(
                        OrganizationInvitationRecord.email == row.email,
                        OrganizationInvitationRecord.accepted_user_id.is_not(None),
                        OrganizationInvitationRecord.accepted_user_id != payload.user_id,
                    )
                    .first()
                )
                if conflicting_identity is not None:
                    outcome = "denied"
                    message = "Organization invitation acceptance failed."
                    invitation = self._invitation_from_record(row)
                    error_detail = "Identity email is already bound to a different user."
                else:
                    row.status = "accepted"
                    row.accepted_user_id = payload.user_id
                    row.accepted_at = now
                    if db.get(UserProfileRecord, payload.user_id) is None:
                        db.add(UserProfileRecord(user_id=payload.user_id, display_name=row.display_name, created_at=now))
                    membership_row = (
                        db.query(OrganizationMembershipRecord)
                        .filter_by(organization_id=organization_id, user_id=payload.user_id)
                        .one_or_none()
                    )
                    if membership_row is None:
                        membership_row = OrganizationMembershipRecord(
                            membership_id=new_id("mbr"),
                            organization_id=organization_id,
                            user_id=payload.user_id,
                            role=row.role,
                            active=True,
                            created_at=now,
                        )
                        db.add(membership_row)
                    else:
                        membership_row.role = row.role
                        membership_row.active = True
                    outcome = "success"
                    message = "Organization invitation accepted."
                    invitation = self._invitation_from_record(row)
                    error_detail = None
            audit = validate_audit_event(
                actor_id=actor_id,
                action="invitation.accept",
                target_id=invitation.invitation_id,
                outcome=outcome,
                correlation_id=f"invitation-accept-{invitation.invitation_id}",
                message=message,
            ).as_dict()
            audit["organization_id"] = organization_id
            db.add(self._audit_to_record(audit))
            db.commit()

        if error_detail is not None:
            self.load()
            raise ValueError(error_detail)
        self.load()
        return self.clone(invitation)

    def audit_break_glass_case_access(self, organization_id: str, case_id: str, *, actor_id: str) -> None:
        with self.SessionLocal() as db:
            case_row = db.get(ChildCaseRecord, case_id)
            if case_row is None or case_row.organization_id != organization_id:
                raise KeyError(case_id)
            audit = validate_audit_event(
                actor_id=actor_id,
                action="break_glass.case_access",
                target_id=case_id,
                outcome="success",
                correlation_id=f"break-glass-case-{case_id}",
                message="Scoped break-glass case access granted.",
            ).as_dict()
            audit["organization_id"] = organization_id
            db.add(self._audit_to_record(audit))
            db.commit()
        self.audit_log.append(audit)

    def assign_care_team_member(
        self,
        case_id: str,
        payload: CareTeamAssignmentCreate,
        *,
        actor_id: str,
    ) -> CareTeamAssignment:
        now = _utc_now()
        if payload.is_primary and (not payload.active or payload.role != "therapist"):
            raise ValueError("Primary therapist assignment must be an active therapist.")
        with self.SessionLocal() as db:
            case_row = db.get(ChildCaseRecord, case_id)
            if case_row is None:
                raise KeyError(case_id)
            row = (
                db.query(CaseCareTeamAssignmentRecord)
                .filter_by(organization_id=case_row.organization_id, case_id=case_id, user_id=payload.user_id)
                .one_or_none()
            )
            if row is None:
                assignment = CareTeamAssignment(
                    assignment_id=new_id("team"),
                    organization_id=case_row.organization_id,
                    case_id=case_id,
                    user_id=payload.user_id,
                    role=payload.role,
                    active=payload.active,
                    is_primary=payload.is_primary,
                    created_at=now,
                )
                row = self._care_team_assignment_to_record(assignment)
                db.add(row)
            else:
                row.role = payload.role
                row.active = payload.active
                assignment = self._care_team_assignment_from_record(row).model_copy(update={"is_primary": payload.is_primary})

            care_team = list(case_row.care_team_user_ids or [])
            if payload.active and payload.user_id not in care_team:
                care_team.append(payload.user_id)
            if not payload.active and payload.user_id in care_team:
                care_team = [user_id for user_id in care_team if user_id != payload.user_id]
            case_row.care_team_user_ids = care_team
            if payload.is_primary:
                case_row.primary_therapist_user_id = payload.user_id
            elif case_row.primary_therapist_user_id == payload.user_id and (not payload.active or payload.role != "therapist"):
                case_row.primary_therapist_user_id = None
            case_row.updated_at = now

            audit = validate_audit_event(
                actor_id=actor_id,
                action="care_team.assign",
                target_id=assignment.assignment_id,
                outcome="success",
                correlation_id=f"care-team-assign-{assignment.assignment_id}",
                message="Case care-team assignment updated.",
            ).as_dict()
            audit["organization_id"] = case_row.organization_id
            db.add(self._audit_to_record(audit))
            db.commit()
            db.refresh(case_row)
            updated_case = self._case_from_record(case_row)

        assignment = assignment.model_copy(update={"is_primary": updated_case.primary_therapist_user_id == assignment.user_id})
        self.care_team_assignments[assignment.assignment_id] = assignment
        self.cases[case_id] = updated_case
        self.audit_log.append(audit)
        return self.clone(assignment)

    def create_session(self, case_id: str, payload: TherapySessionCreate, *, actor_id: str) -> TherapySession:
        now = _utc_now()
        case = self.cases[case_id]
        session = TherapySession(
            session_id=new_id("session"),
            case_id=case_id,
            organization_id=case.organization_id,
            **payload.model_dump(),
            created_at=now,
            updated_at=now,
        )
        audit = validate_audit_event(
            actor_id=actor_id,
            action="session.create",
            target_id=session.session_id,
            outcome="success",
            correlation_id=f"session-create-{session.version}",
            message="Session created.",
        )
        with self.SessionLocal() as db:
            case_row = db.get(ChildCaseRecord, case_id)
            if case_row is None:
                raise KeyError(case_id)
            case_row.latest_session_date = session.session_date
            case_row.latest_session_status = session.status.value if hasattr(session.status, "value") else str(session.status)
            case_row.updated_at = now
            db.add(self._session_to_record(session))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(case_row)
            updated_case = self._case_from_record(case_row)
        self.sessions[session.session_id] = session
        self.cases[case_id] = updated_case
        self.audit_log.append(audit.as_dict())
        return self.clone(session)

    def update_session(
        self,
        session_id: str,
        patch: TherapySessionUpdate,
        *,
        expected_version: int | None,
        actor_id: str,
    ) -> TherapySession:
        now = _utc_now()
        patch_values = patch.model_dump(exclude_unset=True)
        with self.SessionLocal() as db:
            row = db.get(SessionRecord, session_id)
            if row is None:
                raise KeyError(session_id)
            if expected_version is not None and row.version != expected_version:
                raise SessionVersionConflictError(
                    f"Session {session_id} expected version {expected_version}, found {row.version}."
                )
            for field, value in patch_values.items():
                setattr(row, field, value.value if hasattr(value, "value") else value)
            row.version += 1
            row.updated_at = now
            audit = validate_audit_event(
                actor_id=actor_id,
                action="session.patch",
                target_id=session_id,
                outcome="success",
                correlation_id=f"session-update-{row.version}",
                message="Session updated.",
            )
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = self._session_from_record(row)
        self.sessions[session_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_transcript(
        self,
        transcript: Transcript,
        *,
        session_status: ReviewStatus,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Transcript:
        transcript.organization_id = self.sessions[transcript.session_id].organization_id
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=transcript.transcript_id,
            outcome="success",
            correlation_id=f"transcript-create-{transcript.version}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, transcript.session_id)
            if session_row is None:
                raise KeyError(transcript.session_id)
            invalidated = self._mark_downstream_rows_stale(db, session_row)
            session_row.transcript_id = transcript.transcript_id
            session_row.status = session_status.value if hasattr(session_status, "value") else str(session_status)
            session_row.updated_at = _utc_now()
            db.add(self._transcript_to_record(transcript))
            db.add(self._audit_to_record(audit.as_dict()))
            invalidation_audit = self._downstream_invalidation_audit(actor_id, transcript.transcript_id, transcript.version) if invalidated else None
            if invalidation_audit is not None:
                db.add(self._audit_to_record(invalidation_audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            updated_session = self._session_from_record(session_row)
        self.sessions[transcript.session_id] = updated_session
        self._mark_downstream_outputs_stale(self.sessions[transcript.session_id])
        self.transcripts[transcript.transcript_id] = transcript
        self.audit_log.append(audit.as_dict())
        if invalidation_audit is not None:
            self.audit_log.append(invalidation_audit.as_dict())
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
        transcript.organization_id = self.sessions[transcript.session_id].organization_id
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=transcript.transcript_id,
            outcome="success",
            correlation_id=f"transcript-update-{transcript.version}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(TranscriptRecord, transcript.transcript_id)
            if row is None:
                raise KeyError(transcript.transcript_id)
            if expected_version is not None and row.version != expected_version:
                raise TranscriptVersionConflictError(
                    f"Transcript {transcript.transcript_id} expected version {expected_version}, found {row.version}."
                )
            previous_version = row.version
            row.source = transcript.source
            row.raw_text = transcript.raw_text
            row.utterances = [item.model_dump(mode="json") for item in transcript.utterances]
            row.qa_status = transcript.qa_status.value if hasattr(transcript.qa_status, "value") else str(transcript.qa_status)
            row.qa_issues = [item.model_dump(mode="json") for item in transcript.qa_issues]
            row.review_status = transcript.review_status.value if hasattr(transcript.review_status, "value") else str(transcript.review_status)
            row.therapist_attested = transcript.therapist_attested
            row.attestation_reason = transcript.attestation_reason
            row.version = transcript.version
            row.updated_at = transcript.updated_at
            session_row = db.get(SessionRecord, transcript.session_id)
            if session_row is None:
                raise KeyError(transcript.session_id)
            invalidated = self._mark_downstream_rows_stale(db, session_row) if invalidate_downstream else False
            if invalidate_downstream and transcript.version != previous_version:
                speech_invalidated = self._mark_speech_pipeline_rows_stale(
                    db,
                    transcript.transcript_id,
                    {
                        "code": "TRANSCRIPT_VERSION_CHANGED",
                        "affected_resource_id": transcript.transcript_id,
                        "affected_resource_version": str(transcript.version),
                        "validator_or_rule_version": "speech-lineage-v1.7.0",
                    },
                )
                invalidated = invalidated or speech_invalidated
            session_row.status = session_status.value if hasattr(session_status, "value") else str(session_status)
            session_row.updated_at = _utc_now()
            db.add(self._audit_to_record(audit.as_dict()))
            invalidation_audit = self._downstream_invalidation_audit(actor_id, transcript.transcript_id, transcript.version) if invalidated else None
            if invalidation_audit is not None:
                db.add(self._audit_to_record(invalidation_audit.as_dict()))
            db.commit()
            db.refresh(row)
            db.refresh(session_row)
            updated = self._transcript_from_record(row)
            updated_session = self._session_from_record(session_row)
        self.transcripts[transcript.transcript_id] = updated
        self.sessions[transcript.session_id] = updated_session
        if invalidate_downstream:
            self._mark_downstream_outputs_stale(self.sessions[transcript.session_id])
            self._refresh_speech_pipeline_state()
        self.audit_log.append(audit.as_dict())
        if invalidation_audit is not None:
            self.audit_log.append(invalidation_audit.as_dict())
        return self.clone(updated)

    @staticmethod
    def _mark_downstream_rows_stale(db, session_row: SessionRecord) -> bool:
        invalidated = False
        feature_row = db.get(FeatureSetRecord, session_row.feature_set_id) if session_row.feature_set_id else None
        if feature_row is not None and feature_row.review_status != ReviewStatus.stale.value:
            feature_row.review_status = ReviewStatus.stale.value
            invalidated = True

        ml_row = db.get(MLResultRecord, session_row.ml_result_id) if session_row.ml_result_id else None
        if ml_row is not None and (ml_row.payload or {}).get("is_current", True):
            payload = dict(ml_row.payload or {})
            payload["is_current"] = False
            ml_row.payload = payload
            invalidated = True

        ai_row = db.get(AiReviewRecord, session_row.ai_review_id) if session_row.ai_review_id else None
        if ai_row is not None and ai_row.therapist_review_status != ReviewStatus.stale.value:
            payload = dict(ai_row.payload or {})
            payload["therapist_review_status"] = ReviewStatus.stale.value
            ai_row.payload = payload
            ai_row.therapist_review_status = ReviewStatus.stale.value
            invalidated = True

        report_row = db.get(ReportRecord, session_row.report_id) if session_row.report_id else None
        if report_row is not None and report_row.status not in {ReviewStatus.signed_off.value, ReviewStatus.stale.value}:
            report_row.status = ReviewStatus.stale.value
            report_row.version += 1
            report_row.updated_at = _utc_now()
            case_row = db.get(ChildCaseRecord, session_row.case_id)
            if case_row is not None:
                case_row.latest_report_status = ReviewStatus.stale.value
            invalidated = True
        return invalidated

    @staticmethod
    def _mark_speech_pipeline_rows_stale(
        db,
        transcript_id: str,
        cause: dict[str, str],
    ) -> bool:
        invalidated = False
        for model, current_status in (
            (SpeakerMappingRecord, "confirmed"),
            (LimitationAcknowledgmentRecord, "current"),
            (TranscriptAttestationRecord, "current"),
            (ChatExportRecord, "current"),
            (FindingsResultRecord, "current"),
        ):
            rows = (
                db.query(model)
                .filter(model.transcript_id == transcript_id, model.status == current_status)
                .all()
            )
            for speech_row in rows:
                payload = deepcopy(speech_row.payload or {})
                payload["status"] = "stale"
                existing_causes = list(payload.get("stale_causes", []))
                if cause not in existing_causes:
                    existing_causes.append(cause)
                payload["stale_causes"] = existing_causes
                speech_row.status = "stale"
                speech_row.payload = payload
                invalidated = True
        return invalidated

    @staticmethod
    def _downstream_invalidation_audit(actor_id: str, transcript_id: str, version: int):
        return validate_audit_event(
            actor_id=actor_id,
            action="workflow.invalidate_downstream",
            target_id=transcript_id,
            outcome="success",
            correlation_id=f"workflow-invalidate-{version}",
            message="Derived workflow outputs marked stale after transcript change.",
        )

    def create_report(
        self,
        report: Report,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> Report:
        report.organization_id = self.cases[report.case_id].organization_id
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=report.report_id,
            outcome="success",
            correlation_id=f"report-create-{report.version}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, report.session_id)
            if session_row is None:
                raise KeyError(report.session_id)
            case_row = db.get(ChildCaseRecord, report.case_id)
            if case_row is None:
                raise KeyError(report.case_id)
            transcript_row = db.get(TranscriptRecord, report.transcript_id) if report.transcript_id else None
            expected_transcript_version = report.generated_from_versions.get("transcript_version")
            if report.transcript_id and (
                transcript_row is None
                or session_row.transcript_id != report.transcript_id
                or expected_transcript_version != str(transcript_row.version)
            ):
                raise ValueError("Transcript changed during report generation; discard the stale draft and retry.")
            feature_row = db.get(FeatureSetRecord, report.feature_result_id) if report.feature_result_id else None
            if report.feature_result_id and (
                session_row.feature_set_id != report.feature_result_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or transcript_row is None
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Findings changed during report generation; discard the stale draft and retry.")
            session_row.report_id = report.report_id
            session_row.updated_at = _utc_now()
            case_row.latest_report_status = report.status.value if hasattr(report.status, "value") else str(report.status)
            case_row.updated_at = _utc_now()
            db.add(self._report_to_record(report))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            db.refresh(case_row)
            updated_session = self._session_from_record(session_row)
            updated_case = self._case_from_record(case_row)
        self.reports[report.report_id] = report
        self.sessions[report.session_id] = updated_session
        self.cases[report.case_id] = updated_case
        self.audit_log.append(audit.as_dict())
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
        report.organization_id = self.cases[report.case_id].organization_id
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=report.report_id,
            outcome="success",
            correlation_id=f"report-update-{report.version}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(ReportRecord, report.report_id)
            if row is None:
                raise KeyError(report.report_id)
            if expected_version is not None and row.version != expected_version:
                raise ReportVersionConflictError(
                    f"Report {report.report_id} expected version {expected_version}, found {row.version}."
                )
            record = self._report_to_record(report)
            for column in ReportRecord.__table__.columns:
                if column.name != "report_id":
                    setattr(row, column.name, getattr(record, column.name))
            case_row = db.get(ChildCaseRecord, report.case_id)
            if case_row is None:
                raise KeyError(report.case_id)
            case_row.latest_report_status = report.status.value if hasattr(report.status, "value") else str(report.status)
            case_row.updated_at = _utc_now()
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            db.refresh(case_row)
            updated = self._report_from_record(row)
            updated_case = self._case_from_record(case_row)
        self.reports[report.report_id] = updated
        self.cases[report.case_id] = updated_case
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=goal.goal_id,
            outcome="success",
            correlation_id=f"therapy-goal-create-{goal.goal_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            if db.get(ChildCaseRecord, goal.case_id) is None:
                raise KeyError(goal.case_id)
            db.add(self._goal_to_record(goal))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
        self.therapy_goals[goal.goal_id] = goal
        self.audit_log.append(audit.as_dict())
        return self.clone(goal)

    def update_therapy_goal(
        self,
        goal: TherapyGoal,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> TherapyGoal:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=goal.goal_id,
            outcome="success",
            correlation_id=f"therapy-goal-update-{goal.goal_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(TherapyGoalRecord, goal.goal_id)
            if row is None:
                raise KeyError(goal.goal_id)
            row.case_id = goal.case_id
            row.title = goal.title
            row.target = goal.target
            row.status = goal.status
            row.notes = goal.notes
            row.retained = goal.retained
            row.created_at = goal.created_at
            row.updated_at = goal.updated_at
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = self._goal_from_record(row)
        self.therapy_goals[goal.goal_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=operation.privacy_operation_id,
            outcome="success",
            correlation_id=f"privacy-operation-create-{operation.privacy_operation_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            if db.get(ChildCaseRecord, operation.case_id) is None:
                raise KeyError(operation.case_id)
            db.add(self._privacy_operation_to_record(operation))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
        self.privacy_operations[operation.privacy_operation_id] = operation
        self.audit_log.append(audit.as_dict())
        return self.clone(operation)

    def update_privacy_operation(
        self,
        operation: PrivacyOperation,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> PrivacyOperation:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=operation.privacy_operation_id,
            outcome="success",
            correlation_id=f"privacy-operation-update-{operation.privacy_operation_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(PrivacyOperationRecord, operation.privacy_operation_id)
            if row is None:
                raise KeyError(operation.privacy_operation_id)
            record = self._privacy_operation_to_record(operation)
            for column in PrivacyOperationRecord.__table__.columns:
                if column.name != "privacy_operation_id":
                    setattr(row, column.name, getattr(record, column.name))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = self._privacy_operation_from_record(row)
        self.privacy_operations[operation.privacy_operation_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_feature_set(
        self,
        feature_set: FeatureSet,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> FeatureSet:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=feature_set.feature_set_id,
            outcome="success",
            correlation_id=f"feature-set-create-{feature_set.feature_set_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, feature_set.session_id)
            if session_row is None:
                raise KeyError(feature_set.session_id)
            transcript_row = db.get(TranscriptRecord, feature_set.transcript_id)
            if (
                transcript_row is None
                or session_row.transcript_id != feature_set.transcript_id
                or transcript_row.version != feature_set.transcript_version
            ):
                raise ValueError("Transcript changed during feature extraction; discard the stale result and retry.")
            session_row.feature_set_id = feature_set.feature_set_id
            session_row.ml_result_id = None
            session_row.updated_at = _utc_now()
            db.add(self._feature_to_record(feature_set))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            updated_session = self._session_from_record(session_row)
        self.features[feature_set.feature_set_id] = feature_set
        self.sessions[feature_set.session_id] = updated_session
        self.audit_log.append(audit.as_dict())
        return self.clone(feature_set)

    def create_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=review.ai_review_id,
            outcome="success",
            correlation_id=f"ai-review-create-{review.ai_review_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, review.session_id)
            if session_row is None:
                raise KeyError(review.session_id)
            case_row = db.get(ChildCaseRecord, session_row.case_id)
            if case_row is None:
                raise KeyError(session_row.case_id)
            transcript_row = db.get(TranscriptRecord, session_row.transcript_id) if session_row.transcript_id else None
            feature_row = db.get(FeatureSetRecord, review.feature_set_id) if review.feature_set_id else None
            if transcript_row is None or transcript_row.version != review.input_transcript_version:
                raise ValueError("Transcript changed during AI-assisted review generation; discard the stale result and retry.")
            if review.feature_set_id and (
                session_row.feature_set_id != review.feature_set_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Findings changed during AI-assisted review generation; discard the stale result and retry.")
            session_row.ai_review_id = review.ai_review_id
            session_row.updated_at = _utc_now()
            case_row.review_priority = review.review_priority
            case_row.updated_at = _utc_now()
            db.add(self._ai_review_to_record(review))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            db.refresh(case_row)
            updated_session = self._session_from_record(session_row)
            updated_case = self._case_from_record(case_row)
        self.ai_reviews[review.ai_review_id] = review
        self.sessions[review.session_id] = updated_session
        self.cases[updated_case.case_id] = updated_case
        self.audit_log.append(audit.as_dict())
        return self.clone(review)

    def update_ai_review(
        self,
        review: AiReview,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> AiReview:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=review.ai_review_id,
            outcome="success",
            correlation_id=f"ai-review-update-{review.ai_review_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(AiReviewRecord, review.ai_review_id)
            if row is None:
                raise KeyError(review.ai_review_id)
            record = self._ai_review_to_record(review)
            row.session_id = record.session_id
            row.payload = record.payload
            row.review_priority = record.review_priority
            row.therapist_review_status = record.therapist_review_status
            row.created_at = record.created_at
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = AiReview.model_validate(row.payload)
        self.ai_reviews[review.ai_review_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def create_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=result.result_id,
            outcome="success",
            correlation_id=f"ml-result-create-{result.result_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            session_row = db.get(SessionRecord, result.session_id)
            if session_row is None:
                raise KeyError(result.session_id)
            transcript_row = db.get(TranscriptRecord, result.transcript_id)
            feature_row = db.get(FeatureSetRecord, result.feature_result_id)
            if (
                transcript_row is None
                or session_row.transcript_id != result.transcript_id
                or session_row.feature_set_id != result.feature_result_id
                or feature_row is None
                or feature_row.review_status == ReviewStatus.stale.value
                or feature_row.transcript_id != transcript_row.transcript_id
                or feature_row.transcript_version != transcript_row.version
            ):
                raise ValueError("Transcript or findings changed during ML review generation; discard the stale result and retry.")
            session_row.ml_result_id = result.result_id
            session_row.updated_at = _utc_now()
            db.add(self._ml_result_to_record(result))
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(session_row)
            updated_session = self._session_from_record(session_row)
        self.ml_results[result.result_id] = result
        self.sessions[result.session_id] = updated_session
        self.audit_log.append(audit.as_dict())
        return self.clone(result)

    def update_ml_result(
        self,
        result: MLResult,
        *,
        actor_id: str,
        audit_action: str,
        audit_message: str,
    ) -> MLResult:
        audit = validate_audit_event(
            actor_id=actor_id,
            action=audit_action,
            target_id=result.result_id,
            outcome="success",
            correlation_id=f"ml-result-update-{result.result_id}",
            message=audit_message,
        )
        with self.SessionLocal() as db:
            row = db.get(MLResultRecord, result.result_id)
            if row is None:
                raise KeyError(result.result_id)
            record = self._ml_result_to_record(result)
            row.session_id = record.session_id
            row.transcript_id = record.transcript_id
            row.payload = record.payload
            row.created_at = record.created_at
            db.add(self._audit_to_record(audit.as_dict()))
            db.commit()
            db.refresh(row)
            updated = MLResult.model_validate(row.payload)
        self.ml_results[result.result_id] = updated
        self.audit_log.append(audit.as_dict())
        return self.clone(updated)

    def load(self) -> None:
        with self.SessionLocal() as db:
            cases = db.query(ChildCaseRecord).all()
            if cases:
                self.cases = {row.case_id: self._case_from_record(row) for row in cases}
                self.sessions = {row.session_id: self._session_from_record(row) for row in db.query(SessionRecord).all()}
                self.transcripts = {row.transcript_id: self._transcript_from_record(row) for row in db.query(TranscriptRecord).all()}
                self.features = {row.feature_set_id: self._feature_from_record(row) for row in db.query(FeatureSetRecord).all()}
                self.ml_results = {row.result_id: MLResult.model_validate(row.payload) for row in db.query(MLResultRecord).all()}
                self.audio_files = {row.audio_file_id: self._audio_from_record(row) for row in db.query(AudioFileRecord).all()}
                normalized_assets = [
                    NormalizedAudioAsset.model_validate(row.payload)
                    for row in db.query(NormalizedAudioAssetRecord).all()
                ]
                self.normalized_audio_assets = {
                    (item.source_audio_file_id, item.asset_version): item
                    for item in normalized_assets
                }
                mappings = [
                    ReviewedSpeakerMapping.model_validate(row.payload)
                    for row in db.query(SpeakerMappingRecord).all()
                ]
                self.speaker_mappings = {
                    (item.mapping_id, item.mapping_version): item for item in mappings
                }
                acknowledgments = [
                    LimitationAcknowledgment.model_validate(row.payload)
                    for row in db.query(LimitationAcknowledgmentRecord).all()
                ]
                self.limitation_acknowledgments = {
                    (item.acknowledgment_id, item.acknowledgment_version): item
                    for item in acknowledgments
                }
                attestations = [
                    TranscriptAttestation.model_validate(row.payload)
                    for row in db.query(TranscriptAttestationRecord).all()
                ]
                self.transcript_attestations = {
                    (item.attestation_id, item.attestation_version): item
                    for item in attestations
                }
                exports = [
                    ChatExport.model_validate(row.payload)
                    for row in db.query(ChatExportRecord).all()
                ]
                self.chat_exports = {
                    (item.export_id, item.export_version): item for item in exports
                }
                findings = [
                    FindingsProjection.model_validate(row.payload)
                    for row in db.query(FindingsResultRecord).all()
                ]
                self.findings_results = {
                    (item.findings_id, item.findings_version): item for item in findings
                }
                self.ai_reviews = {row.ai_review_id: AiReview.model_validate(row.payload) for row in db.query(AiReviewRecord).all()}
                self.reports = {row.report_id: self._report_from_record(row) for row in db.query(ReportRecord).all()}
                profile_names = {row.user_id: row.display_name for row in db.query(UserProfileRecord).all()}
                self.memberships = {
                    row.membership_id: self._membership_from_record(row, display_name=profile_names.get(row.user_id, row.user_id))
                    for row in db.query(OrganizationMembershipRecord).all()
                }
                self.invitations = {
                    row.invitation_id: self._invitation_from_record(row)
                    for row in db.query(OrganizationInvitationRecord).all()
                }
                self.care_team_assignments = {
                    row.assignment_id: self._care_team_assignment_from_record(row)
                    for row in db.query(CaseCareTeamAssignmentRecord).all()
                }
                self.therapy_goals = {row.goal_id: self._goal_from_record(row) for row in db.query(TherapyGoalRecord).all()}
                self.jobs = {row.job_id: self._job_from_record(row) for row in db.query(ProcessingJobRecord).all()}
                self.privacy_operations = {row.privacy_operation_id: self._privacy_operation_from_record(row) for row in db.query(PrivacyOperationRecord).all()}
                self.organization_settings = {
                    row.organization_id: dict(row.settings or {})
                    for row in db.query(OrganizationSettingsRecord).all()
                }
                self.organization_settings.setdefault("pilot_org_001", {"ai_review_enabled": True})
                self.audit_log = [
                    {
                        "audit_id": row.audit_id,
                        "organization_id": row.organization_id,
                        "actor_id": row.actor_id,
                        "action": row.action,
                        "target_id": row.target_id,
                        "outcome": row.outcome,
                        "correlation_id": row.correlation_id,
                        "message": row.message,
                        "timestamp": row.timestamp.isoformat() if hasattr(row.timestamp, "isoformat") else str(row.timestamp),
                    }
                    for row in db.query(AuditLogRecord).all()
                ]
            else:
                self.save()

    def save(self) -> None:
        with self.SessionLocal() as db:
            self._begin_serialized_speech_write(db)
            for model in (
                AuditLogRecord,
                PrivacyOperationRecord,
                ProcessingJobRecord,
                ReportRecord,
                OrganizationSettingsRecord,
                CaseCareTeamAssignmentRecord,
                OrganizationInvitationRecord,
                OrganizationMembershipRecord,
                AiReviewRecord,
                MLResultRecord,
                TherapyGoalRecord,
            ):
                db.query(model).delete()
            self._sync_snapshot_source_rows(db)
            previous_normalized_versions = self._durable_normalized_versions(db)
            for result in self.ml_results.values():
                db.add(MLResultRecord(
                    result_id=result.result_id,
                    session_id=result.session_id,
                    transcript_id=result.transcript_id,
                    payload=result.model_dump(mode="json"),
                    created_at=result.generated_at,
                ))
            self._sync_speech_pipeline_rows(db)
            self._sync_audio_current_pointers(db)
            self._invalidate_normalization_rereview(
                db,
                previous_normalized_versions,
            )
            self._enforce_durable_speech_dependency_closure(db)
            for review in self.ai_reviews.values():
                db.add(AiReviewRecord(
                    ai_review_id=review.ai_review_id,
                    session_id=review.session_id,
                    payload=review.model_dump(mode="json"),
                    review_priority=review.review_priority,
                    therapist_review_status=review.therapist_review_status.value,
                    created_at=review.created_at,
                ))
            for report in self.reports.values():
                db.add(self._report_to_record(report))
            for membership in self.memberships.values():
                if db.get(OrganizationRecord, membership.organization_id) is None:
                    db.add(OrganizationRecord(
                        organization_id=membership.organization_id,
                        name=membership.organization_id,
                        pilot_mode=False,
                        created_at=membership.created_at,
                    ))
                if db.get(UserProfileRecord, membership.user_id) is None:
                    db.add(UserProfileRecord(
                        user_id=membership.user_id,
                        display_name=membership.display_name,
                        created_at=membership.created_at,
                    ))
                db.add(self._membership_to_record(membership))
            for invitation in self.invitations.values():
                if db.get(OrganizationRecord, invitation.organization_id) is None:
                    db.add(OrganizationRecord(
                        organization_id=invitation.organization_id,
                        name=invitation.organization_id,
                        pilot_mode=False,
                        created_at=invitation.created_at,
                    ))
                db.add(self._invitation_to_record(invitation))
            for assignment in self.care_team_assignments.values():
                db.add(self._care_team_assignment_to_record(assignment))
            for goal in self.therapy_goals.values():
                db.add(self._goal_to_record(goal))
            for job in self.jobs.values():
                db.add(self._job_to_record(job))
            for privacy_operation in self.privacy_operations.values():
                db.add(self._privacy_operation_to_record(privacy_operation))
            for organization_id, settings in self.organization_settings.items():
                if db.get(OrganizationRecord, organization_id) is None:
                    db.add(OrganizationRecord(
                        organization_id=organization_id,
                        name=organization_id,
                        pilot_mode=False,
                        created_at=_utc_now(),
                    ))
                db.add(OrganizationSettingsRecord(
                    organization_id=organization_id,
                    ai_drafting_enabled=bool(settings.get("ai_drafting_enabled", False)),
                    default_retention_region=str(settings.get("default_retention_region", "local_pilot")),
                    settings=settings,
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                ))
            for item in self.audit_log:
                db.add(AuditLogRecord(
                    audit_id=item["audit_id"],
                    organization_id=item.get("organization_id", "pilot_org_001"),
                    actor_id=item.get("actor_id", "system"),
                    action=item["action"],
                    target_id=item["target_id"],
                    outcome=item.get("outcome", "success"),
                    correlation_id=item.get("correlation_id", "local"),
                    message=item["message"],
                    timestamp=_parse_datetime(item["timestamp"]),
                ))
            db.commit()
        self._refresh_speech_pipeline_state()

    def _sync_snapshot_source_rows(self, db) -> None:
        for case in self.cases.values():
            if db.get(ChildCaseRecord, case.case_id) is None:
                db.add(self._case_to_record(case))
        for session in self.sessions.values():
            row = db.get(SessionRecord, session.session_id)
            if row is None:
                db.add(self._session_to_record(session))
            elif row.transcript_id is None and session.transcript_id is not None:
                row.transcript_id = session.transcript_id
                row.updated_at = session.updated_at
        for transcript in self.transcripts.values():
            if db.get(TranscriptRecord, transcript.transcript_id) is None:
                db.add(self._transcript_to_record(transcript))
        for feature_set in self.features.values():
            if db.get(FeatureSetRecord, feature_set.feature_set_id) is None:
                db.add(self._feature_to_record(feature_set))
        for audio_file in self.audio_files.values():
            row = db.get(AudioFileRecord, audio_file.audio_file_id)
            if row is None:
                db.add(self._audio_to_record(audio_file))
                continue
            incoming = self._audio_to_record(audio_file)
            for column in AudioFileRecord.__table__.columns:
                if column.name in {
                    "audio_file_id",
                    "checksum_sha256",
                    "source_asset_version",
                    "current_normalized_asset_version",
                    "current_normalized_checksum_sha256",
                }:
                    continue
                setattr(row, column.name, getattr(incoming, column.name))
            if row.checksum_sha256 is None:
                row.checksum_sha256 = incoming.checksum_sha256
            if incoming.source_asset_version > row.source_asset_version:
                row.source_asset_version = incoming.source_asset_version
                row.checksum_sha256 = incoming.checksum_sha256

    def _speech_pipeline_changed(self) -> None:
        with self.SessionLocal() as db:
            self._begin_serialized_speech_write(db)
            previous_normalized_versions = self._durable_normalized_versions(db)
            self._sync_speech_pipeline_rows(db)
            self._sync_audio_current_pointers(db)
            self._invalidate_normalization_rereview(
                db,
                previous_normalized_versions,
            )
            self._enforce_durable_speech_dependency_closure(db)
            db.commit()
        self._refresh_speech_pipeline_state()

    def _persist_speech_pipeline_mutation(self) -> None:
        try:
            super()._persist_speech_pipeline_mutation()
        except Exception as persistence_error:  # noqa: BLE001
            try:
                self._refresh_speech_pipeline_state()
            except Exception as recovery_error:  # noqa: BLE001
                persistence_error.add_note(
                    f"Speech state recovery also failed: {recovery_error}"
                )
            raise

    def complete_audio_upload(
        self,
        audio_file_id: str,
        *,
        checksum_sha256: str,
        size_bytes: int,
        uploaded_at,
        actor_id: str = "system",
    ) -> AudioFileMetadata:
        with self.SessionLocal() as db:
            if db.bind.dialect.name == "sqlite":
                db.execute(text("BEGIN IMMEDIATE"))
            query = db.query(AudioFileRecord).filter_by(
                audio_file_id=audio_file_id
            )
            if db.bind.dialect.name == "postgresql":
                query = query.with_for_update()
            row = query.one_or_none()
            if row is None:
                raise ValueError("Audio file not found.")
            if not row.retained:
                raise ValueError("Audio file is no longer retained.")
            if row.upload_status != "pending_verification":
                raise ValueError(
                    "Audio upload must be re-issued with a new upload intent "
                    "before completion verification."
                )
            row.size_bytes = size_bytes
            row.checksum_sha256 = checksum_sha256
            row.uploaded_at = uploaded_at
            row.upload_status = "uploaded"
            audit = validate_audit_event(
                actor_id=actor_id,
                action="audio.upload_complete",
                target_id=audio_file_id,
                outcome="success",
                correlation_id=f"audio-upload-complete-{row.source_asset_version}",
                message="Audio upload bytes verified and marked complete.",
            )
            audit_data = audit.as_dict()
            audit_data["organization_id"] = row.organization_id
            db.add(self._audit_to_record(audit_data))
            db.commit()
            db.refresh(row)
            completed = self._audio_from_record(row)

        self.audio_files[audio_file_id] = completed
        self.audit_log.append(audit_data)
        return self.clone(completed)

    def has_durable_normalized_audio_reference(
        self,
        *,
        source_audio_file_id: str,
        asset_version: int,
        object_key: str,
        normalized_checksum_sha256: str,
    ) -> bool:
        record_key = f"{source_audio_file_id}:{asset_version}"
        with self.SessionLocal() as db:
            row = db.get(NormalizedAudioAssetRecord, record_key)
            row_payload = dict(row.payload or {}) if row is not None else {}
            return bool(
                row is not None
                and row.source_audio_file_id == source_audio_file_id
                and row.asset_version == asset_version
                and row.normalized_checksum_sha256 == normalized_checksum_sha256
                and row_payload.get("object_key") == object_key
            )

    def _apply_upstream_replacement_invalidation(
        self,
        transcript_id: str,
        *,
        replacement_kind: str,
        resource_id: str,
        resource_version: int,
    ) -> None:
        """SQL invalidation is derived from accepted durable rows in the write transaction."""

    def _begin_serialized_speech_write(self, db) -> None:
        if db.bind.dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))

    @staticmethod
    def _speech_group(model, item) -> tuple[str, str, str]:
        if model is NormalizedAudioAssetRecord:
            return "source_audio_file_id", item.source_audio_file_id, "asset_version"
        if model is SpeakerMappingRecord:
            return "transcript_id", item.transcript_id, "mapping_version"
        if model is LimitationAcknowledgmentRecord:
            return "acknowledgment_id", item.acknowledgment_id, "acknowledgment_version"
        if model is TranscriptAttestationRecord:
            return "transcript_id", item.transcript_id, "attestation_version"
        if model is ChatExportRecord:
            return "transcript_id", item.transcript_id, "export_version"
        if model is FindingsResultRecord:
            return "transcript_id", item.transcript_id, "findings_version"
        raise TypeError(model)

    @staticmethod
    def _is_current_speech_status(status: str) -> bool:
        return status in {"current", "confirmed"}

    def _lock_speech_group(self, db, model, group_field: str, group_value: str):
        if db.bind.dialect.name == "postgresql":
            lock_key = f"{model.__tablename__}:{group_field}:{group_value}"
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": lock_key},
            )
        query = db.query(model).filter(getattr(model, group_field) == group_value)
        if db.bind.dialect.name == "postgresql":
            query = query.with_for_update()
        return query.all()

    @staticmethod
    def _merge_stale_causes(
        stored_causes: list[dict],
        incoming_causes: list[dict],
    ) -> list[dict]:
        merged = deepcopy(stored_causes)
        for cause in incoming_causes:
            if cause not in merged:
                merged.append(deepcopy(cause))
        return merged

    def _set_speech_row_stale(self, row, causes: list[dict] | None = None) -> None:
        payload = deepcopy(row.payload or {})
        payload["status"] = "stale"
        payload["stale_causes"] = self._merge_stale_causes(
            list(payload.get("stale_causes", [])),
            list(causes or []),
        )
        row.status = "stale"
        row.payload = payload

    @staticmethod
    def _durable_upstream_error(detail: str) -> ValueError:
        return ValueError(f"durable upstream {detail} changed before speech artifact persistence")

    def _require_durable_transcript(self, db, item) -> TranscriptRecord:
        transcript = db.get(TranscriptRecord, item.transcript_id)
        if transcript is None or transcript.version != item.transcript_version:
            raise self._durable_upstream_error("transcript version")
        return transcript

    def _require_durable_audio_lineage(self, db, item) -> None:
        audio = db.get(AudioFileRecord, item.source_audio_file_id)
        if (
            audio is None
            or audio.source_asset_version != item.source_asset_version
            or audio.checksum_sha256 != item.source_checksum_sha256
        ):
            raise self._durable_upstream_error("source audio lineage")
        normalized_key = (
            f"{item.source_audio_file_id}:{item.normalized_asset_version}"
            if hasattr(item, "normalized_asset_version")
            else None
        )
        if normalized_key is not None:
            normalized = db.get(NormalizedAudioAssetRecord, normalized_key)
            if (
                normalized is None
                or normalized.status != "current"
                or normalized.normalized_checksum_sha256
                != item.normalized_checksum_sha256
            ):
                raise self._durable_upstream_error("normalized audio lineage")

    def _require_durable_mapping(self, db, item) -> dict:
        mapping = db.get(
            SpeakerMappingRecord,
            f"{item.speaker_mapping_id}:{item.speaker_mapping_version}",
        )
        payload = dict(mapping.payload or {}) if mapping is not None else {}
        if (
            mapping is None
            or mapping.status != "confirmed"
            or mapping.transcript_id != item.transcript_id
            or mapping.transcript_version != item.transcript_version
            or payload.get("mapping_id") != item.speaker_mapping_id
            or payload.get("mapping_version") != item.speaker_mapping_version
        ):
            raise self._durable_upstream_error("speaker mapping")
        return payload

    def _require_durable_acknowledgment_refs(
        self,
        db,
        *,
        transcript_id: str,
        transcript_version: int,
        acknowledgment_refs,
        validator_version: str,
    ) -> None:
        for acknowledgment_id, acknowledgment_version in acknowledgment_refs:
            acknowledgment = db.get(
                LimitationAcknowledgmentRecord,
                f"{acknowledgment_id}:{acknowledgment_version}",
            )
            payload = dict(acknowledgment.payload or {}) if acknowledgment is not None else {}
            if (
                acknowledgment is None
                or acknowledgment.status != "current"
                or acknowledgment.transcript_id != transcript_id
                or acknowledgment.transcript_version != transcript_version
                or acknowledgment.validator_version != validator_version
                or payload.get("acknowledgment_id") != acknowledgment_id
                or payload.get("acknowledgment_version") != acknowledgment_version
                or payload.get("disposition") != "acknowledgeable_limitation"
            ):
                raise self._durable_upstream_error("limitation acknowledgment")

    def _require_durable_attestation(self, db, item) -> dict:
        attestation = db.get(
            TranscriptAttestationRecord,
            f"{item.attestation_id}:{item.attestation_version}",
        )
        payload = dict(attestation.payload or {}) if attestation is not None else {}
        if (
            attestation is None
            or attestation.status != "current"
            or attestation.transcript_id != item.transcript_id
            or attestation.transcript_version != item.transcript_version
            or attestation.speaker_mapping_id != item.speaker_mapping_id
            or attestation.speaker_mapping_version != item.speaker_mapping_version
        ):
            raise self._durable_upstream_error("transcript attestation")
        return payload

    def _require_durable_chat_export(self, db, item) -> dict:
        export = db.get(
            ChatExportRecord,
            f"{item.chat_export_id}:{item.chat_export_version}",
        )
        payload = dict(export.payload or {}) if export is not None else {}
        if (
            export is None
            or export.status != "current"
            or export.transcript_id != item.transcript_id
            or export.transcript_version != item.transcript_version
            or export.canonical_checksum_sha256 != item.chat_export_checksum_sha256
            or payload.get("speaker_mapping_id") != item.speaker_mapping_id
            or payload.get("speaker_mapping_version") != item.speaker_mapping_version
            or payload.get("attestation_id") != item.attestation_id
            or payload.get("attestation_version") != item.attestation_version
            or payload.get("parser_version") != item.parser_version
            or payload.get("serializer_version") != item.serializer_version
            or payload.get("source_audio_file_id") != item.source_audio_file_id
            or payload.get("source_asset_version") != item.source_asset_version
            or payload.get("source_checksum_sha256") != item.source_checksum_sha256
            or payload.get("normalized_asset_version") != item.normalized_asset_version
            or payload.get("normalized_checksum_sha256") != item.normalized_checksum_sha256
            or (payload.get("round_trip") or {}).get("status") != "verified"
        ):
            raise self._durable_upstream_error("CHAT export")
        return payload

    def _validate_durable_speech_dependencies(self, db, model, item) -> None:
        if model is NormalizedAudioAssetRecord:
            audio = db.get(AudioFileRecord, item.source_audio_file_id)
            if (
                audio is None
                or audio.source_asset_version != item.source_asset_version
                or audio.checksum_sha256 != item.source_checksum_sha256
            ):
                raise self._durable_upstream_error("source audio lineage")
            return
        self._require_durable_transcript(db, item)
        if model is SpeakerMappingRecord:
            return
        if model is LimitationAcknowledgmentRecord:
            return
        self._require_durable_mapping(db, item)
        if model is TranscriptAttestationRecord:
            self._require_durable_acknowledgment_refs(
                db,
                transcript_id=item.transcript_id,
                transcript_version=item.transcript_version,
                acknowledgment_refs=item.acknowledgment_refs,
                validator_version=item.qa_validator_version,
            )
            return
        attestation_payload = self._require_durable_attestation(db, item)
        if model is ChatExportRecord:
            self._require_durable_acknowledgment_refs(
                db,
                transcript_id=item.transcript_id,
                transcript_version=item.transcript_version,
                acknowledgment_refs=attestation_payload.get("acknowledgment_refs", []),
                validator_version=str(attestation_payload.get("qa_validator_version", "")),
            )
            self._require_durable_audio_lineage(db, item)
            return
        if model is FindingsResultRecord:
            self._require_durable_chat_export(db, item)
            self._require_durable_audio_lineage(db, item)
            validator_version = str(attestation_payload.get("qa_validator_version", ""))
            self._require_durable_acknowledgment_refs(
                db,
                transcript_id=item.transcript_id,
                transcript_version=item.transcript_version,
                acknowledgment_refs=item.acknowledgment_refs,
                validator_version=validator_version,
            )
            if sorted(attestation_payload.get("acknowledgment_refs", [])) != sorted(
                [list(reference) for reference in item.acknowledgment_refs]
            ):
                raise self._durable_upstream_error("attestation acknowledgment references")
            return
        raise TypeError(model)

    def _sync_speech_pipeline_record(self, db, model, key: str, item, factory) -> None:
        group_field, group_value, version_field = self._speech_group(model, item)
        group_rows = self._lock_speech_group(
            db,
            model,
            group_field,
            group_value,
        )
        row = next((candidate for candidate in group_rows if candidate.record_key == key), None)
        incoming_payload = item.model_dump(mode="json")
        if row is None:
            new_row = factory()
            incoming_status = incoming_payload["status"]
            if self._is_current_speech_status(incoming_status):
                self._validate_durable_speech_dependencies(db, model, item)
                current_rows = [
                    candidate
                    for candidate in group_rows
                    if self._is_current_speech_status(candidate.status)
                ]
                highest_current = max(
                    current_rows,
                    key=lambda candidate: getattr(candidate, version_field),
                    default=None,
                )
                if (
                    highest_current is not None
                    and getattr(highest_current, version_field) >= getattr(new_row, version_field)
                ):
                    incoming_payload["status"] = "stale"
                    new_row.status = "stale"
                    new_row.payload = incoming_payload
                else:
                    for current_row in current_rows:
                        self._set_speech_row_stale(current_row)
            db.add(new_row)
            return
        stored_payload = deepcopy(row.payload)
        stored_immutable = self._without_speech_lifecycle(stored_payload)
        incoming_immutable = self._without_speech_lifecycle(incoming_payload)
        if stored_immutable != incoming_immutable:
            raise ValueError(f"Immutable speech artifact {key} conflicts with the stored version.")
        stored_status = stored_payload["status"]
        incoming_status = incoming_payload["status"]
        if self._is_current_speech_status(stored_status):
            if not self._is_current_speech_status(incoming_status):
                stored_status = "stale"
        else:
            stored_status = "stale"
        stored_payload["status"] = stored_status
        stored_payload["stale_causes"] = self._merge_stale_causes(
            list(stored_payload.get("stale_causes", [])),
            list(incoming_payload.get("stale_causes", [])),
        )
        row.status = stored_status
        row.payload = stored_payload

    @staticmethod
    def _without_speech_lifecycle(payload: dict) -> dict:
        value = deepcopy(payload)
        value.pop("status", None)
        value.pop("stale_causes", None)
        return value

    def _sync_audio_current_pointers(self, db) -> None:
        db.flush()
        for audio_row in db.query(AudioFileRecord).all():
            current = (
                db.query(NormalizedAudioAssetRecord)
                .filter_by(
                    source_audio_file_id=audio_row.audio_file_id,
                    status="current",
                )
                .order_by(NormalizedAudioAssetRecord.asset_version.desc())
                .first()
            )
            audio_row.current_normalized_asset_version = (
                current.asset_version if current is not None else None
            )
            audio_row.current_normalized_checksum_sha256 = (
                current.normalized_checksum_sha256 if current is not None else None
            )
            if current is not None:
                normalized = NormalizedAudioAsset.model_validate(current.payload)
                if normalized.provenance is not None:
                    audio_row.duration_seconds = (
                        normalized.provenance.source_frame_count
                        / normalized.provenance.source_sample_rate_hz
                    )
                    audio_row.sample_rate_hz = (
                        normalized.provenance.source_sample_rate_hz
                    )
                    audio_row.channels = normalized.provenance.source_channels

    @staticmethod
    def _durable_normalized_versions(db) -> dict[str, int | None]:
        return {
            row.audio_file_id: row.current_normalized_asset_version
            for row in db.query(AudioFileRecord).all()
        }

    def _invalidate_normalization_rereview(
        self,
        db,
        previous_versions: dict[str, int | None],
    ) -> None:
        for audio_row in db.query(AudioFileRecord).all():
            previous_version = previous_versions.get(audio_row.audio_file_id)
            current_version = audio_row.current_normalized_asset_version
            if (
                previous_version is None
                or current_version is None
                or previous_version == current_version
            ):
                continue
            session_row = db.get(SessionRecord, audio_row.session_id)
            if session_row is None or session_row.transcript_id is None:
                continue
            cause = {
                "code": "NORMALIZATION_LINEAGE_CHANGED",
                "affected_resource_id": audio_row.audio_file_id,
                "affected_resource_version": str(current_version),
                "validator_or_rule_version": "speech-lineage-v1.7.0",
            }
            for model in (
                LimitationAcknowledgmentRecord,
                TranscriptAttestationRecord,
            ):
                rows = (
                    db.query(model)
                    .filter(
                        model.transcript_id == session_row.transcript_id,
                        model.status == "current",
                    )
                    .all()
                )
                for row in rows:
                    self._set_speech_row_stale(row, [cause])

    def _enforce_durable_speech_dependency_closure(self, db) -> None:
        cause = {
            "code": "UPSTREAM_LINEAGE_CHANGED",
            "affected_resource_id": "speech_pipeline",
            "affected_resource_version": "current",
            "validator_or_rule_version": "speech-lineage-v1.7.0",
        }
        for model, schema in (
            (TranscriptAttestationRecord, TranscriptAttestation),
            (ChatExportRecord, ChatExport),
            (FindingsResultRecord, FindingsProjection),
        ):
            rows = db.query(model).filter(model.status == "current").all()
            for row in rows:
                try:
                    item = schema.model_validate(row.payload)
                    self._validate_durable_speech_dependencies(
                        db,
                        model,
                        item,
                    )
                except (TypeError, ValueError):
                    self._set_speech_row_stale(row, [cause])

    def _sync_speech_pipeline_rows(self, db) -> None:
        for item in self.normalized_audio_assets.values():
            key = f"{item.source_audio_file_id}:{item.asset_version}"
            self._sync_speech_pipeline_record(
                db,
                NormalizedAudioAssetRecord,
                key,
                item,
                lambda item=item, key=key: NormalizedAudioAssetRecord(
                    record_key=key,
                    organization_id=item.organization_id,
                    session_id=item.session_id,
                    source_audio_file_id=item.source_audio_file_id,
                    source_asset_version=item.source_asset_version,
                    asset_version=item.asset_version,
                    source_checksum_sha256=item.source_checksum_sha256,
                    normalized_checksum_sha256=item.normalized_checksum_sha256,
                    status=item.status.value,
                    payload=item.model_dump(mode="json"),
                    created_at=item.created_at,
                ),
            )
        for item in self.speaker_mappings.values():
            key = f"{item.mapping_id}:{item.mapping_version}"
            self._sync_speech_pipeline_record(
                db,
                SpeakerMappingRecord,
                key,
                item,
                lambda item=item, key=key: SpeakerMappingRecord(
                    record_key=key,
                    organization_id=item.organization_id,
                    session_id=item.session_id,
                    mapping_id=item.mapping_id,
                    mapping_version=item.mapping_version,
                    transcript_id=item.transcript_id,
                    transcript_version=item.transcript_version,
                    status=item.status.value,
                    payload=item.model_dump(mode="json"),
                    created_at=item.confirmed_at,
                ),
            )
        for item in self.transcript_attestations.values():
            key = f"{item.attestation_id}:{item.attestation_version}"
            self._sync_speech_pipeline_record(
                db,
                TranscriptAttestationRecord,
                key,
                item,
                lambda item=item, key=key: TranscriptAttestationRecord(
                    record_key=key,
                    organization_id=item.organization_id,
                    session_id=item.session_id,
                    attestation_id=item.attestation_id,
                    attestation_version=item.attestation_version,
                    transcript_id=item.transcript_id,
                    transcript_version=item.transcript_version,
                    speaker_mapping_id=item.speaker_mapping_id,
                    speaker_mapping_version=item.speaker_mapping_version,
                    status=item.status.value,
                    payload=item.model_dump(mode="json"),
                    created_at=item.attested_at,
                ),
            )
        for item in self.limitation_acknowledgments.values():
            key = f"{item.acknowledgment_id}:{item.acknowledgment_version}"
            self._sync_speech_pipeline_record(
                db,
                LimitationAcknowledgmentRecord,
                key,
                item,
                lambda item=item, key=key: LimitationAcknowledgmentRecord(
                    record_key=key,
                    organization_id=item.organization_id,
                    session_id=item.session_id,
                    acknowledgment_id=item.acknowledgment_id,
                    acknowledgment_version=item.acknowledgment_version,
                    transcript_id=item.transcript_id,
                    transcript_version=item.transcript_version,
                    limitation_code=item.limitation_code,
                    validator_version=item.validator_version,
                    status=item.status.value,
                    payload=item.model_dump(mode="json"),
                    created_at=item.acknowledged_at,
                ),
            )
        for item in self.chat_exports.values():
            key = f"{item.export_id}:{item.export_version}"
            self._sync_speech_pipeline_record(
                db,
                ChatExportRecord,
                key,
                item,
                lambda item=item, key=key: ChatExportRecord(
                    record_key=key,
                    organization_id=item.organization_id,
                    session_id=item.session_id,
                    export_id=item.export_id,
                    export_version=item.export_version,
                    transcript_id=item.transcript_id,
                    transcript_version=item.transcript_version,
                    canonical_checksum_sha256=item.canonical_checksum_sha256,
                    source_audio_file_id=item.source_audio_file_id,
                    source_asset_version=item.source_asset_version,
                    source_checksum_sha256=item.source_checksum_sha256,
                    normalized_asset_version=item.normalized_asset_version,
                    normalized_checksum_sha256=item.normalized_checksum_sha256,
                    round_trip_status=item.round_trip.status.value,
                    status=item.status.value,
                    payload=item.model_dump(mode="json"),
                    created_at=item.created_at,
                ),
            )
        for item in self.findings_results.values():
            key = f"{item.findings_id}:{item.findings_version}"
            self._sync_speech_pipeline_record(
                db,
                FindingsResultRecord,
                key,
                item,
                lambda item=item, key=key: FindingsResultRecord(
                    record_key=key,
                    organization_id=item.organization_id,
                    session_id=item.session_id,
                    findings_id=item.findings_id,
                    findings_version=item.findings_version,
                    transcript_id=item.transcript_id,
                    transcript_version=item.transcript_version,
                    speaker_mapping_id=item.speaker_mapping_id,
                    speaker_mapping_version=item.speaker_mapping_version,
                    attestation_id=item.attestation_id,
                    attestation_version=item.attestation_version,
                    chat_export_id=item.chat_export_id,
                    chat_export_version=item.chat_export_version,
                    source_audio_file_id=item.source_audio_file_id,
                    source_asset_version=item.source_asset_version,
                    source_checksum_sha256=item.source_checksum_sha256,
                    normalized_asset_version=item.normalized_asset_version,
                    normalized_checksum_sha256=item.normalized_checksum_sha256,
                    chat_export_checksum_sha256=item.chat_export_checksum_sha256,
                    algorithm_checksum_sha256=item.algorithm_checksum_sha256,
                    tokenizer_profile_id=(
                        item.tokenizer_profile.profile_id if item.tokenizer_profile else None
                    ),
                    tokenizer_profile_version=(
                        item.tokenizer_profile.profile_version if item.tokenizer_profile else None
                    ),
                    tokenizer_profile_checksum_sha256=(
                        item.tokenizer_profile.profile_checksum_sha256
                        if item.tokenizer_profile
                        else None
                    ),
                    feature_schema_version=item.feature_schema_version,
                    status=item.status.value,
                    payload=item.model_dump(mode="json"),
                    created_at=item.generated_at,
                ),
            )

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

    def has_active_org_admin_membership(self, user_id: str, organization_id: str) -> bool:
        with self.SessionLocal() as db:
            return (
                db.query(OrganizationMembershipRecord)
                .filter_by(
                    organization_id=organization_id,
                    user_id=user_id,
                    role="org_admin",
                    active=True,
                )
                .first()
                is not None
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
        audit = validate_audit_event(
            actor_id=actor_id,
            action=action,
            target_id=target_id,
            outcome=outcome,
            correlation_id=correlation_id,
            message=message,
        ).as_dict()
        audit["organization_id"] = organization_id
        with self.SessionLocal() as db:
            db.add(self._audit_to_record(audit))
            db.commit()
        self.audit_log.append(audit)

    def _case_to_record(self, case: ChildCase) -> ChildCaseRecord:
        return ChildCaseRecord(
            case_id=case.case_id,
            organization_id=case.organization_id,
            care_team_user_ids=case.care_team_user_ids,
            primary_therapist_user_id=case.primary_therapist_user_id,
            child_code=case.child_code,
            nickname=case.nickname,
            age_months=case.age_months,
            language=case.language,
            consent_status=case.consent_status,
            review_priority=case.review_priority,
            notes=case.notes,
            version=case.version,
            latest_session_date=case.latest_session_date,
            latest_session_status=case.latest_session_status.value
            if hasattr(case.latest_session_status, "value")
            else str(case.latest_session_status),
            latest_report_status=case.latest_report_status.value
            if hasattr(case.latest_report_status, "value")
            else str(case.latest_report_status),
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    def _privacy_operation_to_record(self, operation: PrivacyOperation) -> PrivacyOperationRecord:
        return PrivacyOperationRecord(
            privacy_operation_id=operation.privacy_operation_id,
            organization_id=operation.organization_id,
            case_id=operation.case_id,
            operation_type=operation.operation_type,
            status=operation.status,
            requested_by=operation.requested_by,
            requester_role=operation.requester_role,
            reason=operation.reason,
            admin_note=operation.admin_note,
            retention_days=operation.retention_days,
            legal_hold=operation.legal_hold,
            deletion_review_required=operation.deletion_review_required,
            preserve_evidence=operation.preserve_evidence,
            eligible_for_deletion_at=operation.eligible_for_deletion_at,
            completed_at=operation.completed_at,
            evidence_retained=operation.evidence_retained,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
        )

    def _privacy_operation_from_record(self, row: PrivacyOperationRecord) -> PrivacyOperation:
        return PrivacyOperation(
            privacy_operation_id=row.privacy_operation_id,
            organization_id=row.organization_id,
            case_id=row.case_id,
            operation_type=row.operation_type,
            status=row.status,
            requested_by=row.requested_by,
            requester_role=row.requester_role,
            reason=row.reason,
            admin_note=row.admin_note,
            retention_days=row.retention_days,
            legal_hold=row.legal_hold,
            deletion_review_required=row.deletion_review_required,
            preserve_evidence=row.preserve_evidence,
            eligible_for_deletion_at=row.eligible_for_deletion_at,
            completed_at=row.completed_at,
            evidence_retained=row.evidence_retained,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _case_from_record(self, row: ChildCaseRecord) -> ChildCase:
        return ChildCase(
            case_id=row.case_id,
            organization_id=row.organization_id,
            care_team_user_ids=list(row.care_team_user_ids or []),
            primary_therapist_user_id=row.primary_therapist_user_id,
            child_code=row.child_code,
            nickname=row.nickname,
            age_months=row.age_months,
            language=row.language,
            consent_status=row.consent_status,
            review_priority=row.review_priority,
            notes=row.notes,
            version=row.version,
            latest_session_date=row.latest_session_date,
            latest_session_status=ReviewStatus(row.latest_session_status),
            latest_report_status=ReviewStatus(row.latest_report_status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _membership_to_record(self, membership: OrganizationMembership) -> OrganizationMembershipRecord:
        return OrganizationMembershipRecord(
            membership_id=membership.membership_id,
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            role=membership.role,
            active=membership.active,
            created_at=membership.created_at,
        )

    def _membership_from_record(
        self,
        row: OrganizationMembershipRecord,
        *,
        display_name: str,
    ) -> OrganizationMembership:
        return OrganizationMembership(
            membership_id=row.membership_id,
            organization_id=row.organization_id,
            user_id=row.user_id,
            display_name=display_name,
            role=row.role,
            active=row.active,
            created_at=row.created_at,
        )

    def _invitation_to_record(self, invitation: OrganizationInvitation) -> OrganizationInvitationRecord:
        return OrganizationInvitationRecord(
            invitation_id=invitation.invitation_id,
            organization_id=invitation.organization_id,
            email=invitation.email,
            display_name=invitation.display_name,
            role=invitation.role,
            status=invitation.status,
            invited_by=invitation.invited_by,
            accepted_user_id=invitation.accepted_user_id,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
            accepted_at=invitation.accepted_at,
        )

    def _invitation_from_record(self, row: OrganizationInvitationRecord) -> OrganizationInvitation:
        return OrganizationInvitation(
            invitation_id=row.invitation_id,
            organization_id=row.organization_id,
            email=row.email,
            display_name=row.display_name,
            role=row.role,
            status=row.status,
            invited_by=row.invited_by,
            accepted_user_id=row.accepted_user_id,
            expires_at=row.expires_at,
            created_at=row.created_at,
            accepted_at=row.accepted_at,
        )

    def _care_team_assignment_to_record(
        self,
        assignment: CareTeamAssignment,
    ) -> CaseCareTeamAssignmentRecord:
        return CaseCareTeamAssignmentRecord(
            assignment_id=assignment.assignment_id,
            organization_id=assignment.organization_id,
            case_id=assignment.case_id,
            user_id=assignment.user_id,
            role=assignment.role,
            active=assignment.active,
            created_at=assignment.created_at,
        )

    def _care_team_assignment_from_record(
        self,
        row: CaseCareTeamAssignmentRecord,
    ) -> CareTeamAssignment:
        return CareTeamAssignment(
            assignment_id=row.assignment_id,
            organization_id=row.organization_id,
            case_id=row.case_id,
            user_id=row.user_id,
            role=row.role,
            active=row.active,
            created_at=row.created_at,
        )

    def _session_to_record(self, session: TherapySession) -> SessionRecord:
        return SessionRecord(**session.model_dump(mode="python"))

    def _session_from_record(self, row: SessionRecord) -> TherapySession:
        return TherapySession(
            session_id=row.session_id,
            case_id=row.case_id,
            organization_id=row.organization_id,
            version=row.version,
            session_date=row.session_date,
            session_type=row.session_type,
            notes=row.notes,
            status=row.status,
            transcript_id=row.transcript_id,
            feature_set_id=row.feature_set_id,
            ml_result_id=row.ml_result_id,
            ai_review_id=row.ai_review_id,
            report_id=row.report_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _transcript_to_record(self, transcript: Transcript) -> TranscriptRecord:
        return TranscriptRecord(
            transcript_id=transcript.transcript_id,
            session_id=transcript.session_id,
            case_id=transcript.case_id,
            organization_id=transcript.organization_id,
            source=transcript.source,
            raw_text=transcript.raw_text,
            utterances=[item.model_dump(mode="json") for item in transcript.utterances],
            qa_status=transcript.qa_status.value,
            qa_issues=[item.model_dump(mode="json") for item in transcript.qa_issues],
            review_status=transcript.review_status.value,
            therapist_attested=transcript.therapist_attested,
            attestation_reason=transcript.attestation_reason,
            asr_profile=transcript.asr_profile,
            asr_provenance=transcript.asr_provenance,
            raw_speaker_labels=transcript.raw_speaker_labels,
            speech_pipeline_payload={
                "chat_metadata": transcript.chat_metadata,
                "orphan_dependent_tiers": [
                    item.model_dump(mode="json") for item in transcript.orphan_dependent_tiers
                ],
                "malformed_lines": transcript.malformed_lines,
                "parser_version": transcript.parser_version,
                "import_timestamp": transcript.import_timestamp.isoformat(),
                "created_at": transcript.created_at.isoformat(),
                "updated_at": transcript.updated_at.isoformat(),
            },
            version=transcript.version,
            created_at=transcript.created_at,
            updated_at=transcript.updated_at,
        )

    def _transcript_from_record(self, row: TranscriptRecord) -> Transcript:
        pipeline_payload = dict(row.speech_pipeline_payload or {})
        return Transcript.model_validate(
            {
                "transcript_id": row.transcript_id,
                "session_id": row.session_id,
                "case_id": row.case_id,
                "organization_id": row.organization_id,
                "source": row.source,
                "raw_text": row.raw_text,
                "utterances": row.utterances,
                "qa_status": row.qa_status,
                "qa_issues": row.qa_issues,
                "review_status": row.review_status,
                "therapist_attested": row.therapist_attested,
                "attestation_reason": row.attestation_reason,
                "asr_profile": row.asr_profile,
                "asr_provenance": row.asr_provenance,
                "raw_speaker_labels": row.raw_speaker_labels,
                "chat_metadata": pipeline_payload.get("chat_metadata", {}),
                "orphan_dependent_tiers": pipeline_payload.get("orphan_dependent_tiers", []),
                "malformed_lines": pipeline_payload.get("malformed_lines", []),
                "parser_version": pipeline_payload.get("parser_version", "chat-basic-v1"),
                "import_timestamp": pipeline_payload.get("import_timestamp"),
                "version": row.version,
                "created_at": pipeline_payload.get("created_at", row.created_at),
                "updated_at": pipeline_payload.get("updated_at", row.updated_at),
            }
        )

    def _feature_to_record(self, feature_set: FeatureSet) -> FeatureSetRecord:
        return FeatureSetRecord(
            feature_set_id=feature_set.feature_set_id,
            organization_id=feature_set.organization_id,
            session_id=feature_set.session_id,
            transcript_id=feature_set.transcript_id,
            transcript_version=feature_set.transcript_version,
            schema_version=feature_set.schema_version,
            therapist_attested=feature_set.therapist_attested,
            warnings=feature_set.warnings,
            features=[item.model_dump(mode="json") for item in feature_set.features],
            review_status=feature_set.review_status.value,
            speaker_mapping_id=feature_set.speaker_mapping_id,
            speaker_mapping_version=feature_set.speaker_mapping_version,
            attestation_id=feature_set.attestation_id,
            attestation_version=feature_set.attestation_version,
            chat_export_id=feature_set.chat_export_id,
            chat_export_version=feature_set.chat_export_version,
            tokenizer_profile_id=feature_set.tokenizer_profile_id,
            tokenizer_profile_version=feature_set.tokenizer_profile_version,
            tokenizer_profile_checksum_sha256=feature_set.tokenizer_profile_checksum_sha256,
            extracted_at=feature_set.extracted_at,
        )

    def _feature_from_record(self, row: FeatureSetRecord) -> FeatureSet:
        return FeatureSet.model_validate(
            {
                "feature_set_id": row.feature_set_id,
                "organization_id": row.organization_id,
                "session_id": row.session_id,
                "transcript_id": row.transcript_id,
                "transcript_version": row.transcript_version,
                "schema_version": row.schema_version,
                "therapist_attested": row.therapist_attested,
                "warnings": row.warnings,
                "features": row.features,
                "review_status": row.review_status,
                "speaker_mapping_id": row.speaker_mapping_id,
                "speaker_mapping_version": row.speaker_mapping_version,
                "attestation_id": row.attestation_id,
                "attestation_version": row.attestation_version,
                "chat_export_id": row.chat_export_id,
                "chat_export_version": row.chat_export_version,
                "tokenizer_profile_id": row.tokenizer_profile_id,
                "tokenizer_profile_version": row.tokenizer_profile_version,
                "tokenizer_profile_checksum_sha256": row.tokenizer_profile_checksum_sha256,
                "extracted_at": row.extracted_at,
            }
        )

    def _audio_to_record(self, audio_file: AudioFileMetadata) -> AudioFileRecord:
        return AudioFileRecord(**audio_file.model_dump(mode="python"))

    def _audio_from_record(self, row: AudioFileRecord) -> AudioFileMetadata:
        return AudioFileMetadata(
            audio_file_id=row.audio_file_id,
            organization_id=row.organization_id,
            session_id=row.session_id,
            case_id=row.case_id,
            original_filename=row.original_filename,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            storage_mode=row.storage_mode,
            object_key=row.object_key,
            upload_status=row.upload_status,
            duration_seconds=row.duration_seconds,
            sample_rate_hz=row.sample_rate_hz,
            channels=row.channels,
            estimated_noise_level=row.estimated_noise_level,
            silence_ratio=row.silence_ratio,
            checksum_sha256=row.checksum_sha256,
            source_asset_version=row.source_asset_version,
            current_normalized_asset_version=row.current_normalized_asset_version,
            current_normalized_checksum_sha256=row.current_normalized_checksum_sha256,
            uploaded_at=row.uploaded_at,
            storage_delete_status=row.storage_delete_status,
            retained=row.retained,
            created_at=row.created_at,
        )

    def _ai_review_to_record(self, review: AiReview) -> AiReviewRecord:
        return AiReviewRecord(
            ai_review_id=review.ai_review_id,
            organization_id=review.organization_id,
            session_id=review.session_id,
            payload=review.model_dump(mode="json"),
            review_priority=review.review_priority,
            therapist_review_status=review.therapist_review_status.value,
            created_at=review.created_at,
        )

    def _ml_result_to_record(self, result: MLResult) -> MLResultRecord:
        return MLResultRecord(
            result_id=result.result_id,
            organization_id=result.organization_id,
            session_id=result.session_id,
            transcript_id=result.transcript_id,
            payload=result.model_dump(mode="json"),
            created_at=result.generated_at,
        )

    def _report_to_record(self, report: Report) -> ReportRecord:
        data = report.model_dump(mode="python")
        json_data = report.model_dump(mode="json")
        for field in (
            "safety_validation_result",
            "finalized_safety_result",
            "signed_snapshot",
            "session_goals",
            "generated_from_versions",
            "sections",
        ):
            data[field] = json_data[field]
        return ReportRecord(**data)

    def _report_from_record(self, row: ReportRecord) -> Report:
        return Report(
            report_id=row.report_id,
            session_id=row.session_id,
            case_id=row.case_id,
            organization_id=row.organization_id,
            report_type=row.report_type,
            title=row.title,
            markdown=row.markdown,
            html=row.html,
            status=row.status,
            therapist_signoff_status=row.therapist_signoff_status,
            limitation_text=row.limitation_text,
            export_timestamp=row.export_timestamp,
            created_at=row.created_at,
            updated_at=row.updated_at,
            requested_provider=row.requested_provider,
            actual_provider=row.actual_provider,
            provider_version=row.provider_version,
            fallback_reason=row.fallback_reason,
            rewrite_attempted=row.rewrite_attempted,
            rewrite_succeeded=row.rewrite_succeeded,
            safety_validation_result=row.safety_validation_result,
            finalized_safety_result=row.finalized_safety_result,
            finalization_blocked=row.finalization_blocked,
            validator_version=row.validator_version,
            rule_set_version=row.rule_set_version,
            input_hash=row.input_hash,
            version=row.version,
            signed_by=row.signed_by,
            signed_at=row.signed_at,
            signed_snapshot_version=row.signed_snapshot_version,
            signed_snapshot_hash=row.signed_snapshot_hash,
            signed_snapshot=row.signed_snapshot,
            supersedes_report_id=row.supersedes_report_id,
            revision_number=row.revision_number,
            ai_drafting_requested=row.ai_drafting_requested,
            ai_drafting_enabled=row.ai_drafting_enabled,
            ai_drafting_provider=row.ai_drafting_provider,
            ai_drafting_model=row.ai_drafting_model,
            ai_drafting_region=row.ai_drafting_region,
            ai_drafting_input_hash=row.ai_drafting_input_hash,
            transcript_id=row.transcript_id,
            feature_result_id=row.feature_result_id,
            ml_result_id=row.ml_result_id,
            ml_skipped_reason=row.ml_skipped_reason,
            validation_summary=row.validation_summary,
            feature_schema_version=row.feature_schema_version,
            therapist_notes=row.therapist_notes,
            session_goals=row.session_goals,
            generated_from_versions=row.generated_from_versions,
            sections=row.sections,
        )

    def _goal_to_record(self, goal: TherapyGoal) -> TherapyGoalRecord:
        return TherapyGoalRecord(**goal.model_dump(mode="python"))

    def _goal_from_record(self, row: TherapyGoalRecord) -> TherapyGoal:
        return TherapyGoal(
            goal_id=row.goal_id,
            organization_id=row.organization_id,
            case_id=row.case_id,
            title=row.title,
            target=row.target,
            status=row.status,
            notes=row.notes,
            retained=row.retained,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _job_to_record(self, job: ProcessingJob) -> ProcessingJobRecord:
        return ProcessingJobRecord(**job.model_dump(mode="python"))

    def _job_from_record(self, row: ProcessingJobRecord) -> ProcessingJob:
        return ProcessingJob(
            job_id=row.job_id,
            organization_id=row.organization_id,
            session_id=row.session_id,
            status=row.status,
            message=row.message,
            error_code=row.error_code,
            details=row.details,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _audit_to_record(self, item: dict) -> AuditLogRecord:
        return AuditLogRecord(
            audit_id=item["audit_id"],
            organization_id=item.get("organization_id", "pilot_org_001"),
            actor_id=item.get("actor_id", "system"),
            action=item["action"],
            target_id=item["target_id"],
            outcome=item.get("outcome", "success"),
            correlation_id=item.get("correlation_id", "local"),
            message=item["message"],
            timestamp=_parse_datetime(item["timestamp"]),
        )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
INVITATION_EXPIRY_DAYS = 7
