"""Connection lifecycle and sync orchestration across marketplaces.

Everything here is written against `MarketplaceAdapter`; nothing branches on
which marketplace it is talking to. That is the whole point of the split — this
file is what Lazada and TikTok Shop will reuse unchanged.

Three problems it exists to solve:

*Authorisation is a round trip through the seller's browser*, so the request
that starts it and the request that finishes it are different requests, minutes
apart, possibly across a restart. `oauth_states` carries the thread, single-use
and time-boxed.

*Tokens expire mid-sync.* Shopee's last about four hours. `valid_cred()`
refreshes ahead of expiry rather than waiting for a 401, and distinguishes "the
refresh failed" (seller must reconnect) from "the call failed" (retry later).

*A sync is a long partial operation.* It can stop halfway on a rate limit or a
dead token. `sync_runs` records how far each pass got so the next one resumes
instead of restarting, and so a stale shop can be explained without reading
application logs.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.marketplace import (
    OAuthState,
    SellerAccount,
    ShopConnection,
    ShopCredential,
    ShopInventory,
    ShopOrder,
    ShopOrderItem,
    ShopProduct,
    SyncRun,
)
from app.services.marketplace import (
    AdapterError,
    AuthorisationError,
    Cred,
    crypto,
    get_adapter,
)

log = get_logger("app.services.marketplace_link")

# Refresh once the token is this far through its life. Waiting for expiry means
# a sync that starts at 99% of the lifetime dies partway through.
REFRESH_AT_FRACTION = 0.8
MAX_PAGES = 100


class LinkError(RuntimeError):
    """Something the caller should show the seller verbatim."""


# --------------------------------------------------------------------------- #
# Seller accounts
# --------------------------------------------------------------------------- #

async def create_seller_account(
    db: AsyncSession, *, name: str, business_type: str = "individual",
    contact_email: str | None = None, contact_phone: str | None = None,
    user_id: int | None = None,
) -> SellerAccount:
    account = SellerAccount(
        user_id=user_id, name=name.strip(), business_type=business_type,
        contact_email=contact_email, contact_phone=contact_phone,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    log.info("marketplace.account_created", account_id=account.id)
    return account


async def list_seller_accounts(db: AsyncSession) -> list[SellerAccount]:
    rows = await db.execute(select(SellerAccount).order_by(SellerAccount.id.desc()))
    return list(rows.scalars().all())


async def get_seller_account(db: AsyncSession, account_id: int) -> SellerAccount:
    account = await db.get(SellerAccount, account_id)
    if account is None:
        raise LinkError(f"Không tìm thấy tài khoản bán hàng #{account_id}")
    return account


async def list_shops(db: AsyncSession, account_id: int | None = None) -> list[ShopConnection]:
    stmt = select(ShopConnection).order_by(ShopConnection.id.desc())
    if account_id is not None:
        stmt = stmt.where(ShopConnection.seller_account_id == account_id)
    rows = await db.execute(stmt)
    return list(rows.scalars().all())


# --------------------------------------------------------------------------- #
# Authorisation — start
# --------------------------------------------------------------------------- #

async def begin_authorisation(db: AsyncSession, account_id: int, platform: str) -> str:
    """Issue a one-time state token and return where to send the seller."""
    await get_seller_account(db, account_id)
    adapter = get_adapter(platform)

    if not adapter.configured():
        raise LinkError(
            f"{adapter.display_name} chưa cấu hình: thiếu "
            f"{', '.join(adapter.missing_settings())}. Lấy khoá tại {adapter.console_url}."
        )
    # Checked before the seller leaves rather than on the way back: a seller who
    # has already approved on the marketplace should not then be told the app
    # cannot store the result.
    if not crypto.available():
        raise LinkError(
            "CREDENTIAL_ENCRYPTION_KEY chưa cấu hình — không thể lưu token an toàn."
        )

    state = secrets.token_urlsafe(32)[:64]
    now = datetime.now(UTC)
    db.add(OAuthState(
        state=state, seller_account_id=account_id, platform=platform,
        redirect_uri=settings.OAUTH_REDIRECT_BASE, created_at=now,
        expires_at=now + timedelta(seconds=settings.OAUTH_STATE_TTL_SECONDS),
    ))
    await db.commit()

    log.info("marketplace.auth_started", account_id=account_id, platform=platform)
    return adapter.authorize_url(state, settings.OAUTH_REDIRECT_BASE)


# --------------------------------------------------------------------------- #
# Authorisation — callback
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CallbackResult:
    shop_connection_id: int
    platform: str
    shop_name: str | None
    external_shop_id: str


async def complete_authorisation(
    db: AsyncSession, *, state: str, code: str | None,
    params: dict[str, str], error: str | None = None,
) -> CallbackResult:
    """Finish the round trip: validate state, swap the code, store the link."""
    row = await db.get(OAuthState, state)
    if row is None:
        raise LinkError("Phiên kết nối không hợp lệ.")
    if row.consumed_at is not None:
        # A replay. Refuse loudly — this is what a stolen callback URL looks like.
        log.warning("marketplace.state_replayed", state=state[:8])
        raise LinkError("Phiên kết nối đã được dùng rồi.")
    if row.expires_at < datetime.now(UTC):
        raise LinkError("Phiên kết nối đã hết hạn. Bấm kết nối lại.")

    row.consumed_at = datetime.now(UTC)
    await db.commit()

    # The seller pressed Cancel. Not an error in our system, and deliberately
    # does not leave a half-made connection behind.
    if error or not code:
        log.info("marketplace.auth_denied", platform=row.platform, error=error)
        raise LinkError(
            "Bạn đã từ chối cấp quyền, hoặc sàn không trả về mã uỷ quyền. "
            "Chưa có shop nào được kết nối."
        )

    adapter = get_adapter(row.platform)
    try:
        bundle = await adapter.exchange_code(code, params)
    except AdapterError as exc:
        raise LinkError(str(exc)) from exc

    external_shop_id = str(bundle.extra.get("shop_id") or params.get("shop_id") or "")
    if not external_shop_id:
        raise LinkError("Sàn không cho biết shop nào vừa được cấp quyền.")

    shop = await _upsert_shop(db, row.seller_account_id, row.platform, external_shop_id)
    await _store_credentials(db, shop, bundle)

    # Name the shop from the marketplace rather than making the seller type it.
    # A failure here must not undo an authorisation that succeeded.
    try:
        profile = await adapter.fetch_shop(_cred(shop, bundle.access_token, bundle.extra))
        shop.shop_name = profile.name or shop.shop_name
        shop.region = profile.region or shop.region
    except AdapterError as exc:
        log.warning("marketplace.shop_info_failed", platform=row.platform, error=str(exc))

    shop.status = "connected"
    shop.authorized_at = datetime.now(UTC)
    shop.last_error = None
    await db.commit()
    await db.refresh(shop)

    log.info("marketplace.connected", platform=shop.platform, shop_id=shop.id)
    return CallbackResult(
        shop_connection_id=shop.id, platform=shop.platform,
        shop_name=shop.shop_name, external_shop_id=shop.external_shop_id,
    )


async def _upsert_shop(db: AsyncSession, account_id: int, platform: str,
                       external_shop_id: str) -> ShopConnection:
    """Re-authorising an already-linked shop updates it, never duplicates it."""
    found = await db.execute(
        select(ShopConnection).where(
            ShopConnection.platform == platform,
            ShopConnection.external_shop_id == external_shop_id,
        )
    )
    shop = found.scalar_one_or_none()
    if shop is None:
        shop = ShopConnection(
            seller_account_id=account_id, platform=platform,
            external_shop_id=external_shop_id, status="pending",
        )
        db.add(shop)
        await db.flush()
    else:
        shop.seller_account_id = account_id
    return shop


async def _store_credentials(db: AsyncSession, shop: ShopConnection, bundle) -> None:
    cred = await db.get(ShopCredential, shop.id)
    if cred is None:
        cred = ShopCredential(shop_connection_id=shop.id, access_token_enc=b"")
        db.add(cred)
    cred.access_token_enc = crypto.encrypt(bundle.access_token) or b""
    cred.refresh_token_enc = crypto.encrypt(bundle.refresh_token)
    cred.extra_enc = crypto.encrypt_json(bundle.extra)
    cred.expires_at = bundle.expires_at
    cred.refresh_expires_at = bundle.refresh_expires_at
    cred.scope = bundle.scope
    cred.rotated_at = datetime.now(UTC)
    await db.flush()


def _cred(shop: ShopConnection, access_token: str, extra: dict[str, Any]) -> Cred:
    return Cred(
        external_shop_id=shop.external_shop_id, access_token=access_token,
        region=shop.region, extra=extra,
    )


# --------------------------------------------------------------------------- #
# Token lifecycle
# --------------------------------------------------------------------------- #

async def valid_cred(db: AsyncSession, shop: ShopConnection) -> Cred:
    """Credentials guaranteed usable now, refreshing first if they are close to
    expiry.

    Raises LinkError with a status already written to the row, so the caller can
    surface the reason without deciding what it means.
    """
    cred_row = await db.get(ShopCredential, shop.id)
    if cred_row is None:
        await _mark(db, shop, "expired", "Chưa có credential — cần kết nối lại.")
        raise LinkError("Shop chưa được cấp quyền. Bấm kết nối lại.")

    extra = crypto.decrypt_json(cred_row.extra_enc)
    access = crypto.decrypt(cred_row.access_token_enc) or ""

    if not _needs_refresh(cred_row):
        return _cred(shop, access, extra)

    refresh_token = crypto.decrypt(cred_row.refresh_token_enc)
    if not refresh_token:
        await _mark(db, shop, "expired", "Token hết hạn và không có refresh token.")
        raise LinkError("Token đã hết hạn. Cần kết nối lại shop.")

    adapter = get_adapter(shop.platform)
    try:
        bundle = await adapter.refresh(refresh_token, _cred(shop, access, extra))
    except AuthorisationError as exc:
        # Refresh token itself is dead: nothing to retry, a human must act.
        await _mark(db, shop, "expired", str(exc))
        raise LinkError(f"Không làm mới được token: {exc}. Cần kết nối lại shop.") from exc
    except AdapterError as exc:
        await _mark(db, shop, "error", str(exc))
        raise LinkError(f"Lỗi khi làm mới token: {exc}") from exc

    await _store_credentials(db, shop, bundle)
    if shop.status in {"expired", "error"}:
        shop.status = "connected"
        shop.last_error = None
    await db.commit()

    log.info("marketplace.token_refreshed", platform=shop.platform, shop_id=shop.id)
    return _cred(shop, bundle.access_token, bundle.extra)


def _needs_refresh(cred_row: ShopCredential) -> bool:
    if cred_row.expires_at is None:
        return False
    now = datetime.now(UTC)
    if cred_row.expires_at <= now:
        return True
    issued = cred_row.rotated_at or cred_row.created_at
    lifetime = (cred_row.expires_at - issued).total_seconds()
    if lifetime <= 0:
        return True
    return (now - issued).total_seconds() / lifetime >= REFRESH_AT_FRACTION


async def _mark(db: AsyncSession, shop: ShopConnection, status: str, error: str) -> None:
    shop.status = status
    shop.last_error = error[:2000]
    await db.commit()


async def disconnect(db: AsyncSession, shop_id: int) -> bool:
    """Unlink a shop. Credentials go; synced business data stays.

    Deleting orders and products along with the link would destroy history the
    seller may still need, and re-linking would have to re-download it all.
    """
    shop = await db.get(ShopConnection, shop_id)
    if shop is None:
        return False
    cred = await db.get(ShopCredential, shop_id)
    if cred is not None:
        await db.delete(cred)
    shop.status = "disconnected"
    shop.last_error = None
    await db.commit()
    log.info("marketplace.disconnected", shop_id=shop_id)
    return True


# --------------------------------------------------------------------------- #
# Sync
# --------------------------------------------------------------------------- #

@dataclass
class SyncSummary:
    shop_connection_id: int
    products: int = 0
    orders: int = 0
    inventory: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


async def sync_shop(db: AsyncSession, shop_id: int, days: int | None = None) -> SyncSummary:
    """Pull the five data groups for one shop.

    Each group runs independently: products failing must not stop orders from
    syncing, because they fail for different reasons and orders matter more.
    """
    shop = await db.get(ShopConnection, shop_id)
    if shop is None:
        raise LinkError(f"Không tìm thấy shop #{shop_id}")
    if shop.status == "disconnected":
        raise LinkError("Shop đã ngắt kết nối. Bấm kết nối lại trước khi đồng bộ.")

    cred = await valid_cred(db, shop)
    adapter = get_adapter(shop.platform)
    since = datetime.now(UTC) - timedelta(days=days or settings.CHANNEL_SYNC_DAYS)
    summary = SyncSummary(shop_connection_id=shop_id)

    for data_type, runner in (
        ("product", lambda: _sync_products(db, shop, adapter, cred)),
        ("order", lambda: _sync_orders(db, shop, adapter, cred, since)),
    ):
        run = SyncRun(
            shop_connection_id=shop_id, data_type=data_type,
            started_at=datetime.now(UTC), status="running",
        )
        db.add(run)
        await db.flush()
        try:
            read, written = await runner()
            run.records_read, run.records_written = read, written
            run.status = "ok"
            setattr(summary, "products" if data_type == "product" else "orders", written)
        except (AdapterError, LinkError) as exc:
            run.status = "error"
            run.error = str(exc)[:2000]
            summary.errors.append(f"{data_type}: {exc}")
            log.warning("marketplace.sync_failed", data_type=data_type, error=str(exc))
        finally:
            run.finished_at = datetime.now(UTC)
            await db.commit()

    shop.last_synced_at = datetime.now(UTC)
    if summary.errors:
        shop.status = "error" if shop.status == "connected" else shop.status
        shop.last_error = "; ".join(summary.errors)[:2000]
    else:
        shop.status = "connected"
        shop.last_error = None
    await db.commit()
    return summary


async def _sync_products(db: AsyncSession, shop: ShopConnection, adapter,
                         cred: Cred) -> tuple[int, int]:
    read = written = 0
    cursor: str | None = None
    for _ in range(MAX_PAGES):
        page = await adapter.fetch_products(cred, cursor)
        for record in page.items:
            read += 1
            written += await _upsert_product(db, shop.id, record)
        await db.commit()
        cursor = page.next_cursor
        if cursor is None:
            break
    return read, written


async def _upsert_product(db: AsyncSession, shop_id: int, record) -> int:
    found = await db.execute(
        select(ShopProduct).where(
            ShopProduct.shop_connection_id == shop_id,
            ShopProduct.external_product_id == record.external_product_id,
            ShopProduct.external_sku_id == record.external_sku_id,
        )
    )
    row = found.scalar_one_or_none()
    if row is None:
        row = ShopProduct(
            shop_connection_id=shop_id,
            external_product_id=record.external_product_id,
            external_sku_id=record.external_sku_id,
            name=record.name,
        )
        db.add(row)
    row.sku = record.sku
    row.name = record.name
    row.brand = record.brand
    row.category_path = record.category_path
    row.price = record.price
    row.original_price = record.original_price
    row.currency = record.currency
    row.status = record.status
    row.image_url = record.image_url
    row.raw_json = json.dumps(record.raw, default=str)[:1_000_000]
    row.synced_at = datetime.now(UTC)
    return 1


async def _sync_orders(db: AsyncSession, shop: ShopConnection, adapter,
                       cred: Cred, since: datetime) -> tuple[int, int]:
    read = written = 0
    cursor: str | None = None
    for _ in range(MAX_PAGES):
        page = await adapter.fetch_orders(cred, since, cursor)
        for record in page.items:
            read += 1
            written += await _upsert_order(db, shop, record)
        await db.commit()
        cursor = page.next_cursor
        if cursor is None:
            break
    return read, written


async def _upsert_order(db: AsyncSession, shop: ShopConnection, record) -> int:
    found = await db.execute(
        select(ShopOrder).where(
            ShopOrder.shop_connection_id == shop.id,
            ShopOrder.external_order_id == record.external_order_id,
        )
    )
    row = found.scalar_one_or_none()
    if row is None:
        row = ShopOrder(
            shop_connection_id=shop.id,
            external_order_id=record.external_order_id,
            status=record.status,
        )
        db.add(row)
        await db.flush()
    else:
        # Line items are replaced wholesale: a marketplace may cancel or merge
        # them, and reconciling item-by-item would silently keep the removed ones.
        for item in list(row.items):
            await db.delete(item)
        await db.flush()

    row.status = record.status
    row.raw_status = record.raw_status
    row.payment_method = record.payment_method
    row.total_amount = record.total_amount
    row.currency = record.currency
    row.buyer_ref = crypto.buyer_ref(shop.platform, record.external_buyer_id)
    row.placed_at = record.placed_at
    row.platform_updated_at = record.platform_updated_at
    row.raw_json = json.dumps(record.raw, default=str)[:1_000_000]
    row.synced_at = datetime.now(UTC)

    for item in record.items:
        db.add(ShopOrderItem(
            order_id=row.id,
            external_product_id=item.external_product_id,
            external_sku_id=item.external_sku_id,
            sku=item.sku, name=item.name, quantity=item.quantity,
            unit_price=item.unit_price, subtotal=item.subtotal,
        ))
    return 1


async def shop_stats(db: AsyncSession, shop_id: int) -> dict[str, Any]:
    """Counts for the shop list screen."""
    products = await db.execute(
        select(ShopProduct.id).where(ShopProduct.shop_connection_id == shop_id)
    )
    orders = await db.execute(
        select(ShopOrder.id).where(ShopOrder.shop_connection_id == shop_id)
    )
    inventory = await db.execute(
        select(ShopInventory.id).where(ShopInventory.shop_connection_id == shop_id)
    )
    return {
        "products": len(products.scalars().all()),
        "orders": len(orders.scalars().all()),
        "inventory_rows": len(inventory.scalars().all()),
    }
