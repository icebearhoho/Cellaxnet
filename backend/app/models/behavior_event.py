"""Real per-session behaviour event — dwell time, cart-abandon, checkout timing."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BehaviorEvent(Base, TimestampMixin):
    __tablename__ = "behavior_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    customer_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    query: Mapped[str | None] = mapped_column(String(120), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
