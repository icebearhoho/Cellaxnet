"""voucher booster campaigns and audit events

Revision ID: 0012_voucher_booster
Revises: 0011_seller_autopilot
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_voucher_booster"
down_revision = "0011_seller_autopilot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voucher_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("marketplace_shop_id", sa.Integer(), nullable=True),
        sa.Column("source_opportunity_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("platform", sa.String(24), nullable=False),
        sa.Column("promotion_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(28), nullable=False, server_default="draft"),
        sa.Column("objective", sa.String(40), nullable=False),
        sa.Column("product_id", sa.String(120), nullable=True),
        sa.Column("discount_type", sa.String(16), nullable=False),
        sa.Column("discount_value", sa.Integer(), nullable=False),
        sa.Column("max_discount_vnd", sa.Integer(), nullable=True),
        sa.Column("min_order_vnd", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("budget_vnd", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("baseline_snapshot", sa.JSON(), nullable=False),
        sa.Column("simulation", sa.JSON(), nullable=False),
        sa.Column("guardrails", sa.JSON(), nullable=False),
        sa.Column("execution", sa.JSON(), nullable=False),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["seller_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["marketplace_shop_id"], ["marketplace_shops.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_opportunity_id"], ["autopilot_opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
    )
    for column in ("workspace_id", "marketplace_shop_id", "platform", "status"):
        op.create_index(f"ix_voucher_campaigns_{column}", "voucher_campaigns", [column])

    op.create_table(
        "voucher_campaign_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["campaign_id"], ["voucher_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["seller_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    for column in ("campaign_id", "workspace_id", "event_type"):
        op.create_index(f"ix_voucher_campaign_events_{column}", "voucher_campaign_events", [column])


def downgrade() -> None:
    op.drop_table("voucher_campaign_events")
    op.drop_table("voucher_campaigns")
