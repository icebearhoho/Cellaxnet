"""Track 2, Đề 3 — Market Intelligence service.

Heuristic core (deterministic, margin-safe):
- competitor effective price = list * (1 - discount%)
- price floor = cost / (1 - min_margin%)  → guarantees margin-on-price >=
  min_margin% (never recommend below this)
- position = where our current price sits vs the competitor's effective price
- action: if the competitor is materially cheaper, undercut *if* we can stay
  above the floor, else differentiate; near parity → hold; we're cheaper → hold.

The strategic narrative (`reasoning`) runs on the LLM with a templated fallback.
"""

from __future__ import annotations

from statistics import median
from typing import Any, Literal, cast

from app.schemas.market import (
    CompetitorCompare,
    MarketRequest,
    MarketResponse,
    MarketScanRequest,
    MarketScanResponse,
)
from app.services import commerce_store as store
from app.services.llm_reasoning import reason_json

_PositionLit = Literal["cheaper", "parity", "pricier"]
_ActionLit = Literal[
    "hold", "match_price", "undercut", "differentiate", "protect_margin"
]


def _round100(v: float) -> int:
    return int(round(v / 100.0) * 100)


def _heuristic(req: MarketRequest) -> dict:
    eff = req.competitor_price_vnd * (1 - req.competitor_discount_pct / 100.0)
    # Floor is the lowest price that still yields the requested *margin-on-price*
    # (profit / revenue), i.e. (floor - cost) / floor == min_margin_pct. This is
    # the same basis as `margin_pct_at_recommended`, so the reported margin never
    # dips below what the seller asked for. (min_margin_pct is capped at 90 in the
    # schema, so the denominator can't hit zero.)
    denom = max(1 - req.min_margin_pct / 100.0, 0.01)
    floor = req.our_cost_vnd / denom
    eff_i, floor_i = _round100(eff), _round100(floor)

    if req.our_price_vnd < eff * 0.97:
        position = "cheaper"
    elif req.our_price_vnd > eff * 1.03:
        position = "pricier"
    else:
        position = "parity"

    # Decide action + recommended price.
    if position == "pricier":
        target = eff * 0.98  # just under the competitor to win the click
        if target >= floor:
            action, rec = "undercut", target
        else:
            action, rec = "differentiate", float(req.our_price_vnd)
    elif position == "parity":
        action, rec = "hold", float(req.our_price_vnd)
    else:  # we're already cheaper
        action, rec = "hold", float(req.our_price_vnd)

    rec_i = max(_round100(rec), floor_i)
    if rec_i > req.our_price_vnd:
        # No action may be paired with a different recommended number while
        # claiming to keep the current price.
        # When the current price violates the requested margin, restoring the
        # floor is the primary action regardless of competitor position.
        action = "protect_margin"
    margin = (rec_i - req.our_cost_vnd) / rec_i * 100.0 if rec_i > 0 else 0.0
    return {
        "position": position,
        "recommended_action": action,
        "recommended_price_vnd": rec_i,
        "price_floor_vnd": floor_i,
        "margin_pct_at_recommended": round(margin, 1),
        "competitor_effective_price_vnd": eff_i,
    }


_SYSTEM = (
    "You are a pricing & competitive-strategy analyst for a small Vietnamese "
    "e-commerce seller (fashion & cosmetics). Given our product vs a competitor, "
    "and a pre-computed margin-safe recommendation, write ONE short, concrete "
    "Vietnamese paragraph (2-3 sentences) advising the seller. Do NOT change the "
    "numbers. Reply as JSON: {\"reasoning\": \"...\"}"
)


def _fallback_reasoning(req: MarketRequest, h: dict) -> str:
    action_vi = {
        "hold": "giữ giá hiện tại",
        "match_price": "hạ về ngang đối thủ",
        "undercut": f"hạ nhẹ xuống {h['recommended_price_vnd']:,}₫ (dưới đối thủ)",
        "differentiate": "giữ giá và cạnh tranh bằng chất lượng/ưu đãi thay vì phá giá",
        "protect_margin": f"tăng lên sàn lợi nhuận {h['recommended_price_vnd']:,}₫",
    }[h["recommended_action"]]
    return (
        f"{req.competitor_name} đang bán ở mức thực tế {h['competitor_effective_price_vnd']:,}₫; "
        f"ta đang ở thế '{h['position']}'. Đề xuất: {action_vi} — vẫn giữ biên "
        f"{h['margin_pct_at_recommended']}% (sàn an toàn {h['price_floor_vnd']:,}₫)."
    )


