"""A Shopee login a user connected, so the collector can read sales data as them.

One row per user. The session cookies are a bearer credential for that person's
real Shopee account, so `state_encrypted` holds Fernet ciphertext (see
:mod:`app.core.crypto`), never the raw jar.

Deliberately *not* stored: the user's Shopee password. We never see it — they log
in inside their own browser and only the resulting cookie jar is uploaded. That
also means 2FA and OTP keep working, which a password-collecting design would
break.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ShopeeSession(Base, TimestampMixin):
    __tablename__ = "shopee_sessions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_shopee_session_user"),
        Index("ix_shopee_sessions_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: One connection per account. Reconnecting replaces the row's contents.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    #: Fernet-encrypted Playwright storage_state JSON, filtered to Shopee origins.
    state_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    #: Shopee account label the user saw when connecting, so the UI can show
    #: *which* account is attached without decrypting anything.
    shopee_username: Mapped[str | None] = mapped_column(String(120), nullable=True)

    #: Set False once a read comes back with a login wall or error 90309999.
    #: Kept as a flag rather than deleting the row so the UI can say "hết hạn,
    #: kết nối lại" instead of silently forgetting the connection existed.
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_ok_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
