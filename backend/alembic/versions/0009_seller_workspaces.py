"""seller workspaces and membership tenant boundary

Revision ID: 0009_seller_workspaces
Revises: 0008_shopee_sessions
Create Date: 2026-08-12 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_seller_workspaces"
down_revision = "0008_shopee_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seller_workspaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="active"
        ),
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
            "status IN ('active', 'suspended', 'archived')",
            name="ck_seller_workspace_status",
        ),
        sa.UniqueConstraint("slug", name="uq_seller_workspace_slug"),
    )
    op.create_index("ix_seller_workspaces_slug", "seller_workspaces", ["slug"])
    op.create_index("ix_seller_workspaces_status", "seller_workspaces", ["status"])

    op.create_table(
        "workspace_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="viewer"),
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
            "role IN ('owner', 'manager', 'analyst', 'viewer')",
            name="ck_workspace_member_role",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["seller_workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )
    op.create_index(
        "ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"]
    )
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_members_user_id", table_name="workspace_members")
    op.drop_index("ix_workspace_members_workspace_id", table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_index("ix_seller_workspaces_status", table_name="seller_workspaces")
    op.drop_index("ix_seller_workspaces_slug", table_name="seller_workspaces")
    op.drop_table("seller_workspaces")