async def analyze_market(req: MarketRequest) -> MarketResponse:
    h = _heuristic(req)
    data = await reason_json(
        _SYSTEM,
        (
            f"Our product: {req.our_product} ({req.category}), price {req.our_price_vnd:,}₫, "
            f"cost {req.our_cost_vnd:,}₫.\n"
            f"Competitor: {req.competitor_name}, list {req.competitor_price_vnd:,}₫, "
            f"discount {req.competitor_discount_pct}% → effective {h['competitor_effective_price_vnd']:,}₫.\n"
            f"Pre-computed recommendation: {h['recommended_action']} at "
            f"{h['recommended_price_vnd']:,}₫ (margin {h['margin_pct_at_recommended']}%, "
            f"floor {h['price_floor_vnd']:,}₫). Explain why."
        ),
        label="market",
    )
    reasoning = (data or {}).get("reasoning") if data else None
    return MarketResponse(
        position=cast(_PositionLit, h["position"]),
        recommended_action=cast(_ActionLit, h["recommended_action"]),
        recommended_price_vnd=h["recommended_price_vnd"],
        price_floor_vnd=h["price_floor_vnd"],
        margin_pct_at_recommended=h["margin_pct_at_recommended"],
        competitor_effective_price_vnd=h["competitor_effective_price_vnd"],
        reasoning=(reasoning or "").strip() or _fallback_reasoning(req, h),
    )


async def scan_market(req: MarketScanRequest, narrate: bool = True) -> MarketScanResponse:
    """Multi-competitor scan grounded in the store: market position + margin-safe
    recommendation against the most aggressive competitor."""
    p = store.find_product(req.query)
    if not p:
        return MarketScanResponse(
            found=False, product_name="", sku="", our_price_vnd=0, competitors=[],
            market_min_vnd=0, market_median_vnd=0, market_max_vnd=0, our_rank=0, of_total=0,
            recommended_price_vnd=0, price_floor_vnd=0, margin_pct_at_recommended=0.0,
            reasoning=f"Không tìm thấy sản phẩm khớp với '{req.query}'.",
        )
    our = p["price_vnd"]
    comps: list[CompetitorCompare] = []
    eff_prices: list[int] = []
    for c in p["competitors"]:
        eff = int(round(c["price_vnd"] * (1 - c["discount_pct"] / 100.0) / 100) * 100)
        eff_prices.append(eff)
        pos = "cheaper" if eff < our * 0.97 else ("pricier" if eff > our * 1.03 else "parity")
        comps.append(CompetitorCompare(
            name=c["name"], price_vnd=c["price_vnd"], effective_price_vnd=eff,
            discount_pct=c["discount_pct"], position_vs_us=cast(_PositionLit, pos),
            gap_pct=round((eff - our) / our * 100, 1),
        ))
    prices = [our, *eff_prices]
    our_rank = sum(1 for x in eff_prices if x < our) + 1

    cheapest = min(p["competitors"], key=lambda c: c["price_vnd"] * (1 - c["discount_pct"] / 100.0))
    h = _heuristic(MarketRequest(
        our_product=p["name"], category=cast(Any, p["category"]), our_price_vnd=our,
        our_cost_vnd=p["cost_vnd"], competitor_name=cheapest["name"],
        competitor_price_vnd=cheapest["price_vnd"], competitor_discount_pct=cheapest["discount_pct"],
    ))
    data = await reason_json(
        _SYSTEM,
        f"Product {p['name']} ours {our:,}₫. Competitors (effective): "
        f"{[(c.name, c.effective_price_vnd) for c in comps]}. Our rank {our_rank}/{len(prices)} "
        f"(1=cheapest). Recommended {h['recommended_action']} at {h['recommended_price_vnd']:,}₫ "
        f"(margin {h['margin_pct_at_recommended']}%). Advise the seller.",
        label="market_scan",
    ) if narrate else None
    reasoning = (data or {}).get("reasoning") if data else None
    if not (reasoning and reasoning.strip()):
        reasoning = (f"Trên {len(prices)} nhà bán, giá ta xếp hạng {our_rank} (1=rẻ nhất). "
                     f"Đề xuất {h['recommended_action']} về {h['recommended_price_vnd']:,}₫ "
                     f"(biên {h['margin_pct_at_recommended']}%).")
    return MarketScanResponse(
        found=True, product_name=p["name"], sku=p["sku"], our_price_vnd=our, competitors=comps,
        market_min_vnd=min(prices), market_median_vnd=int(median(prices)), market_max_vnd=max(prices),
        our_rank=our_rank, of_total=len(prices),
        recommended_price_vnd=h["recommended_price_vnd"], price_floor_vnd=h["price_floor_vnd"],
        margin_pct_at_recommended=h["margin_pct_at_recommended"],
        reasoning=reasoning.strip(),
    )
