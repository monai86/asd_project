"""Add one-day pilot tenant scaffold.

Revision ID: 0008_add_one_day_pilot_tenant_scaffold
Revises: 0007_add_session_transaction_fields
Create Date: 2026-06-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_add_one_day_pilot_tenant_scaffold"
down_revision = "0007_add_session_transaction_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("organization_id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("pilot_mode", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=128), primary_key=True),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("membership_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("user_profiles.user_id"), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"])
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"])
    op.create_index("ix_organization_memberships_role", "organization_memberships", ["role"])

    op.add_column("child_cases", sa.Column("organization_id", sa.String(length=64), server_default="pilot_org_001", nullable=False))
    op.add_column("child_cases", sa.Column("care_team_user_ids", sa.JSON(), server_default='["therapist-demo"]', nullable=False))
    op.add_column("sessions", sa.Column("organization_id", sa.String(length=64), server_default="pilot_org_001", nullable=False))
    op.add_column("transcripts", sa.Column("organization_id", sa.String(length=64), server_default="pilot_org_001", nullable=False))
    op.add_column("reports", sa.Column("organization_id", sa.String(length=64), server_default="pilot_org_001", nullable=False))

    op.create_index("ix_child_cases_organization_id", "child_cases", ["organization_id"])
    op.create_index("ix_sessions_organization_id", "sessions", ["organization_id"])
    op.create_index("ix_transcripts_organization_id", "transcripts", ["organization_id"])
    op.create_index("ix_reports_organization_id", "reports", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_organization_id", table_name="reports")
    op.drop_index("ix_transcripts_organization_id", table_name="transcripts")
    op.drop_index("ix_sessions_organization_id", table_name="sessions")
    op.drop_index("ix_child_cases_organization_id", table_name="child_cases")
    op.drop_column("reports", "organization_id")
    op.drop_column("transcripts", "organization_id")
    op.drop_column("sessions", "organization_id")
    op.drop_column("child_cases", "care_team_user_ids")
    op.drop_column("child_cases", "organization_id")
    op.drop_index("ix_organization_memberships_role", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_organization_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_table("user_profiles")
    op.drop_table("organizations")
