"""Observed Shopee prices, entered by hand from search-results screenshots.

This is the market reference for categories the organisers' dataset cannot
cover. It is *seed data*, not a feed: someone searched Shopee, read the prices
off the page and typed them into ``data/shopee_listings.json``. Two things
follow from that, and both are surfaced rather than hidden:

* It has a collection date and does not change until someone repeats the
  exercise. `collected_at` travels with every reference so the panel can say
  how old it is.
* It covers whichever keywords were captured. A category with no matching
  query resolves to ``None`` and the caller falls back, exactly as with the
  organisers' dataset.

What makes it worth the manual effort: the alternative in place was the demo
catalogue, which meant a seller's price was compared against *their own other
products* and labelled "thị trường". These are real listings from real
competing shops, so the comparison finally means what it says.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import median as _median

from app.core.logging import get_logger

log = get_logger("app.services.shopee_listings")

_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "shopee_listings.json"

#: Below this many listings a percentile describes the sample rather than the
#: market, so the caller is better off with its own fallback.
_MIN_SAMPLE = 15

#: Search results carry bundles and unrelated items — a "combo 2" or a gift set
#: sits far above the single product a seller is pricing. Trimming the extremes
#: keeps one outlier from dragging the quartiles; 10% each end is enough to
#: drop them without reshaping the middle.
_TRIM_SHARE = 0.10


@dataclass(frozen=True)
class ListingReference:
    """Observed price percentiles for one keyword."""

    keyword: str
    category: str
    collected_at: str
    sample_size: int
    p25: int
    median: int
    p75: int
    prices: tuple[int, ...]

    def percentile_of(self, price: int) -> int | None:
        """Share of observed listings priced at or below `price`, 0-100."""
        if not self.prices:
            return None
        return round(sum(1 for p in self.prices if p <= price) / len(self.prices) * 100)


@lru_cache(maxsize=1)
def _load() -> dict:
    if not _DATA_FILE.exists():
        log.warning("shopee_listings.missing", path=str(_DATA_FILE))
        return {"queries": []}
    try:
        return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.warning("shopee_listings.unreadable", error=str(exc))
        return {"queries": []}


def _percentile(values: list[int], q: float) -> int:
    """Nearest-rank percentile over a sorted list."""
    if not values:
        return 0
    index = min(len(values) - 1, max(0, round(q * (len(values) - 1))))
    return values[index]


def _reference_for(query: dict, collected_at: str) -> ListingReference | None:
    prices = sorted(
        int(item["price"]) for item in query.get("listings", []) if item.get("price")
    )
    if len(prices) < _MIN_SAMPLE:
        return None

    cut = int(len(prices) * _TRIM_SHARE)
    trimmed = prices[cut : len(prices) - cut] or prices

    return ListingReference(
        keyword=query["keyword"],
        category=query["category"],
        collected_at=collected_at,
        sample_size=len(trimmed),
        p25=_percentile(trimmed, 0.25),
        median=_percentile(trimmed, 0.50),
        p75=_percentile(trimmed, 0.75),
        prices=tuple(trimmed),
    )


def reference_for_product(product_name: str, category: str) -> ListingReference | None:
    """Best captured keyword for this product, or None.

    Matched on the product's own words rather than on an exact keyword, so
    "Serum Vitamin C 15%" finds the "serum vitamin c" capture. Falls back to any
    capture in the same category, which is still a real market — just a looser
    comparison than the same product type.
    """
    data = _load()
    collected_at = data.get("collected_at", "")
    queries = [q for q in data.get("queries", []) if q.get("category") == category]
    if not queries:
        return None

    words = set(product_name.lower().split())
    scored = [
        (len(words & set(q["keyword"].lower().split())), q)
        for q in queries
    ]
    best_overlap, best_query = max(scored, key=lambda pair: pair[0])
    if best_overlap == 0:
        # Nothing matched the product; the category capture is still a market,
        # just a broader one. Better than comparing the seller to themselves.
        best_query = queries[0]

    return _reference_for(best_query, collected_at)


def captured_categories() -> tuple[str, ...]:
    """Categories with at least one usable capture."""
    data = _load()
    out = {
        q["category"] for q in data.get("queries", [])
        if _reference_for(q, data.get("collected_at", "")) is not None
    }
    return tuple(sorted(out))
