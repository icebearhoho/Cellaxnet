"""Smart Restock Planner service — turn budget + market signals into quantities.

Market snapshot (`app/data/restock_market.json`) holds the two measured signals:
a 12-month seasonal index per category learned from 5 years of Google Trends,
and the big brands' current sale pressure read off Google Shopping. It is
produced by the offline layer in `restock_planner/` and committed so the API
answers instantly and works with no network — the live refresh below is an
upgrade on top, never a requirement (same contract as supply_news).

Allocation lives here and only here. An earlier offline mirror of these
formulas in restock_planner/ drifted, so the folder now owns only what it is
good at — fetching and modelling market signals — and the money decision has a single
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


def channel_config() -> dict:
    """Return the shared marketplace definitions used by pricing.

    Restock allocation is intentionally store-wide now, but dynamic pricing
    still needs the channel commission rates. Keeping those rates sourced from
    the market snapshot avoids copying business rules into another service.
    """
    channels = _snapshot().get("channels") or {}
    definitions = channels.get("definitions") or {}
    cases = channels.get("cases") or {}
    return {
        "definitions": definitions,
        "cases": cases,
        "default_case": channels.get("default_case") or {},
        "order": channels.get("order") or list(definitions),
        "case_order": channels.get("case_order") or list(cases),
        "market": channels.get("market") or {},
        "market_fetched_at": channels.get("market_fetched_at"),
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


def _allocate(products, budget, month, season, competition, horizon) -> dict:
    """Allocate the budget once per SKU from measured shop demand.

    The current planner UI asks a store-level question: what should the seller
    buy for the next ``horizon`` days? Older code silently split every SKU over
    four channel scenarios even after those controls were removed from the UI.
    That multiplied the same demand several times and made quantities depend on
    assumptions the seller never chose.

    A SKU now appears once. Its baseline is fulfilled units/day from the shop
    order history, adjusted only by Google Trends seasonality and measured
    Google Shopping competition. Channel allocation can be reintroduced when
    real per-SKU marketplace orders exist; it must not be guessed here.
    """
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
        demand_factor = season_idx * comp_mult
        expected_demand = math.ceil(baseline * demand_factor)
        need = max(0, expected_demand - stock)
        if need <= 0:
            continue

        # There is no defensible platform fee until a SKU is assigned to a real
        # channel. Keep this as gross contribution instead of inventing a split
        # and pretending that the result is net profit.
        margin = price - cost
        if margin <= 0:
            continue
        roi = margin / cost
        urgency = _urgency(stock, daily, horizon)

        candidates.append({
            "sku": p.get("sku", ""), "name": p.get("name", ""),
            "brand": p.get("brand", ""), "category": category,
            "channel": "own", "channel_name": "Toàn cửa hàng",
            "price_vnd": int(price), "cost_vnd": int(cost),
            "stock": stock,
            "daily_sales": round(daily, 4),
            "days_of_stock_left": round(stock / daily, 1) if daily else 0.0,
            "season_index": round(season_idx, 3),
            "competition_multiplier": round(comp_mult, 3),
            "baseline_demand": int(round(baseline)),
            "expected_demand": expected_demand,
            "need_qty": need,
            "unit_margin_vnd": int(round(margin)),
            "commission_pct": 0.0,
            "roi": round(roi, 4), "urgency": round(urgency, 2),
            "priority": roi * urgency * demand_factor,
            "_key": p.get("sku", ""),
        })

    candidates.sort(key=lambda c: -c["priority"])

    remaining = float(budget)
    ordered: dict[str, int] = {}

    # Fund the independently ranked needs in order. There is deliberately no
    # hidden "x% per SKU" cap: such a cap is a purchasing policy, not measured
    # store or market data, and previously made the answer change with an
    # unexplained constant.
    for c in candidates:
        qty = min(c["need_qty"], int(remaining // c["cost_vnd"]))
        if qty > 0:
            ordered[c["_key"]] = qty
            remaining -= qty * c["cost_vnd"]

    items, skipped = [], []
    for c in candidates:
        qty = ordered.get(c["_key"], 0)
        if qty <= 0:
            skipped.append({
                "sku": c["sku"], "name": c["name"], "category": c["category"],
                "need_qty": c["need_qty"], "cost_vnd": c["cost_vnd"],
                "reason": "Hết vốn — chưa đủ tiền nhập mã này",
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
    unfunded = sum(
        (c["need_qty"] - ordered.get(c["_key"], 0)) * c["cost_vnd"]
        for c in candidates
    )
    recommended_budget = spent + unfunded
    budget_status = "insufficient" if unfunded > 0 else (
        "surplus" if remaining > 0 else "fully_funded"
    )
    return {
        "items": items, "skipped": skipped,
        "spent_vnd": int(spent), "remaining_vnd": int(max(0, remaining)),
        "recommended_budget_vnd": int(recommended_budget),
        "unfunded_vnd": int(unfunded), "budget_status": budget_status,
        "budget_used_pct": round(spent / budget * 100, 1) if budget else 0.0,
        "item_count": len(items), "skipped_count": len(skipped),
        "total_units": sum(i["order_qty"] for i in items),
        "expected_revenue_vnd": int(revenue), "expected_profit_vnd": int(profit),
        "expected_margin_pct": round(profit / revenue * 100, 1) if revenue else 0.0,
        "roi_pct": round(profit / spent * 100, 1) if spent else 0.0,
    }


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
        if plan["unfunded_vnd"]:
            return ("Ngân sách hiện tại chưa đủ để nhập mã ưu tiên đầu tiên. "
                    f"Còn thiếu {plan['unfunded_vnd']:,}₫ để đáp ứng toàn bộ nhu cầu.")
        return "Tồn kho hiện tại đã đủ cho thời gian đã chọn; chưa cần nhập thêm."
    top = outlook[0] if outlook else None
    if plan["budget_status"] == "surplus":
        head = (f"Kế hoạch cần {plan['spent_vnd']:,}₫ để đủ hàng trong thời gian đã chọn; "
                f"còn lại {plan['remaining_vnd']:,}₫, không cần nhập dư chỉ để dùng hết vốn. "
                f"Nên nhập {plan['total_units']} sản phẩm thuộc {plan['item_count']} mã.")
    else:
        head = (f"Với ngân sách này, nên nhập {plan['total_units']} sản phẩm thuộc "
                f"{plan['item_count']} mã.")
    if top:
        head += f" Nhóm nên ưu tiên: {top['category']} — {top['advice'].lower()}."
    if plan["unfunded_vnd"]:
        head += (f" Còn thiếu {plan['unfunded_vnd']:,}₫ để đáp ứng toàn bộ "
                 "nhu cầu được dự báo.")
    return head


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #

async def build_plan(req: RestockPlanRequest) -> RestockPlanResponse:
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

    # Recompute velocity from exact fulfilled order lines instead of trusting
    # ``product['daily_sales']``. The shared demo catalog floors that field at
    # 0.1 for visual features, which would otherwise create purchasing demand
    # for products with zero completed sales.
    products = []
    for raw in commerce_store.all_products():
        stats = commerce_store.product_sales_stats(raw["id"], days=45)
        products.append({
            **raw,
            "daily_sales": stats["units_sold"] / stats["days"],
        })
    if req.categories:
        products = [p for p in products if p.get("category") in req.categories]

    plan = _allocate(products, req.budget_vnd, month, season, competition,
                     req.horizon_days)
    outlook = _outlook(month, season, competition)
    # The recommendation is store-wide. Returning the old scenario rows here
    # would expose guessed channel figures even though quantities no longer use
    # them.
    channel_rows: list[dict] = []

    # Built as a plain dict and validated in one go: the allocation helpers all
    # deal in dicts, and Pydantic coerces each nested one into its model here.
    # Passing them as keyword arguments works identically at runtime but reads
    # to a type checker as "dict given where model expected" at five call sites.
    payload: dict[str, object] = {
        "month": month,
        "horizon_days": req.horizon_days,
        "budget_vnd": int(req.budget_vnd),
        **{k: plan[k] for k in (
            "spent_vnd", "remaining_vnd", "recommended_budget_vnd",
            "unfunded_vnd", "budget_status", "budget_used_pct", "item_count",
            "skipped_count", "total_units", "expected_revenue_vnd",
            "expected_profit_vnd", "expected_margin_pct", "roi_pct",
            "items", "skipped",
        )},
        "outlook": outlook,
        "channels": channel_rows,
        "channel_market_fetched_at": None,
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
        "shop_data_source": "Dữ liệu shop demo: đơn hợp lệ, tồn kho, giá vốn và giá bán",
        "shop_data_as_of": commerce_store.shop_profile().get("data_as_of"),
        "sales_history_days": 45,
        "profit_basis": "gross_before_platform_and_operating_costs",
    }
    return RestockPlanResponse.model_validate(payload)
