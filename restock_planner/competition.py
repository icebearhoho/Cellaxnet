"""TREND model — convert live big-brand discounting into a demand multiplier.

The seller's question is concrete: "the big brands are running a sale — should I
hold back stock, and by how much?"

Per category we aggregate the brands' `pressure` (breadth x depth of their
current sale, computed in fetch_brand_sale.py) and map it to a multiplier:

    multiplier = 1 - COMPETITION_SENSITIVITY * pressure

pressure 0.00 → multiplier 1.00   nobody is on sale, plan normally
pressure 0.10 → multiplier 0.95   mild campaign, trim stock slightly
pressure 0.30 → multiplier 0.85   heavy campaign, hold back

When the campaign ends the next fetch returns a lower pressure and the
multiplier climbs back on its own — that is the "tăng lại khi hết sale" half of
the requirement, and it happens without anyone editing a number by hand.

Pure stdlib so the backend can reuse the formula.
"""

from __future__ import annotations

import json
import statistics

import config


def category_pressure(brands: list[dict]) -> dict[str, dict]:
    """Aggregate per-brand sale readings into one reading per category."""
    by_cat: dict[str, list[dict]] = {}
    for row in brands:
        by_cat.setdefault(row["category"], []).append(row)

    out: dict[str, dict] = {}
    for category, rows in by_cat.items():
        # Weight each brand by how many offers we actually saw, so a brand with
        # 3 listings cannot outvote one with 40.
        total_seen = sum(r["offers_seen"] for r in rows)
        if total_seen:
            pressure = sum(r["pressure"] * r["offers_seen"] for r in rows) / total_seen
        else:
            pressure = 0.0

        on_sale = [r for r in rows if r["offers_on_sale"] > 0]
        multiplier = 1.0 - config.COMPETITION_SENSITIVITY * pressure
        multiplier = round(min(1.0, max(0.5, multiplier)), 3)

        if pressure >= 0.15:
            level, note = "high", "Big brand đang sale mạnh — giảm nhập, chờ hết sale"
        elif pressure >= 0.05:
            level, note = "medium", "Big brand có sale nhẹ — nhập dè chừng"
        else:
            level, note = "low", "Big brand không sale đáng kể — nhập bình thường"

        # The brand leading the campaign is the one a seller should watch.
        leader = max(rows, key=lambda r: r["pressure"]) if rows else None

        out[category] = {
            "pressure": round(pressure, 4),
            "demand_multiplier": multiplier,
            "level": level,
            "note": note,
            "brands_on_sale": len(on_sale),
            "brands_checked": len(rows),
            "avg_discount": round(
                statistics.fmean([r["avg_discount"] for r in on_sale]), 4
            ) if on_sale else 0.0,
            "leader": {
                "brand": leader["brand"],
                "sale_ratio": leader["sale_ratio"],
                "avg_discount": leader["avg_discount"],
            } if leader else None,
            "detail": sorted(rows, key=lambda r: -r["pressure"]),
        }
    return out


def load_pressure() -> dict[str, dict]:
    if not config.BRAND_SALE_JSON.exists():
        raise FileNotFoundError(
            f"Missing {config.BRAND_SALE_JSON} — run fetch_brand_sale.py first."
        )
    payload = json.loads(config.BRAND_SALE_JSON.read_text(encoding="utf-8"))
    return category_pressure(payload.get("brands", []))


if __name__ == "__main__":
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    for cat, p in load_pressure().items():
        print(f"\n{cat}: pressure {p['pressure']:.3f} → x{p['demand_multiplier']} "
              f"({p['level']})")
        print(f"  {p['brands_on_sale']}/{p['brands_checked']} brand đang sale, "
              f"giảm TB {p['avg_discount']:.0%}")
        if p["leader"]:
            lead = p["leader"]
            print(f"  dẫn đầu: {lead['brand']} "
                  f"({lead['sale_ratio']:.0%} SP sale, -{lead['avg_discount']:.0%})")
