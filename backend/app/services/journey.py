"""Customer Journey Intelligence service — Track 1, Đề 2.

Turns a session's full event sequence (search / click / view / review / cart /
purchase / livestream) into: a funnel-weighted purchase-intent score, the current funnel
stage, an engagement score, the dominant category, the top-3 product picks, and
— per the brief's goal — the predicted NEXT ACTION plus a concrete seller nudge
to move the shopper forward. The numeric scoring is deterministic; the narrative
reasoning runs on the LLM with a templated fallback.
"""

from __future__ import annotations

import math
import time
from collections import Counter

from app.core.i18n import t
from app.schemas.journey import (
    FunnelStage,
    JourneyRequest,
    JourneyResponse,
    NextAction,
)
from app.services import behavior_metrics
from app.services import commerce_store as store
from app.services.genai.demo_data import image_url_for_type
from app.services.llm_reasoning import reason_json
from app.services.personal_shopper import _card


def _as_catalog_item(p: dict) -> dict:
    """Adapt a commerce_store product into the shape `_card()` expects."""
    return {
        "id": p["id"],
        "title": p["name"],
        "metadata": {
            "category": p["category"], "platform": "Shopee",
            "price_vnd": p["price_vnd"], "brand": p["brand"],
        },
    }


def _funnel_stage(counts: dict[str, int]) -> FunnelStage:
    if counts["purchase"]:
        return "purchase"
    if counts["cart"]:
        return "intent"
    if counts["view"] or counts["click"] or counts["livestream"] or counts["review"]:
        return "consideration"
    return "awareness"


def _next_action(stage: FunnelStage, prob: float, engagement: float,
                 has_search: bool, top_category: str | None,
                 counts: dict[str, int]) -> tuple[NextAction, str, str]:
    """Return (action_key, vietnamese_label, seller_nudge). The nudge is built
    per-case (not one fixed string per stage) so it names the actual category
    and cites the numbers driving the call — a seller acting on it should be
    able to tell WHY, not just WHAT."""
    cat = top_category or "sản phẩm khách đang xem"
    pct = round(prob * 100)
    # Reading reviews is a trust-building signal worth calling out wherever the
    # shopper hasn't already purchased — it's WHY a borderline case tips over.
    review_note = (
        f" Khách đã đọc đánh giá SP ({counts['review']} lần) — mức tin tưởng cao, dễ chốt đơn hơn."
        if counts["review"] and stage != "purchase" else ""
    )

    if stage == "purchase":
        if counts["cart"] == 0:
            # Bought via "Mua ngay" with no cart step — a fast, low-friction
            # decision; the moment to upsell is now, before they leave.
            return ("checkout", t("Đã mua trong phiên — có thể mua thêm"),
                    f"Khách mua thẳng SP {cat} không qua giỏ hàng — quyết định rất nhanh, "
                    f"ít nhạy giá. Gợi ý thêm SP bổ sung cùng ngành {cat} ngay ở trang cảm ơn "
                    f"+ mời tích điểm/thành viên trước khi khách rời trang.")
        return ("checkout", t("Đã mua trong phiên — có thể mua thêm"),
                f"Đã chốt đơn {cat} sau khi cân nhắc trong giỏ hàng. Cross-sell SP bổ sung "
                f"cùng ngành + mời tích điểm/thành viên để tăng giá trị đơn tiếp theo.")

    if stage == "intent":
        if prob >= 0.6:
            return ("checkout", t("Sắp thanh toán"),
                    f"Đã thêm {cat} vào giỏ, mức độ quan tâm cao ({pct}%) — làm nổi bật nút "
                    f"thanh toán + freeship/quà nhỏ để chốt đơn ngay trước khi khách đổi ý."
                    f"{review_note}")
        return ("compare", t("Đang phân vân (đã thêm giỏ nhưng chưa mua)"),
                f"Đã thêm {cat} vào giỏ nhưng xác suất mua chỉ {pct}% — có thể đang so giá "
                f"hoặc chờ khuyến mãi. Gửi mã giảm giá giới hạn thời gian + review nổi bật "
                f"của SP này để thúc đẩy chốt đơn.{review_note}")

    # Leave risk = a low-engagement bounce with no active search intent. An
    # explicit search means the shopper is hunting for something, so treat that
    # as early-funnel browsing to nurture, not a bounce.
    if engagement < 0.2 and prob < 0.35 and not has_search:
        return ("leave", t("Nguy cơ rời đi"),
                f"Tương tác rất thấp ({round(engagement * 100)}%) với {cat}, không có tìm "
                f"kiếm chủ động — nguy cơ rời trang cao. Bật popup ưu đãi/mã giảm ngay để "
                f"giữ chân trước khi khách thoát.")

    if stage == "consideration":
        if prob >= 0.5:
            return ("add_to_cart", t("Có khả năng thêm vào giỏ"),
                    f"Khách đã xem/click nhiều lần ngành {cat}, mức quan tâm {pct}% — nhắc "
                    f"lại lợi ích chính + hiển thị review nổi bật để tạo động lực thêm giỏ."
                    f"{review_note}")
        return ("keep_browsing", t("Còn xem tiếp, chưa quyết"),
                f"Khách mới xem qua vài SP {cat}, chưa có dấu hiệu quyết định rõ ({pct}%) — "
                f"đề xuất SP liên quan cùng danh mục để giữ chân và dẫn dắt tiếp.{review_note}")

    # awareness
    if has_search:
        return ("keep_browsing", "Mới bắt đầu tìm hiểu",
                f"Khách đang chủ động tìm kiếm SP {cat} — hiển thị hàng bán chạy khớp từ "
                f"khoá tìm kiếm để dẫn vào phễu mua sắm.")
    return ("keep_browsing", "Mới bắt đầu tìm hiểu",
            f"Hành vi còn rất sớm (mới lướt qua {cat}) — hiển thị sản phẩm bán chạy để dẫn "
            f"khách vào phễu mua sắm.")


