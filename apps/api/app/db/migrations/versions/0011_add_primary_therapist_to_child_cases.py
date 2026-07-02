"""Add primary therapist tracking to child cases.

Revision ID: 0011_primary_therapist
Revises: 0010_auth_lifecycle
Create Date: 2026-06-26
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0011_primary_therapist"
down_revision = "0010_auth_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("child_cases", sa.Column("primary_therapist_user_id", sa.String(length=128), nullable=True))
    op.create_index(
        "ix_child_cases_primary_therapist_user_id",
        "child_cases",
        ["primary_therapist_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_child_cases_primary_therapist_user_id", table_name="child_cases")
    op.drop_column("child_cases", "primary_therapist_user_id")
