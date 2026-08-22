"""Lazada Open Platform adapter.

Authorisation is three-legged like the others, but four things about Lazada's
API differ from both Shopee and TikTok and shape this file:

*The signature is not wrapped in the secret and the digest is upper-cased.*
Lazada signs `api_path + sorted(key+value)` with HMAC-SHA256 and then upper-cases
the hex. Shopee concatenates different members; TikTok wraps the whole string in
the secret at both ends. Reusing either algorithm here produces a signature
error that names nothing, so `_sign` is written once against Lazada's spec.

*`access_token` is part of the signed material.* It travels as a query parameter
rather than a header, so unlike TikTok it must not be excluded when signing.

*The API host is per-country.* One app serves several markets and each has its
own host; the region recorded on the connection selects it. Calling the wrong
host with a valid token yields an unhelpful rejection.

*`code` comes back as a string.* `"0"` means success. Comparing it to the integer
0 silently treats every response as a failure, so it is normalised to a string
before the check.

One thing Lazada makes easier: the token response already carries the seller id
and country, so unlike TikTok no second call is needed to learn which shop was
authorised.

Endpoint paths follow the current REST API. Lazada deprecates endpoints over
time, so they are stated in one place to be checked against live documentation
at integration time.
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

log = get_logger("app.services.marketplace.lazada")

TIMEOUT = httpx.Timeout(30.0, connect=8.0)

AUTHORIZE_URL = "https://auth.lazada.com/oauth/authorize"
AUTH_HOST = "https://auth.lazada.com/rest"

# One app serves several markets, each behind its own host. The region stored on
# the connection picks the right one; guessing would send a valid token to the
# wrong country and get an unhelpful rejection back.
REGION_HOSTS: dict[str, str] = {
    "VN": "https://api.lazada.vn/rest",
    "SG": "https://api.lazada.sg/rest",
    "MY": "https://api.lazada.com.my/rest",
    "TH": "https://api.lazada.co.th/rest",
    "PH": "https://api.lazada.com.ph/rest",
    "ID": "https://api.lazada.co.id/rest",
}
DEFAULT_REGION = "VN"

PATH_TOKEN = "/auth/token/create"
PATH_REFRESH = "/auth/token/refresh"
PATH_SELLER = "/seller/get"
PATH_PRODUCTS = "/products/get"
PATH_ORDERS = "/orders/get"
PATH_ORDER_ITEMS = "/orders/items/get"

PAGE_SIZE = 50

# Lazada's order statuses -> our canonical vocabulary. Anything absent maps to
# "unknown" and is logged rather than guessed: a wrong guess silently miscounts
# revenue, which is worse than an obviously missing value.
ORDER_STATUS_MAP: dict[str, str] = {
    "unpaid": "unpaid",
    "pending": "awaiting_shipment",
    "packed": "awaiting_shipment",
    "topack": "awaiting_shipment",
    "toship": "awaiting_shipment",
    "ready_to_ship": "awaiting_shipment",
    "shipped": "shipped",
    "shipping": "shipped",
    "delivered": "delivered",
    "confirmed": "completed",
    "canceled": "cancelled",
    "cancelled": "cancelled",
    "failed": "cancelled",
    "returned": "returned",
    "lost": "cancelled",
    "damaged": "cancelled",
}

# Error codes that mean the authorisation is dead rather than the call having
# failed transiently. The seller has to reconnect; retrying will never help.
DEAD_AUTH_CODES = {
    "IllegalAccessToken",
    "InvalidAccessToken",
    "AccessTokenExpired",
    "MissingAccessToken",
    "InvalidToken",
}


class LazadaAdapter:
    platform = "lazada"
    display_name = "Lazada"
    console_url = "https://open.lazada.com"

    # --- configuration ----------------------------------------------------

    def configured(self) -> bool:
        return bool(settings.LAZADA_APP_KEY and settings.LAZADA_APP_SECRET)

    def missing_settings(self) -> list[str]:
        out = []
        if not settings.LAZADA_APP_KEY:
            out.append("LAZADA_APP_KEY")
        if not settings.LAZADA_APP_SECRET:
            out.append("LAZADA_APP_SECRET")
        return out

    def _require_config(self) -> tuple[str, str]:
        if not self.configured():
            raise AdapterError(
                f"Lazada chưa cấu hình: thiếu {', '.join(self.missing_settings())}. "
                f"Lấy khoá tại {self.console_url}."
            )
        return str(settings.LAZADA_APP_KEY), str(settings.LAZADA_APP_SECRET)

    def _host(self, region: str) -> str:
        key = (region or DEFAULT_REGION).upper()
        return REGION_HOSTS.get(key, REGION_HOSTS[DEFAULT_REGION])

    # --- signing ----------------------------------------------------------

    def _sign(self, path: str, params: dict[str, Any]) -> str:
        """HMAC-SHA256 over `path + sorted(key+value)`, upper-cased.

        Only `sign` is excluded. `access_token` is deliberately kept: Lazada
        sends it as a query parameter and includes it in the signed material,
        unlike TikTok where it is a header and must be left out.
        """
        _, app_secret = self._require_config()
        signable = {k: v for k, v in params.items() if k != "sign"}
        joined = "".join(f"{k}{signable[k]}" for k in sorted(signable))
        base = f"{path}{joined}"
        return hmac.new(
            app_secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256
        ).hexdigest().upper()

    def _common_params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        app_key, _ = self._require_config()
        params: dict[str, Any] = {
            "app_key": app_key,
            "sign_method": "sha256",
            # Lazada expects milliseconds, not seconds.
            "timestamp": int(time.time() * 1000),
        }
        if extra:
            params.update({k: v for k, v in extra.items() if v is not None})
        return params

    # --- authorisation ----------------------------------------------------

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        """Where to send the seller to approve access.

        Lazada does not echo an arbitrary `state`, so it is carried on the
        redirect URL instead — the callback still arrives with something only we
        could have issued, which is what the CSRF check needs.
        """
        app_key, _ = self._require_config()
        return f"{AUTHORIZE_URL}?" + urlencode({
            "response_type": "code",
            "force_auth": "true",
            "redirect_uri": f"{redirect_uri}?state={state}",
            "client_id": app_key,
        })

    async def exchange_code(self, code: str, params: dict[str, str]) -> TokenBundle:
        """Swap the callback's one-time code for tokens.

        A single round trip: unlike TikTok, Lazada's token response already says
        which seller and country the authorisation covers.
        """
        payload = await self._auth_call(PATH_TOKEN, {"code": code})
        return self._token_bundle(payload)

    async def refresh(self, refresh_token: str, cred: Cred) -> TokenBundle:
        payload = await self._auth_call(PATH_REFRESH, {"refresh_token": refresh_token})
        bundle = self._token_bundle(payload)
        # A refresh response may omit the seller block; keep what we already know
        # rather than losing the shop identity on a routine token rotation.
        return TokenBundle(
            access_token=bundle.access_token,
            refresh_token=bundle.refresh_token,
            expires_at=bundle.expires_at,
            refresh_expires_at=bundle.refresh_expires_at,
            extra={**cred.extra, **bundle.extra},
        )

    def _token_bundle(self, payload: dict[str, Any]) -> TokenBundle:
        access = payload.get("access_token")
        if not access:
            raise AdapterError(f"Lazada không trả về access_token: {payload}")

        country_info = payload.get("country_user_info") or []
        first = country_info[0] if country_info else {}
        region = str(
            first.get("country") or payload.get("country") or DEFAULT_REGION
        ).upper()

        extra = {
            k: v for k, v in (
                ("shop_id", str(first.get("seller_id") or "")),
                ("short_code", first.get("short_code")),
                ("account", payload.get("account")),
                ("region", region),
            ) if v
        }

        # Documented defaults keep the columns honest when the response omits a
        # lifetime; an empty column would read as "never expires".
        expires_in = _as_int(payload.get("expires_in"), 0) or 604_800
        refresh_in = _as_int(payload.get("refresh_expires_in"), 0) or 2_592_000
        return TokenBundle(
            access_token=access,
            refresh_token=payload.get("refresh_token"),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            refresh_expires_at=datetime.now(UTC) + timedelta(seconds=refresh_in),
            extra=extra,
        )

    # --- reading ----------------------------------------------------------

    async def fetch_shop(self, cred: Cred) -> ShopProfile:
        payload = await self._get(PATH_SELLER, cred, {})
        data = payload.get("data") or {}
        return ShopProfile(
            external_shop_id=cred.external_shop_id or str(data.get("seller_id") or ""),
            name=data.get("name") or data.get("name_company"),
            region=str(data.get("location") or cred.region or DEFAULT_REGION).upper(),
            status=data.get("status"),
            raw=data,
        )

    async def fetch_products(self, cred: Cred, cursor: str | None) -> Page:
        offset = _as_int(cursor, 0)
        payload = await self._get(PATH_PRODUCTS, cred, {
            "filter": "all", "limit": PAGE_SIZE, "offset": offset,
        })
        data = payload.get("data") or {}
        products = data.get("products") or []

        records: list[ProductRecord] = []
        for product in products:
            item_id = str(product.get("item_id") or "")
            attrs = product.get("attributes") or {}
            name = str(attrs.get("name") or "")
            brand = attrs.get("brand")
            images = product.get("images") or []

            skus = product.get("skus") or []
            if not skus:
                # Empty string, not NULL: NULL never equals NULL, which would
                # break the unique constraint this row is keyed on.
                records.append(ProductRecord(
                    external_product_id=item_id, external_sku_id="", name=name,
                    brand=brand, status=_product_status(product), raw=product,
                ))
                continue

            for sku in skus:
                sku_images = sku.get("Images") or images
                records.append(ProductRecord(
                    external_product_id=item_id,
                    external_sku_id=str(sku.get("SkuId") or ""),
                    sku=sku.get("SellerSku"),
                    name=name,
                    brand=brand,
                    category_path=str(product.get("primary_category") or "") or None,
                    # special_price is the live selling price when a promotion
                    # runs; price is the list price. Recording both keeps margin
                    # calculations from silently using the wrong one.
                    price=_money(sku.get("special_price") or sku.get("price")),
                    original_price=_money(sku.get("price")),
                    currency="VND",
                    status=_product_status(product, sku),
                    image_url=next((i for i in sku_images if i), None),
                    raw={**product, "_sku": sku},
                ))

        return Page(items=records, next_cursor=_next_offset(
            offset, len(products), _as_int(data.get("total_products"), -1)
        ))

    async def fetch_inventory(self, cred: Cred, cursor: str | None) -> Page:
        """Stock arrives inside the product payload, so this reuses that call.

        Lazada has no separate inventory endpoint: each SKU carries its
        quantity. Walking products and extracting them avoids inventing a second
        API surface that does not exist.
        """
        offset = _as_int(cursor, 0)
        payload = await self._get(PATH_PRODUCTS, cred, {
            "filter": "all", "limit": PAGE_SIZE, "offset": offset,
        })
        data = payload.get("data") or {}
        products = data.get("products") or []

        out: list[InventoryRecord] = []
        for product in products:
            item_id = str(product.get("item_id") or "")
            for sku in product.get("skus") or []:
                out.append(InventoryRecord(
                    external_product_id=item_id,
                    external_sku_id=str(sku.get("SkuId") or ""),
                    warehouse_id=str(sku.get("warehouse_code") or ""),
                    quantity_available=_as_int(sku.get("quantity"), 0),
                    quantity_reserved=_as_int(sku.get("occupied_quantity"), 0),
                ))

        return Page(items=out, next_cursor=_next_offset(
            offset, len(products), _as_int(data.get("total_products"), -1)
        ))

    async def fetch_orders(self, cred: Cred, since: datetime, cursor: str | None) -> Page:
        offset = _as_int(cursor, 0)
        payload = await self._get(PATH_ORDERS, cred, {
            "created_after": since.astimezone(UTC).isoformat(),
            "limit": PAGE_SIZE,
            "offset": offset,
            "sort_by": "created_at",
            "sort_direction": "DESC",
        })
        data = payload.get("data") or {}
        orders = data.get("orders") or []

        # Line items live behind a second endpoint; fetching them for the whole
        # page at once keeps this to two calls per page rather than one per order.
        items_by_order = await self._order_items(
            cred, [str(o.get("order_id")) for o in orders if o.get("order_id")]
        )

        records: list[OrderRecord] = []
        for order in orders:
            order_id = str(order.get("order_id") or "")
            raw_status = _first_status(order.get("statuses"))
            status = ORDER_STATUS_MAP.get(raw_status.lower(), "unknown")
            if status == "unknown" and raw_status:
                log.warning("lazada.unmapped_order_status", status=raw_status)

            records.append(OrderRecord(
                external_order_id=order_id,
                status=status,
                raw_status=raw_status or None,
                payment_method=order.get("payment_method"),
                total_amount=_money(order.get("price")) or 0,
                currency="VND",
                external_buyer_id=str(order.get("customer_id") or "") or None,
                placed_at=_parse_dt(order.get("created_at")),
                platform_updated_at=_parse_dt(order.get("updated_at")),
                items=items_by_order.get(order_id, []),
                raw=order,
            ))

        return Page(items=records, next_cursor=_next_offset(
            offset, len(orders), _as_int(data.get("countTotal"), -1)
        ))

    async def _order_items(
        self, cred: Cred, order_ids: list[str]
    ) -> dict[str, list[OrderItemRecord]]:
        if not order_ids:
            return {}

        ids = "[" + ",".join(order_ids) + "]"
        try:
            payload = await self._get(PATH_ORDER_ITEMS, cred, {"order_ids": ids})
        except AdapterError as exc:
            # Orders without their lines are still worth recording: totals and
            # dates drive most of the planning. Losing the whole page because the
            # detail call failed would be the worse outcome.
            log.warning("lazada.order_items_failed", error=str(exc))
            return {}

        out: dict[str, list[OrderItemRecord]] = {}
        for group in payload.get("data") or []:
            order_id = str(group.get("order_id") or "")
            lines: list[OrderItemRecord] = []
            for item in group.get("order_items") or []:
                price = _money(item.get("paid_price") or item.get("item_price")) or 0
                lines.append(OrderItemRecord(
                    external_product_id=str(item.get("product_id") or "") or None,
                    external_sku_id=str(item.get("sku_id") or "") or None,
                    sku=item.get("sku"),
                    name=item.get("name"),
                    # Lazada returns one row per unit sold, so each line is one.
                    quantity=1,
                    unit_price=price,
                    subtotal=price,
                ))
            out[order_id] = lines
        return out

    # --- transport --------------------------------------------------------

    async def _auth_call(self, path: str, extra: dict[str, Any]) -> dict[str, Any]:
        """Token endpoints live on the auth host and take no access token."""
        params = self._common_params(extra)
        params["sign"] = self._sign(path, params)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(f"{AUTH_HOST}{path}", data=params)
        return self._unwrap(r, path)

    async def _get(self, path: str, cred: Cred, query: dict[str, Any]) -> dict[str, Any]:
        params = self._common_params({**query, "access_token": cred.access_token})
        params["sign"] = self._sign(path, params)
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{self._host(cred.region)}{path}", params=params)
        return self._unwrap(r, path)

    def _unwrap(self, r: httpx.Response, path: str) -> dict[str, Any]:
        """Lazada reports failure in the body, not the status code.

        A refusal arrives as HTTP 200 with a non-"0" `code`. Checking only the
        status code would treat every rejection as success and store an empty
        result — the failure mode this method exists to prevent.
        """
        if r.status_code == 429:
            raise RateLimitedError("Lazada giới hạn tần suất gọi API", retry_after_s=60)

        try:
            payload = r.json()
        except ValueError as exc:
            raise AdapterError(
                f"Lazada trả về phản hồi không phải JSON (HTTP {r.status_code})"
            ) from exc

        if not isinstance(payload, dict):
            raise AdapterError(f"Lazada trả về cấu trúc lạ tại {path}")

        # `code` is a string here. Comparing it to the integer 0 would treat every
        # successful response as a failure.
        code = str(payload.get("code", "0"))
        if code not in ("0", ""):
            message = str(payload.get("message") or "")
            log.warning("lazada.api_error", path=path, code=code, message=message)
            if code in DEAD_AUTH_CODES:
                raise AuthorisationError(
                    f"Lazada từ chối quyền truy cập ({code}). Cần kết nối lại shop."
                )
            raise AdapterError(f"Lazada lỗi {code}: {message or 'không rõ nguyên nhân'}")

        if r.status_code >= 400:
            raise AdapterError(f"Lazada trả về HTTP {r.status_code}: {r.text[:200]}")
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
    """Lazada returns amounts as decimal strings; keep them integral in đồng."""
    if value is None or value == "":
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    """Lazada timestamps carry an offset; normalise to aware UTC.

    Naive datetimes compare wrongly against aware ones, and the database column
    is timezone-aware, so a naive value would be stored as if it were UTC.
    """
    if not value:
        return None
    raw = str(value).strip()
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        # Lazada also emits "YYYY-MM-DD HH:MM:SS +0700", which fromisoformat
        # rejects because the offset has no colon.
        for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _first_status(statuses: Any) -> str:
    """Lazada reports a list, because lines in one order can differ.

    The order-level status is the first entry; per-line status is not modelled,
    so taking the first is deliberate rather than accidental.
    """
    if isinstance(statuses, list) and statuses:
        return str(statuses[0] or "")
    if isinstance(statuses, str):
        return statuses
    return ""


def _product_status(product: dict[str, Any], sku: dict[str, Any] | None = None) -> str:
    raw = str((sku or {}).get("Status") or product.get("status") or "").lower()
    return "active" if raw in ("active", "") else "inactive"


def _next_offset(offset: int, returned: int, total: int) -> str | None:
    """Offset paging: stop on a short page, or once the total is reached.

    An empty page alone is not a reliable end signal — a filter can empty one
    page while more data follows — so both conditions are checked.
    """
    if returned == 0:
        return None
    seen = offset + returned
    if returned < PAGE_SIZE:
        return None
    if 0 <= total <= seen:
        return None
    return str(seen)


adapter = LazadaAdapter()
register(adapter)
