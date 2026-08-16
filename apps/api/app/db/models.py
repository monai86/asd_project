"""SQLAlchemy model boundary for the lingualens PostgreSQL-ready schema."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class OrganizationRecord(Base):
    __tablename__ = "organizations"

    organization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    pilot_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class OrganizationSettingsRecord(Base):
    __tablename__ = "organization_settings"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), primary_key=True)
    ai_drafting_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    default_retention_region: Mapped[str] = mapped_column(String(64), default="local_pilot", nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class UserProfileRecord(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class OrganizationMembershipRecord(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_organization_memberships_org_user"),)

    membership_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class OrganizationInvitationRecord(Base):
    __tablename__ = "organization_invitations"

    invitation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    invited_by: Mapped[str] = mapped_column(String(128), nullable=False)
    accepted_user_id: Mapped[str | None] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CaseCareTeamAssignmentRecord(Base):
    __tablename__ = "case_care_team_assignments"
    __table_args__ = (UniqueConstraint("organization_id", "case_id", "user_id", name="uq_case_care_team_org_case_user"),)

    assignment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), default="clinician", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IdentityProfileRecord(Base):
    __tablename__ = "identity_profiles"

    identity_profile_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    encrypted_payload_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    key_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RegionalRetentionPolicyRecord(Base):
    __tablename__ = "regional_retention_policies"
    __table_args__ = (UniqueConstraint("organization_id", "region", "record_type", name="uq_retention_policy_org_region_record"),)

    retention_policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    record_type: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    legal_hold_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    consent_record_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(64), default="clinical_workflow", nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(512))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationRecord(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False, index=True)
    recipient_user_id: Mapped[str] = mapped_column(ForeignKey("user_profiles.user_id"), nullable=False, index=True)
    message_type: Mapped[str] = mapped_column(String(64), nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(64), default="queued", nullable=False, index=True)
    safe_message: Mapped[str] = mapped_column(Text, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ChildCaseRecord(Base):
    __tablename__ = "child_cases"

    case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    care_team_user_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    primary_therapist_user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    child_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    nickname: Mapped[str | None] = mapped_column(String(128))
    age_months: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(128), default="English", nullable=False)
    consent_status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False, index=True)
    review_priority: Mapped[str] = mapped_column(String(32), default="low", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    latest_session_date: Mapped[str | None] = mapped_column(String(32))
    latest_session_status: Mapped[str] = mapped_column(String(32), default="Draft", nullable=False)
    latest_report_status: Mapped[str] = mapped_column(String(32), default="Draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    sessions: Mapped[list["SessionRecord"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class TherapyGoalRecord(Base):
    __tablename__ = "therapy_goals"

    goal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    target: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False, index=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    retained: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    session_date: Mapped[str] = mapped_column(String(32), nullable=False)
    session_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Draft", nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    transcript_id: Mapped[str | None] = mapped_column(String(64))
    feature_set_id: Mapped[str | None] = mapped_column(String(64))
    ml_result_id: Mapped[str | None] = mapped_column(String(64))
    ai_review_id: Mapped[str | None] = mapped_column(String(64))
    report_id: Mapped[str | None] = mapped_column(String(64))
    cues_acknowledged_at: Mapped[str | None] = mapped_column(String(64))
    cues_acknowledged_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case: Mapped[ChildCaseRecord] = relationship(back_populates="sessions")


class TranscriptRecord(Base):
    __tablename__ = "transcripts"

    transcript_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    utterances: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    qa_status: Mapped[str] = mapped_column(String(32), default="NOT_RUN", nullable=False)
    qa_issues: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="Needs Review", nullable=False)
    therapist_attested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attestation_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class FeatureSetRecord(Base):
    __tablename__ = "feature_sets"

    feature_set_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.transcript_id"), nullable=False, index=True)
    transcript_version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    therapist_attested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    features: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="Ready", nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AudioFileRecord(Base):
    __tablename__ = "audio_files"

    audio_file_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_mode: Mapped[str] = mapped_column(String(64), default="metadata_only", nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(512))
    upload_status: Mapped[str] = mapped_column(String(64), default="pending", nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    sample_rate_hz: Mapped[int | None] = mapped_column(Integer)
    channels: Mapped[int | None] = mapped_column(Integer)
    estimated_noise_level: Mapped[float | None] = mapped_column(Float)
    silence_ratio: Mapped[float | None] = mapped_column(Float)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_delete_status: Mapped[str | None] = mapped_column(String(128))
    retained: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AiReviewRecord(Base):
    __tablename__ = "ai_reviews"

    ai_review_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    review_priority: Mapped[str] = mapped_column(String(32), default="low", nullable=False)
    therapist_review_status: Mapped[str] = mapped_column(String(32), default="Needs Review", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class MLResultRecord(Base):
    __tablename__ = "ml_results"

    result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcripts.transcript_id"), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReportRecord(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    report_type: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    html: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="Draft", nullable=False)
    therapist_signoff_status: Mapped[str] = mapped_column(String(32), default="Needs Review", nullable=False)
    limitation_text: Mapped[str] = mapped_column(Text, nullable=False)
    export_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    requested_provider: Mapped[str] = mapped_column(String(64), default="template", nullable=False)
    actual_provider: Mapped[str] = mapped_column(String(64), default="template", nullable=False)
    provider_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    fallback_reason: Mapped[str | None] = mapped_column(Text)
    rewrite_attempted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rewrite_succeeded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    safety_validation_result: Mapped[dict | None] = mapped_column(JSON)
    finalized_safety_result: Mapped[dict | None] = mapped_column(JSON)
    finalization_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validator_version: Mapped[str] = mapped_column(String(64), default="safety-validator-v1.0", nullable=False)
    rule_set_version: Mapped[str] = mapped_column(String(64), default="rules-v1.0", nullable=False)
    input_hash: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    signed_by: Mapped[str | None] = mapped_column(String(256))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_snapshot_version: Mapped[int | None] = mapped_column(Integer)
    signed_snapshot_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    signed_snapshot: Mapped[dict | None] = mapped_column(JSON)
    supersedes_report_id: Mapped[str | None] = mapped_column(String(64), index=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ai_drafting_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_drafting_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_drafting_provider: Mapped[str | None] = mapped_column(String(64))
    ai_drafting_model: Mapped[str | None] = mapped_column(String(128))
    ai_drafting_region: Mapped[str | None] = mapped_column(String(64))
    ai_drafting_input_hash: Mapped[str | None] = mapped_column(String(64))

    transcript_id: Mapped[str | None] = mapped_column(String(64))
    feature_result_id: Mapped[str | None] = mapped_column(String(64))
    ml_result_id: Mapped[str | None] = mapped_column(String(64))
    ml_skipped_reason: Mapped[str | None] = mapped_column(Text)
    validation_summary: Mapped[str | None] = mapped_column(Text)
    feature_schema_version: Mapped[str | None] = mapped_column(String(64))
    therapist_notes: Mapped[str | None] = mapped_column(Text)
    session_goals: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    generated_from_versions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sections: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)


class ProcessingJobRecord(Base):
    __tablename__ = "processing_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(128))
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class PrivacyOperationRecord(Base):
    __tablename__ = "privacy_operations"

    privacy_operation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("child_cases.case_id"), nullable=False, index=True)
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    requester_role: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    admin_note: Mapped[str] = mapped_column(Text, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    legal_hold: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deletion_review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    preserve_evidence: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    eligible_for_deletion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_retained: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(64), default="pilot_org_001", nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, default="local")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class JobAttemptRecord(Base):
    __tablename__ = "job_attempts"

    attempt_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.organization_id"), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("processing_jobs.job_id"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
