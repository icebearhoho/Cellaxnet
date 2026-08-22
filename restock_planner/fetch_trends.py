"""SEASON signal — pull 5 years of Google Trends history via SerpApi.

One call per category keyword returns a weekly series going back 5 years, which
is what makes a seasonal index possible: 5 observations per calendar month is
enough to separate "this category always peaks in December" from "one odd spike
last December".

Writes outputs/trends_history.json so the rest of the pipeline (and the demo)
never has to hit the network again.
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

GEO = "VN"
SLEEP_BETWEEN = 1.5


def fetch_series(keyword: str) -> list[dict]:
    """Return [{date: 'YYYY-MM-DD', interest: int}] — 5y weekly, real values."""
    params = {
        "engine": "google_trends",
        "q": keyword,
        "geo": GEO,
        "date": config.TRENDS_WINDOW,
        "data_type": "TIMESERIES",
        "api_key": config.serpapi_key(),
    }
    r = requests.get(config.SERPAPI_ENDPOINT, params=params, timeout=40)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"SerpApi error: {data['error']}")

    timeline = data.get("interest_over_time", {}).get("timeline_data", [])
    if not timeline:
        raise RuntimeError("empty timeline_data")

    import datetime as dt

    out = []
    for pt in timeline:
        ts = int(pt["timestamp"])
        val = pt["values"][0]["extracted_value"]
        date = dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()
        out.append({"date": date.isoformat(), "interest": int(max(min(val, 100), 0))})
    return out


def main() -> None:
    key = config.serpapi_key()
    if not key:
        print("ERROR: no SERPAPI_KEY (put it in restock_planner/.env)")
        return
    print(f"API key: {key[:8]}... | window: {config.TRENDS_WINDOW} | geo: {GEO}")

    result: dict[str, dict[str, list[dict]]] = {}
    total = sum(len(v) for v in config.CATEGORY_KEYWORDS.values())
    done = fail = 0

    for category, keywords in config.CATEGORY_KEYWORDS.items():
        result[category] = {}
        for kw in keywords:
            try:
                series = fetch_series(kw)
                result[category][kw] = series
                done += 1
                print(f"  [{done + fail}/{total}] OK  {category} / {kw} "
                      f"-> {len(series)} weeks")
            except Exception as exc:  # noqa: BLE001 — report and continue
                fail += 1
                print(f"  [{done + fail}/{total}] FAIL {category} / {kw} -> {exc}")
            time.sleep(SLEEP_BETWEEN)

    if not done:
        print("No series fetched — nothing written.")
        return

    payload = {
        "window": config.TRENDS_WINDOW,
        "geo": GEO,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "categories": result,
    }
    config.TRENDS_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nSaved {config.TRENDS_JSON.name} | {done} ok, {fail} failed")


if __name__ == "__main__":
    main()
