"""The contract every marketplace adapter implements.

This file is the reason adding Lazada or TikTok Shop later is a new file rather
than an edit spread across the codebase. Everything above the adapters — the
connect flow, the sync loop, the storage layer, the UI — is written against
these types and never against a marketplace.

The rule that keeps it that way: no string literal "shopee" / "lazada" /
"tiktok" may appear outside an adapter and the platform registry. Where the
caller needs to branch on marketplace, it asks the adapter, it does not
`if platform == ...`.

What each adapter is responsible for hiding:

  signing        Shopee HMACs a concatenation, Lazada HMACs sorted key+value
                 pairs and upper-cases the result, TikTok signs sorted query
                 params. None of that is visible above.
  pagination     Shopee and Lazada page by offset, TikTok by opaque cursor.
                 All three surface here as `Page(items, next_cursor)`.
  identifiers    item_id/model_id vs item_id/sku_id vs product_id/sku_id, all
                 flattened to external_product_id + external_sku_id.
  status names   translated to the canonical vocabulary in models.marketplace.
  extra state    TikTok additionally requires a shop_cipher on every call after
                 authorisation, which is why TokenBundle carries a free-form
                 `extra` rather than three fixed fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


class AdapterError(RuntimeError):
    """A marketplace refused, or the adapter is not configured."""


class AuthorisationError(AdapterError):
    """Credentials are no longer usable; the seller must authorise again.

    Split from AdapterError because the caller reacts differently: a transient
    refusal is worth retrying, a dead authorisation is not — it needs a human.
    """


class RateLimitedError(AdapterError):
    """The marketplace asked us to slow down."""

    def __init__(self, message: str, retry_after_s: int = 60) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


# --------------------------------------------------------------------------- #
# Value objects crossing the adapter boundary
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class TokenBundle:
    """What an authorisation or refresh yields."""

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    refresh_expires_at: datetime | None = None
    scope: str | None = None
    # Marketplace-specific material needed on later calls (TikTok shop_cipher,
    # Lazada account id). Stored encrypted alongside the tokens.
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Cred:
    """Everything an adapter needs to make one authenticated call."""

    external_shop_id: str
    access_token: str
    region: str = "VN"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ShopProfile:
    external_shop_id: str
    name: str | None = None
    region: str = "VN"
    status: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProductRecord:
    external_product_id: str
    external_sku_id: str
    name: str
    sku: str | None = None
    brand: str | None = None
    category_path: str | None = None
    price: int | None = None          # smallest currency unit
    original_price: int | None = None
    currency: str = "VND"
    status: str = "active"
    image_url: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InventoryRecord:
    external_product_id: str
    external_sku_id: str
    warehouse_id: str = ""
    quantity_available: int = 0
    quantity_reserved: int = 0


@dataclass(frozen=True)
class OrderItemRecord:
    external_product_id: str | None = None
    external_sku_id: str | None = None
    sku: str | None = None
    name: str | None = None
    quantity: int = 1
    unit_price: int = 0
    subtotal: int = 0


@dataclass(frozen=True)
class OrderRecord:
    external_order_id: str
    status: str                        # canonical, see ORDER_STATUSES
    raw_status: str | None = None      # verbatim, for diagnosing bad mappings
    payment_method: str | None = None
    total_amount: int = 0
    currency: str = "VND"
    external_buyer_id: str | None = None   # hashed before storage, never kept
    placed_at: datetime | None = None
    platform_updated_at: datetime | None = None
    items: list[OrderItemRecord] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Page:
    """One page of results plus how to ask for the next one.

    `next_cursor is None` is the only end-of-data signal callers may use. An
    empty `items` list is not sufficient: some marketplaces return an empty
    page with more to follow when a filter excludes everything on that page.
    """

    items: list[Any]
    next_cursor: str | None = None


# --------------------------------------------------------------------------- #
# The contract
# --------------------------------------------------------------------------- #

@runtime_checkable
class MarketplaceAdapter(Protocol):
    platform: str
    display_name: str
    # Where a seller obtains app credentials, shown in the UI when unconfigured.
    console_url: str

    def configured(self) -> bool: ...
    def missing_settings(self) -> list[str]: ...

    # --- authorisation ---
    def authorize_url(self, state: str, redirect_uri: str) -> str: ...
    async def exchange_code(self, code: str, params: dict[str, str]) -> TokenBundle: ...
    async def refresh(self, refresh_token: str, cred: Cred) -> TokenBundle: ...

    # --- reading ---
    async def fetch_shop(self, cred: Cred) -> ShopProfile: ...
    async def fetch_products(self, cred: Cred, cursor: str | None) -> Page: ...
    async def fetch_orders(
        self, cred: Cred, since: datetime, cursor: str | None
    ) -> Page: ...
    async def fetch_inventory(self, cred: Cred, cursor: str | None) -> Page: ...


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

_ADAPTERS: dict[str, MarketplaceAdapter] = {}


def register(adapter: MarketplaceAdapter) -> None:
    _ADAPTERS[adapter.platform] = adapter


def get_adapter(platform: str) -> MarketplaceAdapter:
    adapter = _ADAPTERS.get(platform)
    if adapter is None:
        raise AdapterError(f"Chưa hỗ trợ sàn '{platform}'")
    return adapter


def all_adapters() -> list[MarketplaceAdapter]:
    return list(_ADAPTERS.values())
