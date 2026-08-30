"""Accounts that can sign in as buyers, sellers, or platform admins."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # admin | seller | buyer — self-registration starts as buyer, workspace
    # creation activates seller, and only scripts/create_admin.py grants admin.
    role: Mapped[str] = mapped_column(String(16), default="buyer", nullable=False)
