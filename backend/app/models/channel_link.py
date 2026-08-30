"""Stored seller-platform connection (Nhanh.vn).

One row per linked account. Tokens live here because the seller authorises once
and the app keeps pulling afterwards.

Tokens are secrets: they are never returned by the API, only their presence and
expiry are. A production deployment should additionally encrypt these columns at
rest (pgcrypto or app-level envelope encryption); that is out of scope here and
called out so it is not mistaken for done.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ChannelConnection(Base, TimestampMixin):
    __tablename__ = "channel_connections"
    __table_args__ = (
        UniqueConstraint("platform", "shop_id", name="uq_channel_platform_shop"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    shop_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    shop_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # shop_cipher (TikTok) and anything else a platform demands on later calls.
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # pending -> the seller was sent to the platform but has not come back yet.
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- last order sync ----------------------------------------------------
    # Only aggregates are kept, never customer records: the planner needs the
    # sales rate, nothing personal.
    synced_orders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_revenue_vnd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    synced_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # {"shopee": {"orders": 340, "revenue_vnd": ...}, "lazada": {...}} — one
    # link carries several marketplaces, and the planner allocates stock per
    # marketplace, so the split has to survive alongside the total.
    channel_orders_json: Mapped[str | None] = mapped_column(Text, nullable=True)
