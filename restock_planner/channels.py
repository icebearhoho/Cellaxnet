"""Sales channels and their demand profiles.

The seller lists on four places at once, and the same SKU behaves differently on
each. This module holds two things the planner needs to tell them apart:

  CHANNELS   who they are, and the platform fee that eats into margin
  CASES      the four demand archetypes the seller asked to model

WHAT IS MEASURED AND WHAT IS ASSUMED — read before quoting any number:

  * Measured (Google Shopping, per platform): how many listings each platform
    carries in a category, at what price, and how deeply discounted. Google
    returns the merchant in `source`, so "Shopee has 9 of the 40 listings for
    kem chống nắng" is an observation, not a guess. Lives in
    fetch_channel_market.py.

  * Assumed (the seller's own order volume per channel): no public API exposes
    how many orders a specific shop gets. Shopee/Lazada/TikTok all gate that
    behind a seller OAuth token we do not have. So the four CASES below are
    labelled archetypes the seller picks per channel — a planning scenario, the
    same contract as the 11.11 what-if, never presented as a reading.

  * Assumed (platform fees): published rates move with category and seller
    tier. The defaults are typical VN rates and are configurable per request.
"""

from __future__ import annotations

# --- the four channels ------------------------------------------------------
# `source_match` maps Google Shopping's merchant string onto a channel. Matching
# is lowercase substring: "Lazada Vietnam" and "lazada.vn" both fold to lazada.
CHANNELS: dict[str, dict] = {
    "shopee": {
        "name": "Shopee",
        "kind": "marketplace",
        "commission_pct": 5.0,
        "source_match": ["shopee"],
        "note": "Sàn lớn nhất VN, cạnh tranh giá gay gắt",
    },
    "lazada": {
        "name": "Lazada",
        "kind": "marketplace",
        "commission_pct": 4.0,
        "source_match": ["lazada"],
        "note": "Sàn lớn, thiên về hàng chính hãng",
    },
    "tiktok": {
        "name": "TikTok Shop",
        "kind": "marketplace",
        "commission_pct": 5.0,
        "source_match": ["tiktok"],
        "note": "Bán theo trend/livestream, biến động mạnh",
    },
    "own": {
        "name": "Cửa hàng riêng",
        "kind": "own",
        # No marketplace cut, but the payment gateway still takes a slice.
        "commission_pct": 2.0,
        "source_match": [],
        "note": "Storefront của hệ thống — không mất phí sàn, nhưng phải tự kéo khách",
    },
}

CHANNEL_ORDER = ["shopee", "lazada", "tiktok", "own"]


# --- the four demand cases --------------------------------------------------
# volume  : scales the SKU's baseline daily sales on this channel
# season  : how hard the seasonal index bites (1.0 = as measured, 2.5 = amplified)
# trend   : how hard big-brand discounting bites
#
# `season` and `trend` amplify the *deviation from 1.0*, so a channel with
# season=2.5 in a month whose index is 1.41 sees 1 + 0.41*2.5 = 2.03, and in a
# 0.79 month sees 1 - 0.21*2.5 = 0.48. That spread is the whole point of case 3.
CASES: dict[str, dict] = {
    "hot": {
        "label": "Bán chạy, nhiều đơn",
        "volume": 2.0,
        "season": 1.0,
        "trend": 0.8,   # a loyal base shrugs off rivals' sales
        "desc": "Kênh chủ lực — đơn đều và nhiều, ít bị đối thủ hút mất khách",
    },
    "slow": {
        "label": "Bán ít, ít đơn",
        "volume": 0.35,
        "season": 0.8,
        "trend": 1.2,   # thin traffic is easier for rivals to poach
        "desc": "Kênh yếu — đơn nhỏ giọt, dễ mất khách khi đối thủ sale",
    },
    "seasonal": {
        "label": "Theo mùa & trend",
        "volume": 1.0,
        "season": 2.5,
        "trend": 2.0,
        "desc": "Kênh bùng nổ đúng mùa rồi nguội hẳn — nhạy cả mùa vụ lẫn sale đối thủ",
    },
    "dead": {
        "label": "Không bán được hàng",
        "volume": 0.0,
        "season": 1.0,
        "trend": 1.0,
        "desc": "Kênh chưa ra đơn — nhập thêm chỉ làm đọng vốn, cần sửa kênh trước",
    },
}

CASE_ORDER = ["hot", "slow", "seasonal", "dead"]

# Default pairing, chosen so all four behaviours are visible side by side on
# first load. It is a starting point the seller overrides per channel, NOT a
# claim about how these platforms actually perform.
DEFAULT_CASE_BY_CHANNEL: dict[str, str] = {
    "shopee": "hot",
    "lazada": "slow",
    "tiktok": "seasonal",
    "own": "dead",
}


def _amplify(value: float, strength: float) -> float:
    """Stretch a multiplier's distance from 1.0 by `strength`, floored at 0.05.

    Amplifying the deviation rather than the value keeps 1.0 ("an ordinary
    month", "nobody on sale") fixed at 1.0 for every case, so the cases only
    diverge where there is actually a signal to react to.
    """
    return max(0.05, 1.0 + (value - 1.0) * strength)


def channel_demand_factor(case_id: str, season_index: float, competition_multiplier: float) -> dict:
    """How this channel's demand for a SKU scales, split into its three parts."""
    case = CASES.get(case_id) or CASES["hot"]
    season_adj = _amplify(season_index, case["season"])
    trend_adj = _amplify(competition_multiplier, case["trend"])
    factor = case["volume"] * season_adj * trend_adj
    return {
        "volume": case["volume"],
        "season_adj": round(season_adj, 3),
        "trend_adj": round(trend_adj, 3),
        "factor": round(factor, 4),
    }


def resolve_cases(overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Per-channel case ids, defaults filled in and unknown ids rejected."""
    out = dict(DEFAULT_CASE_BY_CHANNEL)
    for channel_id, case_id in (overrides or {}).items():
        if channel_id in CHANNELS and case_id in CASES:
            out[channel_id] = case_id
    return out


def match_channel(source: str) -> str | None:
    """Fold a Google Shopping merchant string onto a channel id, if it is one."""
    low = (source or "").lower()
    for channel_id in CHANNEL_ORDER:
        for token in CHANNELS[channel_id]["source_match"]:
            if token in low:
                return channel_id
    return None


if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print("Kênh:")
    for cid in CHANNEL_ORDER:
        c = CHANNELS[cid]
        print(f"  {c['name']:<16} phí {c['commission_pct']:>4.1f}%  {c['note']}")

    print("\nHệ số cầu theo case (mùa cao 1.41 vs mùa thấp 0.79, đối thủ sale x0.85):")
    for case_id in CASE_ORDER:
        hi = channel_demand_factor(case_id, 1.41, 0.85)
        lo = channel_demand_factor(case_id, 0.79, 0.85)
        print(f"  {CASES[case_id]['label']:<22} mùa cao x{hi['factor']:<6.2f} "
              f"mùa thấp x{lo['factor']:.2f}")
