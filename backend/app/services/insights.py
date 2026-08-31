"""Scorers for #01 Review Sentiment, #05 Fake Review, #02 Dynamic Pricing,
#04 Churn, #10 Return, #15 Regret, #08 Inventory Alert.

#01 and #05 are genuine language tasks, so they run on the real LLM
(OpenAI when configured — see factory.get_llm_client) with a deterministic
heuristic fallback if the LLM is unavailable/errors, so the demo never breaks.
The numeric scorers (pricing/churn/return/regret/inventory) stay heuristic —
they are formula-based, not language tasks; the offline modeling layer
(dynamic_pricing/, customer_churn/) uses the same formulas.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, cast

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.insights import (
    ChurnRequest,
    ChurnResponse,
    FakeReviewRequest,
    FakeReviewResponse,
    InventoryAlertRequest,
    InventoryAlertResponse,
    PriceSource,
    PricingRequest,
    PricingResponse,
    RegretRequest,
    RegretResponse,
    ReturnRequest,
    ReturnResponse,
    SentimentRequest,
    SentimentResponse,
)
from app.services import btc_market
from app.services import commerce_store as store
from app.services.genai.base import LlmMessage
from app.services.genai.factory import get_llm_client
from app.services.restock import channel_config

log = get_logger("app.services.insights")

# Aliases matching the response schemas' Literal fields (for cast narrowing —
# the values are validated at runtime by the branch logic / Pydantic).
_SentimentLit = Literal["positive", "neutral", "negative"]
_RiskBandLit = Literal["low", "medium", "high"]
_AlertLevelLit = Literal["none", "watch", "urgent"]


def _llm_ready() -> bool:
    """True if a real (non-mock) LLM is configured."""
    return not settings.DEMO_MODE and bool(settings.OPENAI_API_KEY or settings.GEMINI_API_KEY)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start:end + 1] if start != -1 and end != -1 else raw)


# English + Vietnamese cue words (the seller platform sees both).
_POS = {
    "love", "great", "excellent", "perfect", "amazing", "comfortable", "soft",
    "recommend", "happy", "beautiful", "quality", "fast", "breathable", "worth",
    "tuyệt", "đẹp", "tốt", "thích", "hài lòng", "mượt", "chuẩn", "nhanh", "ưng",
}
_NEG = {
    "bad", "poor", "terrible", "disappointed", "cheap", "broke", "broken", "thin",
    "refund", "return", "smell", "fake", "worst", "damaged", "late", "wrong",
    "tệ", "dởm", "kém", "thất vọng", "rách", "hỏng", "chậm", "lừa", "trả hàng", "mỏng",
}
_GENERIC = {
    "highly recommend", "best ever", "best purchase", "love it", "amazing quality",
    "great quality", "works perfectly", "highly recommended", "so good", "perfect",
}


def _words(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", text.lower(), flags=re.UNICODE)


def _analyze_sentiment_heuristic(req: SentimentRequest) -> SentimentResponse:
    low = req.text.lower()
    words = set(_words(req.text))
    pos = sum(1 for w in _POS if (" " in w and w in low) or w in words)
    neg = sum(1 for w in _NEG if (" " in w and w in low) or w in words)

    score = pos - neg
    if req.rating is not None:  # rating is a strong prior when present
        score += {1: -2, 2: -1, 3: 0, 4: 1, 5: 2}[req.rating]

    if score > 1:
        s, reason = "positive", f"Tín hiệu tích cực ({pos}) nhiều hơn tín hiệu tiêu cực ({neg})."
    elif score < -1:
        s, reason = "negative", f"Đánh giá có nhiều tín hiệu tiêu cực ({neg})."
    else:
        s, reason = "neutral", "Tín hiệu còn lẫn lộn hoặc chủ yếu mô tả thông tin thực tế."

    confidence = min(0.95, 0.5 + 0.12 * abs(score))
    return SentimentResponse(sentiment=cast(_SentimentLit, s), confidence=round(confidence, 2), reason=reason)


def _detect_fake_heuristic(req: FakeReviewRequest) -> FakeReviewResponse:
    low = req.text.lower()
    words = _words(req.text)
    signals: list[str] = []

    generic_hits = [g for g in _GENERIC if g in low]
    if generic_hits:
        signals.append(f"Cụm từ quá chung chung: {', '.join(generic_hits[:2])}")
    if len(words) < 6:
        signals.append("Nội dung rất ngắn, không có chi tiết về sản phẩm")
    if low.count("!") >= 3:
        signals.append("Dùng quá nhiều dấu chấm than")
    # repetition of the same token (hollow enthusiasm)
    if words and max((words.count(w) for w in set(words)), default=0) >= 3:
        signals.append("Lặp lại từ ngữ")
    # 5★ + purely generic praise is a classic CG pattern
    specifics = any(k in low for k in (
        "fit", "size", "fabric", "color", "colour", "wash", "material", "scent",
        "smell", "delivery", "ship", "vải", "size", "màu", "giao", "chất liệu",
    ))
    if not specifics:
        signals.append("Không có chi tiết cụ thể về chất liệu, mùi hương hoặc giao hàng")

    score = len(signals) - (1 if specifics else 0)
    is_fake = score >= 2
    confidence = min(0.95, 0.5 + 0.13 * score) if is_fake else min(0.9, 0.5 + 0.1 * (2 - score))
    reason = (
        "Có nhiều dấu hiệu bất thường nhưng thiếu chi tiết cụ thể." if is_fake
        else "Nội dung có chi tiết cụ thể hoặc cách diễn đạt cân bằng."
    )
    return FakeReviewResponse(
        is_fake=is_fake, confidence=round(max(0.5, confidence), 2),
        signals=signals or ["Không có dấu hiệu giả mạo rõ ràng"], reason=reason,
    )


# ---------------------------------------------------------------------------
# #01 / #05 — LLM-primary (OpenAI), heuristic fallback.
# These are language-understanding tasks, so the real model leads; if it is
# unavailable (DEMO_MODE, no key, timeout, bad JSON) we fall back to the
# deterministic scorers above so the seller app always gets a live answer.
# ---------------------------------------------------------------------------
_SENTIMENT_SYSTEM = (
    "You are a precise product-review sentiment classifier for an e-commerce "
    "seller dashboard (fashion & cosmetics). Read the review and the star "
    "rating (if given) and decide the overall sentiment. Reply with ONLY a "
    "compact JSON object, no prose:\n"
    '{"sentiment": "positive|neutral|negative", "confidence": 0.0-1.0, '
    '"reason": "one short sentence"}\n'
    "Weigh the star rating heavily when present. 'neutral' is for mixed or "
    "purely factual reviews. The seller dashboard is Vietnamese-only. Always "
    "write reason in Vietnamese, even when the review itself is English."
)

_FAKE_SYSTEM = (
    "You are a fake/computer-generated review detector for an e-commerce "
    "seller dashboard. Genuine reviews mention concrete specifics (fit, size, "
    "fabric, colour, scent, delivery). Fake ones are generic, repetitive, "
    "over-enthusiastic, and lack product detail. Reply with ONLY a compact "
    "JSON object, no prose:\n"
    '{"is_fake": true|false, "confidence": 0.0-1.0, '
    '"signals": ["short phrase", ...], "reason": "one short sentence"}\n'
    "The seller dashboard is Vietnamese-only. Always write reason and every "
    "signal in Vietnamese, even when the review itself is English."
)


async def analyze_sentiment(req: SentimentRequest) -> SentimentResponse:
    """#01 — OpenAI-backed sentiment with heuristic fallback."""
    if not _llm_ready():
        return _analyze_sentiment_heuristic(req)
    try:
        rating = f"Star rating: {req.rating}/5.\n" if req.rating is not None else ""
        resp = await get_llm_client().chat(
            [
                LlmMessage(role="system", content=_SENTIMENT_SYSTEM),
                LlmMessage(role="user", content=f"{rating}Review: {req.text}"),
            ],
            temperature=0.0,
            max_tokens=200,
        )
        data = _parse_json(resp.content)
        sentiment = str(data.get("sentiment", "")).lower()
        if sentiment not in {"positive", "neutral", "negative"}:
            raise ValueError(f"bad sentiment: {sentiment!r}")
        conf = float(data.get("confidence", 0.7))
        return SentimentResponse(
            sentiment=cast(_SentimentLit, sentiment),
            confidence=round(min(0.99, max(0.0, conf)), 2),
            reason=str(data.get("reason", "")).strip() or "Đã phân loại nội dung đánh giá.",
        )
    except Exception as exc:  # noqa: BLE001 — any LLM failure falls back
        log.warning("insights.sentiment.llm_fallback", error=str(exc))
        return _analyze_sentiment_heuristic(req)


