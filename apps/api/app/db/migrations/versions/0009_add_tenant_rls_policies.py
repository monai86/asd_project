"""Add tenant-scoped records and PostgreSQL RLS policies.

Revision ID: 0009_add_tenant_rls_policies
Revises: 0008_add_one_day_pilot_tenant_scaffold
Create Date: 2026-06-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_add_tenant_rls_policies"
down_revision = "0008_add_one_day_pilot_tenant_scaffold"
branch_labels = None
depends_on = None


TENANT_TABLES = [
    "child_cases",
    "therapy_goals",
    "sessions",
    "transcripts",
    "feature_sets",
    "audio_files",
    "ai_reviews",
    "ml_results",
    "reports",
    "processing_jobs",
    "privacy_operations",
    "audit_logs",
]

RLS_POLICY_MANIFEST = """
ALTER TABLE child_cases ENABLE ROW LEVEL SECURITY
CREATE POLICY child_cases_tenant_isolation
ALTER TABLE therapy_goals ENABLE ROW LEVEL SECURITY
CREATE POLICY therapy_goals_tenant_isolation
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY
CREATE POLICY sessions_tenant_isolation
ALTER TABLE transcripts ENABLE ROW LEVEL SECURITY
CREATE POLICY transcripts_tenant_isolation
ALTER TABLE feature_sets ENABLE ROW LEVEL SECURITY
CREATE POLICY feature_sets_tenant_isolation
ALTER TABLE audio_files ENABLE ROW LEVEL SECURITY
CREATE POLICY audio_files_tenant_isolation
ALTER TABLE ai_reviews ENABLE ROW LEVEL SECURITY
CREATE POLICY ai_reviews_tenant_isolation
ALTER TABLE ml_results ENABLE ROW LEVEL SECURITY
CREATE POLICY ml_results_tenant_isolation
ALTER TABLE reports ENABLE ROW LEVEL SECURITY
CREATE POLICY reports_tenant_isolation
ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY
CREATE POLICY processing_jobs_tenant_isolation
ALTER TABLE privacy_operations ENABLE ROW LEVEL SECURITY
CREATE POLICY privacy_operations_tenant_isolation
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY
CREATE POLICY audit_logs_tenant_isolation
"""


def upgrade() -> None:
    op.create_table(
        "organization_settings",
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), primary_key=True),
        sa.Column("ai_drafting_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("default_retention_region", sa.String(length=64), server_default="local_pilot", nullable=False),
        sa.Column("settings", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "case_care_team_assignments",
        sa.Column("assignment_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("user_profiles.user_id"), nullable=False),
        sa.Column("role", sa.String(length=64), server_default="clinician", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "case_id", "user_id", name="uq_case_care_team_org_case_user"),
    )
    op.create_index("ix_case_care_team_assignments_organization_id", "case_care_team_assignments", ["organization_id"])
    op.create_index("ix_case_care_team_assignments_case_id", "case_care_team_assignments", ["case_id"])
    op.create_index("ix_case_care_team_assignments_user_id", "case_care_team_assignments", ["user_id"])

    op.create_table(
        "identity_profiles",
        sa.Column("identity_profile_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("encrypted_payload_ref", sa.String(length=512), nullable=False),
        sa.Column("key_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_identity_profiles_organization_id", "identity_profiles", ["organization_id"])
    op.create_index("ix_identity_profiles_case_id", "identity_profiles", ["case_id"])

    op.create_table(
        "regional_retention_policies",
        sa.Column("retention_policy_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False),
        sa.Column("record_type", sa.String(length=64), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("legal_hold_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "region", "record_type", name="uq_retention_policy_org_region_record"),
    )
    op.create_index("ix_regional_retention_policies_organization_id", "regional_retention_policies", ["organization_id"])

    op.create_table(
        "consent_records",
        sa.Column("consent_record_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("consent_type", sa.String(length=64), server_default="clinical_workflow", nullable=False),
        sa.Column("recorded_by", sa.String(length=128), nullable=False),
        sa.Column("evidence_ref", sa.String(length=512)),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_consent_records_organization_id", "consent_records", ["organization_id"])
    op.create_index("ix_consent_records_case_id", "consent_records", ["case_id"])
    op.create_index("ix_consent_records_status", "consent_records", ["status"])

    op.create_table(
        "notifications",
        sa.Column("notification_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("recipient_user_id", sa.String(length=128), sa.ForeignKey("user_profiles.user_id"), nullable=False),
        sa.Column("message_type", sa.String(length=64), nullable=False),
        sa.Column("delivery_status", sa.String(length=64), server_default="queued", nullable=False),
        sa.Column("safe_message", sa.Text(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=256)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"])
    op.create_index("ix_notifications_delivery_status", "notifications", ["delivery_status"])

    op.create_table(
        "job_attempts",
        sa.Column("attempt_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("job_id", sa.String(length=64), sa.ForeignKey("processing_jobs.job_id"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("leased_until", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_attempts_organization_id", "job_attempts", ["organization_id"])
    op.create_index("ix_job_attempts_job_id", "job_attempts", ["job_id"])
    op.create_index("ix_job_attempts_status", "job_attempts", ["status"])

    for table_name in [
        "therapy_goals",
        "feature_sets",
        "audio_files",
        "ai_reviews",
        "ml_results",
        "processing_jobs",
        "privacy_operations",
        "audit_logs",
    ]:
        op.add_column(table_name, sa.Column("organization_id", sa.String(length=64), server_default="pilot_org_001", nullable=False))
        op.create_index(f"ix_{table_name}_organization_id", table_name, ["organization_id"])

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table_name in TENANT_TABLES:
            op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
            op.execute(
                f"""
                CREATE POLICY {table_name}_tenant_isolation
                ON {table_name}
                USING (organization_id = current_setting('app.current_organization_id', true))
                WITH CHECK (organization_id = current_setting('app.current_organization_id', true))
                """
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table_name in reversed(TENANT_TABLES):
            op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}")
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")

    for table_name in [
        "audit_logs",
        "privacy_operations",
        "processing_jobs",
        "ml_results",
        "ai_reviews",
        "audio_files",
        "feature_sets",
        "therapy_goals",
    ]:
        op.drop_index(f"ix_{table_name}_organization_id", table_name=table_name)
        op.drop_column(table_name, "organization_id")

    op.drop_index("ix_job_attempts_status", table_name="job_attempts")
    op.drop_index("ix_job_attempts_job_id", table_name="job_attempts")
    op.drop_index("ix_job_attempts_organization_id", table_name="job_attempts")
    op.drop_table("job_attempts")
    op.drop_index("ix_notifications_delivery_status", table_name="notifications")
    op.drop_index("ix_notifications_recipient_user_id", table_name="notifications")
    op.drop_index("ix_notifications_organization_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_consent_records_status", table_name="consent_records")
    op.drop_index("ix_consent_records_case_id", table_name="consent_records")
    op.drop_index("ix_consent_records_organization_id", table_name="consent_records")
    op.drop_table("consent_records")
    op.drop_index("ix_regional_retention_policies_organization_id", table_name="regional_retention_policies")
    op.drop_table("regional_retention_policies")
    op.drop_index("ix_identity_profiles_case_id", table_name="identity_profiles")
    op.drop_index("ix_identity_profiles_organization_id", table_name="identity_profiles")
    op.drop_table("identity_profiles")
    op.drop_index("ix_case_care_team_assignments_user_id", table_name="case_care_team_assignments")
    op.drop_index("ix_case_care_team_assignments_case_id", table_name="case_care_team_assignments")
    op.drop_index("ix_case_care_team_assignments_organization_id", table_name="case_care_team_assignments")
    op.drop_table("case_care_team_assignments")
    op.drop_table("organization_settings")
