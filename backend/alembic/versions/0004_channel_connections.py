"""marketplace seller-account connections

Revision ID: 0004_channel_connections
Revises: 0003_reviews
Create Date: 2026-08-07 00:00:00.000000

Written against 0001 on a branch, re-parented onto 0003 when it merged: two
migrations both revising 0001 leave Alembic with two heads, and `upgrade head`
then refuses to run at all. The chain must stay linear.
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_channel_connections"
down_revision = "0003_reviews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channel_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("shop_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("shop_name", sa.String(length=255), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_orders", sa.Integer(), nullable=True),
        sa.Column("synced_units", sa.Integer(), nullable=True),
        sa.Column("synced_revenue_vnd", sa.BigInteger(), nullable=True),
        sa.Column("synced_days", sa.Integer(), nullable=True),
        sa.Column("channel_orders_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_channel_connections_platform", "channel_connections", ["platform"])
    op.create_unique_constraint(
        "uq_channel_platform_shop", "channel_connections", ["platform", "shop_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_channel_platform_shop", "channel_connections", type_="unique")
    op.drop_index("ix_channel_connections_platform", table_name="channel_connections")
    op.drop_table("channel_connections")
