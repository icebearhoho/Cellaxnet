"""Persistence and tenant-access rules for seller workspaces."""

from __future__ import annotations

import re
import unicodedata
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.models.user import User
from app.models.workspace import SellerWorkspace, WorkspaceMember


def _slugify(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFD", value.lower())
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug[:65].rstrip("-") or "workspace"


async def create_workspace(
    db: AsyncSession, *, user_id: int, name: str, slug: str | None = None
) -> tuple[SellerWorkspace, WorkspaceMember, User]:
    """Create a tenant, make the caller owner, and activate seller access."""
    user = await db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Tài khoản không còn tồn tại.")

    final_slug = slug or f"{_slugify(name)}-{uuid.uuid4().hex[:6]}"
    workspace = SellerWorkspace(name=name, slug=final_slug, status="active")
    db.add(workspace)
    try:
        await db.flush()
        membership = WorkspaceMember(
            workspace_id=workspace.id, user_id=user_id, role="owner"
        )
        db.add(membership)
        if user.role == "buyer":
            user.role = "seller"
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Slug workspace đã được sử dụng.") from exc

    await db.refresh(workspace)
    await db.refresh(membership)
    await db.refresh(user)
    return workspace, membership, user


async def list_accessible_workspaces(
    db: AsyncSession, *, user_id: int, is_platform_admin: bool = False
) -> list[tuple[SellerWorkspace, str]]:
    if is_platform_admin:
        result = await db.execute(
            select(SellerWorkspace).order_by(SellerWorkspace.created_at.desc())
        )
        return [(workspace, "platform_admin") for workspace in result.scalars().all()]

    result = await db.execute(
        select(SellerWorkspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == SellerWorkspace.id)
        .where(WorkspaceMember.user_id == user_id)
        .order_by(SellerWorkspace.created_at.desc())
    )
    return [(workspace, role) for workspace, role in result.all()]


async def get_accessible_workspace(
    db: AsyncSession,
    *,
    workspace_id: int,
    user_id: int,
    is_platform_admin: bool = False,
) -> tuple[SellerWorkspace, str]:
    if is_platform_admin:
        workspace = await db.get(SellerWorkspace, workspace_id)
        if workspace is None:
            raise NotFoundError("Không tìm thấy workspace.")
        return workspace, "platform_admin"

    result = await db.execute(
        select(SellerWorkspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == SellerWorkspace.id)
        .where(
            SellerWorkspace.id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        # Deliberately hide whether another seller's workspace exists.
        raise NotFoundError("Không tìm thấy workspace.")
    return row[0], row[1]


async def list_members(
    db: AsyncSession, *, workspace_id: int
) -> list[tuple[WorkspaceMember, User]]:
    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.created_at.asc())
    )
    return [(membership, user) for membership, user in result.all()]


def require_owner(role: str) -> None:
    if role not in {"owner", "platform_admin"}:
        raise ForbiddenError("Chỉ chủ sở hữu workspace mới quản lý được thành viên.")


async def add_member(
    db: AsyncSession,
    *,
    workspace_id: int,
    email: str,
    role: str,
) -> tuple[WorkspaceMember, User]:
    user_result = await db.execute(select(User).where(User.email == email.strip().lower()))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("Tài khoản này chưa đăng ký trên hệ thống.")

    existing = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("Tài khoản đã là thành viên của workspace.")

    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user.id,
        role=role,
    )
    db.add(membership)
    if user.role == "buyer":
        user.role = "seller"
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Không thể thêm thành viên trùng lặp.") from exc
    await db.refresh(membership)
    await db.refresh(user)
    return membership, user


async def _get_membership(
    db: AsyncSession, *, workspace_id: int, member_user_id: int
) -> WorkspaceMember:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == member_user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise NotFoundError("Không tìm thấy thành viên trong workspace.")
    return membership


async def _owner_count(db: AsyncSession, *, workspace_id: int) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == "owner",
        )
    )
    return int(result.scalar_one())


async def update_member_role(
    db: AsyncSession,
    *,
    workspace_id: int,
    member_user_id: int,
    role: str,
) -> tuple[WorkspaceMember, User]:
    membership = await _get_membership(
        db, workspace_id=workspace_id, member_user_id=member_user_id
    )
    if (
        membership.role == "owner"
        and role != "owner"
        and await _owner_count(db, workspace_id=workspace_id) <= 1
    ):
        raise BusinessRuleError("Workspace phải luôn có ít nhất một chủ sở hữu.")
    membership.role = role
    await db.commit()
    await db.refresh(membership)
    user = await db.get(User, member_user_id)
    if user is None:
        raise NotFoundError("Tài khoản thành viên không còn tồn tại.")
    return membership, user


async def remove_member(
    db: AsyncSession,
    *,
    workspace_id: int,
    member_user_id: int,
    acting_user_id: int,
) -> None:
    membership = await _get_membership(
        db, workspace_id=workspace_id, member_user_id=member_user_id
    )
    if member_user_id == acting_user_id:
        raise BusinessRuleError("Không thể tự xóa mình khỏi workspace tại đây.")
    if (
        membership.role == "owner"
        and await _owner_count(db, workspace_id=workspace_id) <= 1
    ):
        raise BusinessRuleError("Workspace phải luôn có ít nhất một chủ sở hữu.")
    await db.execute(
        delete(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == member_user_id,
        )
    )
    account = await db.get(User, member_user_id)
    if account is not None and account.role == "seller":
        remaining_result = await db.execute(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.user_id == member_user_id)
        )
        if int(remaining_result.scalar_one()) == 0:
            account.role = "buyer"
    await db.commit()
