"""Marketplace integration layer.

Importing this package registers every adapter, so callers can resolve one by
platform name without knowing which module defines it.

Lazada and TikTok Shop are not implemented yet; adding one means writing a
module here that satisfies `MarketplaceAdapter` and calling `register()`, with
no change to the connect flow, the sync loop, the storage layer or the UI.
"""

from app.services.marketplace import (  # noqa: F401 — shopee import registers the adapter
    crypto,
    shopee,
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
