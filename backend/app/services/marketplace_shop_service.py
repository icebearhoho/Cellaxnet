"""Workspace-scoped marketplace connection persistence.

OAuth route handlers exchange authorization codes; this service owns the safe
database boundary. It accepts plaintext tokens only in memory and encrypts them
before assigning ORM fields. No API response serializer exposes token columns.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.exceptions import NotFoundError, ValidationError
from app.models.marketplace_shop import MARKETPLACE_PLATFORMS, MarketplaceShop


async def list_shops(db: AsyncSession, *, workspace_id: int) -> list[MarketplaceShop]:
    result = await db.execute(
        select(MarketplaceShop)
        .where(MarketplaceShop.workspace_id == workspace_id)
        .order_by(MarketplaceShop.created_at.desc())
    )
    return list(result.scalars().all())


async def get_shop(
    db: AsyncSession, *, workspace_id: int, shop_id: int
) -> MarketplaceShop:
    result = await db.execute(
        select(MarketplaceShop).where(
            MarketplaceShop.id == shop_id,
            MarketplaceShop.workspace_id == workspace_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Không tìm thấy shop trong workspace.")
    return row


async def upsert_authorized_shop(
    db: AsyncSession,
    *,
    workspace_id: int,
    platform: str,
    external_shop_id: str,
    shop_name: str,
    access_token: str,
    refresh_token: str | None,
    token_expires_at: datetime | None,
) -> MarketplaceShop:
    """Create or reconnect one shop after a successful OAuth exchange."""
    if platform not in MARKETPLACE_PLATFORMS:
        raise ValidationError("Sàn thương mại điện tử chưa được hỗ trợ.")
    if not external_shop_id.strip() or not shop_name.strip():
        raise ValidationError("Thông tin shop trả về từ sàn không đầy đủ.")
    # Both encryptions happen before the ORM object is mutated. If the key is
    # unavailable or malformed, no plaintext or partial credential is stored.
    access_encrypted = crypto.encrypt(access_token)
    refresh_encrypted = crypto.encrypt(refresh_token) if refresh_token else None

    result = await db.execute(
        select(MarketplaceShop).where(
            MarketplaceShop.workspace_id == workspace_id,
            MarketplaceShop.platform == platform,
            MarketplaceShop.external_shop_id == external_shop_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = MarketplaceShop(
            workspace_id=workspace_id,
            platform=platform,
            external_shop_id=external_shop_id,
            shop_name=shop_name,
        )
        db.add(row)

    row.shop_name = shop_name
    row.status = "connected"
    row.access_token_encrypted = access_encrypted
    row.refresh_token_encrypted = refresh_encrypted
    row.token_expires_at = token_expires_at
    row.last_error = None
    await db.commit()
    await db.refresh(row)
    return row


async def credentials_for(
    db: AsyncSession, *, workspace_id: int, shop_id: int
) -> tuple[str, str | None]:
    row = await get_shop(db, workspace_id=workspace_id, shop_id=shop_id)
    if row.status != "connected" or not row.access_token_encrypted:
        raise NotFoundError("Shop chưa có kết nối đang hoạt động.")
    access_token = crypto.decrypt(row.access_token_encrypted)
    refresh_token = (
        crypto.decrypt(row.refresh_token_encrypted)
        if row.refresh_token_encrypted
        else None
    )
    return access_token, refresh_token


async def disconnect_shop(
    db: AsyncSession, *, workspace_id: int, shop_id: int
) -> MarketplaceShop:
    """Revoke locally and erase held credentials while retaining audit metadata."""
    row = await get_shop(db, workspace_id=workspace_id, shop_id=shop_id)
    row.status = "revoked"
    row.access_token_encrypted = None
    row.refresh_token_encrypted = None
    row.token_expires_at = None
    row.last_error = None
    await db.commit()
    await db.refresh(row)
    return row
