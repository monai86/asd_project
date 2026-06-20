"""Initial Therapist App v2 schema.

Revision ID: 0001_initial_v2_schema
Revises:
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_v2_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "child_cases",
        sa.Column("case_id", sa.String(length=64), primary_key=True),
        sa.Column("child_code", sa.String(length=128), nullable=False),
        sa.Column("nickname", sa.String(length=128)),
        sa.Column("age_months", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=128), nullable=False),
        sa.Column("consent_status", sa.String(length=64), nullable=False),
        sa.Column("review_priority", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_child_cases_child_code", "child_cases", ["child_code"])
    op.create_index("ix_child_cases_consent_status", "child_cases", ["consent_status"])

    op.create_table(
        "therapy_goals",
        sa.Column("goal_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("retained", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_therapy_goals_case_id", "therapy_goals", ["case_id"])
    op.create_index("ix_therapy_goals_status", "therapy_goals", ["status"])

    op.create_table(
        "sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("session_date", sa.String(length=32), nullable=False),
        sa.Column("session_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("transcript_id", sa.String(length=64)),
        sa.Column("feature_set_id", sa.String(length=64)),
        sa.Column("ai_review_id", sa.String(length=64)),
        sa.Column("report_id", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sessions_case_id", "sessions", ["case_id"])

    op.create_table(
        "transcripts",
        sa.Column("transcript_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("utterances", sa.JSON(), nullable=False),
        sa.Column("qa_status", sa.String(length=32), nullable=False),
        sa.Column("qa_issues", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("therapist_attested", sa.Boolean(), nullable=False),
        sa.Column("attestation_reason", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_transcripts_session_id", "transcripts", ["session_id"])
    op.create_index("ix_transcripts_case_id", "transcripts", ["case_id"])

    op.create_table(
        "feature_sets",
        sa.Column("feature_set_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("transcript_id", sa.String(length=64), sa.ForeignKey("transcripts.transcript_id"), nullable=False),
        sa.Column("transcript_version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("therapist_attested", sa.Boolean(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feature_sets_session_id", "feature_sets", ["session_id"])
    op.create_index("ix_feature_sets_transcript_id", "feature_sets", ["transcript_id"])

    op.create_table(
        "audio_files",
        sa.Column("audio_file_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("original_filename", sa.String(length=256), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_mode", sa.String(length=64), nullable=False),
        sa.Column("object_key", sa.String(length=512)),
        sa.Column("upload_status", sa.String(length=64), nullable=False),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("sample_rate_hz", sa.Integer()),
        sa.Column("channels", sa.Integer()),
        sa.Column("estimated_noise_level", sa.Float()),
        sa.Column("silence_ratio", sa.Float()),
        sa.Column("checksum_sha256", sa.String(length=64)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True)),
        sa.Column("storage_delete_status", sa.String(length=128)),
        sa.Column("retained", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audio_files_session_id", "audio_files", ["session_id"])
    op.create_index("ix_audio_files_case_id", "audio_files", ["case_id"])

    op.create_table(
        "ai_reviews",
        sa.Column("ai_review_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("review_priority", sa.String(length=32), nullable=False),
        sa.Column("therapist_review_status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_reviews_session_id", "ai_reviews", ["session_id"])

    op.create_table(
        "reports",
        sa.Column("report_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("report_type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("therapist_signoff_status", sa.String(length=32), nullable=False),
        sa.Column("limitation_text", sa.Text(), nullable=False),
        sa.Column("export_timestamp", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_session_id", "reports", ["session_id"])
    op.create_index("ix_reports_case_id", "reports", ["case_id"])

    op.create_table(
        "processing_jobs",
        sa.Column("job_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(length=128)),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_processing_jobs_session_id", "processing_jobs", ["session_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])

    op.create_table(
        "privacy_operations",
        sa.Column("privacy_operation_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("child_cases.case_id"), nullable=False),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("requester_role", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_privacy_operations_case_id", "privacy_operations", ["case_id"])
    op.create_index("ix_privacy_operations_operation_type", "privacy_operations", ["operation_type"])
    op.create_index("ix_privacy_operations_status", "privacy_operations", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.String(length=64), primary_key=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("target_id", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_target_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_privacy_operations_status", table_name="privacy_operations")
    op.drop_index("ix_privacy_operations_operation_type", table_name="privacy_operations")
    op.drop_index("ix_privacy_operations_case_id", table_name="privacy_operations")
    op.drop_table("privacy_operations")
    op.drop_index("ix_processing_jobs_status", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_session_id", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index("ix_reports_case_id", table_name="reports")
    op.drop_index("ix_reports_session_id", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_ai_reviews_session_id", table_name="ai_reviews")
    op.drop_table("ai_reviews")
    op.drop_index("ix_feature_sets_transcript_id", table_name="feature_sets")
    op.drop_index("ix_feature_sets_session_id", table_name="feature_sets")
    op.drop_index("ix_audio_files_case_id", table_name="audio_files")
    op.drop_index("ix_audio_files_session_id", table_name="audio_files")
    op.drop_table("audio_files")
    op.drop_table("feature_sets")
    op.drop_index("ix_transcripts_case_id", table_name="transcripts")
    op.drop_index("ix_transcripts_session_id", table_name="transcripts")
    op.drop_table("transcripts")
    op.drop_index("ix_sessions_case_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_therapy_goals_status", table_name="therapy_goals")
    op.drop_index("ix_therapy_goals_case_id", table_name="therapy_goals")
    op.drop_table("therapy_goals")
    op.drop_index("ix_child_cases_consent_status", table_name="child_cases")
    op.drop_index("ix_child_cases_child_code", table_name="child_cases")
    op.drop_table("child_cases")
