"""reviews

Revision ID: 0003_reviews
Revises: 0002_behavior_events
Create Date: 2026-08-06 00:00:01.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_reviews"
down_revision = "0002_behavior_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=64), nullable=True),
        sa.Column("author_name", sa.String(length=80), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("moderation_confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_reviews_product_id", "reviews", ["product_id"])
    op.create_index("ix_reviews_status", "reviews", ["status"])


def downgrade() -> None:
    op.drop_index("ix_reviews_status", table_name="reviews")
    op.drop_index("ix_reviews_product_id", table_name="reviews")
    op.drop_table("reviews")
