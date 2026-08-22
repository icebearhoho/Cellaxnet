"""Marketplace integration layer.

Importing this package registers every adapter, so callers can resolve one by
platform name without knowing which module defines it.

Shopee, TikTok Shop and Lazada are all in. Each was added the same way: one
module here satisfying `MarketplaceAdapter` and calling `register()`, with no
change to the connect flow, the sync loop, the storage layer or the UI. A fourth
marketplace is the same shape of work.
"""

from app.services.marketplace import (  # noqa: F401 — importing registers each adapter
    crypto,
    lazada,
    shopee,
    tiktok,
)
from app.services.marketplace.base import (
    AdapterError,
    AuthorisationError,
    Cred,
    MarketplaceAdapter,
    RateLimitedError,
    TokenBundle,
    all_adapters,
    get_adapter,
)

__all__ = [
    "AdapterError",
    "AuthorisationError",
    "Cred",
    "MarketplaceAdapter",
    "RateLimitedError",
    "TokenBundle",
    "all_adapters",
    "crypto",
    "get_adapter",
]
