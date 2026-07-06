"""Add report runtime metadata fields.

Revision ID: 0012_report_runtime_fields
Revises: 0011_primary_therapist
Create Date: 2026-07-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_report_runtime_fields"
down_revision = "0011_primary_therapist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("requested_provider", sa.String(length=64), server_default="template", nullable=False))
    op.add_column("reports", sa.Column("actual_provider", sa.String(length=64), server_default="template", nullable=False))
    op.add_column("reports", sa.Column("provider_version", sa.String(length=32), server_default="1.0.0", nullable=False))
    op.add_column("reports", sa.Column("fallback_reason", sa.Text(), nullable=True))
    op.add_column("reports", sa.Column("rewrite_attempted", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("reports", sa.Column("rewrite_succeeded", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("reports", sa.Column("safety_validation_result", sa.JSON(), nullable=True))
    op.add_column("reports", sa.Column("finalized_safety_result", sa.JSON(), nullable=True))
    op.add_column("reports", sa.Column("finalization_blocked", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("reports", sa.Column("validator_version", sa.String(length=64), server_default="safety-validator-v1.0", nullable=False))
    op.add_column("reports", sa.Column("rule_set_version", sa.String(length=64), server_default="rules-v1.0", nullable=False))
    op.add_column("reports", sa.Column("input_hash", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("reports", sa.Column("transcript_id", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("feature_result_id", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("ml_result_id", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("ml_skipped_reason", sa.Text(), nullable=True))
    op.add_column("reports", sa.Column("validation_summary", sa.Text(), nullable=True))
    op.add_column("reports", sa.Column("feature_schema_version", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("therapist_notes", sa.Text(), nullable=True))
    op.add_column("reports", sa.Column("session_goals", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("reports", sa.Column("generated_from_versions", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("reports", sa.Column("sections", sa.JSON(), server_default="[]", nullable=False))


def downgrade() -> None:
    op.drop_column("reports", "sections")
    op.drop_column("reports", "generated_from_versions")
    op.drop_column("reports", "session_goals")
    op.drop_column("reports", "therapist_notes")
    op.drop_column("reports", "feature_schema_version")
    op.drop_column("reports", "validation_summary")
    op.drop_column("reports", "ml_skipped_reason")
    op.drop_column("reports", "ml_result_id")
    op.drop_column("reports", "feature_result_id")
    op.drop_column("reports", "transcript_id")
    op.drop_column("reports", "version")
    op.drop_column("reports", "input_hash")
    op.drop_column("reports", "rule_set_version")
    op.drop_column("reports", "validator_version")
    op.drop_column("reports", "finalization_blocked")
    op.drop_column("reports", "finalized_safety_result")
    op.drop_column("reports", "safety_validation_result")
    op.drop_column("reports", "rewrite_succeeded")
    op.drop_column("reports", "rewrite_attempted")
    op.drop_column("reports", "fallback_reason")
    op.drop_column("reports", "provider_version")
    op.drop_column("reports", "actual_provider")
    op.drop_column("reports", "requested_provider")
