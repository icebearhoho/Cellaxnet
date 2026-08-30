"""seller autopilot opportunities and audit events

Revision ID: 0011_seller_autopilot
Revises: 0010_marketplace_shops
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_seller_autopilot"
down_revision = "0010_marketplace_shops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "autopilot_opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="detected"),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(80), nullable=True),
        sa.Column("llm_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selected_option_id", sa.String(80), nullable=True),
        sa.Column("approved_by", sa.Integer(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["workspace_id"], ["seller_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
    )
    for column in ("workspace_id", "fingerprint", "kind", "severity", "status"):
        op.create_index(f"ix_autopilot_opportunities_{column}", "autopilot_opportunities", [column])

    op.create_table(
        "autopilot_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["opportunity_id"], ["autopilot_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["seller_workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    for column in ("opportunity_id", "workspace_id", "event_type"):
        op.create_index(f"ix_autopilot_audit_events_{column}", "autopilot_audit_events", [column])


def downgrade() -> None:
    op.drop_table("autopilot_audit_events")
    op.drop_table("autopilot_opportunities")
