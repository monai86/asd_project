"""Add private checksum-bound ASR evidence records.

Revision ID: 0014_private_asr_evidence
Revises: 0013_v170_speech_pipeline
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_private_asr_evidence"
down_revision = "0013_v170_speech_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audio_files",
        sa.Column("active_upload_receipt", sa.JSON(), nullable=True),
    )
    op.add_column(
        "audio_files",
        sa.Column(
            "upload_cleanup_remediation",
            sa.JSON(),
            nullable=True,
        ),
    )
    op.create_table(
        "asr_private_evidence",
        sa.Column(
            "job_id",
            sa.String(length=64),
            sa.ForeignKey("processing_jobs.job_id"),
            primary_key=True,
        ),
        sa.Column(
            "transcript_id",
            sa.String(length=64),
            sa.ForeignKey("transcripts.transcript_id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "raw_provider_payload_checksum_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "speech_detection_evidence_checksum_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "canonical_private_record_checksum_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("private_record", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_asr_private_evidence_transcript_id",
        "asr_private_evidence",
        ["transcript_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_asr_private_evidence_transcript_id",
        table_name="asr_private_evidence",
    )
    op.drop_table("asr_private_evidence")
    op.drop_column("audio_files", "upload_cleanup_remediation")
    op.drop_column("audio_files", "active_upload_receipt")
