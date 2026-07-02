"""Add report signed snapshot metadata.

Revision ID: 0003_report_signed_snapshot
Revises: 0002_add_ml_review_results
Create Date: 2026-06-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0003_report_signed_snapshot"
down_revision = "0002_add_ml_review_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("signed_by", sa.String(length=256), nullable=True))
    op.add_column("reports", sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reports", sa.Column("signed_snapshot_version", sa.Integer(), nullable=True))
    op.add_column("reports", sa.Column("signed_snapshot_hash", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("signed_snapshot", sa.JSON(), nullable=True))
    op.add_column("reports", sa.Column("supersedes_report_id", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("revision_number", sa.Integer(), server_default="1", nullable=False))
    op.add_column("reports", sa.Column("ai_drafting_requested", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("reports", sa.Column("ai_drafting_enabled", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("reports", sa.Column("ai_drafting_provider", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("ai_drafting_model", sa.String(length=128), nullable=True))
    op.add_column("reports", sa.Column("ai_drafting_region", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("ai_drafting_input_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_reports_signed_snapshot_hash", "reports", ["signed_snapshot_hash"])
    op.create_index("ix_reports_supersedes_report_id", "reports", ["supersedes_report_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_supersedes_report_id", table_name="reports")
    op.drop_index("ix_reports_signed_snapshot_hash", table_name="reports")
    op.drop_column("reports", "revision_number")
    op.drop_column("reports", "supersedes_report_id")
    op.drop_column("reports", "ai_drafting_input_hash")
    op.drop_column("reports", "ai_drafting_region")
    op.drop_column("reports", "ai_drafting_model")
    op.drop_column("reports", "ai_drafting_provider")
    op.drop_column("reports", "ai_drafting_enabled")
    op.drop_column("reports", "ai_drafting_requested")
    op.drop_column("reports", "signed_snapshot")
    op.drop_column("reports", "signed_snapshot_hash")
    op.drop_column("reports", "signed_snapshot_version")
    op.drop_column("reports", "signed_at")
    op.drop_column("reports", "signed_by")
