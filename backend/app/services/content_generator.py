"""#09 Content Generator — 3 platform variants + predicted CTR."""

from __future__ import annotations

import asyncio
import re

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.genai import ContentGeneratorRequest, ContentGeneratorResponse, ContentVariant
from app.services.genai import CONTENT_GENERATOR_PROMPT, llm_cache
from app.services.genai.base import LlmMessage
from app.services.genai.factory import get_llm_client

log = get_logger("app.services.content_generator")

_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]",
    flags=re.UNICODE,
)


def _estimate_ctr(platform: str, title: str, body: str) -> float:
    """Cheap heuristic. Replace with a trained model when one is ready.

    Rules (rough, biased toward the demo baselines):
    - TikTok Shop gains the most from emoji + short hook.
    - Shopee rewards concrete shipping/discount mentions.
    - Tiki rewards 'chính hãng' / 'TikiNOW' mentions.
    """
    text = f"{title} {body}".lower()
    score = 0.045  # baseline

    if platform == "Shopee":
        if "free ship" in text or "freeship" in text:
            score += 0.025
        if any(k in text for k in ("chính hãng", "bảo hành")):
            score += 0.010
    elif platform == "Tiki":
        if "chính hãng" in text:
            score += 0.018
        if "tikinow" in text or "giao 2h" in text:
            score += 0.012
        if "đổi trả" in text:
            score += 0.008
    elif platform == "TikTok Shop":
        emoji_count = len(_EMOJI_RE.findall(f"{title} {body}"))
        score += min(0.04, emoji_count * 0.012)
        if len(title) < 50:
            score += 0.020
        if "comment" in text or "voucher" in text:
            score += 0.018
        if "best seller" in text or "🔥" in f"{title} {body}":
            score += 0.008

    # Body length penalty (over 200 chars hurts retention).
    if len(body) > 220:
        score -= 0.008
    return round(min(0.20, max(0.01, score)), 4)


def _rationale(platform: str, title: str, body: str) -> str:
    text = f"{title} {body}".lower()
    if platform == "Shopee":
        if "free ship" in text:
            return "Hero keywords: shipping hook + concrete features — Shopee ưu tiên free-ship."
        return "Tiêu chí Shopee: bullet ngắn + thông số rõ."
    if platform == "Tiki":
        if "tikinow" in text:
            return "Đề cao 'TikiNOW' + 'chính hãng' — phù hợp khách Tiki tìm đảm bảo."
        return "Tiki: tiêu đề rõ ràng + thông tin sản phẩm có cấu trúc."
    emoji = len(_EMOJI_RE.findall(f"{title} {body}"))
    if emoji:
        return f"Hook ngắn + {emoji} emoji — TikTok Shop thường thắng trên impulse."
    return "Hook ngắn, gọn — TikTok Shop ưu tiên dưới 50 ký tự."


def _demo_copy(req: ContentGeneratorRequest, platform: str) -> tuple[str, str]:
    """Ground deterministic fallback copy in the seller's actual input.

    The old demo always advertised a denim jacket, free shipping, TikiNOW and
    a seven-day return policy regardless of the submitted product. Those are
    commercial promises the platform cannot safely invent.
    """
    product = req.product_name.strip()
    features = req.features.strip()
    if platform == "Shopee":
        return product[:120], f"Điểm nổi bật:\n• {features}"
    if platform == "Tiki":
        return f"{product} | Thông tin sản phẩm"[:120], f"Thông tin nổi bật: {features}"
    return f"{product} ✨"[:120], f"Điểm nổi bật: {features}. Xem chi tiết để chọn phiên bản phù hợp."


def _fallback_variant(req: ContentGeneratorRequest, platform: str) -> ContentVariant:
    title, body = _demo_copy(req, platform)
    return ContentVariant(
        platform=platform,  # type: ignore[arg-type]
        title=title,
        body=body,
        predicted_ctr=_estimate_ctr(platform, req.product_name, body),
        rationale=_rationale(platform, req.product_name, body),
    )


async def _generate_variant(req, platform: str, llm) -> ContentVariant:  # noqa: ANN001
    prompt = CONTENT_GENERATOR_PROMPT.format(
        platform=platform,
        product_name=req.product_name,
        features=req.features,
    )
    messages = [
        LlmMessage(
            role="system",
            content=(
                "Bạn là copywriter chuyên nghiệp cho sàn TMĐT Việt Nam. "
                "Chỉ dùng dữ kiện người bán cung cấp; không tự thêm freeship, voucher, "
                "bảo hành, chính hãng, đổi trả hoặc cam kết giao hàng."
            ),
        ),
        LlmMessage(role="user", content=prompt),
    ]
    try:
        resp = await llm.chat(messages, temperature=0.7, max_tokens=400)
    except Exception as exc:
        log.warning("content_generator.variant_fallback", platform=platform, error=str(exc))
        return _fallback_variant(req, platform)

    raw_title, _, raw_body = resp.content.partition("\n")
    fallback_title, fallback_body = _demo_copy(req, platform)
    final_title = raw_title.strip()[:120] or fallback_title
    final_body = raw_body.strip()[:600] or fallback_body
    return ContentVariant(
        platform=platform,  # type: ignore[arg-type]
        title=final_title,
        body=final_body,
        predicted_ctr=_estimate_ctr(platform, final_title, final_body),
        rationale=_rationale(platform, final_title, final_body),
    )


@llm_cache(prefix="content_generator")
async def generate(req: ContentGeneratorRequest) -> ContentGeneratorResponse:
    if settings.DEMO_MODE or not (
        settings.GEMINI_API_KEY or settings.OPENAI_API_KEY or settings.OLLAMA_API_KEY
    ):
        log.info("content_generator.demo_mode")
        variants = [_fallback_variant(req, platform) for platform in req.platforms]
        return ContentGeneratorResponse(
            variants=variants,
            model="mock-demo",
            demo_mode=True,
        )

    llm = get_llm_client()
    # Platform calls are independent. Run them concurrently so generating
    # three variants costs one upstream round-trip instead of three in series.
    out = await asyncio.gather(
        *(_generate_variant(req, platform, llm) for platform in req.platforms)
    )

    return ContentGeneratorResponse(
        variants=out,
        model=llm.model,
        demo_mode=False,
    )
