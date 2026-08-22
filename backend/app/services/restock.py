"""Smart Restock Planner service — turn budget + market signals into quantities.

Market snapshot (`app/data/restock_market.json`) holds the two measured signals:
a 12-month seasonal index per category learned from 5 years of Google Trends,
and the big brands' current sale pressure read off Google Shopping. It is
produced by the offline layer in `restock_planner/` and committed so the API
answers instantly and works with no network — the live refresh below is an
upgrade on top, never a requirement (same contract as supply_news).

Allocation lives here and only here. An earlier offline mirror of these
formulas in restock_planner/ drifted the moment channels were added, so the
folder now owns only what it is good at — fetching signals and modelling them
(season, competition, channels) — and the money decision has a single
implementation.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import time
from functools import lru_cache
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.restock import RestockPlanRequest, RestockPlanResponse
from app.services import commerce_store

log = get_logger("app.services.restock")

_DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "restock_market.json"

# Defaults mirror restock_planner/config.py — keep the two in step.
DEFAULT_SENSITIVITY = 0.5
MAX_SKU_BUDGET_SHARE = 0.25
URGENCY_CAP = 3.0

_SERPAPI = "https://serpapi.com/search"
_LIVE_TTL = 6 * 3600.0  # a sale campaign does not turn on and off by the minute
_LIVE_CACHE: dict[str, tuple[float, list[dict]]] = {}
_MAX_OFFERS = 40


# --------------------------------------------------------------------------- #
# market snapshot
# --------------------------------------------------------------------------- #

@lru_cache(maxsize=1)
def _snapshot() -> dict:
    if not _DATA_FILE.exists():
        log.error("restock.snapshot_missing", path=str(_DATA_FILE))
        return {"meta": {}, "season": {}, "competition": {}}
    return json.loads(_DATA_FILE.read_text(encoding="utf-8"))


def _season_profiles() -> dict[str, dict]:
    """Seasonal indices with integer month keys (JSON turns them into strings)."""
    out = {}
    for category, prof in _snapshot().get("season", {}).items():
        idx = {int(m): float(v) for m, v in (prof.get("seasonal_index") or {}).items()}
        out[category] = {**prof, "seasonal_index": idx}
    return out


def _channel_config() -> dict:
    """Channel definitions, cases and measured platform presence.

    Sourced from the snapshot rather than redeclared here, so the offline layer
    in restock_planner/channels.py stays the single place they are defined.
    """
    ch = _snapshot().get("channels") or {}
    return {
        "definitions": ch.get("definitions") or {},
        "cases": ch.get("cases") or {},
        "default_case": ch.get("default_case") or {},
        "order": ch.get("order") or list((ch.get("definitions") or {}).keys()),
        "case_order": ch.get("case_order") or list((ch.get("cases") or {}).keys()),
        "market": ch.get("market") or {},
        "market_fetched_at": ch.get("market_fetched_at"),
    }


def _brand_rows() -> list[dict]:
    rows: list[dict] = []
    for reading in _snapshot().get("competition", {}).values():
        rows.extend(reading.get("detail", []))
    return rows


# --------------------------------------------------------------------------- #
# competition: measured, live-refreshed, or scenario
# --------------------------------------------------------------------------- #

def _aggregate(brands: list[dict], sensitivity: float) -> dict[str, dict]:
    """Weighted per-category sale pressure → a demand multiplier."""
    by_cat: dict[str, list[dict]] = {}
    for row in brands:
        by_cat.setdefault(row["category"], []).append(row)

    out: dict[str, dict] = {}
    for category, rows in by_cat.items():
        # Weight by offers seen so a brand with 3 listings cannot outvote one
        # with 40.
        seen = sum(r["offers_seen"] for r in rows)
        pressure = (
            sum(r["pressure"] * r["offers_seen"] for r in rows) / seen if seen else 0.0
        )
        on_sale = [r for r in rows if r["offers_on_sale"] > 0]
        multiplier = round(min(1.0, max(0.5, 1.0 - sensitivity * pressure)), 3)

        if pressure >= 0.15:
            level = "high"
            note = "Big brand đang sale mạnh — giảm nhập, chờ hết sale"
        elif pressure >= 0.05:
            level = "medium"
            note = "Big brand có sale nhẹ — nhập dè chừng"
        else:
            level = "low"
            note = "Big brand không sale đáng kể — nhập bình thường"

        leader = max(rows, key=lambda r: r["pressure"]) if rows else None
        out[category] = {
            "category": category,
            "pressure": round(pressure, 4),
            "demand_multiplier": multiplier,
            "level": level,
            "note": note,
            "brands_on_sale": len(on_sale),
            "brands_checked": len(rows),
            "avg_discount": round(
                sum(r["avg_discount"] for r in on_sale) / len(on_sale), 4
            ) if on_sale else 0.0,
            "leader_brand": leader["brand"] if leader else None,
        }
    return out


def _scenario(measured: dict[str, dict], target: float, sensitivity: float) -> dict[str, dict]:
    """A what-if reading: scale today's campaign up to `target` average pressure.

    Deliberately NOT a flat "every category is at `target`". The ranking that
    drives allocation is `roi x urgency x season x competition`, so a multiplier
    identical across every category is a constant factor that cancels out —
    it changes each SKU's demand figure but leaves the *order* untouched, which
    means the plan comes back byte-identical whether you model a 10% campaign
    or a 50% one. Scaling the measured per-category pressures preserves the
    real spread between categories, so the scenario actually moves capital the
    way a heavier campaign would.

    Falls back to a flat distribution only when nothing measurable is on sale
    (nothing to preserve the shape of).

    The response flags `scenario`, so the UI never presents this as an
    observation.
    """
    cats = list(measured)
    if not cats:
        return {}

    base = {c: float(measured[c].get("pressure", 0.0)) for c in cats}
    mean = sum(base.values()) / len(base)
    # Preserve relative structure; if the market is flat, spread evenly.
    scale = (target / mean) if mean > 1e-6 else 0.0

    out: dict[str, dict] = {}
    for c in cats:
        p = min(1.0, base[c] * scale) if scale else target
        multiplier = round(min(1.0, max(0.5, 1.0 - sensitivity * p)), 3)
        level = "high" if p >= 0.15 else "medium" if p >= 0.05 else "low"
        out[c] = {
            "category": c,
            "pressure": round(p, 4),
            "demand_multiplier": multiplier,
            "level": level,
            "note": f"Kịch bản giả định: áp lực sale {p:.0%} (đo thật {base[c]:.1%})",
            "brands_on_sale": measured[c].get("brands_on_sale", 0),
            "brands_checked": measured[c].get("brands_checked", 0),
            "avg_discount": measured[c].get("avg_discount", 0.0),
            "leader_brand": measured[c].get("leader_brand"),
        }
    return out


def _discount_depths(results: list[dict]) -> list[float]:
    depths = []
    for item in results[:_MAX_OFFERS]:
        price = item.get("extracted_price")
        old = item.get("extracted_old_price")
        if not price or not old or old <= 0 or price >= old:
            continue
        depth = 1.0 - (price / old)
        if 0.0 < depth < 0.95:  # >95% off is a data artefact, not a sale
            depths.append(depth)
    return depths


async def _fetch_live_brands() -> list[dict]:
    """Re-read the big brands' current discounting from Google Shopping."""
    if not settings.SERPAPI_KEY:
        return []

    baseline = _brand_rows()
    now = time.monotonic()
    cached = _LIVE_CACHE.get("brands")
    if cached and now - cached[0] < _LIVE_TTL:
        return cached[1]

    rows: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
            for base in baseline:
                params = {
                    "engine": "google_shopping",
                    "q": f"{base['brand']} {base['category']}",
                    "gl": "vn", "hl": "vi",
                    "api_key": settings.SERPAPI_KEY,
                }
                r = await client.get(_SERPAPI, params=params)
                if r.status_code >= 400:
                    log.warning("restock.live_http_error", status=r.status_code,
                                brand=base["brand"])
                    continue
                results = r.json().get("shopping_results", []) or []
                seen = min(len(results), _MAX_OFFERS)
                depths = _discount_depths(results)
                ratio = (len(depths) / seen) if seen else 0.0
                avg = (sum(depths) / len(depths)) if depths else 0.0
                rows.append({
                    "brand": base["brand"], "category": base["category"],
                    "offers_seen": seen, "offers_on_sale": len(depths),
                    "sale_ratio": round(ratio, 4), "avg_discount": round(avg, 4),
                    "pressure": round(ratio * avg, 4),
                })
    except Exception as exc:  # noqa: BLE001 — live refresh is best-effort
        log.warning("restock.live_failed", error=str(exc))
        return cached[1] if cached else []

    if rows:
        _LIVE_CACHE["brands"] = (now, rows)
    return rows


