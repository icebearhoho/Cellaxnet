"""Seller accounts and marketplace shop connections.

The callback endpoint is the one piece a marketplace calls rather than our own
frontend, so it answers with a redirect back into the app instead of JSON: the
seller's browser lands here, and a JSON body would be shown to a human.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.responses import ApiResponse, PageMeta
from app.db.session import get_db
from app.models.marketplace import PLATFORMS
from app.schemas.marketplace import (
    BeginAuthRequest,
    BeginAuthResponse,
    PlatformOut,
    SellerAccountCreate,
    SellerAccountOut,
    ShopConnectionOut,
    SyncResponse,
)
from app.services import marketplace_link
from app.services.marketplace import AdapterError, all_adapters

router = APIRouter()

PLATFORM_LABELS = {"shopee": "Shopee", "lazada": "Lazada", "tiktok": "TikTok Shop"}
STATUS_LABELS = {
    "pending": "Đang chờ cấp quyền",
    "connected": "Đã kết nối",
    "expired": "Token hết hạn — cần kết nối lại",
    "revoked": "Người bán đã thu hồi quyền",
    "error": "Lỗi đồng bộ",
    "disconnected": "Đã ngắt kết nối",
}


def _ok(data, meta: PageMeta | None = None):
    return ApiResponse(success=True, data=data, meta=meta or PageMeta(), error=None)


# --------------------------------------------------------------------------- #
# Platforms
# --------------------------------------------------------------------------- #

@router.get("/platforms", response_model=ApiResponse[list[PlatformOut]])
async def platforms() -> ApiResponse[list[PlatformOut]]:
    """Which marketplaces exist, and which are ready to connect."""
    built = {a.platform: a for a in all_adapters()}
    out: list[PlatformOut] = []
    for platform in PLATFORMS:
        adapter = built.get(platform)
        if adapter is None:
            out.append(PlatformOut(
                platform=platform, display_name=PLATFORM_LABELS.get(platform, platform),
                configured=False, missing_settings=[], console_url="", implemented=False,
            ))
            continue
        out.append(PlatformOut(
            platform=adapter.platform, display_name=adapter.display_name,
            configured=adapter.configured(), missing_settings=adapter.missing_settings(),
            console_url=adapter.console_url, implemented=True,
        ))
    return _ok(out)


# --------------------------------------------------------------------------- #
# Seller accounts
# --------------------------------------------------------------------------- #

@router.get("/accounts", response_model=ApiResponse[list[SellerAccountOut]])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SellerAccountOut]]:
    accounts = await marketplace_link.list_seller_accounts(db)
    return _ok([
        SellerAccountOut(
            id=a.id, name=a.name, business_type=a.business_type,
            contact_email=a.contact_email, contact_phone=a.contact_phone,
            status=a.status, shop_count=len(a.shops), created_at=a.created_at,
        )
        for a in accounts
    ])


@router.post("/accounts", response_model=ApiResponse[SellerAccountOut])
async def create_account(
    payload: SellerAccountCreate, db: AsyncSession = Depends(get_db),
) -> ApiResponse[SellerAccountOut]:
    account = await marketplace_link.create_seller_account(
        db, name=payload.name, business_type=payload.business_type,
        contact_email=payload.contact_email, contact_phone=payload.contact_phone,
    )
    return _ok(SellerAccountOut(
        id=account.id, name=account.name, business_type=account.business_type,
        contact_email=account.contact_email, contact_phone=account.contact_phone,
        status=account.status, shop_count=0, created_at=account.created_at,
    ))


# --------------------------------------------------------------------------- #
# Shops
# --------------------------------------------------------------------------- #

@router.get("/shops", response_model=ApiResponse[list[ShopConnectionOut]])
async def list_shops(
    seller_account_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[ShopConnectionOut]]:
    """Connected shops with marketplace, status and last sync time."""
    shops = await marketplace_link.list_shops(db, seller_account_id)
    out: list[ShopConnectionOut] = []
    for shop in shops:
        stats = await marketplace_link.shop_stats(db, shop.id)
        out.append(ShopConnectionOut(
            id=shop.id, seller_account_id=shop.seller_account_id,
            platform=shop.platform,
            platform_label=PLATFORM_LABELS.get(shop.platform, shop.platform),
            external_shop_id=shop.external_shop_id, shop_name=shop.shop_name,
            region=shop.region, status=shop.status,
            status_label=STATUS_LABELS.get(shop.status, shop.status),
            authorized_at=shop.authorized_at, last_synced_at=shop.last_synced_at,
            last_error=shop.last_error,
            products=stats["products"], orders=stats["orders"],
        ))
    return _ok(out, PageMeta(page=1, page_size=len(out), total=len(out)))


@router.post("/connect", response_model=ApiResponse[BeginAuthResponse])
async def begin_connect(
    payload: BeginAuthRequest, db: AsyncSession = Depends(get_db),
) -> ApiResponse[BeginAuthResponse]:
    """Start authorisation; returns where to send the seller."""
    try:
        url = await marketplace_link.begin_authorisation(
            db, payload.seller_account_id, payload.platform
        )
    except (marketplace_link.LinkError, AdapterError) as exc:
        raise ValidationError(str(exc)) from exc
    return _ok(BeginAuthResponse(
        authorize_url=url, expires_in_seconds=settings.OAUTH_STATE_TTL_SECONDS
    ))


@router.get("/callback")
async def callback(
    request: Request,
    state: str = Query(default=""),
    code: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Where the marketplace sends the seller back.

    Always redirects into the app — a human is looking at this response. The
    outcome travels as query parameters so the panel can show it.
    """
    ui = "http://localhost:3000/seller/marketplace"
    params = {k: v for k, v in request.query_params.items()}
    try:
        result = await marketplace_link.complete_authorisation(
            db, state=state, code=code, params=params, error=error
        )
    except (marketplace_link.LinkError, AdapterError) as exc:
        from urllib.parse import quote
        return RedirectResponse(f"{ui}?connect=error&message={quote(str(exc))}", 302)
    return RedirectResponse(
        f"{ui}?connect=ok&shop={result.shop_connection_id}"
        f"&platform={result.platform}", 302
    )


@router.post("/shops/{shop_id}/sync", response_model=ApiResponse[SyncResponse])
async def sync_shop(
    shop_id: int, days: int | None = Query(default=None, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SyncResponse]:
    try:
        summary = await marketplace_link.sync_shop(db, shop_id, days)
    except (marketplace_link.LinkError, AdapterError) as exc:
        raise ValidationError(str(exc)) from exc
    return _ok(SyncResponse(
        shop_connection_id=summary.shop_connection_id, products=summary.products,
        orders=summary.orders, errors=summary.errors,
    ))


@router.post("/shops/{shop_id}/disconnect", response_model=ApiResponse[dict])
async def disconnect_shop(
    shop_id: int, db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict]:
    removed = await marketplace_link.disconnect(db, shop_id)
    return _ok({"disconnected": removed})
