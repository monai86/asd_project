"""Add persisted ML review results.

Revision ID: 0002_add_ml_review_results
Revises: 0001_initial_v2_schema
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_ml_review_results"
down_revision = "0001_initial_v2_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("ml_result_id", sa.String(length=64), nullable=True))
    op.create_table(
        "ml_results",
        sa.Column("result_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("sessions.session_id"), nullable=False),
        sa.Column("transcript_id", sa.String(length=64), sa.ForeignKey("transcripts.transcript_id"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ml_results_session_id", "ml_results", ["session_id"])
    op.create_index("ix_ml_results_transcript_id", "ml_results", ["transcript_id"])


def downgrade() -> None:
    op.drop_index("ix_ml_results_transcript_id", table_name="ml_results")
    op.drop_index("ix_ml_results_session_id", table_name="ml_results")
    op.drop_table("ml_results")
    op.drop_column("sessions", "ml_result_id")
