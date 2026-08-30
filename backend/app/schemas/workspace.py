"""Request and response shapes for seller workspaces."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

WorkspaceStatus = Literal["active", "suspended", "archived"]
WorkspaceRole = Literal["owner", "manager", "analyst", "viewer", "platform_admin"]
MemberRole = Literal["owner", "manager", "analyst", "viewer"]
AssignableMemberRole = Literal["manager", "analyst", "viewer"]
MarketplacePlatform = Literal["shopee", "lazada", "tiktok_shop"]
MarketplaceConnectionStatus = Literal["connected", "expired", "revoked", "error"]

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=80)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Tên workspace phải có ít nhất 2 ký tự.")
        return value

    @field_validator("slug")
    @classmethod
    def _slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not _SLUG_RE.fullmatch(value):
            raise ValueError("Slug chỉ gồm chữ thường, số và dấu gạch ngang.")
        return value


class WorkspaceOut(BaseModel):
    id: int
    name: str
    slug: str
    status: WorkspaceStatus
    current_role: WorkspaceRole
    created_at: datetime
    updated_at: datetime


class WorkspaceMemberAddRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: AssignableMemberRole = "viewer"

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Email không hợp lệ.")
        return value


class WorkspaceMemberRoleRequest(BaseModel):
    role: MemberRole


class WorkspaceMemberOut(BaseModel):
    user_id: int
    email: str
    name: str | None
    role: MemberRole
    joined_at: datetime


class MarketplaceShopOut(BaseModel):
    id: int
    workspace_id: int
    platform: MarketplacePlatform
    external_shop_id: str
    shop_name: str
    status: MarketplaceConnectionStatus
    token_expires_at: datetime | None
    last_synced_at: datetime | None
    last_error: str | None
    connected_at: datetime
    updated_at: datetime
