"""SEASON model — turn 5 years of Google Trends history into a seasonal index.

Method (classic seasonal-index decomposition, no black box):
  1. Google Trends rescales every query to its own 0-100 range, so each keyword
     is first normalised against its own mean → a unitless "how busy is this
     term compared to its normal" ratio.
  2. Those ratios are averaged per calendar month across all 5 years. Averaging
     across years is what separates a genuine seasonal pattern from a one-off
     spike in a single December.
  3. A category's index is the mean of its keywords' indices, clamped to a sane
     band so one noisy term cannot swing the plan.

index[m] = 1.0  → month m is an ordinary month for this category
index[m] = 1.3  → demand in month m runs ~30% above the category's own normal

Momentum answers the seller's other question — "is my revenue margin widening
or shrinking *right now*" — by comparing the last 8 weeks against the 8 before.

Pure stdlib: the backend imports the same formulas without pulling in pandas.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict

import config

RECENT_WEEKS = 8


def _monthly_index(series: list[dict]) -> dict[int, float]:
    """Seasonal index per calendar month for one keyword series."""
    values = [p["interest"] for p in series if p["interest"] > 0]
    if not values:
        return {}
    overall = statistics.fmean(values)
    if overall <= 0:
        return {}

    by_month: dict[int, list[float]] = defaultdict(list)
    for p in series:
        if p["interest"] <= 0:
            continue
        month = int(p["date"][5:7])
        by_month[month].append(p["interest"] / overall)

    return {m: statistics.fmean(v) for m, v in by_month.items() if v}


def _momentum(series: list[dict]) -> float:
    """Recent-vs-previous change in %, bounded to [-100, 100].

    Uses the same bounded form as #08 so the two features speak the same
    language: (recent - previous) / (recent + previous) * 100.
    """
    values = [p["interest"] for p in series]
    if len(values) < RECENT_WEEKS * 2:
        return 0.0
    recent = statistics.fmean(values[-RECENT_WEEKS:])
    previous = statistics.fmean(values[-RECENT_WEEKS * 2:-RECENT_WEEKS])
    total = recent + previous
    if total <= 0:
        return 0.0
    return round((recent - previous) / total * 100, 1)


def build_profiles(trends: dict) -> dict[str, dict]:
    """Per-category seasonal profile from the cached Trends payload."""
    profiles: dict[str, dict] = {}

    for category, keywords in trends.get("categories", {}).items():
        if not keywords:
            continue

        per_month: dict[int, list[float]] = defaultdict(list)
        momentums: list[float] = []
        weeks = 0

        for _kw, series in keywords.items():
            if not series:
                continue
            weeks = max(weeks, len(series))
            for month, idx in _monthly_index(series).items():
                per_month[month].append(idx)
            momentums.append(_momentum(series))

        if not per_month:
            continue

        index = {}
        for month in range(1, 13):
            vals = per_month.get(month)
            raw = statistics.fmean(vals) if vals else 1.0
            index[month] = round(
                min(config.SEASON_INDEX_MAX, max(config.SEASON_INDEX_MIN, raw)), 3
            )

        peak = max(index, key=lambda m: index[m])
        low = min(index, key=lambda m: index[m])
        mom = round(statistics.fmean(momentums), 1) if momentums else 0.0

        profiles[category] = {
            "seasonal_index": index,
            "peak_month": peak,
            "low_month": low,
            "momentum": mom,
            "direction": "rising" if mom >= 5 else "falling" if mom <= -5 else "stable",
            "keywords": list(keywords.keys()),
            "weeks_of_history": weeks,
        }

    return profiles


def load_profiles() -> dict[str, dict]:
    if not config.TRENDS_JSON.exists():
        raise FileNotFoundError(
            f"Missing {config.TRENDS_JSON} — run fetch_trends.py first."
        )
    trends = json.loads(config.TRENDS_JSON.read_text(encoding="utf-8"))
    return build_profiles(trends)


if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    for cat, prof in load_profiles().items():
        idx = prof["seasonal_index"]
        print(f"\n{cat}  ({prof['weeks_of_history']} weeks, "
              f"momentum {prof['momentum']:+.1f} → {prof['direction']})")
        print("  peak month:", prof["peak_month"], "| low month:", prof["low_month"])
        print("  " + "  ".join(f"T{m}:{idx[m]:.2f}" for m in range(1, 13)))
