"""add draft fields to contracts

Revision ID: 20260623_0004
Revises: 20260619_0003
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260623_0004"
down_revision = "20260619_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contracts", sa.Column("draft_content", sa.Text(), nullable=True))
    op.add_column("contracts", sa.Column("draft_updated_at", sa.DateTime(timezone=False), nullable=True))


def downgrade() -> None:
    op.drop_column("contracts", "draft_updated_at")
    op.drop_column("contracts", "draft_content")
