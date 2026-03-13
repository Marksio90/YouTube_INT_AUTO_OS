"""Add performance indexes to channels table

Revision ID: 003
Revises: 002
Create Date: 2026-03-13

Adds:
- ix_channels_is_active_created_at — composite index for active-channel time-range queries
- ix_channels_niche — index for filtering/grouping by niche
- ix_channels_ypp_status — index for filtering by YPP monetization status
"""
from alembic import op

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_channels_is_active_created_at",
        "channels",
        ["is_active", "created_at"],
    )
    op.create_index(
        "ix_channels_niche",
        "channels",
        ["niche"],
    )
    op.create_index(
        "ix_channels_ypp_status",
        "channels",
        ["ypp_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_channels_ypp_status", table_name="channels")
    op.drop_index("ix_channels_niche", table_name="channels")
    op.drop_index("ix_channels_is_active_created_at", table_name="channels")
