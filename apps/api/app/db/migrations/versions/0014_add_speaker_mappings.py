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
