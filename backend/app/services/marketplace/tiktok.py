"""TikTok Shop Partner API adapter.

Authorisation is three-legged like Shopee's, but three things about TikTok's API
shape this file and have no counterpart in the Shopee adapter:

*Every shop-scoped call needs a `shop_cipher`.* The token alone is not enough.
The cipher is obtained by calling `/authorization/202309/shops` after the token
exchange, and must then travel on every subsequent request. It is fetched during
`exchange_code` and carried in `TokenBundle.extra`, which is precisely why that
field exists on the protocol.

*Listing endpoints are POST with a JSON body, not GET with query parameters.*
Filters like a date range live in the body, while paging and the cipher stay in
the query string — and the signature has to cover both.

*Paging is by opaque cursor, not offset.* `next_page_token` is returned by the
API and passed back verbatim; there is no arithmetic to do, and an empty token
is the only reliable end-of-data signal.

The signature covers the path, the sorted query parameters, and the body, all
wrapped in the app secret at both ends. Getting any part of that ordering wrong
produces a generic signature error that names nothing, so `_sign` is written
once and every request goes through it.

Endpoint versions (202309, 202312) are stated in one place to be checked against
current documentation at integration time; TikTok versions its API by date and
retires older versions.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.marketplace.base import (
    AdapterError,
    AuthorisationError,
    Cred,
    InventoryRecord,
    OrderItemRecord,
    OrderRecord,
    Page,
    ProductRecord,
    RateLimitedError,
    ShopProfile,
    TokenBundle,
    register,
)

log = get_logger("app.services.marketplace.tiktok")

TIMEOUT = httpx.Timeout(30.0, connect=8.0)

# Authorisation lives on a different host from the business APIs.
AUTH_HOST = "https://auth.tiktok-shops.com"
API_HOST = "https://open-api.tiktokglobalshop.com"
AUTHORIZE_URL = "https://services.tiktokshop.com/open/authorize"

PATH_TOKEN = "/api/v2/token/get"
PATH_REFRESH = "/api/v2/token/refresh"
PATH_SHOPS = "/authorization/202309/shops"
PATH_ORDER_SEARCH = "/order/202309/orders/search"
PATH_PRODUCT_SEARCH = "/product/202312/products/search"

PAGE_SIZE = 50

# TikTok's order statuses -> our canonical vocabulary. Anything absent maps to
# "unknown" and is logged rather than guessed: a wrong guess silently miscounts
# revenue, which is worse than an obviously missing value.
ORDER_STATUS_MAP: dict[str, str] = {
    "UNPAID": "unpaid",
    "ON_HOLD": "awaiting_shipment",
    "AWAITING_SHIPMENT": "awaiting_shipment",
    "PARTIALLY_SHIPPING": "awaiting_shipment",
    "AWAITING_COLLECTION": "shipped",
    "IN_TRANSIT": "shipped",
    "DELIVERED": "delivered",
    "COMPLETED": "completed",
    "CANCELLED": "cancelled",
}

# Response codes that mean the authorisation is dead rather than the call having
# failed transiently. The seller has to reconnect; retrying will never help.
DEAD_AUTH_CODES = {105000, 105001, 105002, 105003, 36004003}


class TikTokAdapter:
    platform = "tiktok"
    display_name = "TikTok Shop"
    console_url = "https://partner.tiktokshop.com"

    # --- configuration ----------------------------------------------------

    def configured(self) -> bool:
        return bool(
            settings.TIKTOK_APP_KEY and settings.TIKTOK_APP_SECRET
            and settings.TIKTOK_SERVICE_ID
        )

    def missing_settings(self) -> list[str]:
        out = []
        if not settings.TIKTOK_APP_KEY:
            out.append("TIKTOK_APP_KEY")
        if not settings.TIKTOK_APP_SECRET:
            out.append("TIKTOK_APP_SECRET")
        if not settings.TIKTOK_SERVICE_ID:
            # Distinct from the App Key: shown just below the app name on its
            # detail page in Partner Center. Falling back to the App Key here
            # produces "This service does not exist" on the authorize screen —
            # a TikTok-side error that names nothing, so the check has to.
            out.append("TIKTOK_SERVICE_ID")
        return out

    def _require_config(self) -> tuple[str, str]:
        if not self.configured():
            raise AdapterError(
                f"TikTok Shop chưa cấu hình: thiếu {', '.join(self.missing_settings())}. "
                f"Lấy khoá tại {self.console_url}."
            )
        return str(settings.TIKTOK_APP_KEY), str(settings.TIKTOK_APP_SECRET)

    # --- signing ----------------------------------------------------------

    def _sign(self, path: str, params: dict[str, Any], body: str | None = None) -> str:
        """HMAC-SHA256 over path + sorted query params + body, wrapped in the secret.

        `sign` and `access_token` are excluded: the first does not exist yet, and
        the second is sent as a header rather than being part of the signed
        material. Sorting is by key, and the pairs are concatenated with no
        separators.
        """
        _, app_secret = self._require_config()
        signable = {
            k: v for k, v in params.items() if k not in ("sign", "access_token")
        }
        joined = "".join(f"{k}{signable[k]}" for k in sorted(signable))
        base = f"{path}{joined}"
        if body:
            base += body
        wrapped = f"{app_secret}{base}{app_secret}"
        return hmac.new(
            app_secret.encode("utf-8"), wrapped.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _common_params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        app_key, _ = self._require_config()
        params: dict[str, Any] = {"app_key": app_key, "timestamp": int(time.time())}
        if extra:
            params.update(extra)
        return params

    # --- authorisation ----------------------------------------------------

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        """Where to send the seller to approve access.

        TikTok echoes `state` back on the callback, so unlike Shopee it does not
        need to be smuggled through the redirect URL. The redirect itself is
        configured in Partner Center rather than passed here, so it is not sent.

        `service_id` is not the App Key — it is a separate id shown just below
        the app name on its detail page in Partner Center. Passing the App Key
        here is accepted by the URL builder but rejected by TikTok with
        "This service does not exist", which names nothing wrong.
        """
        self._require_config()
        service_id = settings.TIKTOK_SERVICE_ID
        return f"{AUTHORIZE_URL}?{urlencode({'service_id': service_id, 'state': state})}"

    async def exchange_code(self, code: str, params: dict[str, str]) -> TokenBundle:
        """Swap the callback's one-time code for tokens, then resolve the shop.

        Two round trips, not one: TikTok's token response says who authorised but
        not which shop, and every later call needs the shop's `cipher`. Doing it
        here means the rest of the system never has to know that.
        """
        app_key, app_secret = self._require_config()
        query = {
            "app_key": app_key,
            "app_secret": app_secret,
            "auth_code": code,
            "grant_type": "authorized_code",
        }
        payload = await self._auth_call(PATH_TOKEN, query)
        bundle = self._token_bundle(payload)

        # Resolve shop id and cipher while we have a fresh token.
        shop = await self._first_shop(bundle.access_token)
        return TokenBundle(
            access_token=bundle.access_token,
            refresh_token=bundle.refresh_token,
            expires_at=bundle.expires_at,
            refresh_expires_at=bundle.refresh_expires_at,
            extra={**bundle.extra, **shop},
        )

    async def refresh(self, refresh_token: str, cred: Cred) -> TokenBundle:
        app_key, app_secret = self._require_config()
        query = {
            "app_key": app_key,
            "app_secret": app_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        payload = await self._auth_call(PATH_REFRESH, query)
        bundle = self._token_bundle(payload)
        # Keep the cipher: refreshing a token does not change which shop it is
        # for, and re-resolving it would cost a round trip on every refresh.
        return TokenBundle(
            access_token=bundle.access_token,
            refresh_token=bundle.refresh_token,
            expires_at=bundle.expires_at,
            refresh_expires_at=bundle.refresh_expires_at,
            extra={**cred.extra, **bundle.extra},
        )

    def _token_bundle(self, payload: dict[str, Any]) -> TokenBundle:
        data = payload.get("data") or {}
        access = data.get("access_token")
        if not access:
            raise AdapterError(f"TikTok Shop không trả về access_token: {payload}")

        now = int(time.time())
        # TikTok returns absolute expiry timestamps, not durations. Falling back
        # to the documented 7 day / 365 day lifetimes keeps the columns honest
        # rather than leaving them empty, which would read as "never expires".
        access_exp = _as_int(data.get("access_token_expire_in"), 0)
        refresh_exp = _as_int(data.get("refresh_token_expire_in"), 0)
        return TokenBundle(
            access_token=access,
            refresh_token=data.get("refresh_token"),
            expires_at=(
                datetime.fromtimestamp(access_exp, tz=UTC) if access_exp > now
                else datetime.now(UTC) + timedelta(days=7)
            ),
            refresh_expires_at=(
                datetime.fromtimestamp(refresh_exp, tz=UTC) if refresh_exp > now
                else datetime.now(UTC) + timedelta(days=365)
            ),
            extra={
                k: v for k, v in (
                    ("seller_name", data.get("seller_name")),
                    ("open_id", data.get("open_id")),
                ) if v
            },
        )

    async def _first_shop(self, access_token: str) -> dict[str, Any]:
        """The shop this authorisation covers, plus its cipher.

        A seller may authorise several shops; the sync layer models one shop per
        connection, so the first is taken and the rest are logged. Linking the
        others is a second authorisation, which the connect flow already handles.
        """
        payload = await self._get(PATH_SHOPS, access_token, {})
        shops = (payload.get("data") or {}).get("shops") or []
        if not shops:
            raise AdapterError(
                "TikTok Shop không trả về cửa hàng nào cho quyền vừa cấp. "
                "Kiểm tra tài khoản đã có shop hoạt động chưa."
            )
        if len(shops) > 1:
            log.info("tiktok.multiple_shops", count=len(shops))

        shop = shops[0]
        return {
            "shop_id": str(shop.get("id") or ""),
            "shop_cipher": str(shop.get("cipher") or ""),
            "shop_name": shop.get("name"),
            "region": shop.get("region") or "VN",
        }

    # --- reading ----------------------------------------------------------

    async def fetch_shop(self, cred: Cred) -> ShopProfile:
        payload = await self._get(PATH_SHOPS, cred.access_token, {})
        shops = (payload.get("data") or {}).get("shops") or []
        mine = next(
            (s for s in shops if str(s.get("id")) == cred.external_shop_id),
            shops[0] if shops else {},
        )
        return ShopProfile(
            external_shop_id=cred.external_shop_id,
            name=mine.get("name"),
            region=mine.get("region") or cred.region,
            status=mine.get("seller_type"),
            raw=mine,
        )

    async def fetch_products(self, cred: Cred, cursor: str | None) -> Page:
        query: dict[str, Any] = {"page_size": PAGE_SIZE}
        if cursor:
            query["page_token"] = cursor
        payload = await self._post(
            PATH_PRODUCT_SEARCH, cred, query, {"status": "ACTIVATE"}
        )
        data = payload.get("data") or {}

        records: list[ProductRecord] = []
        for product in data.get("products") or []:
            product_id = str(product.get("id") or "")
            title = str(product.get("title") or "")
            status = "active" if product.get("status") == "ACTIVATE" else "inactive"
            images = product.get("main_images") or []
            image_url = None
            if images and isinstance(images[0], dict):
                urls = images[0].get("urls") or []
                image_url = urls[0] if urls else None

            skus = product.get("skus") or []
            if not skus:
                # A listing with no variants still needs a row; "" keeps the
                # unique key well-defined, since NULL never equals NULL in SQL.
                records.append(ProductRecord(
                    external_product_id=product_id, external_sku_id="",
                    name=title, status=status, image_url=image_url, raw=product,
                ))
                continue

            for sku in skus:
                price = sku.get("price") or {}
                records.append(ProductRecord(
                    external_product_id=product_id,
                    external_sku_id=str(sku.get("id") or ""),
                    sku=sku.get("seller_sku"),
                    name=title,
                    brand=(product.get("brand") or {}).get("name"),
                    category_path=_category_path(product),
                    price=_money(price.get("sale_price")),
                    original_price=_money(price.get("original_price")),
                    currency=price.get("currency") or "VND",
                    status=status,
                    image_url=image_url,
                    raw={**product, "_sku": sku},
                ))

        return Page(items=records, next_cursor=data.get("next_page_token") or None)

    async def fetch_inventory(self, cred: Cred, cursor: str | None) -> Page:
        """Stock arrives inside the product payload, so this reuses that call.

        TikTok has no separate inventory endpoint at this version: each SKU
        carries its per-warehouse quantities. Walking products and extracting
        them avoids a second API surface that does not exist.
        """
        query: dict[str, Any] = {"page_size": PAGE_SIZE}
        if cursor:
            query["page_token"] = cursor
        payload = await self._post(
            PATH_PRODUCT_SEARCH, cred, query, {"status": "ACTIVATE"}
        )
        data = payload.get("data") or {}

        out: list[InventoryRecord] = []
        for product in data.get("products") or []:
            product_id = str(product.get("id") or "")
            for sku in product.get("skus") or []:
                sku_id = str(sku.get("id") or "")
                for stock in sku.get("inventory") or []:
                    out.append(InventoryRecord(
                        external_product_id=product_id,
                        external_sku_id=sku_id,
                        warehouse_id=str(stock.get("warehouse_id") or ""),
                        quantity_available=_as_int(stock.get("quantity"), 0),
                    ))
        return Page(items=out, next_cursor=data.get("next_page_token") or None)

    async def fetch_orders(self, cred: Cred, since: datetime, cursor: str | None) -> Page:
        query: dict[str, Any] = {"page_size": PAGE_SIZE, "sort_field": "create_time"}
        if cursor:
            query["page_token"] = cursor
        body = {
            "create_time_ge": int(since.timestamp()),
            "create_time_lt": int(datetime.now(UTC).timestamp()),
        }
        payload = await self._post(PATH_ORDER_SEARCH, cred, query, body)
        data = payload.get("data") or {}

        records: list[OrderRecord] = []
        for order in data.get("orders") or []:
            raw_status = str(order.get("status") or "")
            status = ORDER_STATUS_MAP.get(raw_status, "unknown")
            if status == "unknown" and raw_status:
                log.warning("tiktok.unmapped_order_status", status=raw_status)

            payment = order.get("payment") or {}
            items = [
                OrderItemRecord(
                    external_product_id=str(it.get("product_id") or "") or None,
                    external_sku_id=str(it.get("sku_id") or "") or None,
                    sku=it.get("seller_sku"),
                    name=it.get("product_name"),
                    quantity=1,  # TikTok returns one line per unit sold
                    unit_price=_money(it.get("sale_price")) or 0,
                    subtotal=_money(it.get("sale_price")) or 0,
                )
                for it in order.get("line_items") or []
            ]

            records.append(OrderRecord(
                external_order_id=str(order.get("id") or ""),
                status=status,
                raw_status=raw_status or None,
                payment_method=order.get("payment_method_name"),
                total_amount=_money(payment.get("total_amount")) or 0,
                currency=payment.get("currency") or "VND",
                external_buyer_id=str(order.get("user_id") or "") or None,
                placed_at=_ts(order.get("create_time")),
                platform_updated_at=_ts(order.get("update_time")),
                items=items,
                raw=order,
            ))

        return Page(items=records, next_cursor=data.get("next_page_token") or None)

    # --- transport --------------------------------------------------------

    async def _auth_call(self, path: str, query: dict[str, Any]) -> dict[str, Any]:
        """Token endpoints live on the auth host and are not signed."""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{AUTH_HOST}{path}", params=query)
        return self._unwrap(r, path)

    async def _get(
        self, path: str, access_token: str, query: dict[str, Any]
    ) -> dict[str, Any]:
        params = self._common_params(query)
        params["sign"] = self._sign(path, params)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(
                f"{API_HOST}{path}", params=params,
                headers={"x-tts-access-token": access_token},
            )
        return self._unwrap(r, path)

    async def _post(
        self, path: str, cred: Cred, query: dict[str, Any], body: dict[str, Any]
    ) -> dict[str, Any]:
        cipher = str(cred.extra.get("shop_cipher") or "")
        if not cipher:
            # Without the cipher every call is rejected, and the error TikTok
            # returns does not say why. Fail here with a message that does.
            raise AuthorisationError(
                "Thiếu shop_cipher của TikTok Shop — cần kết nối lại shop."
            )

        params = self._common_params({**query, "shop_cipher": cipher})
        # The body is part of the signed material, so it must be serialised once
        # and the exact same bytes sent — re-serialising could reorder keys and
        # invalidate the signature.
        raw_body = json.dumps(body, separators=(",", ":"))
        params["sign"] = self._sign(path, params, raw_body)

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{API_HOST}{path}", params=params, content=raw_body,
                headers={
                    "x-tts-access-token": cred.access_token,
                    "content-type": "application/json",
                },
            )
        return self._unwrap(r, path)

    def _unwrap(self, r: httpx.Response, path: str) -> dict[str, Any]:
        """TikTok reports failure in the body, not the status code.

        A refusal arrives as HTTP 200 with a non-zero `code`. Checking only the
        status code would treat every rejection as success and store an empty
        result — the failure mode this method exists to prevent.
        """
        if r.status_code == 429:
            raise RateLimitedError("TikTok Shop giới hạn tần suất gọi API", retry_after_s=60)

        try:
            payload = r.json()
        except ValueError as exc:
            raise AdapterError(
                f"TikTok Shop trả về phản hồi không phải JSON (HTTP {r.status_code})"
            ) from exc

        if not isinstance(payload, dict):
            raise AdapterError(f"TikTok Shop trả về cấu trúc lạ tại {path}")

        code = _as_int(payload.get("code"), -1)
        if code != 0:
            message = str(payload.get("message") or "")
            log.warning("tiktok.api_error", path=path, code=code, message=message)
            if code in DEAD_AUTH_CODES:
                raise AuthorisationError(
                    f"TikTok Shop từ chối quyền truy cập ({code}). Cần kết nối lại shop."
                )
            raise AdapterError(
                f"TikTok Shop lỗi {code}: {message or 'không rõ nguyên nhân'}"
            )

        if r.status_code >= 400:
            raise AdapterError(f"TikTok Shop trả về HTTP {r.status_code}: {r.text[:200]}")
        return payload


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _money(value: Any) -> int | None:
    """TikTok returns amounts as decimal strings; keep them integral in đồng."""
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _ts(value: Any) -> datetime | None:
    """Unix seconds -> aware UTC. Naive datetimes compare wrongly against aware."""
    seconds = _as_int(value, 0)
    if seconds <= 0:
        return None
    return datetime.fromtimestamp(seconds, tz=UTC)


def _category_path(product: dict[str, Any]) -> str | None:
    chain = product.get("category_chains") or []
    names = [str(c.get("local_name")) for c in chain if isinstance(c, dict) and c.get("local_name")]
    return " > ".join(names) or None


adapter = TikTokAdapter()
register(adapter)
