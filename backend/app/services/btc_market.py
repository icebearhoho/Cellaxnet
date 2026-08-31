"""Price references read from the organisers' observed Shopee dataset.

This is *external market data*, not Cellaxnet's own catalogue, so the module
keeps three rules:

* **Read-only, own engine.** A separate pool on the BTC database. Nothing here
  writes, and a stall there must not consume the app's connections.
* **Optional.** With ``BTC_DATABASE_URL`` unset every function returns ``None``
  and callers keep their previous behaviour. The feature degrades, never fails.
* **Honest about coverage.** The accessible dataset is a handful of shops
  observed over ~3 weeks of July 2026, so a percentile taken from it is a
  reference from observed listings — not the Shopee-wide market price. Callers
  render it with that wording, and :class:`PriceReference` carries the shop
  count so the UI can say so.

Only the app categories that the dataset can actually support are mapped.
``_CATEGORY_GROUPS`` holds shop-defined collection names, and a category with
no entry (fashion, accessories — absent from the accessible rows) resolves to
``None`` so the caller falls back rather than borrowing an unrelated median.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("app.services.btc_market")

#: The two observed origins. Kept narrower than `PriceSource` (which also has
#: "demo") because this module never produces a synthetic figure.
ObservedSource = Literal["btc_live", "btc_snapshot"]

#: Shop collections usable as a price reference, per market. Keyed by the
#: market the app serves, because Shopee runs a separate marketplace per
#: country at its own price level: an Indonesian median is not a cheaper
#: version of the Vietnamese one, it is a different market's answer.
#:
#: The accessible Vietnamese rows are confectionery, coffee and dairy — no
#: cosmetics, no clothing, no accessories — so the three app categories have
#: no Vietnamese reference and are deliberately absent. Cosmetics data does
#: exist here, but only under country_code "id", and pricing a Vietnamese
#: seller off it would advise cutting prices 24-43% toward a market they do
#: not sell in.
#:
#: `categories` also mixes real product groupings ("SKINCARE") with
#: merchandising tabs ("Giảm giá", "BEST SELLING"); only the former belong
#: here, since a "discounted items" median prices a promotion, not a product.
_CATEGORY_GROUPS: dict[str, dict[str, tuple[str, ...]]] = {
    "vn": {
        # Nothing yet: the Vietnamese shops in reach sell none of the three
        # categories the app prices. Add entries here only alongside app
        # categories that match what those shops actually list.
    },
    "id": {
        "Mỹ phẩm": (
            "SKINCARE",
            "SHOP BY NEEDS",
            "MAKE UP",
            "Facial Cleanser",
            "Moisturizer",
            "Skin Care",
            "LET IT GLOW",
            "LVJ BODY CARE SERIES",
            "LVJ HAIR CARE SERIES",
            "Anti-jerawat",
            "Mencerahkan kulit",
            "🌸Skincare Bundle",
        ),
    },
}


def _groups_for(category: str) -> tuple[str, ...]:
    """Collections to measure for `category` in the configured market."""
    return _CATEGORY_GROUPS.get(settings.BTC_MARKET, {}).get(category, ())


_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "btc_price_reference.json"

# One product may sit in several collections, so the inner DISTINCT collapses
# it to a single row before percentiles run — otherwise a heavily-tagged
# product would be counted several times and drag the median toward itself.
_PERCENTILE_SQL = """
SELECT
    COUNT(*)                                              AS sample_size,
    COUNT(DISTINCT shop_id)                               AS shop_count,
    -- The dataset spans more than one Shopee market, and a median that mixes
    -- them is a reference to nowhere. Carried through so the UI can name the
    -- market instead of implying the seller's own.
    ARRAY_AGG(DISTINCT country_code)                      AS country_codes,
    MIN(price)                                            AS min_price,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY price)   AS p25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY price)   AS median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY price)   AS p75,
    MAX(price)                                            AS max_price,
    -- Sorted prices, so a seller's own price can be placed in the
    -- distribution exactly rather than interpolated between quartiles.
    ARRAY_AGG(price ORDER BY price)                       AS prices
