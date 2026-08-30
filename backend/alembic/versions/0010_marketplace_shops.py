"""normalized workspace marketplace connections

Revision ID: 0010_marketplace_shops
Revises: 0009_seller_workspaces
Create Date: 2026-08-12 00:00:10.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_marketplace_shops"
down_revision = "0009_seller_workspaces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "marketplace_shops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=24), nullable=False),
        sa.Column("external_shop_id", sa.String(length=120), nullable=False),
        sa.Column("shop_name", sa.String(length=160), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="connected",
        ),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "platform IN ('shopee', 'lazada', 'tiktok_shop')",
            name="ck_marketplace_shop_platform",
        ),
        sa.CheckConstraint(
            "status IN ('connected', 'expired', 'revoked', 'error')",
            name="ck_marketplace_shop_status",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["seller_workspaces.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "platform",
            "external_shop_id",
            name="uq_marketplace_shop_identity",
        ),
    )
    op.create_index(
        "ix_marketplace_shops_workspace_id", "marketplace_shops", ["workspace_id"]
    )
    op.create_index(
        "ix_marketplace_shops_platform", "marketplace_shops", ["platform"]
    )
    op.create_index("ix_marketplace_shops_status", "marketplace_shops", ["status"])


def downgrade() -> None:
    op.drop_index("ix_marketplace_shops_status", table_name="marketplace_shops")
    op.drop_index("ix_marketplace_shops_platform", table_name="marketplace_shops")
    op.drop_index("ix_marketplace_shops_workspace_id", table_name="marketplace_shops")
    op.drop_table("marketplace_shops")