async def analyze_journey(
    req: JourneyRequest, *, use_llm_reasoning: bool = True, now_ms: int | None = None
) -> JourneyResponse:
    counts = {t: 0 for t in ("search", "click", "view", "cart", "purchase", "livestream", "review")}
    for e in req.events:
        counts[e.type] += 1

    cat_counts = Counter(e.category for e in req.events if e.category)
    top_category = cat_counts.most_common(1)[0][0] if cat_counts else None

    # Funnel-weighted intent: later-funnel actions weigh far more; early actions
    # (search/click/view) are capped so idle browsing alone can't dominate.
    # Reading reviews sits between view/click and cart — it's a real trust
    # signal (a shopper checking reviews is meaningfully closer to buying than
    # one who only skimmed thumbnails), so it's weighted well above view/click.
    z = (0.10 * min(counts["search"], 10)
         + 0.15 * min(counts["click"], 15)
         + 0.15 * min(counts["view"], 10)
         + 0.35 * min(counts["review"], 10)
         + 0.40 * counts["livestream"]
         + 0.70 * counts["cart"]
         + 1.50 * counts["purchase"]
         - 1.0)
    prob = 1 / (1 + math.exp(-z))
    will_purchase = prob >= 0.5

    eng_raw = (0.5 * counts["search"] + 0.7 * counts["click"] + 0.7 * counts["view"]
               + 1.0 * counts["review"] + 1.5 * counts["livestream"] + 2.0 * counts["cart"]
               + 2.5 * counts["purchase"])
    engagement = round(min(1.0, eng_raw / 12.0), 2)

    stage = _funnel_stage(counts)
    action, label, nudge = _next_action(
        stage, prob, engagement, has_search=counts["search"] > 0,
        top_category=top_category, counts=counts,
    )

    # Ground recommendations in the shop's REAL catalog: prioritize the exact
    # product the shopper searched for, then the best-moving items in the
    # category they're actually browsing (not a generic, category-blind slice).
    query = next((e.query for e in reversed(req.events) if e.query), None)
    candidates = store.products_by_category(top_category) if top_category else store.all_products()
    picks: list[dict] = []
    if query:
        matched = store.find_product(query)
        if matched and matched in candidates:
            picks.append(matched)
    ranked = sorted(
        (p for p in candidates if p not in picks),
        key=lambda p: (p["trend"] == "rising", p["daily_sales"]),
        reverse=True,
    )
    picks += ranked[: 3 - len(picks)]
    products = [
        _card(_as_catalog_item(p), round(0.9 - i * 0.08, 2), image_url=image_url_for_type(p["type_key"]))
        for i, p in enumerate(picks)
    ]

    reasoning = (
        await _reason(counts, top_category, prob, engagement, stage, label)
        if use_llm_reasoning
        else _fallback_reasoning(counts, top_category, label, prob, engagement)
    )

    # Real timing signals (mentor feedback: dwell time / cart-abandon / time to
    # purchase) — computed from event `ts`, None whenever no timestamps exist.
    effective_now = now_ms if now_ms is not None else int(time.time() * 1000)
    abandoned = behavior_metrics.cart_abandoned(req.events, now_ms=effective_now)
    if abandoned and stage != "purchase":
        nudge += (" Giỏ hàng đã im lặng khá lâu, không có hành động tiếp theo — "
                   "đây là dấu hiệu bỏ giỏ rõ, nên nhắc lại ngay.")

    return JourneyResponse(
        will_purchase=will_purchase,
        purchase_probability=round(prob, 2),
        predicted_next_action=action,
        next_action_label=label,
        funnel_stage=stage,
        engagement_score=engagement,
        nudge=nudge,
        top_category=top_category,
        category_breakdown={str(k): v for k, v in cat_counts.items()},
        recommended_products=products,
        reasoning=reasoning,
        session_duration_seconds=behavior_metrics.session_duration_seconds(req.events),
        avg_dwell_seconds=behavior_metrics.avg_dwell_seconds(req.events),
        time_to_purchase_seconds=behavior_metrics.time_to_purchase_seconds(req.events),
        cart_abandoned=abandoned,
    )