FROM (
    SELECT DISTINCT p.country_code, p.shop_id, p.item_id, p.price
    FROM {schema}.products p
    JOIN {schema}.product_categories pc
          ON  pc.country_code = p.country_code
          AND pc.shop_id      = p.shop_id
          AND pc.item_id      = p.item_id
    JOIN {schema}.categories c
          ON  c.country_code = pc.country_code
          AND c.shop_id      = pc.shop_id
          AND c.category_id  = pc.category_id
    WHERE p.country_code = :market
      AND p.price BETWEEN :price_min AND :price_max
      AND c.display_name = ANY(:groups)
) t
"""


@dataclass(frozen=True)
class PriceReference:
    """Observed price percentiles for one app category."""

    category: str
    sample_size: int
    shop_count: int
    min_price: int
    p25: int
    median: int
    p75: int
    max_price: int
    source: ObservedSource
    #: Shopee markets the sample covers ("id", "vn", …). More than one entry
    #: means the percentiles blend markets and should be read with care.
    countries: tuple[str, ...] = ()
    #: Every observed price, ascending. Empty when a snapshot predates this
    #: field — `percentile_of` then declines to answer rather than guessing.
    prices: tuple[int, ...] = ()

    def percentile_of(self, price: int) -> int | None:
        """Share of observed products priced at or below `price`, 0-100."""
        if not self.prices:
            return None
        at_or_below = sum(1 for p in self.prices if p <= price)
        return round(at_or_below / len(self.prices) * 100)

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "sample_size": self.sample_size,
            "shop_count": self.shop_count,
            "min_price": self.min_price,
            "p25": self.p25,
            "median": self.median,
            "p75": self.p75,
            "max_price": self.max_price,
            "source": self.source,
            "countries": list(self.countries),
            "prices": list(self.prices),
        }


def supported_categories() -> tuple[str, ...]:
    """App categories the dataset can price *in the configured market*."""
    return tuple(_CATEGORY_GROUPS.get(settings.BTC_MARKET, {}))


# --------------------------------------------------------------------------- #
# Live engine — built lazily so an unset/broken URL costs nothing at import.
# --------------------------------------------------------------------------- #
_engine: AsyncEngine | None = None
_engine_failed = False


def _get_engine() -> AsyncEngine | None:
    global _engine, _engine_failed
    if _engine_failed or not settings.BTC_DATABASE_URL:
        return None
    if _engine is None:
        try:
            _engine = create_async_engine(
                settings.BTC_DATABASE_URL,
                # Read-only reference data queried a handful of times per
                # process. A pool would hold idle connections to someone
                # else's database for no gain.
                poolclass=NullPool,
                pool_pre_ping=True,
                future=True,
            )
        except Exception as exc:  # noqa: BLE001 — bad URL must not stop the app
            _engine_failed = True
            log.warning("btc.engine_failed", error=str(exc))
            return None
    return _engine


async def close_btc_engine() -> None:
    """Dispose the pool on shutdown. Safe when the engine was never built."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


def _row_to_reference(category: str, row: Any, source: ObservedSource) -> PriceReference | None:
    if row is None or row.sample_size is None or row.sample_size < settings.BTC_MIN_SAMPLE:
        return None
    return PriceReference(
        category=category,
        sample_size=int(row.sample_size),
        shop_count=int(row.shop_count or 0),
        min_price=int(row.min_price),
        p25=int(round(float(row.p25))),
        median=int(round(float(row.median))),
        p75=int(round(float(row.p75))),
        max_price=int(row.max_price),
        source=source,
        countries=tuple(sorted(str(c) for c in (row.country_codes or ()))),
        prices=tuple(int(p) for p in (row.prices or ())),
    )


async def _query_live(category: str) -> PriceReference | None:
    engine = _get_engine()
    groups = _groups_for(category)
    if engine is None or not groups:
        return None

    sql = text(_PERCENTILE_SQL.format(schema=settings.BTC_SCHEMA))
    try:
        async with engine.connect() as conn:
            result = await asyncio.wait_for(
                conn.execute(
                    sql,
                    {
                        "market": settings.BTC_MARKET,
                        "groups": list(groups),
                        "price_min": settings.BTC_PRICE_MIN_VND,
                        "price_max": settings.BTC_PRICE_MAX_VND,
                    },
                ),
                timeout=settings.BTC_QUERY_TIMEOUT_S,
            )
            return _row_to_reference(category, result.first(), "btc_live")
    except TimeoutError:
        log.warning("btc.query_timeout", category=category)
    except Exception as exc:  # noqa: BLE001 — external DB, best-effort by design
        log.warning("btc.query_failed", category=category, error=str(exc))
    return None


# --------------------------------------------------------------------------- #
# Snapshot fallback — written by scripts/refresh_btc_reference.py from the same
# query, so the demo still shows observed figures when the RDS is unreachable.
# --------------------------------------------------------------------------- #
_snapshot: dict[str, PriceReference] | None = None


def _load_snapshot() -> dict[str, PriceReference]:
    global _snapshot
    if _snapshot is not None:
        return _snapshot
    _snapshot = {}
    if _SNAPSHOT_PATH.exists():
        try:
            raw = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
            # A snapshot written for another marketplace is not a fallback for
            # this one. Older files carry no market at all; refusing them is
            # right too, since there is no way to tell which one they measured.
            if raw.get("market") != settings.BTC_MARKET:
                log.warning(
                    "btc.snapshot_wrong_market",
                    snapshot_market=raw.get("market"), expected=settings.BTC_MARKET,
                )
                return _snapshot
            for category, entry in raw.get("categories", {}).items():
                if int(entry["sample_size"]) < settings.BTC_MIN_SAMPLE:
                    continue
                _snapshot[category] = PriceReference(
                    category=category,
                    sample_size=int(entry["sample_size"]),
                    shop_count=int(entry["shop_count"]),
                    min_price=int(entry["min_price"]),
                    p25=int(entry["p25"]),
                    median=int(entry["median"]),
                    p75=int(entry["p75"]),
                    max_price=int(entry["max_price"]),
                    source="btc_snapshot",
                    countries=tuple(entry.get("countries", ())),
                    prices=tuple(int(p) for p in entry.get("prices", ())),
                )
        except (OSError, ValueError, KeyError) as exc:
            log.warning("btc.snapshot_unreadable", error=str(exc))
    return _snapshot


async def price_reference(category: str) -> PriceReference | None:
    """Observed percentiles for `category`, or None when unavailable.

    Live query first so a refreshed dataset is picked up without a redeploy;
    the snapshot covers an unreachable database. Returning None is a normal
    outcome — for an unmapped category it is the *only* correct one.
    """
    if not _groups_for(category):
        # Not a shortcut: an unmapped category has no honest reference at all,
        # so neither the live query nor the snapshot should be consulted.
        return None
    live = await _query_live(category)
    if live is not None:
        return live
    return _load_snapshot().get(category)
