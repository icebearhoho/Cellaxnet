"""Bundle the two API pulls into one self-contained file the backend reads.

demo_data.json holds everything the planner needs about the *market* (seasonal
indices + current big-brand sale pressure). The seller's side of the problem —
budget, catalog, costs — comes from the request and the shop database, so it is
deliberately not baked in here.

Having this file means the backend answers instantly and works offline; the
live SerpApi refresh in the service is an upgrade on top, never a requirement.
"""

from __future__ import annotations

import json
import sys
import time

import channels
import competition
import config
import season_model

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main() -> None:
    trends_raw = json.loads(config.TRENDS_JSON.read_text(encoding="utf-8"))
    brand_raw = json.loads(config.BRAND_SALE_JSON.read_text(encoding="utf-8"))

    profiles = season_model.build_profiles(trends_raw)
    pressure = competition.category_pressure(brand_raw.get("brands", []))

    # Per-platform market reading is optional: the planner still works from the
    # channel CASES alone if this pull was never run.
    channel_market: dict = {}
    if config.CHANNEL_MARKET_JSON.exists():
        channel_market = json.loads(config.CHANNEL_MARKET_JSON.read_text(encoding="utf-8"))

    payload = {
        "meta": {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "trends_fetched_at": trends_raw.get("fetched_at"),
            "brand_sale_fetched_at": brand_raw.get("fetched_at"),
            "trends_window": trends_raw.get("window"),
            "geo": trends_raw.get("geo"),
            "source": "SerpApi — Google Trends (TIMESERIES) + Google Shopping",
            "categories": list(profiles.keys()),
            "weeks_of_history": max(
                (p.get("weeks_of_history", 0) for p in profiles.values()), default=0
            ),
            "brands_checked": len(brand_raw.get("brands", [])),
        },
        "season": profiles,
        "competition": pressure,
        "channels": {
            "definitions": channels.CHANNELS,
            "cases": channels.CASES,
            "default_case": channels.DEFAULT_CASE_BY_CHANNEL,
            "order": channels.CHANNEL_ORDER,
            "case_order": channels.CASE_ORDER,
            # Measured platform presence; empty dict when the pull never ran.
            "market": channel_market.get("categories", {}),
            "market_fetched_at": channel_market.get("fetched_at"),
        },
    }

    config.DEMO_DATA_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    size_kb = config.DEMO_DATA_JSON.stat().st_size // 1024
    print(f"Created: {config.DEMO_DATA_JSON.name} ({size_kb} KB)")
    print(f"  categories : {', '.join(profiles)}")
    print(f"  history    : {payload['meta']['weeks_of_history']} weeks")
    print(f"  brands     : {payload['meta']['brands_checked']}")


if __name__ == "__main__":
    main()
