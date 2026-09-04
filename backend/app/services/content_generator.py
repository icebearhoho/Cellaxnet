"""#09 Content Generator — 3 platform variants + predicted CTR."""

from __future__ import annotations

import asyncio
import re

from app.core.config import settings
from app.core.exceptions import UpstreamUnavailableError
from app.schemas.genai import ContentGeneratorRequest, ContentGeneratorResponse, ContentVariant
from app.services.genai import CONTENT_GENERATOR_PROMPT, llm_cache
from app.services.genai.base import LlmMessage
from app.services.genai.factory import get_llm_client

_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]",
    flags=re.UNICODE,
)


def _estimate_ctr(platform: str, title: str, body: str) -> float:
    """Cheap heuristic. Replace with a trained model when one is ready.

    Rules (rough, calibrated against the current catalog baselines):
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


def _test_copy(req: ContentGeneratorRequest, platform: str) -> tuple[str, str]:
    """Ground deterministic test output in the submitted product facts.

    The old fixture always advertised a denim jacket, free shipping, TikiNOW and
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


def _test_variant(req: ContentGeneratorRequest, platform: str) -> ContentVariant:
    title, body = _test_copy(req, platform)
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
    resp = await llm.chat(messages, temperature=0.7, max_tokens=400)

    # Dòng đầu là tiêu đề, phần còn lại là thân bài. Model đôi khi trả về một
    # đoạn liền không xuống dòng — khi đó cắt ở câu đầu tiên thay vì báo lỗi,
    # vì nội dung vẫn dùng được và người bán chỉ nhận một lần thất bại không
    # giải thích được.
    raw_title, _, raw_body = resp.content.partition("\n")
    if not raw_body.strip():
        head, sep, tail = resp.content.partition(". ")
        if sep and tail.strip():
            raw_title, raw_body = head + ".", tail

    final_title = raw_title.strip()[:120]
    final_body = raw_body.strip()[:600]
    if not final_title or not final_body:
        raise UpstreamUnavailableError(
            "LLM trả về nội dung không đầy đủ.", code="LLM_INVALID_RESPONSE"
        )
    return ContentVariant(
        platform=platform,  # type: ignore[arg-type]
        title=final_title,
        body=final_body,
        predicted_ctr=_estimate_ctr(platform, final_title, final_body),
        rationale=_rationale(platform, final_title, final_body),
    )


@llm_cache(prefix="content_generator")
async def generate(req: ContentGeneratorRequest) -> ContentGeneratorResponse:
    if settings.APP_ENV == "test":
        variants = [_test_variant(req, platform) for platform in req.platforms]
        return ContentGeneratorResponse(
            variants=variants,
            model="test-double",
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
    )
