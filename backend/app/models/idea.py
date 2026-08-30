"""Idea ORM model — mirrors ``dataset/by_idea/idea_*`` metadata."""

from __future__ import annotations

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Idea(Base, TimestampMixin):
    __tablename__ = "ideas"
    __table_args__ = (UniqueConstraint("slug", name="uq_ideas_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
