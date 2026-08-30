"""KiotViet connection status — what the Connect screen renders.

Tokens never appear here. A caller learns that a link exists, when it expires,
and how many orders each marketplace contributed — never the secret itself.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

LinkStatus = Literal["not_configured", "disconnected", "pending", "connected", "error"]


class MarketplaceRow(BaseModel):
    """Orders one marketplace contributed over the sync window.

    `channel` matches the ids the restock planner allocates stock for, so the
    two views line up without translation.
    """

    channel: str
    name: str
    orders: int
    revenue_vnd: int = 0
    daily_orders: float = 0.0


class ChannelLinkStatus(BaseModel):
    platform: str = "kiotviet"
    name: str = "KiotViet"
    status: LinkStatus
    # False when the app credentials are absent, which is why the UI must not
    # offer a Connect button: the handshake could not complete.
    configured: bool
    missing_settings: list[str] = Field(default_factory=list)

    retailer: str | None = None
    connected_at: datetime | None = None
    last_synced_at: datetime | None = None
    last_error: str | None = None

    sync_days: int | None = None
    total_orders: int | None = None
    marketplaces: list[MarketplaceRow] = Field(default_factory=list)

    docs_url: str
    portal_url: str
    # Where in the seller's own store settings the API keys live.
    credentials_hint: str = ""
    # Which marketplaces a single link can carry — shown before any sync so the
    # seller knows what to expect.
    supported: list[str] = Field(default_factory=list)
