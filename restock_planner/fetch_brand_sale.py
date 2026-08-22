"""TREND signal — how deeply are the big brands discounting *right now*.

Google Shopping (via SerpApi) lists live offers with both the current price and,
when an item is on sale, the struck-through original price. The gap between them
is a real, observable discount — not an assumption about whether a sale campaign
is running.

Per brand we keep:
  - offers_seen        how many live offers we looked at
  - offers_on_sale     how many of them are discounted
  - sale_ratio         share of the brand's catalog currently on sale
  - avg_discount       mean depth across the discounted offers (0-1)
  - pressure           sale_ratio * avg_discount → the number the planner uses

`pressure` is deliberately the product of breadth and depth: one item at -70%
is not a campaign, but half the catalog at -30% is, and only the latter should
push a small seller to hold back stock.

Writes outputs/brand_sale.json.
"""

from __future__ import annotations

import json
import sys
import time

import requests

import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

GL, HL = "vn", "vi"
SLEEP_BETWEEN = 1.5
MAX_OFFERS = 40


def _discounts(shopping_results: list[dict]) -> list[float]:
    """Discount depth (0-1) for every offer that shows a struck-through price."""
    out: list[float] = []
    for item in shopping_results[:MAX_OFFERS]:
        price = item.get("extracted_price")
        old = item.get("extracted_old_price")
        if not price or not old or old <= 0 or price >= old:
            continue
        depth = 1.0 - (price / old)
        if 0.0 < depth < 0.95:  # >95% off is a data artefact, not a sale
            out.append(depth)
    return out


def fetch_brand(brand: str, category: str) -> dict:
    params = {
        "engine": "google_shopping",
        "q": f"{brand} {category}",
        "gl": GL,
        "hl": HL,
        "api_key": config.serpapi_key(),
    }
    r = requests.get(config.SERPAPI_ENDPOINT, params=params, timeout=40)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"SerpApi error: {data['error']}")

    results = data.get("shopping_results", []) or []
    seen = min(len(results), MAX_OFFERS)
    depths = _discounts(results)

    sale_ratio = (len(depths) / seen) if seen else 0.0
    avg_discount = (sum(depths) / len(depths)) if depths else 0.0

    return {
        "brand": brand,
        "category": category,
        "offers_seen": seen,
        "offers_on_sale": len(depths),
        "sale_ratio": round(sale_ratio, 4),
        "avg_discount": round(avg_discount, 4),
        "pressure": round(sale_ratio * avg_discount, 4),
    }


def main() -> None:
    key = config.serpapi_key()
    if not key:
        print("ERROR: no SERPAPI_KEY (put it in restock_planner/.env)")
        return

    pairs = [(b, c) for c, bs in config.BIG_BRANDS.items() for b in bs]
    print(f"API key: {key[:8]}... | {len(pairs)} brands | gl={GL}")

    brands: list[dict] = []
    done = fail = 0
    for brand, category in pairs:
        try:
            row = fetch_brand(brand, category)
            brands.append(row)
            done += 1
            print(f"  [{done + fail}/{len(pairs)}] OK  {brand:16s} "
                  f"seen={row['offers_seen']:2d} on_sale={row['offers_on_sale']:2d} "
                  f"avg={row['avg_discount']:.0%} pressure={row['pressure']:.3f}")
        except Exception as exc:  # noqa: BLE001 — report and continue
            fail += 1
            print(f"  [{done + fail}/{len(pairs)}] FAIL {brand} -> {exc}")
        time.sleep(SLEEP_BETWEEN)

    if not brands:
        print("No brand data fetched — nothing written.")
        return

    payload = {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "geo": GL,
        "brands": brands,
    }
    config.BRAND_SALE_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nSaved {config.BRAND_SALE_JSON.name} | {done} ok, {fail} failed")


if __name__ == "__main__":
    main()
