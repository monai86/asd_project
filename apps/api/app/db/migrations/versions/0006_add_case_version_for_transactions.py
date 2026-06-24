"""Add child case optimistic concurrency version.

Revision ID: 0006_add_case_version_for_transactions
Revises: 0005_add_privacy_operation_review_fields
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_add_case_version_for_transactions"
down_revision = "0005_add_privacy_operation_review_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("child_cases", sa.Column("version", sa.Integer(), server_default="1", nullable=False))


def downgrade() -> None:
    op.drop_column("child_cases", "version")
