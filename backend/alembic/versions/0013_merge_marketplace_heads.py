"""merge marketplace connector and seller operating-system histories

Revision ID: 0013_merge_marketplace_heads
Revises: 0005_marketplace_connections, 0012_voucher_booster
"""

from collections.abc import Sequence

revision = "0013_merge_marketplace_heads"
down_revision = ("0005_marketplace_connections", "0012_voucher_booster")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join the two already-applied migration branches."""


def downgrade() -> None:
    """Split back to the two parent heads."""
