"""KiotViet connector — one link that carries Shopee, Lazada and TikTok Shop.

Why through KiotViet instead of three direct integrations:

Reading a shop's orders on Shopee/Lazada/TikTok requires an app that platform
has already approved, and each approval gates on business or identity documents
plus a review queue. KiotViet is a Vietnamese retail/multi-channel platform that
went through those approvals years ago, syncs orders from all three, and exposes
a public API on top. The seller links their marketplaces to KiotViet once — the
normal thing they do anyway — and this app reads from KiotViet.

Why KiotViet rather than another aggregator: it authenticates with an OAuth2
*client credentials* grant, which is a plain server-to-server call. There is no
authorisation redirect, so no public HTTPS callback, no tunnel for local
development, and no developer-portal app review. The seller copies two strings
out of their own store settings and the link works.

Verified against the live service before this was written:
  POST id.kiotviet.vn/connect/token  -> {"error":"invalid_client"} for bad keys
      (not "unsupported_grant_type", so the grant type is accepted)
  GET  public.kiotapi.com/orders      -> 401 with www-authenticate: jwt
  GET  public.kiotapi.com/salechannel -> 401 with www-authenticate: jwt

Nothing here invents data. With no credentials configured the connector reports
`configured=False` and the UI offers no Connect button.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("app.services.channel_connectors")

TIMEOUT = httpx.Timeout(30.0, connect=8.0)

TOKEN_URL = "https://id.kiotviet.vn/connect/token"
API_HOST = "https://public.kiotapi.com"

# The channel ids the restock planner plans for. Everything the seller owns
# outright — their own storefront, walk-in sales, Facebook — rolls up under
# "own": for stock allocation those share one storefront and one fee structure.
OWN_CHANNEL = "own"
MARKETPLACE_LABELS: dict[str, str] = {
    "shopee": "Shopee",
    "lazada": "Lazada",
    "tiktok": "TikTok Shop",
    OWN_CHANNEL: "Cửa hàng riêng",
}

# KiotViet assigns sale-channel ids per retailer, so they cannot be hardcoded.
# The connector reads /salechannel and matches on name instead — these are the
# substrings that identify each marketplace.
NAME_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("shopee", ("shopee",)),
    ("lazada", ("lazada",)),
    ("tiktok", ("tiktok", "tik tok")),
]


class ConnectorError(RuntimeError):
    """KiotViet refused the request, or the app is not configured."""


@dataclass(frozen=True)
class TokenResult:
    access_token: str
    retailer: str
    expires_at: int | None


@dataclass(frozen=True)
class ChannelOrders:
    channel: str
    orders: int
    revenue_vnd: float


@dataclass(frozen=True)
class OrderSummary:
    days: int
    total_orders: int
    per_channel: list[ChannelOrders]
    first_order_at: str | None
    last_order_at: str | None
    pages_read: int
    # Which sale channels the retailer actually has, so the UI can say what was
    # found rather than implying a marketplace is missing when it simply is not
    # linked on the KiotViet side.
    channels_seen: list[str] = field(default_factory=list)


class KiotVietConnector:
    platform = "kiotviet"
    display_name = "KiotViet"
    docs_url = "https://www.kiotviet.vn/huong-dan-su-dung-kiotviet/thiet-lap/quan-ly-cau-hinh/"
    portal_url = "https://www.kiotviet.vn"
    # Where the seller finds the two strings this connector needs.
    credentials_hint = "Thiết lập cửa hàng → Thiết lập kết nối API"

    # --- configuration ----------------------------------------------------

    def configured(self) -> bool:
        return bool(
            settings.KIOTVIET_CLIENT_ID
            and settings.KIOTVIET_CLIENT_SECRET
            and settings.KIOTVIET_RETAILER
        )

    def missing_settings(self) -> list[str]:
        out = []
        if not settings.KIOTVIET_CLIENT_ID:
            out.append("KIOTVIET_CLIENT_ID")
        if not settings.KIOTVIET_CLIENT_SECRET:
            out.append("KIOTVIET_CLIENT_SECRET")
        if not settings.KIOTVIET_RETAILER:
            out.append("KIOTVIET_RETAILER")
        return out

    # --- step 1: get a token ----------------------------------------------

    async def authenticate(self) -> TokenResult:
        """Exchange the store's API keys for a bearer token.

        A plain server-to-server call: no seller redirect, no callback URL.
        The token lasts about an hour, so it is fetched per sync rather than
        stored — one extra request beats reasoning about a stale token.
        """
        if not self.configured():
            raise ConnectorError(
                f"KiotViet chưa cấu hình: thiếu {', '.join(self.missing_settings())}"
            )

        form = {
            "scopes": "PublicApi",
            "grant_type": "client_credentials",
            "client_id": settings.KIOTVIET_CLIENT_ID,
            "client_secret": settings.KIOTVIET_CLIENT_SECRET,
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                TOKEN_URL, data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if r.status_code >= 400:
            detail = _safe_json(r)
            err = detail.get("error") if isinstance(detail, dict) else None
            if err == "invalid_client":
                raise ConnectorError(
                    "KiotViet từ chối: sai Client ID hoặc Client Secret. "
                    "Kiểm tra lại ở Thiết lập cửa hàng → Thiết lập kết nối API."
                )
            raise ConnectorError(f"KiotViet trả về HTTP {r.status_code}: {r.text[:200]}")

        data = _safe_json(r)
        token = data.get("access_token") if isinstance(data, dict) else None
        if not token:
            raise ConnectorError("KiotViet không trả về access_token")

        expires_in = data.get("expires_in")
        return TokenResult(
            access_token=token,
            retailer=settings.KIOTVIET_RETAILER or "",
            expires_at=int(time.time()) + int(expires_in) if expires_in else None,
        )

    def _headers(self, token: str) -> dict[str, str]:
        # Retailer identifies which store the token acts on; KiotViet rejects
        # API calls without it even when the token is valid.
        return {
            "Authorization": f"Bearer {token}",
            "Retailer": settings.KIOTVIET_RETAILER or "",
        }

    # --- step 2: learn this retailer's channel ids ------------------------

    async def channel_map(self, token: str) -> dict[int, str]:
        """saleChannelId -> our channel id, resolved by name.

        Ids are per-retailer, so matching on the name KiotViet stores is the
        only stable way. Anything that is not one of the three marketplaces is
        left out and falls through to "own" at counting time.
        """
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.get(f"{API_HOST}/salechannel", headers=self._headers(token))
        if r.status_code == 401:
            raise ConnectorError("KiotViet từ chối token — kết nối lại")
        if r.status_code >= 400:
            # Not fatal: without the map every order counts as "own", which is
            # wrong but not silently wrong — the UI reports zero marketplaces.
            log.warning("kiotviet.salechannel_failed", status=r.status_code)
            return {}

        payload = _safe_json(r)
        rows = payload.get("data") if isinstance(payload, dict) else payload
        out: dict[int, str] = {}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            cid = _as_int(row.get("id"))
            name = str(row.get("name") or "").lower()
            if cid < 0 or not name:
                continue
            for channel, patterns in NAME_PATTERNS:
                if any(p in name for p in patterns):
                    out[cid] = channel
                    break
        log.info("kiotviet.channel_map", resolved=len(out))
        return out

    # --- step 3: read the orders ------------------------------------------

    async def _walk(self, client: httpx.AsyncClient, path: str, token: str,
                    since: str) -> tuple[list[dict], int]:
        """Page through an endpoint and return every row, plus the page count."""
        out: list[dict] = []
        pages = 0
        current = 0
        page_size = 100

        while pages < 50:  # 50 x 100 rows is plenty for planning
            params: dict[str, str | int] = {
                "fromPurchaseDate": since,
                "pageSize": page_size,
                "currentItem": current,
                "orderBy": "purchaseDate",
                "orderDirection": "Desc",
            }
            r = await client.get(
                f"{API_HOST}{path}", params=params, headers=self._headers(token)
            )
            if r.status_code == 401:
                raise ConnectorError("KiotViet từ chối token — kết nối lại")
            if r.status_code >= 400:
                raise ConnectorError(
                    f"KiotViet trả về HTTP {r.status_code}: {r.text[:200]}")

            payload = _safe_json(r)
            rows = payload.get("data") if isinstance(payload, dict) else None
            if not rows:
                break

            out.extend(row for row in rows if isinstance(row, dict))
            pages += 1
            current += len(rows)
            total_available = _as_int(payload.get("total")) if isinstance(payload, dict) else -1
            if len(rows) < page_size or (0 <= total_available <= current):
                break

        return out, pages

    async def fetch_orders(self, token: str, days: int) -> OrderSummary:
        """Walk the retailer's sales and tally each marketplace separately.

        Reads both /invoices and /orders, because KiotViet splits a sale across
        the two and which one holds it depends on how it arrived:

          * "invoice" = a completed sale. A shop ringing up a walk-in customer
            goes straight here with no order in between. Verified on a live
            store: /orders returned 0 while /invoices returned 46, matching the
            revenue on the dashboard — reading /orders alone would have shown
            an empty shop.
          * "order" = a sale placed ahead of fulfilment. Marketplace orders
            synced in from Shopee/Lazada/TikTok land here first and only become
            an invoice once fulfilled, so reading /invoices alone would miss
            everything still in transit — exactly the demand signal restock
            planning cares most about.

        Rows are deduplicated on the order code an invoice carries once it is
        raised from an order, so a sale counted as an invoice is not counted a
        second time as its originating order.
        """
        mapping = await self.channel_map(token)

        import datetime as dt

        since = (dt.datetime.now(dt.UTC) - dt.timedelta(days=days)).strftime("%Y-%m-%d")
        counts: dict[str, int] = {}
        revenue: dict[str, float] = {}
        seen_channel_ids: set[int] = set()
        first_ts: str | None = None
        last_ts: str | None = None
        total = 0

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            invoices, inv_pages = await self._walk(client, "/invoices", token, since)
            orders, ord_pages = await self._walk(client, "/orders", token, since)

        # An invoice raised from an order carries that order's code; drop the
        # order so the same sale is not counted twice.
        invoiced = {str(row.get("orderCode")).strip()
                    for row in invoices if str(row.get("orderCode") or "").strip()}
        pending = [row for row in orders
                   if str(row.get("code") or "").strip() not in invoiced]

        for row in invoices + pending:
            total += 1
            cid = _as_int(row.get("saleChannelId"))
            if cid >= 0:
                seen_channel_ids.add(cid)
            channel = mapping.get(cid, OWN_CHANNEL)
            counts[channel] = counts.get(channel, 0) + 1
            revenue[channel] = revenue.get(channel, 0.0) + _as_float(
                row.get("total") or row.get("totalPayment") or 0
            )
            stamp = row.get("purchaseDate") or row.get("createdDate")
            if stamp:
                s = str(stamp)
                first_ts = s if first_ts is None else min(first_ts, s)
                last_ts = s if last_ts is None else max(last_ts, s)

        pages = inv_pages + ord_pages
        per_channel = [
            ChannelOrders(channel=c, orders=n, revenue_vnd=round(revenue.get(c, 0.0), 2))
            for c, n in sorted(counts.items(), key=lambda kv: -kv[1])
        ]
        log.info("kiotviet.orders_fetched", total=total, pages=pages,
                 invoices=len(invoices), pending_orders=len(pending),
                 channels={c.channel: c.orders for c in per_channel})
        return OrderSummary(
            days=days, total_orders=total, per_channel=per_channel,
            first_order_at=first_ts, last_order_at=last_ts, pages_read=pages,
            channels_seen=sorted({mapping[c] for c in seen_channel_ids if c in mapping}),
        )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def _safe_json(r: httpx.Response) -> Any:
    try:
        return r.json()
    except Exception:  # noqa: BLE001 — caller decides what a non-JSON body means
        return {}


def _as_int(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return -1


def _as_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


connector = KiotVietConnector()
