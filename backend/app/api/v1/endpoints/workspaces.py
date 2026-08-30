"""Authenticated seller-workspace onboarding and lookup."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    WorkspaceAccess,
    get_current_user,
    get_db_dep,
    get_workspace_access,
    require_workspace_role,
)
from app.core.exceptions import NotFoundError
from app.core.responses import ApiResponse, PageMeta
from app.schemas.workspace import (
    MarketplaceConnectionStatus,
    MarketplacePlatform,
    MarketplaceShopOut,
    WorkspaceCreateRequest,
    WorkspaceMemberAddRequest,
    WorkspaceMemberOut,
    WorkspaceMemberRoleRequest,
    WorkspaceOut,
    WorkspaceRole,
)
from app.services import marketplace_shop_service, user_service, workspace_service

router = APIRouter()
_OWNER_ACCESS = require_workspace_role("owner")
_SHOP_MANAGER_ACCESS = require_workspace_role("owner", "manager")


def _serialize(workspace, role: str) -> dict:  # noqa: ANN001
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        status=workspace.status,
        current_role=cast(WorkspaceRole, role),
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    ).model_dump()


def _serialize_member(membership, account) -> dict:  # noqa: ANN001
    return WorkspaceMemberOut(
        user_id=account.id,
        email=account.email,
        name=account.name,
        role=membership.role,
        joined_at=membership.created_at,
    ).model_dump()


def _serialize_shop(shop) -> dict:  # noqa: ANN001
    return MarketplaceShopOut(
        id=shop.id,
        workspace_id=shop.workspace_id,
        platform=cast(MarketplacePlatform, shop.platform),
        external_shop_id=shop.external_shop_id,
        shop_name=shop.shop_name,
        status=cast(MarketplaceConnectionStatus, shop.status),
        token_expires_at=shop.token_expires_at,
        last_synced_at=shop.last_synced_at,
        last_error=shop.last_error,
        connected_at=shop.created_at,
        updated_at=shop.updated_at,
    ).model_dump()


@router.post("/", response_model=ApiResponse[dict])
async def create_workspace(
    req: WorkspaceCreateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    workspace, membership, account = await workspace_service.create_workspace(
        db, user_id=int(user["sub"]), name=req.name, slug=req.slug
    )
    return ApiResponse[dict](
        success=True,
        data={
            "workspace": _serialize(workspace, membership.role),
            "auth": user_service.issue_token_response(account),
        },
        meta=PageMeta(),
        error=None,
    )


@router.get("/", response_model=ApiResponse[list[dict]])
async def list_workspaces(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[list[dict]]:
    rows = await workspace_service.list_accessible_workspaces(
        db, user_id=int(user["sub"]), is_platform_admin=user.get("role") == "admin"
    )
    items = [_serialize(workspace, role) for workspace, role in rows]
    return ApiResponse[list[dict]](
        success=True,
        data=items,
        meta=PageMeta(page=1, page_size=len(items), total=len(items)),
        error=None,
    )


@router.get("/{workspace_id}", response_model=ApiResponse[dict])
async def get_workspace(
    workspace_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    workspace, role = await workspace_service.get_accessible_workspace(
        db,
        workspace_id=workspace_id,
        user_id=int(user["sub"]),
        is_platform_admin=user.get("role") == "admin",
    )
    return ApiResponse[dict](
        success=True,
        data=_serialize(workspace, role),
        meta=PageMeta(),
        error=None,
    )


@router.get("/{workspace_id}/members", response_model=ApiResponse[list[dict]])
async def list_members(
    workspace_id: int,
    access: WorkspaceAccess = Depends(get_workspace_access),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[list[dict]]:
    if access.workspace_id != workspace_id:
        # Header and path must describe one verified tenant; never silently use
        # one while showing the other in logs or browser history.
        raise NotFoundError("Không tìm thấy workspace.")
    rows = await workspace_service.list_members(db, workspace_id=workspace_id)
    items = [_serialize_member(membership, account) for membership, account in rows]
    return ApiResponse[list[dict]](
        success=True,
        data=items,
        meta=PageMeta(page=1, page_size=len(items), total=len(items)),
        error=None,
    )


@router.post("/{workspace_id}/members", response_model=ApiResponse[dict])
async def add_member(
    workspace_id: int,
    req: WorkspaceMemberAddRequest,
    access: WorkspaceAccess = Depends(_OWNER_ACCESS),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    if access.workspace_id != workspace_id:
        raise NotFoundError("Không tìm thấy workspace.")
    membership, account = await workspace_service.add_member(
        db, workspace_id=workspace_id, email=req.email, role=req.role
    )
    return ApiResponse[dict](
        success=True,
        data=_serialize_member(membership, account),
        meta=PageMeta(),
        error=None,
    )


@router.patch("/{workspace_id}/members/{member_user_id}", response_model=ApiResponse[dict])
async def update_member_role(
    workspace_id: int,
    member_user_id: int,
    req: WorkspaceMemberRoleRequest,
    access: WorkspaceAccess = Depends(_OWNER_ACCESS),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    if access.workspace_id != workspace_id:
        raise NotFoundError("Không tìm thấy workspace.")
    membership, account = await workspace_service.update_member_role(
        db,
        workspace_id=workspace_id,
        member_user_id=member_user_id,
        role=req.role,
    )
    return ApiResponse[dict](
        success=True,
        data=_serialize_member(membership, account),
        meta=PageMeta(),
        error=None,
    )


@router.delete("/{workspace_id}/members/{member_user_id}", response_model=ApiResponse[dict])
async def remove_member(
    workspace_id: int,
    member_user_id: int,
    access: WorkspaceAccess = Depends(_OWNER_ACCESS),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    if access.workspace_id != workspace_id:
        raise NotFoundError("Không tìm thấy workspace.")
    await workspace_service.remove_member(
        db,
        workspace_id=workspace_id,
        member_user_id=member_user_id,
        acting_user_id=access.user_id,
    )
    return ApiResponse[dict](
        success=True,
        data={"removed": True},
        meta=PageMeta(),
        error=None,
    )


@router.get("/{workspace_id}/shops", response_model=ApiResponse[list[dict]])
async def list_connected_shops(
    workspace_id: int,
    access: WorkspaceAccess = Depends(get_workspace_access),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[list[dict]]:
    if access.workspace_id != workspace_id:
        raise NotFoundError("Không tìm thấy workspace.")
    shops = await marketplace_shop_service.list_shops(db, workspace_id=workspace_id)
    items = [_serialize_shop(shop) for shop in shops]
    return ApiResponse[list[dict]](
        success=True,
        data=items,
        meta=PageMeta(page=1, page_size=len(items), total=len(items)),
        error=None,
    )


@router.delete("/{workspace_id}/shops/{shop_id}", response_model=ApiResponse[dict])
async def disconnect_shop(
    workspace_id: int,
    shop_id: int,
    access: WorkspaceAccess = Depends(_SHOP_MANAGER_ACCESS),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    if access.workspace_id != workspace_id:
        raise NotFoundError("Không tìm thấy workspace.")
    shop = await marketplace_shop_service.disconnect_shop(
        db, workspace_id=workspace_id, shop_id=shop_id
    )
    return ApiResponse[dict](
        success=True,
        data=_serialize_shop(shop),
        meta=PageMeta(),
        error=None,
    )
