"""Add versioned speaker mappings.

Revision ID: 0014_speaker_mappings
Revises: 0013_session_cues_acknowledgement
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_speaker_mappings"
down_revision = "0013_session_cues_acknowledgement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audio_files",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.add_column(sa.Column("audio_file_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("active_audio_file_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_foreign_key(
            "fk_processing_jobs_audio_file_id",
            "audio_files",
            ["audio_file_id"],
            ["audio_file_id"],
        )
        batch_op.create_foreign_key(
            "fk_processing_jobs_active_audio_file_id",
            "audio_files",
            ["active_audio_file_id"],
            ["audio_file_id"],
        )
        batch_op.create_unique_constraint(
            "uq_processing_jobs_active_audio_file_id",
            ["active_audio_file_id"],
        )
    op.create_table(
        "speaker_mappings",
        sa.Column("mapping_id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column(
            "transcript_id",
            sa.String(length=64),
            sa.ForeignKey("transcripts.transcript_id"),
            nullable=False,
        ),
        sa.Column("source_transcript_version", sa.Integer(), nullable=False),
        sa.Column("applied_transcript_version", sa.Integer(), nullable=True),
        sa.Column("mapping_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("entries", sa.JSON(), nullable=False),
        sa.Column("confirmed_by_user_id", sa.String(length=128), nullable=True),
        sa.Column("confirmed_by_role", sa.String(length=64), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "transcript_id",
            "mapping_version",
            name="uq_speaker_mapping_transcript_version",
        ),
    )
    op.create_index(
        "ix_speaker_mappings_organization_id",
        "speaker_mappings",
        ["organization_id"],
    )
    op.create_index(
        "ix_speaker_mappings_transcript_id",
        "speaker_mappings",
        ["transcript_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_speaker_mappings_transcript_id", table_name="speaker_mappings")
    op.drop_index("ix_speaker_mappings_organization_id", table_name="speaker_mappings")
    op.drop_table("speaker_mappings")
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.drop_constraint("uq_processing_jobs_active_audio_file_id", type_="unique")
        batch_op.drop_constraint("fk_processing_jobs_active_audio_file_id", type_="foreignkey")
        batch_op.drop_constraint("fk_processing_jobs_audio_file_id", type_="foreignkey")
        batch_op.drop_column("version")
        batch_op.drop_column("active_audio_file_id")
        batch_op.drop_column("audio_file_id")
    op.drop_column("audio_files", "version")
