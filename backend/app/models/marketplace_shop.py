"""Normalized marketplace shops connected to a seller workspace."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

MARKETPLACE_PLATFORMS = ("shopee", "lazada", "tiktok_shop")
MARKETPLACE_CONNECTION_STATUSES = (
    "connected",
    "expired",
    "revoked",
    "error",
)


class MarketplaceShop(Base, TimestampMixin):
    __tablename__ = "marketplace_shops"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "platform",
            "external_shop_id",
            name="uq_marketplace_shop_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("seller_workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    external_shop_id: Mapped[str] = mapped_column(String(120), nullable=False)
    shop_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="connected", index=True, nullable=False
    )

    # OAuth credentials are encrypted before persistence. Marketplace account
    # passwords never belong in this table or anywhere else in the app.
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    workspace = relationship("SellerWorkspace")
