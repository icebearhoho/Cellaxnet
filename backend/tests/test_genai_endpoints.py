"""Tests for the 4 fullstack GenAI endpoints + their envelope shape.

DEMO_MODE is on by default in Settings, so these tests exercise the
mock client path. They verify the contract the frontend consumes:
shape, key fields, demo_mode flag.

The shared test environment forces demo mode so CI never depends on an API key,
quota, network timing, or a provider client bound to another event loop.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.genai.cache import _LOCAL_CACHE


def _setup() -> None:
    """Clear in-process cache + reset lru_cache factories between tests."""
    _LOCAL_CACHE.clear()
    from app.services.genai import factory

    factory.get_llm_client.cache_clear()
    factory.get_rag.cache_clear()


@pytest.mark.asyncio
async def test_shopper_products_returns_envelope():
    _setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/api/v1/personal-shopper/products",
            params={"query": "son cho da ngăm", "top_k": 3},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert len(body["data"]["products"]) <= 3
    for p in body["data"]["products"]:
        assert p["platform"] in ("Shopee", "Tiki", "TikTok Shop")
        assert 0.0 <= p["similarity"] <= 1.0


@pytest.mark.asyncio
async def test_shopper_respects_explicit_budget_ceiling():
    _setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(
            "/api/v1/personal-shopper/products",
            params={"query": "serum cho da dầu dưới 400k", "top_k": 8},
        )
    assert r.status_code == 200
    products = r.json()["data"]["products"]
    assert products
    assert all(product["price_vnd"] <= 400_000 for product in products)


@pytest.mark.asyncio
async def test_shopper_chat_streams_sse():
    _setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac, ac.stream(
        "POST",
        "/api/v1/personal-shopper/",
        json={"query": "quà sinh nhật 500k", "top_k": 3, "stream": True},
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        payload = b""
        async for chunk in r.aiter_bytes():
            payload += chunk
    text = payload.decode()
    # The mock client streams several chunks + a done frame.
    assert text.count("data: ") >= 5
    assert '"finish_reason": "stop"' in text
    assert '"done": true' in text


@pytest.mark.asyncio
async def test_content_generator_returns_three_variants(admin_headers):
    _setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/content-generator/",
            json={
                "product_name": "Áo khoác denim unisex",
                "features": "Denim 12oz, wash nhẹ, free ship",
            },
            headers=admin_headers,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    # Reported either way — asserting a specific value would just be
    # asserting this machine's DEMO_MODE setting.
    assert isinstance(body["data"]["demo_mode"], bool)
    variants = body["data"]["variants"]
    platforms = {v["platform"] for v in variants}
    assert {"Shopee", "Tiki", "TikTok Shop"}.issubset(platforms)
    for v in variants:
        assert 0.0 <= v["predicted_ctr"] <= 1.0
        assert v["title"]
        assert v["body"]


@pytest.mark.asyncio
async def test_recsys_ai_mode_with_signals():
    _setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/recsys/",
            json={
                "user_id": "u-42",
                "signals": {"skin_type": "dry", "bought_30d": "BHA serum"},
                "top_k": 4,
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    assert data["mode"] == "ai"
    assert len(data["items"]) == 4
    assert data["metrics"]["recall_at_10"] > 0.15
    for item in data["items"]:
        assert item["reason"]


@pytest.mark.asyncio
async def test_recsys_traditional_mode():
    _setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/recsys/",
            json={"user_id": "cf:legacy", "signals": {}, "top_k": 4},
        )
    body = r.json()
    assert body["data"]["mode"] == "traditional"


@pytest.mark.asyncio
async def test_seller_coach_returns_audit_and_roadmap(admin_headers):
    _setup()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/seller-coach/",
            json={"seller_id": "shop-001"},
            headers=admin_headers,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data["demo_mode"], bool)
    assert 0 <= data["overall"] <= 100
    assert len(data["audit"]) == 5
    assert len(data["roadmap"]) == 4
    for step in data["audit"]:
        assert 0 <= step["score"] <= 100
        assert step["tip"]
    for week in data["roadmap"]:
        assert 1 <= week["week"] <= 4
        assert week["bullets"]