async def detect_fake(req: FakeReviewRequest) -> FakeReviewResponse:
    """#05 — OpenAI-backed fake-review detection with heuristic fallback."""
    if not _llm_ready():
        return _detect_fake_heuristic(req)
    try:
        rating = f"Star rating: {req.rating}/5.\n" if req.rating is not None else ""
        resp = await get_llm_client().chat(
            [
                LlmMessage(role="system", content=_FAKE_SYSTEM),
                LlmMessage(role="user", content=f"{rating}Review: {req.text}"),
            ],
            temperature=0.0,
            max_tokens=250,
        )
        data = _parse_json(resp.content)
        is_fake = bool(data.get("is_fake", False))
        conf = float(data.get("confidence", 0.7))
        signals = [str(s).strip() for s in data.get("signals", []) if str(s).strip()]
        return FakeReviewResponse(
            is_fake=is_fake,
            confidence=round(min(0.99, max(0.5, conf)), 2),
            signals=signals or (["Có dấu hiệu nội dung được tạo tự động"] if is_fake else ["Nội dung có vẻ tự nhiên"]),
            reason=str(data.get("reason", "")).strip() or "Đã kiểm tra độ đáng tin của đánh giá.",
        )
    except Exception as exc:  # noqa: BLE001 — any LLM failure falls back
        log.warning("insights.fake.llm_fallback", error=str(exc))
        return _detect_fake_heuristic(req)


