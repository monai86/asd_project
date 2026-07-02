"""Add production audit event shape fields.

Revision ID: 0004_audit_event_shape
Revises: 0003_report_signed_snapshot
Create Date: 2026-06-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0004_audit_event_shape"
down_revision = "0003_report_signed_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("actor_id", sa.String(length=128), server_default="system", nullable=False))
    op.add_column("audit_logs", sa.Column("outcome", sa.String(length=32), server_default="success", nullable=False))
    op.add_column("audit_logs", sa.Column("correlation_id", sa.String(length=128), server_default="local", nullable=False))
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_correlation_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_column("audit_logs", "correlation_id")
    op.drop_column("audit_logs", "outcome")
    op.drop_column("audit_logs", "actor_id")