_SYSTEM = (
    "You are a customer-journey analyst for a Vietnamese e-commerce shop's seller "
    "dashboard. Given a session's event counts, the category involved, purchase "
    "probability, engagement score and the predicted next action, explain in ONE short "
    "paragraph (2-3 sentences) WHY that next action follows from THIS specific behavior "
    "pattern — cite the actual numbers and category, don't just restate the counts as a "
    "list. If purchase happened with zero cart events, that means a direct \"buy now\" "
    "with no cart step — call that out, it signals a fast/low-friction decision. Do not "
    "invent data not given to you. This dashboard is Vietnamese-only — write the "
    "reasoning IN VIETNAMESE regardless of any English words in the input data. "
    'Reply as JSON: {"reasoning": "..."}'
)


def _fallback_reasoning(counts: dict[str, int], top_category: str | None,
                        label: str, prob: float, engagement: float) -> str:
    parts = []
    order = [("search", "tìm kiếm {n} lần"), ("click", "click {n} lần"),
             ("view", "xem {n} sản phẩm"), ("review", "đọc đánh giá {n} lần"),
             ("livestream", "tương tác livestream {n} lần"),
             ("cart", "thêm {n} sản phẩm vào giỏ"), ("purchase", "mua {n} lần")]
    for key, tmpl in order:
        if counts[key]:
            parts.append(tmpl.format(n=counts[key]))
    activity = ", ".join(parts) if parts else "chưa có hành vi rõ ràng"
    cat_txt = f" ở ngành {top_category}" if top_category else ""

    direct_buy_txt = ""
    if counts["purchase"] and not counts["cart"]:
        direct_buy_txt = " Đáng chú ý: khách bấm mua thẳng, không qua bước thêm giỏ — quyết định rất nhanh."

    return (
        f"Trong phiên này khách {activity}{cat_txt}. Xác suất mua tính được là "
        f"{round(prob * 100)}%, điểm tương tác {round(engagement * 100)}%.{direct_buy_txt} "
        f"Với các tín hiệu này, bước tiếp theo dự đoán là: {label.lower()}."
    )


async def _reason(counts: dict[str, int], top_category: str | None, prob: float,
                  engagement: float, stage: FunnelStage, label: str) -> str:
    data = await reason_json(
        _SYSTEM,
        f"Event counts: {counts}. Top category: {top_category}. Funnel stage: {stage}. "
        f"Purchase probability: {prob:.2f}. Engagement score: {engagement:.2f}. "
        f"Predicted next action: {label}.",
        label="journey",
    )
    r = (data or {}).get("reasoning") if data else None
    return (r or "").strip() or _fallback_reasoning(counts, top_category, label, prob, engagement)