# ---------------------------------------------------------------------------
# #02 Dynamic Pricing — comps-median baseline (same idea as
# dynamic_pricing/src/02_recommend.py, using the demo catalog as comps).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _CostFloor:
    """The lowest price that still pays the seller, and what it is made of."""

    floor: int
    channel_name: str | None
    commission_pct: float


def _cost_floor(req: PricingRequest) -> _CostFloor | None:
    """Cheapest price whose profit is `min_margin_pct` of the *sticker price*.

    Margin here is profit over the price the buyer pays, the same basis
    market.py's floor uses, so both features answer "20%" identically. The
    channel's cut is a cost like any other, which puts every deduction on one
    side: ``p - c·p - cost = m·p`` → ``p = cost / (1 - c - m)``.

    Solving instead for a margin on post-commission revenue — ``p·(1-c)`` —
    yields a lower floor that quietly under-delivers: at 5% commission and a
    requested 20%, the seller keeps 19% of what the buyer paid.
    """
    if req.unit_cost is None:
        return None

    commission_pct, channel_name = 0.0, None
    if req.channel:
        definition = channel_config()["definitions"].get(req.channel)
        if definition:
            commission_pct = float(definition.get("commission_pct", 0.0))
            channel_name = definition.get("name")

    # Commission and margin together can exceed the price (a 40% margin on a
    # 5% channel is fine; 90% is not). Clamping keeps the floor finite and
    # positive — the schema caps margin at 90, so this is a guard, not a path.
    keep = max(1.0 - (commission_pct + req.min_margin_pct) / 100.0, 0.01)
    floor = req.unit_cost / keep
    return _CostFloor(
        floor=int(-(-floor // 100) * 100),  # round up: rounding down breaks the floor
        channel_name=channel_name,
        commission_pct=commission_pct,
    )


def _net_margin_pct(price: int, cost: int, commission_pct: float) -> float:
    """Profit at `price`, after commission and cost, as a share of that price."""
    profit = price * (1.0 - commission_pct / 100.0) - cost
    return round(profit / price * 100.0, 1) if price > 0 else 0.0


#: Shopee runs a separate marketplace per country, at its own price level. The
#: label names the one actually measured — calling Indonesian listings "Shopee"
#: in a Vietnamese UI reads as the seller's own market, which they are not.
_MARKETS = {"vn": "Shopee Việt Nam", "id": "Shopee Indonesia",
            "th": "Shopee Thái Lan", "my": "Shopee Malaysia",
            "ph": "Shopee Philippines", "sg": "Shopee Singapore",
            "tw": "Shopee Đài Loan", "br": "Shopee Brazil"}


def _market_label(countries: tuple[str, ...]) -> str:
    """Name the marketplace(s) a sample came from."""
    named = [_MARKETS.get(c, f"Shopee {c.upper()}") for c in countries]
    if not named:
        return "Shopee"
    if len(named) == 1:
        return named[0]
    return " + ".join(named)


def _vnd(amount: int) -> str:
    """Vietnamese money formatting: 67.900₫, not the 67,900₫ Python defaults to."""
    return f"{amount:,}".replace(",", ".") + "₫"


@dataclass(frozen=True)
class _PriceStats:
    """Percentiles plus where they came from, so the caller can label them."""

    median: int
    p25: int
    p75: int
    sample_size: int
    source: PriceSource
    shop_count: int | None = None
    #: Shopee markets behind the figures, so the label can name them.
    countries: tuple[str, ...] = ()
    #: Placement of the seller's own price, when the source can compute one.
    percentile_of: Callable[[int], int | None] | None = None


def _category_price_stats(category: str) -> _PriceStats:
    """Percentiles over the demo catalogue — the always-available baseline."""
    prices = sorted(
        item["price_vnd"]
        for item in store.all_products()
        if item.get("category") == category
    )
    if not prices:
        prices = sorted(item["price_vnd"] for item in store.all_products())
    n = len(prices)
    return _PriceStats(
        median=prices[n // 2],
        p25=prices[max(0, n // 4)],
        p75=prices[min(n - 1, (3 * n) // 4)],
        sample_size=n,
        source="demo",
    )


async def _price_stats(category: str) -> _PriceStats:
    """Observed market percentiles when the dataset covers `category`.

    The BTC dataset carries no fashion or accessory listings, so those keep the
    demo catalogue rather than borrowing an unrelated median — a wrong
    reference is worse than an openly synthetic one.
    """
    ref = await btc_market.price_reference(category)
    if ref is None:
        return _category_price_stats(category)
    return _PriceStats(
        median=ref.median, p25=ref.p25, p75=ref.p75,
        sample_size=ref.sample_size, source=ref.source, shop_count=ref.shop_count,
        countries=ref.countries, percentile_of=ref.percentile_of,
    )


async def recommend_price(req: PricingRequest) -> PricingResponse:
    stats = await _price_stats(req.category)
    median, p25, p75 = stats.median, stats.p25, stats.p75

    if stats.source == "demo":
        basis = f"trung vị danh mục {req.category} trên {stats.sample_size} sản phẩm mô phỏng"
    else:
        shops = f" của {stats.shop_count} nhà bán" if stats.shop_count else ""
        basis = (
            f"trung vị {_vnd(stats.median)} từ {stats.sample_size} sản phẩm {req.category}"
            f"{shops} quan sát được trên {_market_label(stats.countries)} (T7/2026)"
        )

    if req.current_price is None:
        recommended = median
        rationale = f"Chưa có giá hiện tại — lấy {basis}."
    else:
        cur = req.current_price
        if cur > median * 1.3:
            recommended = round((cur + median * 1.1) / 2)
            rationale = f"{_vnd(cur)} cao hơn nhiều so với {basis} — đề xuất giảm để cạnh tranh hơn."
        elif cur < median * 0.7:
            recommended = round((cur + median * 0.9) / 2)
            rationale = f"{_vnd(cur)} thấp hơn nhiều so với {basis} — có thể đang bán dưới giá, đề xuất tăng."
        else:
            recommended = round((cur + median) / 2)
            rationale = f"{_vnd(cur)} đã sát {basis} — chỉ cần tinh chỉnh nhẹ."

    # Where the seller actually sits. A gap to the median says how far; the
    # percentile says how unusual — 502,000₫ against a 67,900₫ median reads as
    # "3.5x over" but lands as "pricier than 99% of what is on sale".
    percentile = (
        stats.percentile_of(req.current_price)
        if stats.percentile_of and req.current_price is not None
        else None
    )
    if percentile is not None:
        if percentile >= 98:
            placement = "đắt hơn gần như toàn bộ sản phẩm đang bán"
        elif percentile <= 2:
            placement = "rẻ hơn gần như toàn bộ sản phẩm đang bán"
        else:
            placement = f"đắt hơn {percentile}% sản phẩm đang bán"
        rationale += f" Mức giá này {placement}."

    # The floor outranks the market: undercutting the competition at a loss is
    # not a cheaper price, it is a slower way to lose money.
    cost_floor = _cost_floor(req)
    floor_above_market = False
    margin_at_rec: float | None = None
    if cost_floor is not None:
        assert req.unit_cost is not None  # _cost_floor returns None without it
        if recommended < cost_floor.floor:
            recommended = cost_floor.floor
            floor_above_market = median < cost_floor.floor
            fee = (
                f" sau phí {cost_floor.channel_name} {cost_floor.commission_pct:g}%"
                if cost_floor.channel_name else ""
            )
            rationale = (
                f"{basis[0].upper()}{basis[1:]} thấp hơn giá vốn cho phép. Để giữ biên "
                f"{req.min_margin_pct:g}%{fee}, giá thấp nhất là {_vnd(cost_floor.floor)} — "
                f"đề xuất giữ ở mức này thay vì chạy theo thị trường."
            )
        margin_at_rec = _net_margin_pct(
            int(recommended), req.unit_cost, cost_floor.commission_pct
        )

    return PricingResponse(
        recommended_price=int(recommended), low=int(min(p25, recommended)),
        high=int(max(p75, recommended)), category_median=int(median),
        sample_size=stats.sample_size, rationale=rationale,
        market_p25=int(p25), market_p75=int(p75), price_percentile=percentile,
        market_label=_market_label(stats.countries) if stats.source != "demo" else None,
        price_floor=cost_floor.floor if cost_floor else None,
        margin_pct_at_recommended=margin_at_rec,
        channel_name=cost_floor.channel_name if cost_floor else None,
        channel_commission_pct=cost_floor.commission_pct if cost_floor else None,
        floor_above_market=floor_above_market,
        data_source=stats.source, shop_count=stats.shop_count,
    )


# ---------------------------------------------------------------------------
# #04 Churn Prediction — same rule_risk formula as
# customer_churn/src/02_score.py:rule_risk, ported to be key-free/deterministic.
# ---------------------------------------------------------------------------
def score_churn(req: ChurnRequest) -> ChurnResponse:
    z = (0.012 * req.recency_days - 0.15 * req.frequency_orders
         - 0.08 * req.sessions_last_month + 2.2 * req.cart_abandon_rate)
    z += 1.1 if req.trend == "declining" else (-0.9 if req.trend == "growing" else 0)
    z -= 1.6
    risk = 1 / (1 + math.exp(-z))

    band = "high" if risk >= 0.6 else ("medium" if risk >= 0.3 else "low")

    drivers = []
    if req.recency_days > 60:
        drivers.append(f"Không mua hàng {req.recency_days} ngày")
    if req.frequency_orders <= 1:
        drivers.append("Rất ít đơn trước đây")
    if req.sessions_last_month <= 1:
        drivers.append("Gần đây hầu như không vào xem")
    if req.cart_abandon_rate > 0.5:
        drivers.append(f"Bỏ giỏ hàng {req.cart_abandon_rate:.0%} số lần")
    if req.trend == "declining":
        drivers.append("Mức độ hoạt động đang giảm")
    if not drivers:
        drivers.append("Vẫn mua đều, không có dấu hiệu bất thường")

    action = (
        "Gửi ưu đãi giữ chân (giảm giá hoặc miễn phí vận chuyển) trước khi khách rời đi."
        if band == "high" else
        "Gửi email gợi ý sản phẩm phù hợp để kéo khách quay lại."
        if band == "medium" else
        "Chưa cần can thiệp — tiếp tục chăm sóc như hiện tại."
    )
    return ChurnResponse(
        churn_risk=round(risk, 2), risk_band=cast(_RiskBandLit, band), drivers=drivers, retention_action=action,
    )


def _risk_band(risk: float) -> str:
    return "high" if risk >= 0.6 else ("medium" if risk >= 0.3 else "low")


# ---------------------------------------------------------------------------
# #10 Return/Refund Prediction — heuristic: high price + sizing risk + heavy
# discount (impulse buy) + new customer + few reviews read all raise return risk.
# ---------------------------------------------------------------------------
# Category base return rates — grounded in 2026 industry benchmarks: apparel
# runs 20-40% (highest of any category, driven by sizing/fit uncertainty and
# "bracketing"), beauty/cosmetics runs 4-12% (hygiene concerns keep it low).
# Sources: capitaloneshopping.com/research/average-retail-return-rate,
# richpanel.com/learn/ecommerce-return-rates (2026 benchmarks).
_BASE_RETURN_RATE = {"Thời trang": 0.28, "Mỹ phẩm": 0.08, "Phụ kiện": 0.12}


def score_return(req: ReturnRequest) -> ReturnResponse:
    base = _BASE_RETURN_RATE[req.category]
    z = math.log(base / (1 - base))  # start from the category's real base rate
    z += 0.5 if req.size_related else 0.0   # fit/sizing is THE documented driver of apparel returns
    z += 0.015 * req.discount_pct
    z += 0.4 if req.is_new_customer else 0.0
    # Reading reviews reduces risk, but with diminishing returns — cap the
    # benefit so it can't cancel out a genuine sizing/fit return risk. (QA:
    # previously uncapped, letting reviews_read=30+ collapse a high-risk order to "low".)
    z -= 0.12 * min(req.reviews_read, 4)
    z += (req.price_vnd / 1_000_000) * 0.15
    risk = 1 / (1 + math.exp(-z))
    band = _risk_band(risk)

    drivers = []
    if req.size_related:
        drivers.append("Hàng phụ thuộc size (quần áo/giày) — dễ không vừa")
    if req.discount_pct >= 30:
        drivers.append(f"Giảm giá sâu ({req.discount_pct:.0f}%) — có thể mua bốc đồng")
    if req.is_new_customer:
        drivers.append("Khách mua lần đầu — chưa có lịch sử để đối chiếu")
    if req.reviews_read == 0:
        drivers.append("Mua mà không đọc đánh giá nào")
    if req.price_vnd >= 1_000_000:
        drivers.append("Đơn giá trị cao — dễ đắn đo sau khi mua")
    if not drivers:
        drivers.append("Hồ sơ ít rủi ro")

    action = (
        "Chủ động gửi hướng dẫn chọn size và nhắc chính sách đổi trả trước khi giao."
        if band == "high" else
        "Kèm bảng size hoặc hướng dẫn sử dụng trong phiếu giao hàng."
        if band == "medium" else
        "Không cần xử lý gì đặc biệt."
    )
    return ReturnResponse(return_risk=round(risk, 2), risk_band=cast(_RiskBandLit, band), drivers=drivers, action=action)


# ---------------------------------------------------------------------------
# #15 Post-purchase Regret Predictor — heuristic: fast/late-night/discount-driven
# purchases with no comparison shopping signal higher regret risk.
# ---------------------------------------------------------------------------
# Grounded in impulse-buying research: cognitive/self-control decline sets in
# after ~10pm (decision fatigue + prefrontal cortex impairment), and ~48% of
# impulse purchases are later regretted (vs. a much lower base rate for
# deliberate purchases). Sources: capitaloneshopping.com/research/
# impulse-buying-statistics, simplicitydx.com (48% regret finding), 100.3thepeak
# late-night-shopping coverage (worst decisions after 10pm).
_LATE_NIGHT_HOURS = {22, 23, 0, 1, 2, 3}
_IMPULSE_REGRET_RATE = 0.48
_DELIBERATE_REGRET_RATE = 0.12


def score_regret(req: RegretRequest) -> RegretResponse:
    impulsive = req.decision_time_seconds < 60 or req.revisit_count == 0
    base = _IMPULSE_REGRET_RATE if impulsive else _DELIBERATE_REGRET_RATE
    z = math.log(base / (1 - base))
    z += 0.5 if req.decision_time_seconds < 60 else 0.0
    z += 0.3 if req.revisit_count == 0 else 0.0
    z += 0.6 if req.purchase_hour in _LATE_NIGHT_HOURS else 0.0
    z += 0.3 if req.used_discount else 0.0
    z += 0.3 if req.price_vnd >= 1_000_000 else 0.0
    risk = 1 / (1 + math.exp(-z))
    band = _risk_band(risk)

    drivers = []
    if req.decision_time_seconds < 60:
        drivers.append("Quyết định dưới một phút — mua bốc đồng")
    if req.revisit_count == 0:
        drivers.append("Mua mà không so sánh lựa chọn khác")
    if req.purchase_hour in _LATE_NIGHT_HOURS:
        drivers.append("Mua lúc đêm khuya — khả năng tự kiểm soát thấp hơn")
    if req.used_discount:
        drivers.append("Mua chủ yếu vì có khuyến mãi")
    if req.price_vnd >= 1_000_000:
        drivers.append("Đơn giá trị cao — dễ hối hận hơn")
    if not drivers:
        drivers.append("Quyết định mua có cân nhắc kỹ")

    if band == "high":
        msg = "Cảm ơn bạn đã mua hàng! Nếu sản phẩm chưa phù hợp, hãy xem chính sách đổi trả của cửa hàng hoặc liên hệ hỗ trợ nhé 💛"
    elif band == "medium":
        msg = "Đơn hàng của bạn đang được xử lý. Nếu cần đổi size hoặc màu khác, hãy liên hệ cửa hàng để được hỗ trợ theo chính sách hiện hành."
    else:
        msg = "Cảm ơn bạn đã tin tưởng lựa chọn kỹ lưỡng — chúc bạn hài lòng với sản phẩm!"

    return RegretResponse(regret_risk=round(risk, 2), risk_band=cast(_RiskBandLit, band), drivers=drivers, reassurance_message=msg)


# ---------------------------------------------------------------------------
# #08 Sentiment-driven Inventory Alert — combine social buzz (mentions x
# sentiment) with current stock runway to flag understock risk before a
# viral moment causes a stockout. Approach is grounded in real research: 59%
# of consumers say viral trends now cause faster sellouts, blending social
# sentiment with historical sales improves forecast accuracy by ~42%, and
# early trend detection cut stockouts ~40% in one study. Sources:
# homeofdirectcommerce.com (1-in-3-shoppers social-speed-retail),
# sranalytics.io/blog/predictive-inventory-analytics.
# ---------------------------------------------------------------------------
def score_inventory_alert(req: InventoryAlertRequest) -> InventoryAlertResponse:
    trend_score = (req.social_mentions_7d / 100) * max(0.0, (req.social_sentiment + 1) / 2)
    is_trending = trend_score >= 2.0

    days_left = req.current_stock / max(req.avg_daily_sales, 0.1)
    projected_daily = req.avg_daily_sales * (1 + min(2.0, trend_score / 3))

    # Stock health is a hard constraint even when social buzz is quiet. The
    # previous implementation returned ``none`` for a sold-out product with no
    # mentions and even said its runway was fine.
    if days_left <= 3:
        level = "urgent"
    elif days_left <= 7 or (is_trending and days_left <= 14):
        level = "watch"
    else:
        level = "none"

    target_days = 14
    needed = max(0, round(projected_daily * target_days - req.current_stock))

    if level == "urgent" and is_trending:
        reason = (f"'{req.product_name}' is trending (score {trend_score:.1f}) "
                  f"with only {days_left:.1f} days of stock left — restock now.")
    elif level == "urgent":
        reason = (f"'{req.product_name}' has only {days_left:.1f} days of stock left "
                  "at the current sales rate — restock now even without unusual social buzz.")
    elif level == "watch" and is_trending:
        reason = (f"'{req.product_name}' is picking up buzz (score {trend_score:.1f}) "
                  f"and stock runway is getting short ({days_left:.1f} days) — plan a restock.")
    elif level == "watch":
        reason = (f"'{req.product_name}' has a short stock runway ({days_left:.1f} days) "
                  "at the current sales rate — plan a restock.")
    else:
        reason = "No unusual social buzz — current stock runway looks fine."

    return InventoryAlertResponse(
        is_trending=is_trending, trend_score=round(trend_score, 2),
        days_of_stock_left=round(days_left, 1), alert_level=cast(_AlertLevelLit, level),
        recommended_restock_qty=needed, reason=reason,
    )
