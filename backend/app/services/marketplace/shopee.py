"""Shopee Open Platform adapter.

Authorisation is three-legged: the seller is sent to Shopee, approves, and
Shopee redirects back with a `code` and the `shop_id` they approved for. The
code is then exchanged for tokens server-to-server.

Two properties of Shopee's API drive the shape of this file:

*Every* call is signed. The signature is an HMAC-SHA256 over a concatenation
whose members differ by call type — public calls (getting a token) sign
`partner_id | path | timestamp`, shop-scoped calls append `access_token` and
`shop_id`. Getting the member list or their order wrong yields a generic
"wrong sign" error that names nothing, so `_sign` is written once and every
request goes through it.

Access tokens last about four hours — by far the shortest of the three
marketplaces — while the refresh token lasts about thirty days. Any design that
fetches a token and assumes it stays valid for the length of a sync will break
here; refresh is handled by the caller through `refresh()`, driven off
`expires_at`.

Endpoint paths follow API v2. Shopee versions its API and deprecates paths, so
these are stated in one place to be checked against current documentation at
integration time rather than scattered through the code.
"""

from __future__ import annotations

import hashlib
import hmac
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

log = get_logger("app.services.marketplace.shopee")

TIMEOUT = httpx.Timeout(30.0, connect=8.0)

LIVE_HOST = "https://partner.shopeemobile.com"
SANDBOX_HOST = "https://partner.test-stable.shopeemobile.com"

PATH_AUTH = "/api/v2/shop/auth_partner"
PATH_TOKEN = "/api/v2/auth/token/get_access_token"
PATH_REFRESH = "/api/v2/auth/access_token/get"
PATH_SHOP_INFO = "/api/v2/shop/get_shop_info"
PATH_ITEM_LIST = "/api/v2/product/get_item_list"
PATH_ITEM_INFO = "/api/v2/product/get_item_base_info"
PATH_MODEL_LIST = "/api/v2/product/get_model_list"
PATH_ORDER_LIST = "/api/v2/order/get_order_list"
PATH_ORDER_DETAIL = "/api/v2/order/get_order_detail"

PAGE_SIZE = 50

# Shopee's order_status values -> our canonical vocabulary. Anything absent maps
# to "unknown" and is logged rather than guessed: a wrong guess here silently
# miscounts revenue, which is worse than an obviously missing value.
ORDER_STATUS_MAP: dict[str, str] = {
    "UNPAID": "unpaid",
    "READY_TO_SHIP": "awaiting_shipment",
    "PROCESSED": "awaiting_shipment",
    "RETRY_SHIP": "awaiting_shipment",
    "SHIPPED": "shipped",
    "TO_CONFIRM_RECEIVE": "delivered",
    "COMPLETED": "completed",
    "CANCELLED": "cancelled",
    "IN_CANCEL": "cancelled",
    "INVOICE_PENDING": "awaiting_shipment",
    "TO_RETURN": "returned",
}

# Errors that mean "this authorisation is dead", as opposed to a transient
# refusal. The seller has to reconnect; retrying will never help.
DEAD_AUTH_ERRORS = {
    "error_auth",
    "error_permission",
    "invalid_access_token",
    "access_token_error",
    "error_token_expired",
    "shop_not_authorized",
}


