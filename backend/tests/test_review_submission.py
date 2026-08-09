"""POST /storefront/products/{pid}/reviews — submission + moderation queue.

No DB fixture exists in this repo yet (see backend/tests/conftest.py), so
``review_service`` is monkeypatched with a tiny in-memory store rather than
hitting a real Postgres — this exercises the endpoint contract and the real
moderation policy (via mocked ``insights``), not the SQL itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.insights import FakeReviewResponse, SentimentResponse
from app.services import insights, review_service


@dataclass
class _FakeReview:
    id: int
    product_id: str
    author_name: str
    rating: int
    text: str
    status: str
    moderation_reason: str | None
    moderation_confidence: float | None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class _FakeStore:
    def __init__(self):
        self.rows: dict[int, _FakeReview] = {}
        self._next_id = 1

    async def create_review(self, db, *, product_id, req, category):
        from app.services import review_moderation

        decision = await review_moderation.moderate(req.text, req.rating, category)
        row = _FakeReview(
            id=self._next_id, product_id=product_id, author_name=req.author_name,
            rating=req.rating, text=req.text, status=decision.status,
            moderation_reason=decision.reason, moderation_confidence=decision.confidence,
        )
        self.rows[row.id] = row
        self._next_id += 1
        return row

    async def list_published_reviews(self, db, product_id):
        return [r for r in self.rows.values() if r.product_id == product_id and r.status == "published"]

    async def list_queue(self, db):
        return [r for r in self.rows.values() if r.status in ("pending", "flagged")]

    async def set_status(self, db, review_id, status):
        row = self.rows[review_id]
        row.status = status
        return row


@pytest.fixture
def fake_store(monkeypatch):
    store = _FakeStore()
    monkeypatch.setattr(review_service, "create_review", store.create_review)
    monkeypatch.setattr(review_service, "list_published_reviews", store.list_published_reviews)
    monkeypatch.setattr(review_service, "list_queue", store.list_queue)
    monkeypatch.setattr(review_service, "set_status", store.set_status)
    return store


def _patch_insights(monkeypatch, *, is_fake: bool, fake_confidence: float, sentiment: str):
    async def fake_detect_fake(req):
        return FakeReviewResponse(is_fake=is_fake, confidence=fake_confidence, signals=[], reason="mock")

    async def fake_analyze_sentiment(req):
        return SentimentResponse(sentiment=sentiment, confidence=0.8, reason="mock")

    monkeypatch.setattr(insights, "detect_fake", fake_detect_fake)
    monkeypatch.setattr(insights, "analyze_sentiment", fake_analyze_sentiment)


@pytest.mark.asyncio
async def test_detailed_review_is_published_immediately(fake_store, monkeypatch):
    _patch_insights(monkeypatch, is_fake=False, fake_confidence=0.6, sentiment="positive")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listing = await ac.get("/api/v1/storefront/products")
        pid = listing.json()["data"]["products"][0]["id"]

        response = await ac.post(
            f"/api/v1/storefront/products/{pid}/reviews",
            json={"author_name": "Minh", "rating": 5,
                  "text": "Vải mát, form chuẩn, giao nhanh, đóng gói kỹ, rất ưng sản phẩm này."},
        )
        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "published"
        assert body["review"] is not None

        detail = await ac.get(f"/api/v1/storefront/products/{pid}")
        review_items = detail.json()["data"]["review_items"]
        assert any(r["author"] == "Minh" for r in review_items)


@pytest.mark.asyncio
async def test_generic_short_review_is_flagged_not_published(fake_store, monkeypatch):
    _patch_insights(monkeypatch, is_fake=True, fake_confidence=0.9, sentiment="positive")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listing = await ac.get("/api/v1/storefront/products")
        pid = listing.json()["data"]["products"][0]["id"]

        response = await ac.post(
            f"/api/v1/storefront/products/{pid}/reviews",
            json={"author_name": "Anh", "rating": 5, "text": "Great! Love it! Best ever!"},
        )
        assert response.status_code == 200
        body = response.json()["data"]
        assert body["status"] == "rejected"
        assert body["review"] is None

        detail = await ac.get(f"/api/v1/storefront/products/{pid}")
        review_items = detail.json()["data"]["review_items"]
        assert not any(r["author"] == "Anh" for r in review_items)


@pytest.mark.asyncio
async def test_flagged_review_appears_in_queue_and_approve_publishes_it(fake_store, monkeypatch):
    _patch_insights(monkeypatch, is_fake=False, fake_confidence=0.6, sentiment="positive")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listing = await ac.get("/api/v1/storefront/products")
        pid = listing.json()["data"]["products"][0]["id"]

        submit = await ac.post(
            f"/api/v1/storefront/products/{pid}/reviews",
            json={"author_name": "Kiet", "rating": 5, "text": "tốt lắm"},  # too short -> flagged
        )
        assert submit.json()["data"]["status"] == "flagged"

        queue = await ac.get("/api/v1/storefront/reviews/queue")
        queue_items = queue.json()["data"]
        assert any(r["author_name"] == "Kiet" for r in queue_items)
        review_id = next(r["id"] for r in queue_items if r["author_name"] == "Kiet")

        approve = await ac.post(f"/api/v1/storefront/reviews/{review_id}/approve")
        assert approve.json()["data"]["status"] == "published"

        detail = await ac.get(f"/api/v1/storefront/products/{pid}")
        review_items = detail.json()["data"]["review_items"]
        assert any(r["author"] == "Kiet" for r in review_items)
