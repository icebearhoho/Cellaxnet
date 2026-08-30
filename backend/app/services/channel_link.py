"""Connection bookkeeping for the seller's KiotViet store.

Much smaller than an OAuth link: KiotViet authenticates server-to-server with
the store's API keys, so there is no seller redirect, no `state` to guard, and
no callback to receive. "Connecting" means proving the keys work and recording
that they do; the token itself is short-lived and fetched per sync rather than
stored, which removes a whole class of stale-credential bugs.

One connection carries several marketplaces, so a sync stores the per-channel
order counts, not a single total: the restock planner allocates stock per
channel and needs to tell a Shopee order from a TikTok one.

The table is created on first use rather than assuming `alembic upgrade head`
has run — this project's containers do not run migrations at boot. Migration
0004 remains the source of truth for a real deployment. Note that creating on
first use does NOT add columns to an existing table, so a schema change still
needs the migration (or a drop).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import engine
from app.models.channel_link import ChannelConnection
from app.schemas.channel_link import ChannelLinkStatus, MarketplaceRow
from app.services.channel_connectors import (
    MARKETPLACE_LABELS,
    ConnectorError,
    connector,
)

log = get_logger("app.services.channel_link")

PLATFORM = "kiotviet"
_table_ready = False


async def _ensure_table() -> None:
    global _table_ready
    if _table_ready:
        return
    # `__table__` is typed as the broader FromClause on the declarative base;
    # it is always a Table for a mapped class, and only Table carries .create().
    table = cast(Table, ChannelConnection.__table__)
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: table.create(bind=c, checkfirst=True))
    _table_ready = True


async def _row(db: AsyncSession) -> ChannelConnection | None:
    """The current link.

    A failed attempt is written before the retailer is known, i.e. with an
    empty shop_id, so it can sit alongside a later successful link. Prefer a
    connected row over reporting a stale error atop a live connection.
    """
    rows = (await db.execute(
        select(ChannelConnection)
        .where(ChannelConnection.platform == PLATFORM)
        .order_by(ChannelConnection.id.desc())
    )).scalars().all()
    if not rows:
        return None
    for row in rows:
        if row.status == "connected":
            return row
    return rows[0]


async def get_status(db: AsyncSession) -> ChannelLinkStatus:
    await _ensure_table()
    row = await _row(db)
    configured = connector.configured()

    if not configured:
        status = "not_configured"
    elif row is None:
        status = "disconnected"
    else:
        status = row.status

    marketplaces: list[MarketplaceRow] = []
    if row and row.channel_orders_json:
        try:
            counts = json.loads(row.channel_orders_json)
        except (TypeError, ValueError):
            counts = {}
        days = row.synced_days or settings.CHANNEL_SYNC_DAYS
        for channel, payload in counts.items():
            orders = int(payload.get("orders", 0)) if isinstance(payload, dict) else int(payload)
            marketplaces.append(MarketplaceRow(
                channel=channel,
                name=MARKETPLACE_LABELS.get(channel, channel),
                orders=orders,
                revenue_vnd=int(payload.get("revenue_vnd", 0))
                if isinstance(payload, dict) else 0,
                daily_orders=round(orders / days, 2) if days else 0.0,
            ))
        marketplaces.sort(key=lambda m: -m.orders)

    return ChannelLinkStatus(
        platform=PLATFORM,
        name=connector.display_name,
        status=status,  # type: ignore[arg-type]
        configured=configured,
        missing_settings=connector.missing_settings(),
        retailer=row.shop_id if row and row.shop_id else settings.KIOTVIET_RETAILER,
        connected_at=row.updated_at if row and row.status == "connected" else None,
        last_synced_at=row.last_synced_at if row else None,
        last_error=row.last_error if row else None,
        sync_days=row.synced_days if row else None,
        total_orders=row.synced_orders if row else None,
        marketplaces=marketplaces,
        docs_url=connector.docs_url,
        portal_url=connector.portal_url,
        credentials_hint=connector.credentials_hint,
        supported=[MARKETPLACE_LABELS[c] for c in ("shopee", "lazada", "tiktok", "own")],
    )


async def _upsert(db: AsyncSession) -> ChannelConnection:
    """Collapse to a single row so a stale error cannot outlive its link."""
    existing = (await db.execute(
        select(ChannelConnection).where(ChannelConnection.platform == PLATFORM)
    )).scalars().all()
    row = None
    for candidate in existing:
        if row is None:
            row = candidate
        else:
            await db.delete(candidate)
    if row is None:
        row = ChannelConnection(platform=PLATFORM, shop_id="")
        db.add(row)
    return row


async def connect(db: AsyncSession) -> dict:
    """Prove the store's API keys work, and record the link.

    Authenticating here rather than at sync time means a wrong key is reported
    the moment the seller presses Connect, instead of surfacing later as a
    failed sync that looks like "the shop has no orders".
    """
    await _ensure_table()
    token = await connector.authenticate()  # raises ConnectorError on bad keys

    row = await _upsert(db)
    row.shop_id = token.retailer
    row.status = "connected"
    row.last_error = None
    # The token is deliberately not stored: it lives about an hour and every
    # sync fetches a fresh one, so there is nothing here to go stale.
    row.access_token = None
    await db.commit()
    log.info("channel_link.connected", retailer=token.retailer)
    return {"retailer": token.retailer}


async def mark_error(db: AsyncSession, message: str) -> None:
    await _ensure_table()
    row = await _upsert(db)
    row.status = "error"
    row.last_error = message[:500]
    await db.commit()
    log.warning("channel_link.failed", error=message[:200])


async def disconnect(db: AsyncSession) -> bool:
    """Forget the link and every figure synced through it."""
    await _ensure_table()
    rows = (await db.execute(
        select(ChannelConnection).where(ChannelConnection.platform == PLATFORM)
    )).scalars().all()
    if not rows:
        return False
    for row in rows:
        await db.delete(row)
    await db.commit()
    log.info("channel_link.disconnected")
    return True


async def sync_orders(db: AsyncSession) -> dict:
    """Pull recent orders and store the per-marketplace counts.

    A failed sync keeps the previous figures. Zeroing them on an API error
    would tell the planner these channels sell nothing — a very different, and
    much more expensive, claim than "KiotViet was unreachable just now".
    """
    await _ensure_table()
    row = await _row(db)
    if row is None or row.status != "connected":
        raise ConnectorError("Chưa kết nối KiotViet")

    token = await connector.authenticate()
    days = settings.CHANNEL_SYNC_DAYS
    summary = await connector.fetch_orders(token.access_token, days)

    counts = {
        c.channel: {"orders": c.orders, "revenue_vnd": int(c.revenue_vnd)}
        for c in summary.per_channel
    }
    row.channel_orders_json = json.dumps(counts, ensure_ascii=False)
    row.synced_orders = summary.total_orders
    row.synced_days = summary.days
    row.last_synced_at = datetime.now(UTC)
    row.last_error = None
    await db.commit()

    return {
        "days": summary.days,
        "total_orders": summary.total_orders,
        "pages_read": summary.pages_read,
        "first_order_at": summary.first_order_at,
        "last_order_at": summary.last_order_at,
        "marketplaces": [
            {
                "channel": c.channel,
                "name": MARKETPLACE_LABELS.get(c.channel, c.channel),
                "orders": c.orders,
                "revenue_vnd": int(c.revenue_vnd),
                "daily_orders": round(c.orders / summary.days, 2) if summary.days else 0.0,
            }
            for c in summary.per_channel
        ],
    }


async def synced_rates(db: AsyncSession) -> dict[str, float]:
    """channel -> orders per day, for the restock planner.

    This is what lets the planner stop asking the seller to describe each
    channel by hand.
    """
    await _ensure_table()
    row = await _row(db)
    if row is None or row.status != "connected" or not row.channel_orders_json:
        return {}
    if not row.synced_days:
        return {}
    try:
        counts = json.loads(row.channel_orders_json)
    except (TypeError, ValueError):
        return {}
    out: dict[str, float] = {}
    for channel, payload in counts.items():
        orders = payload.get("orders", 0) if isinstance(payload, dict) else payload
        if orders:
            out[channel] = float(orders) / row.synced_days
    return out