class ShopeeAdapter:
    platform = "shopee"
    display_name = "Shopee"
    console_url = "https://open.shopee.com"

    # --- configuration ----------------------------------------------------

    @property
    def host(self) -> str:
        return SANDBOX_HOST if settings.SHOPEE_SANDBOX else LIVE_HOST

    def configured(self) -> bool:
        return bool(settings.SHOPEE_PARTNER_ID and settings.SHOPEE_PARTNER_KEY)

    def missing_settings(self) -> list[str]:
        out = []
        if not settings.SHOPEE_PARTNER_ID:
            out.append("SHOPEE_PARTNER_ID")
        if not settings.SHOPEE_PARTNER_KEY:
            out.append("SHOPEE_PARTNER_KEY")
        return out

    def _require_config(self) -> tuple[str, str]:
        if not self.configured():
            raise AdapterError(
                f"Shopee chưa cấu hình: thiếu {', '.join(self.missing_settings())}. "
                f"Lấy khoá tại {self.console_url}."
            )
        return str(settings.SHOPEE_PARTNER_ID), str(settings.SHOPEE_PARTNER_KEY)

    # --- signing ----------------------------------------------------------

    def _sign(self, path: str, timestamp: int,
              access_token: str | None = None,
              shop_id: str | None = None) -> str:
        """HMAC-SHA256 over the base string Shopee specifies for this call.

        Public calls sign `partner_id | path | timestamp`. Shop-scoped calls
        append `access_token | shop_id`. Order is significant and there are no
        separators.
        """
        partner_id, partner_key = self._require_config()
        base = f"{partner_id}{path}{timestamp}"
        if access_token:
            base += access_token
        if shop_id:
            base += str(shop_id)
        return hmac.new(
            partner_key.encode("utf-8"), base.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _common_params(self, path: str, cred: Cred | None = None) -> dict[str, Any]:
        partner_id, _ = self._require_config()
        ts = int(time.time())
        if cred is None:
            return {"partner_id": partner_id, "timestamp": ts,
                    "sign": self._sign(path, ts)}
        return {
            "partner_id": partner_id,
            "timestamp": ts,
            "access_token": cred.access_token,
            "shop_id": cred.external_shop_id,
            "sign": self._sign(path, ts, cred.access_token, cred.external_shop_id),
        }

    # --- authorisation ----------------------------------------------------

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        """Where to send the seller to approve access.

        Shopee does not echo an arbitrary `state` back, so it is carried on the
        redirect URL instead — the callback still arrives with something only we
        could have issued, which is what the CSRF check needs.
        """
        partner_id, _ = self._require_config()
        ts = int(time.time())
        redirect = f"{redirect_uri}?state={state}"
        qs = urlencode({
            "partner_id": partner_id,
            "timestamp": ts,
            "sign": self._sign(PATH_AUTH, ts),
            "redirect": redirect,
        })
        return f"{self.host}{PATH_AUTH}?{qs}"

    async def exchange_code(self, code: str, params: dict[str, str]) -> TokenBundle:
        """Swap the callback's one-time code for tokens.

        `shop_id` comes back on the callback query string, not from us, so it is
        read from `params` rather than assumed.
        """
        partner_id, _ = self._require_config()
        shop_id = params.get("shop_id") or params.get("main_account_id")
        if not shop_id:
            raise AdapterError("Shopee không trả về shop_id trên callback")

        body = {"code": code, "shop_id": int(shop_id), "partner_id": int(partner_id)}
        payload = await self._post(PATH_TOKEN, self._common_params(PATH_TOKEN), body)
        return self._token_bundle(payload, extra={"shop_id": str(shop_id)})

    async def refresh(self, refresh_token: str, cred: Cred) -> TokenBundle:
        partner_id, _ = self._require_config()
        body = {
            "refresh_token": refresh_token,
            "shop_id": int(cred.external_shop_id),
            "partner_id": int(partner_id),
        }
        payload = await self._post(PATH_REFRESH, self._common_params(PATH_REFRESH), body)
        return self._token_bundle(payload, extra=dict(cred.extra))

    def _token_bundle(self, payload: dict[str, Any], extra: dict[str, Any]) -> TokenBundle:
        access = payload.get("access_token")
        if not access:
            raise AdapterError(f"Shopee không trả về access_token: {payload}")
        # expire_in is seconds; Shopee's is ~4 hours. The refresh token's own
        # lifetime is not returned, so the documented 30 days is assumed and
        # recorded — better an explicit assumption than an empty column that
        # reads as "never expires".
        expires_in = int(payload.get("expire_in") or 0)
        return TokenBundle(
            access_token=access,
            refresh_token=payload.get("refresh_token"),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in or 14400),
            refresh_expires_at=datetime.now(UTC) + timedelta(days=30),
            extra=extra,
        )

    # --- reading ----------------------------------------------------------

    async def fetch_shop(self, cred: Cred) -> ShopProfile:
        payload = await self._get(PATH_SHOP_INFO, self._common_params(PATH_SHOP_INFO, cred))
        return ShopProfile(
            external_shop_id=cred.external_shop_id,
            name=payload.get("shop_name"),
            region=payload.get("region") or cred.region,
            status=payload.get("status"),
            raw=payload,
        )

    async def fetch_products(self, cred: Cred, cursor: str | None) -> Page:
        offset = _as_int(cursor, 0)
        params = self._common_params(PATH_ITEM_LIST, cred)
        params.update({
            "offset": offset,
            "page_size": PAGE_SIZE,
            "item_status": "NORMAL",
        })
        payload = await self._get(PATH_ITEM_LIST, params)
        response = payload.get("response") or payload
        rows = response.get("item") or []
        item_ids = [str(r.get("item_id")) for r in rows if r.get("item_id")]

        records: list[ProductRecord] = []
        if item_ids:
            records = await self._product_details(cred, item_ids)

        has_next = bool(response.get("has_next_page"))
        next_cursor = str(response.get("next_offset") or offset + len(rows)) if has_next else None
        return Page(items=records, next_cursor=next_cursor)

    async def _product_details(self, cred: Cred, item_ids: list[str]) -> list[ProductRecord]:
        """Listing endpoint returns ids only; names and prices need a second call."""
        params = self._common_params(PATH_ITEM_INFO, cred)
        params["item_id_list"] = ",".join(item_ids)
        payload = await self._get(PATH_ITEM_INFO, params)
        response = payload.get("response") or payload

        out: list[ProductRecord] = []
        for item in response.get("item_list") or []:
            price_info = (item.get("price_info") or [{}])[0]
            images = (item.get("image") or {}).get("image_url_list") or []
            out.append(ProductRecord(
                external_product_id=str(item.get("item_id") or ""),
                # Variant-level rows come from get_model_list; a listing with no
                # variants keeps "" so the unique key stays well-defined.
                external_sku_id="",
                sku=item.get("item_sku"),
                name=str(item.get("item_name") or ""),
                brand=(item.get("brand") or {}).get("original_brand_name"),
                category_path=str(item.get("category_id") or "") or None,
                price=_money(price_info.get("current_price")),
                original_price=_money(price_info.get("original_price")),
                currency=price_info.get("currency") or "VND",
                status="active" if item.get("item_status") == "NORMAL" else "inactive",
                image_url=images[0] if images else None,
                raw=item,
            ))
        return out

    async def fetch_inventory(self, cred: Cred, cursor: str | None) -> Page:
        """Stock lives on the variant (model) list, one call per listing.

        `cursor` is the item id to read, so the sync loop can walk listings
        without this adapter holding state between calls.
        """
        if not cursor:
            return Page(items=[], next_cursor=None)

        params = self._common_params(PATH_MODEL_LIST, cred)
        params["item_id"] = cursor
        payload = await self._get(PATH_MODEL_LIST, params)
        response = payload.get("response") or payload

        out: list[InventoryRecord] = []
        for model in response.get("model") or []:
            for stock in model.get("stock_info_v2", {}).get("seller_stock", []) or []:
                out.append(InventoryRecord(
                    external_product_id=str(cursor),
                    external_sku_id=str(model.get("model_id") or ""),
                    warehouse_id=str(stock.get("location_id") or ""),
                    quantity_available=_as_int(stock.get("stock"), 0),
                ))
        return Page(items=out, next_cursor=None)

    async def fetch_orders(self, cred: Cred, since: datetime, cursor: str | None) -> Page:
        params = self._common_params(PATH_ORDER_LIST, cred)
        params.update({
            "time_range_field": "create_time",
            "time_from": int(since.timestamp()),
            "time_to": int(datetime.now(UTC).timestamp()),
            "page_size": PAGE_SIZE,
            "response_optional_fields": "order_status",
        })
        if cursor:
            params["cursor"] = cursor

        payload = await self._get(PATH_ORDER_LIST, params)
        response = payload.get("response") or payload
        rows = response.get("order_list") or []
        sns = [str(r.get("order_sn")) for r in rows if r.get("order_sn")]

        records: list[OrderRecord] = []
        if sns:
            records = await self._order_details(cred, sns)

        next_cursor = response.get("next_cursor") if response.get("more") else None
        return Page(items=records, next_cursor=next_cursor or None)

    async def _order_details(self, cred: Cred, order_sns: list[str]) -> list[OrderRecord]:
        params = self._common_params(PATH_ORDER_DETAIL, cred)
        params.update({
            "order_sn_list": ",".join(order_sns),
            "response_optional_fields": "item_list,total_amount,payment_method,buyer_user_id",
        })
        payload = await self._get(PATH_ORDER_DETAIL, params)
        response = payload.get("response") or payload

        out: list[OrderRecord] = []
        for order in response.get("order_list") or []:
            raw_status = str(order.get("order_status") or "")
            status = ORDER_STATUS_MAP.get(raw_status, "unknown")
            if status == "unknown" and raw_status:
                log.warning("shopee.unmapped_order_status", status=raw_status)

            items = [
                OrderItemRecord(
                    external_product_id=str(it.get("item_id") or "") or None,
                    external_sku_id=str(it.get("model_id") or "") or None,
                    sku=it.get("item_sku") or it.get("model_sku"),
                    name=it.get("item_name"),
                    quantity=_as_int(it.get("model_quantity_purchased"), 1),
                    unit_price=_money(it.get("model_discounted_price")) or 0,
                    subtotal=(_money(it.get("model_discounted_price")) or 0)
                    * _as_int(it.get("model_quantity_purchased"), 1),
                )
                for it in order.get("item_list") or []
            ]

            out.append(OrderRecord(
                external_order_id=str(order.get("order_sn") or ""),
                status=status,
                raw_status=raw_status or None,
                payment_method=order.get("payment_method"),
                total_amount=_money(order.get("total_amount")) or 0,
                currency=order.get("currency") or "VND",
                external_buyer_id=str(order.get("buyer_user_id") or "") or None,
                placed_at=_ts(order.get("create_time")),
                platform_updated_at=_ts(order.get("update_time")),
                items=items,
                raw=order,
            ))
        return out

    # --- transport --------------------------------------------------------

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{self.host}{path}", params=params)
        return self._unwrap(r, path)

    async def _post(self, path: str, params: dict[str, Any],
                    body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{self.host}{path}", params=params, json=body)
        return self._unwrap(r, path)

    def _unwrap(self, r: httpx.Response, path: str) -> dict[str, Any]:
        """Shopee reports failure in the body, not the status code.

        A refusal arrives as HTTP 200 with a non-empty `error` field. Checking
        only `status_code` would treat every rejection as a success and store an
        empty result — the failure mode this method exists to prevent.
        """
        if r.status_code == 429:
            raise RateLimitedError("Shopee giới hạn tần suất gọi API", retry_after_s=60)

        try:
            payload = r.json()
        except ValueError as exc:
            raise AdapterError(
                f"Shopee trả về phản hồi không phải JSON (HTTP {r.status_code})"
            ) from exc

        if not isinstance(payload, dict):
            raise AdapterError(f"Shopee trả về cấu trúc lạ tại {path}")

        error = str(payload.get("error") or "")
        if error:
            message = str(payload.get("message") or "")
            log.warning("shopee.api_error", path=path, error=error, message=message)
            if error in DEAD_AUTH_ERRORS:
                raise AuthorisationError(
                    f"Shopee từ chối quyền truy cập ({error}). Cần kết nối lại shop."
                )
            raise AdapterError(f"Shopee lỗi {error}: {message or 'không rõ nguyên nhân'}")

        if r.status_code >= 400:
            raise AdapterError(f"Shopee trả về HTTP {r.status_code}: {r.text[:200]}")
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
    """Shopee returns VND already in đồng; keep it integral."""
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


adapter = ShopeeAdapter()
register(adapter)