# --------------------------------------------------------------------------- #
# allocation
# --------------------------------------------------------------------------- #

def _urgency(stock: int, daily: float, horizon: int) -> float:
    if daily <= 0:
        return 1.0
    runway = stock / daily
    if runway <= 0:
        return URGENCY_CAP
    return min(URGENCY_CAP, max(1.0, horizon / runway))


def _reason(c: dict, qty: int, partial: bool) -> str:
    bits: list[str] = []
    if c["season_index"] >= 1.08:
        bits.append(f"mùa cao điểm (chỉ số {c['season_index']:.2f})")
    elif c["season_index"] <= 0.92:
        bits.append(f"mùa thấp điểm (chỉ số {c['season_index']:.2f})")
    if c["competition_multiplier"] <= 0.95:
        bits.append(f"big brand đang sale (cầu x{c['competition_multiplier']:.2f})")
    if c["days_of_stock_left"] <= 7:
        bits.append(f"chỉ còn {c['days_of_stock_left']:.0f} ngày hàng")
    bits.append(f"ROI {c['roi']:.0%}/đồng vốn")
    head = f"Nhập {qty}" + (f"/{c['need_qty']} (thiếu vốn)" if partial else "")
    return f"{head} — " + ", ".join(bits)


def _amplify(value: float, strength: float) -> float:
    """Stretch a multiplier's distance from 1.0. Mirrors restock_planner/channels.py.

    Amplifying the deviation, not the value, pins 1.0 ("ordinary month",
    "nobody on sale") at 1.0 for every case, so cases only diverge where there
    is a signal to react to.
    """
    return max(0.05, 1.0 + (value - 1.0) * strength)


