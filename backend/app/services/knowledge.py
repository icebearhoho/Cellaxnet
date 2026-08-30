"""Track 2, Đề 1 — Product Knowledge service (sales-signal explanation).

Heuristic signal attribution (deterministic): computes the sales change and
ranks possible contributing factors — stock availability, price change,
traffic change, competitor promotion and own promotion. This is descriptive,
not causal inference. The natural-language explanation runs on the LLM with a
templated fallback.
"""

from __future__ import annotations

from typing import Literal, cast

from app.schemas.knowledge import Driver, ProductKnowledgeRequest, ProductKnowledgeResponse
from app.services.llm_reasoning import reason_json

_IMPACT_RANK = {"high": 3, "medium": 2, "low": 1}


def _impact(mag: float, med: float, high: float) -> str:
    if mag >= high:
        return "high"
    if mag >= med:
        return "medium"
    return "low"


def _drivers(req: ProductKnowledgeRequest) -> list[Driver]:
    out: list[Driver] = []

    if req.stock_status == "out":
        out.append(Driver(factor="Hết hàng (out of stock)", direction="down", impact="high"))
    elif req.stock_status == "low":
        out.append(Driver(factor="Tồn kho thấp", direction="down", impact="medium"))

    if abs(req.price_change_pct) >= 1:
        # Price up → downward pressure on sales, and vice-versa.
        direction = "down" if req.price_change_pct > 0 else "up"
        out.append(Driver(
            factor=f"Giá thay đổi {req.price_change_pct:+.0f}%",
            direction=cast('Literal["up", "down"]', direction),
            impact=cast('Literal["low", "medium", "high"]', _impact(abs(req.price_change_pct), 5, 15)),
        ))

    if abs(req.traffic_change_pct) >= 3:
        direction = "up" if req.traffic_change_pct > 0 else "down"
        out.append(Driver(
            factor=f"Lưu lượng truy cập {req.traffic_change_pct:+.0f}%",
            direction=cast('Literal["up", "down"]', direction),
            impact=cast('Literal["low", "medium", "high"]', _impact(abs(req.traffic_change_pct), 10, 30)),
        ))

    if req.competitor_promo:
        out.append(Driver(factor="Đối thủ đang khuyến mãi", direction="down", impact="medium"))

    if req.promotion_active:
        out.append(Driver(factor="Đang chạy khuyến mãi của mình", direction="up", impact="medium"))

    out.sort(key=lambda d: _IMPACT_RANK[d.impact], reverse=True)
    return out


def _promo_effectiveness(req: ProductKnowledgeRequest, change: float) -> str:
    if not req.promotion_active:
        return "Không có khuyến mãi đang chạy cho sản phẩm này."
    if change >= 10:
        return f"Khuyến mãi trùng thời điểm doanh số tăng {change:+.0f}%; chưa thể tách riêng quan hệ nhân quả."
    if change <= -5:
        return "Doanh số vẫn giảm trong lúc chạy khuyến mãi; cần kiểm tra thêm mức ưu đãi và nguồn traffic."
    return "Doanh số ít thay đổi trong lúc chạy khuyến mãi; chưa đủ dữ liệu để kết luận hiệu quả."


_SYSTEM = (
    "You are a product-analytics agent for a Vietnamese e-commerce seller. Given "
    "a product's sales change and possible contributing signals, explain in ONE "
    "short paragraph (2-3 sentences) WHY sales moved, referencing the "
    "top drivers. Do not invent facts beyond the drivers given. "
    'Reply as JSON: {"explanation": "..."}'
)


def _fallback_explanation(req: ProductKnowledgeRequest, change: float, drivers: list[Driver]) -> str:
    if not drivers:
        return (
            f"Doanh số '{req.product}' thay đổi {change:+.0f}% nhưng không có yếu tố "
            f"nào nổi bật — nhiều khả năng dao động tự nhiên của thị trường."
        )
    top = ", ".join(f"{d.factor} (kéo {d.direction})" for d in drivers[:3])
    return (
        f"Doanh số '{req.product}' {('giảm' if change < 0 else 'tăng')} {abs(change):.0f}%. "
        f"Các tín hiệu có thể góp phần, xếp theo mức tác động heuristic: {top}."
    )


async def explain_sales(req: ProductKnowledgeRequest) -> ProductKnowledgeResponse:
    change = (req.sales_curr - req.sales_prev) / req.sales_prev * 100.0 if req.sales_prev > 0 else (
        100.0 if req.sales_curr > 0 else 0.0
    )
    change = round(change, 1)
    direction = "up" if change > 3 else ("down" if change < -3 else "flat")
    drivers = _drivers(req)
    promo = _promo_effectiveness(req, change)

    driver_txt = "; ".join(f"{d.factor} → {d.direction}/{d.impact}" for d in drivers) or "none"
    data = await reason_json(
        _SYSTEM,
        f"Product: {req.product} ({req.category}). Sales {req.sales_prev:,} → "
        f"{req.sales_curr:,} ({change:+.0f}%). Ranked drivers: {driver_txt}.",
        label="knowledge",
    )
    explanation = (data or {}).get("explanation") if data else None
    return ProductKnowledgeResponse(
        sales_change_pct=change,
        direction=cast('Literal["up", "down", "flat"]', direction),
        drivers=drivers,
        promotion_effectiveness=promo,
        explanation=(explanation or "").strip() or _fallback_explanation(req, change, drivers),
    )
