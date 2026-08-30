"""Per-platform market reading — who actually sells this category, and at what price.

Google Shopping names the merchant behind every listing in `source`, so folding
those onto our four channels gives a real, checkable answer to "how crowded is
Shopee for kem chống nắng, and is it cheaper than Lazada" — no assumption
involved. Listings whose merchant is neither Shopee/Lazada/TikTok nor us (e.g.
Hasaki, Watsons) are kept as `other`, because ignoring them would overstate how
much of the category the big three hold.

This is the measured half of the channel model; the seller's own order volume
per channel is the assumed half and lives in channels.py as CASES.

Writes outputs/channel_market.json.
"""

from __future__ import annotations

import json
import statistics
import sys
import time

import requests

import channels
import config

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

GL, HL = "vn", "vi"
SLEEP_BETWEEN = 1.5
MAX_OFFERS = 40


def fetch_keyword(keyword: str) -> list[dict]:
    params = {
        "engine": "google_shopping",
        "q": keyword,
        "gl": GL,
        "hl": HL,
        "api_key": config.serpapi_key(),
    }
    r = requests.get(config.SERPAPI_ENDPOINT, params=params, timeout=40)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"SerpApi error: {data['error']}")
    return (data.get("shopping_results") or [])[:MAX_OFFERS]


def _bucket(results: list[dict]) -> dict[str, dict]:
    """Group one keyword's listings by channel (plus an `other` bucket)."""
    buckets: dict[str, dict] = {}
    for item in results:
        source = item.get("source") or ""
        channel_id = channels.match_channel(source) or "other"
        b = buckets.setdefault(channel_id, {"prices": [], "discounts": [], "merchants": set()})
        price = item.get("extracted_price")
        if price and price > 0:
            b["prices"].append(float(price))
        old = item.get("extracted_old_price")
        if price and old and old > price > 0:
            depth = 1.0 - (price / old)
            if 0.0 < depth < 0.95:
                b["discounts"].append(depth)
        b["merchants"].add(source)
    return buckets


def main() -> None:
    key = config.serpapi_key()
    if not key:
        print("ERROR: no SERPAPI_KEY (put it in restock_planner/.env)")
        return

    keywords = [(cat, kw) for cat, kws in config.CATEGORY_KEYWORDS.items() for kw in kws]
    print(f"API key: {key[:8]}... | {len(keywords)} truy vấn | gl={GL}")

    # category -> channel -> accumulated stats
    acc: dict[str, dict[str, dict]] = {}
    done = fail = 0

    for category, keyword in keywords:
        try:
            results = fetch_keyword(keyword)
            per_channel = _bucket(results)
            cat_acc = acc.setdefault(category, {})
            for channel_id, b in per_channel.items():
                c = cat_acc.setdefault(
                    channel_id, {"listings": 0, "prices": [], "discounts": [], "merchants": set()}
                )
                c["listings"] += len(b["prices"]) or len(b["merchants"])
                c["prices"].extend(b["prices"])
                c["discounts"].extend(b["discounts"])
                c["merchants"] |= b["merchants"]
            done += 1
            shown = ", ".join(
                f"{cid}:{len(b['prices'])}" for cid, b in sorted(per_channel.items())
            )
            print(f"  [{done + fail}/{len(keywords)}] OK  {keyword:<16} -> {shown}")
        except Exception as exc:  # noqa: BLE001 — report and continue
            fail += 1
            print(f"  [{done + fail}/{len(keywords)}] FAIL {keyword} -> {exc}")
        time.sleep(SLEEP_BETWEEN)

    if not acc:
        print("Khong lay duoc du lieu nao — khong ghi file.")
        return

    out: dict[str, dict] = {}
    for category, per_channel in acc.items():
        total = sum(c["listings"] for c in per_channel.values()) or 1
        rows: dict[str, dict] = {}
        for channel_id, c in per_channel.items():
            prices = c["prices"]
            discounts = c["discounts"]
            rows[channel_id] = {
                "listings": c["listings"],
                "share_pct": round(c["listings"] / total * 100, 1),
                "median_price_vnd": int(statistics.median(prices)) if prices else 0,
                "on_sale": len(discounts),
                "avg_discount": round(statistics.fmean(discounts), 4) if discounts else 0.0,
                "merchants": sorted(m for m in c["merchants"] if m)[:6],
            }
        out[category] = {"total_listings": total, "channels": rows}

    payload = {
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "geo": GL,
        "source": "SerpApi — Google Shopping (merchant field)",
        "categories": out,
    }
    config.CHANNEL_MARKET_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nSaved {config.CHANNEL_MARKET_JSON.name} | {done} ok, {fail} failed")
    for category, row in out.items():
        top = sorted(row["channels"].items(), key=lambda kv: -kv[1]["listings"])[:4]
        s = "  ".join(f"{k}={v['share_pct']}%" for k, v in top)
        print(f"  {category}: {s}")


if __name__ == "__main__":
    main()
