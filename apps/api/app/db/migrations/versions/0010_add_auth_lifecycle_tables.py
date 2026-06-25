"""Add auth lifecycle tables.

Revision ID: 0010_add_auth_lifecycle_tables
Revises: 0009_add_tenant_rls_policies
Create Date: 2026-06-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_add_auth_lifecycle_tables"
down_revision = "0009_add_tenant_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_invitations",
        sa.Column("invitation_id", sa.String(length=128), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("invited_by", sa.String(length=128), nullable=False),
        sa.Column("accepted_user_id", sa.String(length=128)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_organization_invitations_organization_id", "organization_invitations", ["organization_id"])
    op.create_index("ix_organization_invitations_role", "organization_invitations", ["role"])
    op.create_index("ix_organization_invitations_status", "organization_invitations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_organization_invitations_status", table_name="organization_invitations")
    op.drop_index("ix_organization_invitations_role", table_name="organization_invitations")
    op.drop_index("ix_organization_invitations_organization_id", table_name="organization_invitations")
    op.drop_table("organization_invitations")
