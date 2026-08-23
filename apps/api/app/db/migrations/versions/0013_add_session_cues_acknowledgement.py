"""Add reviewed-cues acknowledgment fields to sessions.

Revision ID: 0013_session_cues_acknowledgement
Revises: 0012_report_runtime_fields
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_session_cues_acknowledgement"
down_revision = "0012_report_runtime_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("cues_acknowledged_at", sa.String(length=64), nullable=True))
    op.add_column("sessions", sa.Column("cues_acknowledged_by", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "cues_acknowledged_by")
    op.drop_column("sessions", "cues_acknowledged_at")
