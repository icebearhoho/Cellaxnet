"""Pure unit tests for the review moderation policy.

`insights.detect_fake`/`analyze_sentiment` are monkeypatched with canned
responses so this test is deterministic regardless of the ambient
DEMO_MODE/API-key configuration (a local dev `.env` may point at a real LLM).
"""

from __future__ import annotations

import pytest

from app.schemas.insights import FakeReviewResponse, SentimentResponse
from app.services import insights, review_moderation


def _patch_insights(monkeypatch, *, is_fake: bool, fake_confidence: float,
                    sentiment: str, sentiment_confidence: float = 0.8):
    async def fake_detect_fake(req):
        return FakeReviewResponse(
            is_fake=is_fake, confidence=fake_confidence,
            signals=["mock signal"], reason="mock reason",
        )

    async def fake_analyze_sentiment(req):
        return SentimentResponse(sentiment=sentiment, confidence=sentiment_confidence, reason="mock reason")

    monkeypatch.setattr(insights, "detect_fake", fake_detect_fake)
    monkeypatch.setattr(insights, "analyze_sentiment", fake_analyze_sentiment)


@pytest.mark.asyncio
async def test_detailed_aligned_review_is_published(monkeypatch):
    _patch_insights(monkeypatch, is_fake=False, fake_confidence=0.6, sentiment="positive")
    decision = await review_moderation.moderate(
        "Vải mát, form chuẩn, giao nhanh, đóng gói kỹ, rất ưng ý sản phẩm này.", 5, "Thời trang",
    )
    assert decision.status == "published"


@pytest.mark.asyncio
async def test_high_confidence_fake_is_flagged_for_human_review(monkeypatch):
    _patch_insights(monkeypatch, is_fake=True, fake_confidence=0.9, sentiment="positive")
    decision = await review_moderation.moderate("Amazing! Love it! Best product ever!", 5, "Thời trang")
    assert decision.status == "flagged"


@pytest.mark.asyncio
async def test_low_confidence_fake_is_flagged_not_rejected(monkeypatch):
    _patch_insights(monkeypatch, is_fake=True, fake_confidence=0.55, sentiment="positive")
    decision = await review_moderation.moderate("Good quality nice product", 5, "Thời trang")
    assert decision.status == "flagged"


@pytest.mark.asyncio
async def test_very_short_text_is_flagged(monkeypatch):
    _patch_insights(monkeypatch, is_fake=False, fake_confidence=0.6, sentiment="positive")
    decision = await review_moderation.moderate("tốt lắm", 5, "Thời trang")
    assert decision.status == "flagged"


@pytest.mark.asyncio
async def test_rating_sentiment_mismatch_is_flagged(monkeypatch):
    _patch_insights(monkeypatch, is_fake=False, fake_confidence=0.6, sentiment="negative")
    decision = await review_moderation.moderate(
        "Sản phẩm giao trễ, chất lượng không như mong đợi, vải khá mỏng.", 5, "Thời trang",
    )
    assert decision.status == "flagged"
