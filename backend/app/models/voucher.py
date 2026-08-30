"""Workspace-scoped voucher campaigns and immutable lifecycle events."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class VoucherCampaign(Base, TimestampMixin):
    __tablename__ = "voucher_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("seller_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    marketplace_shop_id: Mapped[int | None] = mapped_column(
        ForeignKey("marketplace_shops.id", ondelete="SET NULL"), index=True, nullable=True
    )
    source_opportunity_id: Mapped[int | None] = mapped_column(
        ForeignKey("autopilot_opportunities.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    platform: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    promotion_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(28), index=True, nullable=False, default="draft")
    objective: Mapped[str] = mapped_column(String(40), nullable=False)
    product_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)
    max_discount_vnd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_order_vnd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_vnd: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    baseline_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    simulation: Mapped[dict] = mapped_column(JSON, nullable=False)
    guardrails: Mapped[dict] = mapped_column(JSON, nullable=False)
    execution: Mapped[dict] = mapped_column(JSON, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VoucherCampaignEvent(Base):
    __tablename__ = "voucher_campaign_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("voucher_campaigns.id", ondelete="CASCADE"), index=True, nullable=False
    )
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("seller_workspaces.id", ondelete="CASCADE"), index=True, nullable=False
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
