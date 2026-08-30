"""Connect the app to the seller's KiotViet store.

One link carries Shopee, Lazada and TikTok Shop, because KiotViet already holds
approved apps with all three and stamps every order with its sale channel.

There is no OAuth callback here: KiotViet authenticates server-to-server with
the store's API keys, so connecting is a single request the seller triggers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, PageMeta
from app.db.session import get_db
from app.schemas.channel_link import ChannelLinkStatus
from app.services import channel_link
from app.services.channel_connectors import ConnectorError

router = APIRouter()


@router.get("/", response_model=ApiResponse[ChannelLinkStatus])
async def status(db: AsyncSession = Depends(get_db)) -> ApiResponse[ChannelLinkStatus]:
    """Where the link stands, plus the per-marketplace order split. No secrets."""
    data = await channel_link.get_status(db)
    return ApiResponse[ChannelLinkStatus](
        success=True, data=data, meta=PageMeta(), error=None
    )


@router.post("/connect", response_model=ApiResponse[dict])
async def connect(db: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    """Verify the store's API keys and record the link.

    Failure is recorded too, so the panel can show *why* the last attempt did
    not take rather than silently staying disconnected.
    """
    try:
        data = await channel_link.connect(db)
    except ConnectorError as exc:
        from app.core.exceptions import ValidationError

        await channel_link.mark_error(db, str(exc))
        raise ValidationError(str(exc)) from exc
    return ApiResponse[dict](success=True, data=data, meta=PageMeta(), error=None)


@router.post("/sync", response_model=ApiResponse[dict])
async def sync(db: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    """Pull recent orders and store how many came from each marketplace."""
    try:
        data = await channel_link.sync_orders(db)
    except ConnectorError as exc:
        from app.core.exceptions import ValidationError

        raise ValidationError(str(exc)) from exc
    return ApiResponse[dict](success=True, data=data, meta=PageMeta(), error=None)


@router.post("/disconnect", response_model=ApiResponse[dict])
async def disconnect(db: AsyncSession = Depends(get_db)) -> ApiResponse[dict]:
    removed = await channel_link.disconnect(db)
    return ApiResponse[dict](
        success=True, data={"removed": removed}, meta=PageMeta(), error=None
    )
