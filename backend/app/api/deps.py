"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Depends, Header
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError, ValidationError
from app.core.security import decode_access_token
from app.db.redis import get_redis
from app.db.session import get_db  # re-export

if TYPE_CHECKING:
    from app.models.workspace import SellerWorkspace


async def get_db_dep() -> AsyncIterator[AsyncSession]:  # alias for clarity
    async for s in get_db():
        yield s


async def get_redis_dep() -> Redis:
    return get_redis()


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> dict:
    """Decode the Bearer JWT and return its claims — no DB round trip.

    The role lives in the signed token, so authorising a request never needs a
    query. The trade-off: revoking a role or deleting an account only takes
    effect once the token expires (``JWT_EXPIRE_MINUTES``, 24h by default).
    That's an acceptable window here and it keeps the seller portal working
    when Postgres is down.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token.")
    token = authorization.split(" ", 1)[1]
    return decode_access_token(token)


async def get_current_user_optional(
    authorization: str | None = Header(default=None),
) -> dict | None:
    """Claims when a usable token is present, else None — never raises.

    For endpoints that work for guests but should attach the account when the
    caller happens to be signed in (checkout is the case in point).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return decode_access_token(authorization.split(" ", 1)[1])
    except UnauthorizedError:
        # An expired or forged token is treated as "no token" rather than an
        # error: the request is valid as a guest.
        return None


def require_role(*roles: str) -> Callable[..., Awaitable[dict]]:
    """Build a dependency that rejects any token whose role isn't listed.

    Mount it per-router in :mod:`app.api.v1` — ``include_router(...,
    dependencies=[Depends(require_admin)])`` — so a whole feature area is
    gated in one place instead of decorating every endpoint.
    """

    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise ForbiddenError("Bạn không có quyền truy cập khu vực này.")
        return user

    return _dep


require_admin = require_role("admin")


@dataclass(frozen=True)
class WorkspaceAccess:
    """Verified tenant context passed to workspace-scoped seller endpoints."""

    workspace_id: int
    user_id: int
    role: str
    workspace: SellerWorkspace


async def require_seller_workspace_or_admin(
    x_workspace_id: int | None = Header(default=None, alias="X-Workspace-ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> dict:
    """Admit platform admins or a verified member of an active workspace.

    Membership is read from the database on every tool request, so a stale JWT
    cannot retain seller access after removal. Conversely, a newly invited
    member can use the workspace before their coarse role claim is refreshed.
    """
    if user.get("role") == "admin":
        return user
    if x_workspace_id is None:
        if user.get("role") == "buyer":
            raise ForbiddenError("Bạn chưa có quyền truy cập khu vực người bán.")
        raise ValidationError("Thiếu workspace đang hoạt động.")

    from app.services import workspace_service

    workspace, _role = await workspace_service.get_accessible_workspace(
        db,
        workspace_id=x_workspace_id,
        user_id=int(user["sub"]),
        is_platform_admin=False,
    )
    if workspace.status != "active":
        raise ForbiddenError("Workspace hiện không hoạt động.")
    return user


async def get_workspace_access(
    x_workspace_id: int | None = Header(default=None, alias="X-Workspace-ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> WorkspaceAccess:
    """Resolve and verify the active workspace from ``X-Workspace-ID``.

    Future marketplace endpoints should depend on this instead of trusting a
    workspace id from a JSON body. Cross-tenant ids deliberately look missing.
    """
    if x_workspace_id is None:
        raise ValidationError("Thiếu workspace đang hoạt động.")

    # Local import avoids a dependency cycle: services use the DB types above.
    from app.services import workspace_service

    workspace, role = await workspace_service.get_accessible_workspace(
        db,
        workspace_id=x_workspace_id,
        user_id=int(user["sub"]),
        is_platform_admin=user.get("role") == "admin",
    )
    if workspace.status != "active" and role != "platform_admin":
        raise ForbiddenError("Workspace hiện không hoạt động.")
    return WorkspaceAccess(
        workspace_id=workspace.id,
        user_id=int(user["sub"]),
        role=role,
        workspace=workspace,
    )


def require_workspace_role(
    *roles: str,
) -> Callable[..., Awaitable[WorkspaceAccess]]:
    """Require membership in the active workspace with one of ``roles``."""

    async def _dep(
        access: WorkspaceAccess = Depends(get_workspace_access),
    ) -> WorkspaceAccess:
        if access.role != "platform_admin" and access.role not in roles:
            raise ForbiddenError("Bạn không có quyền thực hiện thao tác này trong workspace.")
        return access

    return _dep


__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_db",
    "get_db_dep",
    "get_redis",
    "get_redis_dep",
    "get_workspace_access",
    "require_admin",
    "require_role",
    "require_seller_workspace_or_admin",
    "require_workspace_role",
    "WorkspaceAccess",
]
