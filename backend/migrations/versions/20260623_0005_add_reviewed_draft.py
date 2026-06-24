"""add reviewed_draft to reviews

Revision ID: 20260623_0005
Revises: 20260623_0004
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa


revision = "20260623_0005"
down_revision = "20260623_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column(
            "reviewed_draft",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("reviews", "reviewed_draft")
