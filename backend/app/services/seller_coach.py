"""#17 Seller Coach — 5-step audit + 4-week roadmap."""

from __future__ import annotations

import json

from app.core.logging import get_logger
from app.schemas.genai import (
    AuditStep,
    RoadmapWeek,
    SellerCoachRequest,
    SellerCoachResponse,
)
from app.services import commerce_store as store
from app.services.genai import SELLER_COACH_SYSTEM, llm_cache
from app.services.genai.base import LlmMessage
from app.services.genai.factory import get_llm_client

log = get_logger("app.services.seller_coach")


def _overall(audit: list[AuditStep]) -> int:
    return round(sum(s.score for s in audit) / max(1, len(audit)))


async def _llm_audit(req: SellerCoachRequest) -> SellerCoachResponse:
    """Ask the LLM to score a seller's audit + propose a roadmap as JSON."""
    llm = get_llm_client()
    prompt = (
        "Đánh giá seller dựa trên 5 trục (listing, pricing, visuals, reviews, inventory). "
        "Trả về JSON thuần:\n"
        "{\n"
        '  "audit": [{"id": "...", "label": "...", "score": 0-100, "tip": "..."}],\n'
        '  "roadmap": [{"week": 1, "title": "...", "bullets": ["..."]}]\n'
        "}\n"
        f"Seller id: {req.seller_id or 'demo'}"
    )
    resp = await llm.chat(
        [
            LlmMessage(role="system", content=SELLER_COACH_SYSTEM),
            LlmMessage(role="user", content=prompt),
        ],
        temperature=0.5,
        max_tokens=900,
    )

    # Parse JSON — strip markdown fences if the model wraps it.
    raw = resp.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("seller_coach.json_parse_failed")
        return _demo_response(req)

    audit = [AuditStep(**a) for a in data.get("audit", [])][:5]
    roadmap = [RoadmapWeek(**w) for w in data.get("roadmap", [])][:4]

    if len(audit) < 5 or len(roadmap) < 4:
        return _demo_response(req)

    return SellerCoachResponse(
        overall=_overall(audit),
        audit=audit,
        roadmap=roadmap,
        demo_mode=False,
    )


def _demo_response(req: SellerCoachRequest) -> SellerCoachResponse:
    products = store.all_products()
    reviews = [review for product in products for review in product["reviews_list"]]
    listing_score = round(sum(p["listing_completeness"] for p in products) / len(products))
    visual_score = round(sum(p["image_quality_score"] for p in products) / len(products))
    healthy_price = 0
    for product in products:
        effective = [
            competitor["price_vnd"] * (1 - competitor["discount_pct"] / 100)
            for competitor in product["competitors"]
        ]
        market_reference = sum(effective) / len(effective)
        if 0.9 <= product["price_vnd"] / market_reference <= 1.1:
            healthy_price += 1
    pricing_score = round(healthy_price / len(products) * 100)
    avg_rating = sum(review["rating"] for review in reviews) / len(reviews)
    review_score = round(avg_rating / 5 * 100)
    stockouts = [p for p in products if p["stock_status"] == "out"]
    low_stock = [p for p in products if p["stock_status"] == "low"]
    inventory_score = round(
        (len(products) - len(stockouts) - len(low_stock) * 0.45) / len(products) * 100
    )

    audit = [
        AuditStep(
            id="listing", label="Chất lượng listing", score=listing_score,
            tip=f"{sum(p['listing_completeness'] < 80 for p in products)}/{len(products)} SKU có độ hoàn thiện dưới 80%.",
        ),
        AuditStep(
            id="pricing", label="Giá bán", score=pricing_score,
            tip=f"{healthy_price}/{len(products)} SKU đang trong vùng ±10% so với giá hiệu dụng của đối thủ.",
        ),
        AuditStep(
            id="visuals", label="Hình ảnh", score=visual_score,
            tip=f"{sum(p['image_quality_score'] < 70 for p in products)} SKU có điểm hình ảnh dưới 70 cần chụp lại.",
        ),
        AuditStep(
            id="reviews", label="Đánh giá", score=review_score,
            tip=f"Điểm trung bình {avg_rating:.2f}/5 trên {len(reviews)} review demo có liên kết SKU.",
        ),
        AuditStep(
            id="inventory", label="Tồn kho", score=inventory_score,
            tip=f"{len(stockouts)} SKU hết hàng và {len(low_stock)} SKU tồn thấp cần xử lý.",
        ),
    ]
    lowest = sorted(audit, key=lambda step: step.score)
    roadmap = [
        RoadmapWeek(
            week=1, title=f"Xử lý {lowest[0].label.lower()}",
            bullets=[lowest[0].tip, "Giao owner và deadline cho từng SKU ảnh hưởng."],
        ),
        RoadmapWeek(
            week=2, title=f"Cải thiện {lowest[1].label.lower()}",
            bullets=[lowest[1].tip, "Đo baseline trước khi chỉnh để so sánh sau 7 ngày."],
        ),
        RoadmapWeek(
            week=3, title="Tối ưu nhóm bán chạy",
            bullets=["Ưu tiên 10 SKU doanh thu cao nhất từ lịch sử đơn hàng.", "Kiểm tra giá, nội dung và tồn kho trên cả 4 kênh."],
        ),
        RoadmapWeek(
            week=4, title="Đo lại và chuẩn hoá",
            bullets=["Chạy lại audit trên cùng bộ metric.", "Giữ thay đổi có cải thiện doanh thu hoặc giảm rủi ro."],
        ),
    ]
    return SellerCoachResponse(
        overall=_overall(audit),
        audit=audit,
        roadmap=roadmap,
        demo_mode=True,
    )


@llm_cache(prefix="seller_coach")
async def coach(req: SellerCoachRequest) -> SellerCoachResponse:
    # Scores come from the coherent demo shop, never from an LLM guess based on
    # seller_id. ``demo_mode`` stays true because this is not a connected tenant.
    log.info("seller_coach.coherent_demo_shop", seller_id=req.seller_id)
    return _demo_response(req)
