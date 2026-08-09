"""behavior events

Revision ID: 0002_behavior_events
Revises: 0001_initial
Create Date: 2026-08-06 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_behavior_events"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "behavior_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("query", sa.String(length=120), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_behavior_events_session_id", "behavior_events", ["session_id"])
    op.create_index("ix_behavior_events_customer_id", "behavior_events", ["customer_id"])
    op.create_index("ix_behavior_events_occurred_at", "behavior_events", ["occurred_at"])
    op.create_index(
        "ix_behavior_events_session_occurred",
        "behavior_events", ["session_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_behavior_events_session_occurred", table_name="behavior_events")
    op.drop_index("ix_behavior_events_occurred_at", table_name="behavior_events")
    op.drop_index("ix_behavior_events_customer_id", table_name="behavior_events")
    op.drop_index("ix_behavior_events_session_id", table_name="behavior_events")
    op.drop_table("behavior_events")
