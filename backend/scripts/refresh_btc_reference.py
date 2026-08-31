"""Write the offline copy of the BTC price reference.

`btc_market` queries the organisers' database live, and falls back to the file
this script writes when that database is unreachable — a demo should not go
back to synthetic numbers because of someone else's network.

Every figure comes from the same query the service runs; nothing is typed by
hand. Re-run it whenever the organisers refresh the dataset, and commit the
result so the fallback ships with the code.

Run from the backend directory, with BTC_DATABASE_URL set:

    cd backend
    python scripts/refresh_btc_reference.py

    # or pass it explicitly
    python scripts/refresh_btc_reference.py --url postgresql+asyncpg://user:pass@host/db
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Vietnamese category names and "₫" are unprintable on a cp1252 console, and a
# UnicodeEncodeError there would abort a run whose query already succeeded.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.services import btc_market  # noqa: E402


async def _collect() -> dict:
    categories: dict[str, dict] = {}
    for category in btc_market.supported_categories():
        ref = await btc_market._query_live(category)  # noqa: SLF001 — same query, by design
        if ref is None:
            print(f"  {category}: no usable sample (skipped)")
            continue
        entry = ref.as_dict()
        entry.pop("source")  # the file *is* the snapshot; the label is added on read
        entry.pop("category")
        categories[category] = entry
        print(
            f"  {category}: {ref.sample_size} products, {ref.shop_count} shops, "
            f"median {ref.median:,}₫ (p25 {ref.p25:,} – p75 {ref.p75:,})"
        )
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "schema": settings.BTC_SCHEMA,
        # Stamped so a snapshot can never be read as another market's.
        "market": settings.BTC_MARKET,
        "price_window_vnd": [settings.BTC_PRICE_MIN_VND, settings.BTC_PRICE_MAX_VND],
        "categories": categories,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="BTC database URL (overrides BTC_DATABASE_URL)")
    args = parser.parse_args()

    if args.url:
        settings.BTC_DATABASE_URL = args.url
    if not settings.BTC_DATABASE_URL:
        print("BTC_DATABASE_URL is not set — nothing to query.", file=sys.stderr)
        return 2

    print(f"Querying {settings.BTC_SCHEMA}, market={settings.BTC_MARKET} ...")
    payload = await _collect()
    await btc_market.close_btc_engine()

    if not payload["categories"]:
        print("No category produced a usable sample; file left unchanged.", file=sys.stderr)
        return 1

    path = btc_market._SNAPSHOT_PATH  # noqa: SLF001 — one owner, one path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
