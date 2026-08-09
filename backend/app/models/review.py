"""Real buyer-submitted reviews — gated by review_moderation before publishing."""

from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # future real-auth wiring
    author_name: Mapped[str] = mapped_column(String(80), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # pending | published | flagged | rejected
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    moderation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    moderation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
