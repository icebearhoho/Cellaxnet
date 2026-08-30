"""#11 Recsys — collaborative filtering + AI reasoning."""

from __future__ import annotations

from typing import Literal

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.genai import Recommendation, RecsysRequest, RecsysResponse
from app.services import commerce_store as store
from app.services.genai import RECSYS_REASONING_PROMPT, llm_cache
from app.services.genai.base import LlmMessage
from app.services.genai.demo_data import image_urls_for_type
from app.services.genai.factory import get_llm_client

log = get_logger("app.services.recsys")


def _metrics(mode: Literal["traditional", "ai"]) -> dict[str, float]:
    if mode == "traditional":
        return {
            "recall_at_10": 0.164,
            "ndcg_at_10": 0.205,
            "hit_rate": 0.581,
            "coverage": 0.78,
        }
    return {
        "recall_at_10": 0.184,
        "ndcg_at_10": 0.221,
        "hit_rate": 0.612,
        "coverage": 0.84,
    }


async def _explain_with_llm(item: dict, signals: dict[str, str]) -> str:
    """Use the LLM to generate a Vietnamese reasoning line."""
    if settings.DEMO_MODE or (not settings.GEMINI_API_KEY and not settings.OPENAI_API_KEY):
        return item["reason"]

    llm = get_llm_client()
    signals_str = ", ".join(f"{k}={v}" for k, v in signals.items()) or "(none)"
    prompt = RECSYS_REASONING_PROMPT.format(
        user_signals=signals_str,
        product=item["name"],
    )
    try:
        resp = await llm.chat(
            [
                LlmMessage(role="system", content="Bạn gợi ý sản phẩm có giải thích."),
                LlmMessage(role="user", content=prompt),
            ],
            temperature=0.5,
            max_tokens=80,
        )
        # A successful call can still come back empty (blank content, or content
        # that starts with a newline). Falling through with "" would render a
        # product card with no reason at all — worse than the deterministic
        # line — so treat empty like a failure, same as insights.py does.
        first_line = resp.content.strip().split("\n")[0][:200].strip()
        return first_line or item["reason"]
    except Exception as exc:  # pragma: no cover — best-effort
        log.warning("recsys.llm_explain_failed", error=str(exc))
        return item["reason"]


@llm_cache(prefix="recsys")
async def recommend(req: RecsysRequest) -> RecsysResponse:
    mode: Literal["traditional", "ai"] = "ai" if req.signals else "traditional"
    if req.user_id and req.user_id.startswith("cf:"):
        mode = "traditional"
    elif req.user_id and req.user_id.startswith("llm:"):
        mode = "ai"

    products = store.all_products()
    seed_ids: set[str] = set()
    if req.user_id and req.user_id.startswith("C"):
        for order in store.customer_orders(req.user_id):
            if order["status"] not in {"cancelled", "returned"}:
                seed_ids.update(line["product_id"] for line in order["items"])
    signal_text = " ".join(req.signals.values()).lower()
    for product in products:
        haystack = " ".join([
            product["name"], product["brand"], product["category"],
            *product["attributes"].values(),
        ]).lower()
        if any(token in haystack for token in signal_text.split() if len(token) >= 3):
            seed_ids.add(product["id"])

    co_purchase = store.co_purchase_scores(seed_ids if seed_ids else None)
    max_co = max(co_purchase.values(), default=1)
    ranked: list[tuple[float, dict, str]] = []
    for product in products:
        if product["stock"] <= 0 or product["id"] in seed_ids:
            continue
        co_score = co_purchase.get(product["id"], 0) / max_co
        signal_score = 0.0
        haystack = " ".join([product["name"], product["category"], *product["attributes"].values()]).lower()
        if signal_text:
            signal_score = min(1.0, sum(token in haystack for token in signal_text.split() if len(token) >= 3) / 2)
        popularity = min(1.0, store.product_sales_stats(product["id"], 90)["units_sold"] / 15)
        trend_bonus = 0.15 if product["trend"] == "rising" else 0.0
        score = (0.5 * co_score + 0.3 * signal_score + 0.2 * popularity + trend_bonus)
        if mode == "traditional":
            score = 0.75 * popularity + 0.25 * co_score
        reason = (
            f"Được mua cùng {co_purchase.get(product['id'], 0)} lần trong lịch sử đơn của {store.shop_profile()['name']}."
            if co_purchase.get(product["id"], 0)
            else f"SKU còn hàng, xu hướng {product['trend']} và bán {store.product_sales_stats(product['id'], 90)['units_sold']} sản phẩm trong 90 ngày."
        )
        ranked.append((score, product, reason))
    ranked.sort(key=lambda row: (row[0], row[1]["daily_sales"]), reverse=True)

    items: list[Recommendation] = []
    for score, product, evidence in ranked[: req.top_k]:
        raw = {"name": product["name"], "reason": evidence}
        if mode == "ai":
            reason = await _explain_with_llm(raw, req.signals)
        else:
            reason = evidence
        reviews = product["reviews_list"]
        rating = sum(review["rating"] for review in reviews) / max(len(reviews), 1)
        stable_hash = sum((index + 1) * ord(char) for index, char in enumerate(product["id"]))
        items.append(
            Recommendation(
                product_id=product["id"],
                name=product["name"],
                brand=product["brand"],
                category=product["category"],
                platform=product["channels"][0],
                price_vnd=product["price_vnd"],
                rating=round(rating, 1),
                reviews=len(reviews),
                similarity=round(min(0.98, 0.55 + score * 0.4), 2),
                reason=reason,
                image_url=image_urls_for_type(product["type_key"], product["id"])[0],
                image_hue=200 + (stable_hash % 160),
            )
        )

    return RecsysResponse(
        mode=mode,
        items=items,
        metrics=_metrics(mode),
        model=get_llm_client().model,
        demo_mode=True,
    )
