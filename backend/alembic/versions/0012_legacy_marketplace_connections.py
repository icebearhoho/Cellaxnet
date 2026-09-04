"""bridge databases stamped by the pre-merge marketplace migration

Revision ID: 0012_marketplace_connections
Revises: 0011_seller_autopilot, 0005_marketplace_connections

Some existing environments were stamped with
``0012_marketplace_connections`` after both the workspace and marketplace
branches had already been applied.  That revision was not present in the
merged repository, so Alembic could not reach the Voucher Booster migration
and its campaign tables were never created.

This no-op compatibility merge describes the schema those databases already
have.  Fresh databases can traverse it as well, while legacy databases can
continue from their existing stamp without manual intervention.
"""

from collections.abc import Sequence

revision = "0012_marketplace_connections"
down_revision = ("0011_seller_autopilot", "0005_marketplace_connections")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The legacy revision had already applied both parent branches."""


def downgrade() -> None:
    """Keep the compatibility bridge schema-neutral."""
