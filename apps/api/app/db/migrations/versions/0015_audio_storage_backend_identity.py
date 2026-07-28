"""Bind private audio metadata to a hashed storage backend namespace.

Revision ID: 0015_audio_storage_identity
Revises: 0014_private_asr_evidence
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_audio_storage_identity"
down_revision = "0014_private_asr_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audio_files",
        sa.Column(
            "storage_backend_identity_sha256",
            sa.String(length=64),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "audio_files",
        "storage_backend_identity_sha256",
    )