def _measured_volumes(rates: dict[str, float]) -> dict[str, float]:
    """Turn measured orders-per-day into the same volume factor a case supplies.

    A case's `volume` says "this channel sells N times the baseline". Once real
    order rates exist, that ratio can be measured instead of declared: each
    channel is scaled against the mean rate of the channels we actually have
    data for. Shopee at 5.7 orders/day beside Lazada at 0.8 becomes 1.77x and
    0.23x — the same shape the planner already consumes, but earned rather
    than typed in.
    """
    live = {k: v for k, v in (rates or {}).items() if v > 0}
    if not live:
        return {}
    mean = sum(live.values()) / len(live)
    if mean <= 0:
        return {}
    return {k: round(v / mean, 4) for k, v in live.items()}


def _allocate(products, budget, month, season, competition, horizon,
              channel_cases=None, channel_fees=None, measured=None) -> dict:
    """Allocate one shared budget across every (channel, SKU) pair.

    Stock sent to a marketplace warehouse is committed to that channel, so the
    real decision is not just "which SKU" but "which SKU, on which channel" —
    a SKU that moves on Shopee can sit dead on a channel with no traffic. The
    seller has one pot of money, so all pairs compete in a single ranking.

    Existing stock is central, so it is credited to channels in proportion to
    the demand each one generates; a channel expected to sell nothing is
    credited nothing and therefore asks for nothing.
    """
    chan_cfg = _channel_config()
    definitions = chan_cfg["definitions"]
    cases = chan_cfg["cases"]
    active_cases = dict(chan_cfg["default_case"])
    for cid, case_id in (channel_cases or {}).items():
        if cid in definitions and case_id in cases:
            active_cases[cid] = case_id
    fees = {cid: float(definitions[cid].get("commission_pct", 0.0)) for cid in definitions}
    for cid, pct in (channel_fees or {}).items():
        if cid in fees and 0.0 <= float(pct) <= 50.0:
            fees[cid] = float(pct)

    order = [c for c in chan_cfg["order"] if c in definitions]
    candidates = []

    for p in products:
        category = p.get("category", "")
        cost = float(p.get("cost_vnd") or 0)
        price = float(p.get("price_vnd") or 0)
        stock = int(p.get("stock") or 0)
        daily = float(p.get("daily_sales") or 0)
        if cost <= 0 or price <= cost or daily <= 0:
            continue

        prof = season.get(category) or {}
        season_idx = float((prof.get("seasonal_index") or {}).get(month, 1.0))
        comp_mult = float((competition.get(category) or {}).get("demand_multiplier", 1.0))
        baseline = daily * horizon

        # Demand this SKU generates on each channel, under that channel's case.
        per_channel: dict[str, dict] = {}
        for cid in order:
            case = cases.get(active_cases.get(cid, "hot")) or {}
            season_adj = _amplify(season_idx, float(case.get("season", 1.0)))
            trend_adj = _amplify(comp_mult, float(case.get("trend", 1.0)))
            # A synced channel's real order rate outranks the hand-picked case:
            # the case only ever existed because the rate was unknown.
            volume = float((measured or {}).get(cid, case.get("volume", 0.0)))
            factor = volume * season_adj * trend_adj
            per_channel[cid] = {
                "factor": factor, "season_adj": season_adj, "trend_adj": trend_adj,
                "volume": volume,
                "demand": baseline * factor,
            }

        total_demand = sum(v["demand"] for v in per_channel.values())
        for cid in order:
            v = per_channel[cid]
            if v["demand"] <= 0:
                continue  # a dead channel asks for nothing
            # Central stock credited in proportion to the demand it serves.
            stock_share = stock * (v["demand"] / total_demand) if total_demand else 0.0
            need = max(0, math.ceil(v["demand"] - stock_share))
            if need <= 0:
                continue

            fee_pct = fees.get(cid, 0.0)
            net_price = price * (1.0 - fee_pct / 100.0)
            margin = net_price - cost
            if margin <= 0:
                continue  # the platform's cut wipes out the margin
            roi = margin / cost
            daily_ch = daily * v["factor"]
            urgency = _urgency(int(round(stock_share)), daily_ch, horizon)

            candidates.append({
                "sku": p.get("sku", ""), "name": p.get("name", ""),
                "brand": p.get("brand", ""), "category": category,
                "channel": cid, "channel_name": definitions[cid]["name"],
                "price_vnd": int(price), "cost_vnd": int(cost),
                "stock": int(round(stock_share)),
                "daily_sales": round(daily_ch, 2),
                "days_of_stock_left": round(stock_share / daily_ch, 1) if daily_ch else 0.0,
                "season_index": round(season_idx, 3),
                "competition_multiplier": round(comp_mult, 3),
                "baseline_demand": int(round(baseline)),
                "expected_demand": int(round(v["demand"])),
                "need_qty": need,
                "unit_margin_vnd": int(round(margin)),
                "commission_pct": fee_pct,
                "roi": round(roi, 4), "urgency": round(urgency, 2),
                # The channel's demand factor already folds in season and
                # trend, amplified by that channel's case — so ranking on it
                # sends capital to where the goods will actually move.
                "priority": roi * urgency * v["factor"],
                "_key": f"{cid}|{p.get('sku', '')}",
            })

    candidates.sort(key=lambda c: -c["priority"])

    remaining = float(budget)
    ordered: dict[str, int] = {}

    # Pass 1 — capped so the budget spreads across the portfolio; uncapped
    # ROI-greedy would sink everything into one line.
    #
    # The cap is "no single SKU takes more than MAX_SKU_BUDGET_SHARE", and a
    # SKU is now split across channels, so the per-line cap divides by the
    # number of channels actually asking for stock. Without the division, four
    # channels x 25% fills the budget in four lines and the "cap" stops
    # diversifying anything — channels ranked fifth onward get exactly zero
    # even when their demand is identical.
    live_channels = len({c["channel"] for c in candidates}) or 1
    cap_vnd = budget * MAX_SKU_BUDGET_SHARE / live_channels
    for c in candidates:
        qty = min(c["need_qty"], int(cap_vnd // c["cost_vnd"]),
                  int(remaining // c["cost_vnd"]))
        if qty > 0:
            ordered[c["_key"]] = qty
            remaining -= qty * c["cost_vnd"]

    # Pass 2 — spend the remainder on unmet need, same priority order.
    for c in candidates:
        if remaining < c["cost_vnd"]:
            continue
        already = ordered.get(c["_key"], 0)
        gap = c["need_qty"] - already
        if gap <= 0:
            continue
        extra = min(gap, int(remaining // c["cost_vnd"]))
        if extra > 0:
            ordered[c["_key"]] = already + extra
            remaining -= extra * c["cost_vnd"]

    items, skipped = [], []
    for c in candidates:
        qty = ordered.get(c["_key"], 0)
        if qty <= 0:
            skipped.append({
                "sku": c["sku"], "name": c["name"], "category": c["category"],
                "need_qty": c["need_qty"], "cost_vnd": c["cost_vnd"],
                "reason": f"Hết vốn — không đủ tiền nhập cho {c['channel_name']}",
            })
            continue
        partial = qty < c["need_qty"]
        gross = qty * c["price_vnd"]
        items.append({
            **c, "order_qty": qty, "partial": partial,
            "spend_vnd": qty * c["cost_vnd"],
            "expected_revenue_vnd": gross,
            "commission_cost_vnd": int(round(gross * c["commission_pct"] / 100.0)),
            "expected_profit_vnd": qty * c["unit_margin_vnd"],
            "reason": _reason(c, qty, partial),
        })

    spent = sum(i["spend_vnd"] for i in items)
    revenue = sum(i["expected_revenue_vnd"] for i in items)
    profit = sum(i["expected_profit_vnd"] for i in items)
    return {
        "items": items, "skipped": skipped,
        "spent_vnd": int(spent), "remaining_vnd": int(max(0, remaining)),
        "budget_used_pct": round(spent / budget * 100, 1) if budget else 0.0,
        "item_count": len(items), "skipped_count": len(skipped),
        "total_units": sum(i["order_qty"] for i in items),
        "expected_revenue_vnd": int(revenue), "expected_profit_vnd": int(profit),
        "expected_margin_pct": round(profit / revenue * 100, 1) if revenue else 0.0,
        "roi_pct": round(profit / spent * 100, 1) if spent else 0.0,
    }


def _channel_results(plan: dict, month: int, season: dict, competition: dict,
                     channel_cases=None, channel_fees=None, measured=None) -> list[dict]:
    """Roll the allocation up per channel, and say what to do about each."""
    cfg = _channel_config()
    definitions, cases = cfg["definitions"], cfg["cases"]
    active = dict(cfg["default_case"])
    for cid, case_id in (channel_cases or {}).items():
        if cid in definitions and case_id in cases:
            active[cid] = case_id
    fees = {cid: float(definitions[cid].get("commission_pct", 0.0)) for cid in definitions}
    for cid, pct in (channel_fees or {}).items():
        if cid in fees and 0.0 <= float(pct) <= 50.0:
            fees[cid] = float(pct)

    by_channel: dict[str, list[dict]] = {}
    for i in plan["items"]:
        by_channel.setdefault(i["channel"], []).append(i)
    spent_total = plan["spent_vnd"] or 1

    # Averaged across categories so one channel figure summarises the month.
    season_avg = (
        sum((p.get("seasonal_index") or {}).get(month, 1.0) for p in season.values())
        / len(season) if season else 1.0
    )
    comp_avg = (
        sum(float(c.get("demand_multiplier", 1.0)) for c in competition.values())
        / len(competition) if competition else 1.0
    )

    rows = []
    for cid in cfg["order"]:
        if cid not in definitions:
            continue
        d = definitions[cid]
        case_id = active.get(cid, "hot")
        case = cases.get(case_id) or {}
        season_adj = _amplify(season_avg, float(case.get("season", 1.0)))
        trend_adj = _amplify(comp_avg, float(case.get("trend", 1.0)))
        from_orders = cid in (measured or {})
        volume = float((measured or {}).get(cid, case.get("volume", 0.0)))
        factor = volume * season_adj * trend_adj

        mine = by_channel.get(cid, [])
        spend = sum(i["spend_vnd"] for i in mine)
        revenue = sum(i["expected_revenue_vnd"] for i in mine)
        profit = sum(i["expected_profit_vnd"] for i in mine)
        commission = sum(i.get("commission_cost_vnd", 0) for i in mine)
        demand = sum(i["expected_demand"] for i in mine)
        qty = sum(i["order_qty"] for i in mine)

        # Measured presence — `listings: 0` everywhere means the platform is
        # not visible to Google Shopping at all, which is a limit of the
        # measurement, not evidence the platform is empty.
        measured_rows = []
        for category, row in (cfg["market"] or {}).items():
            m = (row.get("channels") or {}).get(cid)
            if m:
                measured_rows.append({
                    "category": category, "listings": m.get("listings", 0),
                    "share_pct": m.get("share_pct", 0.0),
                    "median_price_vnd": m.get("median_price_vnd", 0),
                    "on_sale": m.get("on_sale", 0),
                    "avg_discount": m.get("avg_discount", 0.0),
                })
        measurable = bool(d.get("source_match")) and any(
            r["listings"] for r in measured_rows
        )

        if volume <= 0:
            verdict = ("Không nhập — kênh chưa ra đơn. Nhập thêm chỉ đọng vốn; "
                       "cần sửa kênh (giá, ảnh, quảng cáo) trước khi rót hàng.")
        elif not mine:
            verdict = "Không được chia vốn — kênh khác cho vòng quay vốn tốt hơn ở tháng này."
        elif factor >= 1.5:
            verdict = f"Ưu tiên rót hàng — cầu gấp {factor:.1f} lần mức nền."
        elif factor <= 0.6:
            verdict = f"Rót dè chừng — cầu chỉ bằng {factor:.0%} mức nền."
        else:
            verdict = "Rót ở mức bình thường."

        rows.append({
            "channel": cid, "name": d.get("name", cid),
            "kind": d.get("kind", "marketplace"),
            "case": case_id, "case_label": case.get("label", case_id),
            "case_desc": case.get("desc", ""),
            "commission_pct": fees.get(cid, 0.0),
            "volume_factor": round(volume, 3),
            "season_adj": round(season_adj, 3),
            "trend_adj": round(trend_adj, 3),
            "demand_factor": round(factor, 3),
            "expected_demand": int(demand),
            "order_qty": int(qty), "spend_vnd": int(spend),
            "expected_revenue_vnd": int(revenue),
            "expected_profit_vnd": int(profit),
            "commission_cost_vnd": int(commission),
            "budget_share_pct": round(spend / spent_total * 100, 1),
            "sku_count": len(mine),
            "verdict": verdict,
            "measured": measured_rows,
            "measurable": measurable,
            # True once the channel's own order history drives the number, so
            # the UI can stop calling it an assumption.
            "volume_from_orders": from_orders,
        })
    return rows


def _outlook(month: int, season: dict, competition: dict) -> list[dict]:
    """Is each category's revenue margin widening or shrinking this month?"""
    prev_month = 12 if month == 1 else month - 1
    rows = []
    for category, prof in season.items():
        idx = prof["seasonal_index"]
        now = idx.get(month, 1.0)
        prev = idx.get(prev_month, 1.0)
        mult = float((competition.get(category) or {}).get("demand_multiplier", 1.0))
        combined = now * mult

        if combined >= 1.05:
            outlook, advice = "expand", "Biên doanh thu đang mở — tăng nhập"
        elif combined <= 0.95:
            outlook, advice = "contract", "Biên doanh thu đang co — giảm nhập, giữ vốn"
        else:
            outlook, advice = "hold", "Doanh thu đi ngang — giữ mức nhập hiện tại"

        rows.append({
            "category": category,
            "season_index": round(now, 3), "season_index_prev": round(prev, 3),
            "season_change_pct": round((now - prev) / prev * 100, 1) if prev else 0.0,
            "momentum": prof.get("momentum", 0.0),
            "direction": prof.get("direction", "stable"),
            "competition_multiplier": mult,
            "competition_level": (competition.get(category) or {}).get("level", "low"),
            "combined_factor": round(combined, 3),
            "outlook": outlook, "advice": advice,
            "peak_month": prof.get("peak_month"), "low_month": prof.get("low_month"),
            "monthly_index": [round(idx.get(m, 1.0), 3) for m in range(1, 13)],
        })
    return sorted(rows, key=lambda r: -r["combined_factor"])


def _summary(plan: dict, month: int, outlook: list[dict], scenario: bool) -> str:
    if not plan["items"]:
        return (f"Tháng {month}: vốn không đủ nhập mặt hàng nào — "
                f"{plan['skipped_count']} SP đang cần hàng.")
    top = outlook[0] if outlook else None
    head = (f"Tháng {month}: nhập {plan['total_units']} sản phẩm thuộc "
            f"{plan['item_count']} mã, dùng {plan['budget_used_pct']:.0f}% vốn, "
            f"lãi dự kiến {plan['expected_profit_vnd']:,}₫ (ROI {plan['roi_pct']:.0f}%).")
    if top:
        head += (f" Ngành đáng đổ vốn nhất: {top['category']} "
                 f"(hệ số {top['combined_factor']:.2f} — {top['advice'].lower()}).")
    if plan["skipped_count"]:
        head += f" {plan['skipped_count']} dòng phải bỏ qua vì hết vốn."
    if scenario:
        head += " [Kịch bản giả định, không phải số đo thật]"
    return head


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #

async def build_plan(
    req: RestockPlanRequest, synced_rates: dict[str, float] | None = None
) -> RestockPlanResponse:
    snap = _snapshot()
    meta = snap.get("meta", {})
    season = _season_profiles()
    month = req.month or dt.date.today().month
    sensitivity = (
        req.competition_sensitivity
        if req.competition_sensitivity is not None
        else DEFAULT_SENSITIVITY
    )

    if req.categories:
        season = {c: p for c, p in season.items() if c in req.categories}

    brands = _brand_rows()
    live = False
    if req.refresh_live:
        fresh = await _fetch_live_brands()
        if fresh:
            brands, live = fresh, True

    competition = _aggregate(brands, sensitivity)
    scenario = req.scenario_pressure is not None
    if scenario:
        # Scale the measured reading rather than replacing it, so the scenario
        # keeps the real spread between categories (see _scenario).
        competition = _scenario(competition, req.scenario_pressure or 0.0, sensitivity)

    products = commerce_store.all_products()
    if req.categories:
        products = [p for p in products if p.get("category") in req.categories]

    measured_volumes = _measured_volumes(synced_rates or {})
    plan = _allocate(products, req.budget_vnd, month, season, competition,
                     req.horizon_days, req.channel_cases, req.channel_fees,
                     measured_volumes)
    outlook = _outlook(month, season, competition)
    channel_rows = _channel_results(plan, month, season, competition,
                                    req.channel_cases, req.channel_fees,
                                    measured_volumes)

    # Built as a plain dict and validated in one go: the allocation helpers all
    # deal in dicts, and Pydantic coerces each nested one into its model here.
    # Passing them as keyword arguments works identically at runtime but reads
    # to a type checker as "dict given where model expected" at five call sites.
    payload: dict[str, object] = {
        "month": month,
        "horizon_days": req.horizon_days,
        "budget_vnd": int(req.budget_vnd),
        **{k: plan[k] for k in (
            "spent_vnd", "remaining_vnd", "budget_used_pct", "item_count",
            "skipped_count", "total_units", "expected_revenue_vnd",
            "expected_profit_vnd", "expected_margin_pct", "roi_pct",
            "items", "skipped",
        )},
        "outlook": outlook,
        "channels": channel_rows,
        "channel_market_fetched_at": _channel_config().get("market_fetched_at"),
        "competition": list(competition.values()),
        "brands": sorted(brands, key=lambda b: -b["pressure"]),
        "summary": _summary(plan, month, outlook, scenario),
        "data_source": meta.get("source", "SerpApi — Google Trends + Google Shopping"),
        "trends_window": meta.get("trends_window"),
        "weeks_of_history": meta.get("weeks_of_history", 0),
        "trends_fetched_at": meta.get("trends_fetched_at"),
        "brand_sale_fetched_at": meta.get("brand_sale_fetched_at"),
        "live_refresh": live,
        "scenario": scenario,
        "competition_sensitivity": sensitivity,
    }
    return RestockPlanResponse.model_validate(payload)
