"""Seller workspaces and their members.

A workspace is the tenant boundary for seller-owned data.  Marketplace shops,
orders and inventory will attach to it in later migrations; membership is kept
separate from the platform-level ``User.role`` so a normal account can own one
workspace and collaborate in another without becoming a platform admin.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

WORKSPACE_STATUSES = ("active", "suspended", "archived")
WORKSPACE_ROLES = ("owner", "manager", "analyst", "viewer")


class SellerWorkspace(Base, TimestampMixin):
    __tablename__ = "seller_workspaces"
    __table_args__ = (UniqueConstraint("slug", name="uq_seller_workspace_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="active", index=True, nullable=False
    )

    memberships: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan", lazy="selectin"
    )


class WorkspaceMember(Base, TimestampMixin):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("seller_workspaces.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), default="viewer", nullable=False)

    workspace: Mapped[SellerWorkspace] = relationship(back_populates="memberships")
