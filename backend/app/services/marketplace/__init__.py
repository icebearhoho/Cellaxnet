"""Marketplace integration layer.

Importing this package registers every adapter, so callers can resolve one by
platform name without knowing which module defines it.

Lazada is not implemented yet; adding it means writing a module here that
satisfies `MarketplaceAdapter` and calling `register()`, with no change to the
connect flow, the sync loop, the storage layer or the UI. TikTok Shop was added
exactly that way and touched nothing above this package.
"""

from app.services.marketplace import (  # noqa: F401 — importing registers each adapter
    crypto,
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
