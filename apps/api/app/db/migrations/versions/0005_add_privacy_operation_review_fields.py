"""Add privacy operation retention and deletion-review fields.

Revision ID: 0005_add_privacy_operation_review_fields
Revises: 0004_add_audit_event_shape_fields
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_privacy_operation_review_fields"
down_revision = "0004_add_audit_event_shape_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("privacy_operations", sa.Column("retention_days", sa.Integer(), server_default="90", nullable=False))
    op.add_column("privacy_operations", sa.Column("legal_hold", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("privacy_operations", sa.Column("deletion_review_required", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("privacy_operations", sa.Column("preserve_evidence", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("privacy_operations", sa.Column("eligible_for_deletion_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("privacy_operations", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("privacy_operations", sa.Column("evidence_retained", sa.JSON(), server_default="{}", nullable=False))
    op.create_index("ix_privacy_operations_legal_hold", "privacy_operations", ["legal_hold"])
    op.create_index("ix_privacy_operations_eligible_for_deletion_at", "privacy_operations", ["eligible_for_deletion_at"])


def downgrade() -> None:
    op.drop_index("ix_privacy_operations_eligible_for_deletion_at", table_name="privacy_operations")
    op.drop_index("ix_privacy_operations_legal_hold", table_name="privacy_operations")
    op.drop_column("privacy_operations", "evidence_retained")
    op.drop_column("privacy_operations", "completed_at")
    op.drop_column("privacy_operations", "eligible_for_deletion_at")
    op.drop_column("privacy_operations", "preserve_evidence")
    op.drop_column("privacy_operations", "deletion_review_required")
    op.drop_column("privacy_operations", "legal_hold")
    op.drop_column("privacy_operations", "retention_days")
