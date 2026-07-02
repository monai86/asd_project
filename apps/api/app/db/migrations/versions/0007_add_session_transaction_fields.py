"""Add session transaction fields.

Revision ID: 0007_session_txn_fields
Revises: 0006_case_version_txn
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_session_txn_fields"
down_revision = "0006_case_version_txn"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("child_cases", sa.Column("latest_session_date", sa.String(length=32), nullable=True))
    op.add_column("child_cases", sa.Column("latest_session_status", sa.String(length=32), server_default="Draft", nullable=False))
    op.add_column("child_cases", sa.Column("latest_report_status", sa.String(length=32), server_default="Draft", nullable=False))


def downgrade() -> None:
    op.drop_column("child_cases", "latest_report_status")
    op.drop_column("child_cases", "latest_session_status")
    op.drop_column("child_cases", "latest_session_date")
    op.drop_column("sessions", "version")
