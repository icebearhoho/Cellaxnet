"""Storefront gallery and review-count contract tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_storefront_products_have_distinct_ten_image_galleries():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/storefront/products")

    assert response.status_code == 200
    products = response.json()["data"]["products"]
    assert products
    for product in products:
        assert len(product["image_urls"]) == 10
        assert len(set(product["image_urls"])) == 10
        assert product["image_url"] == product["image_urls"][0]


@pytest.mark.asyncio
async def test_storefront_detail_review_count_matches_rendered_reviews():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        listing = await ac.get("/api/v1/storefront/products")
        product_id = listing.json()["data"]["products"][0]["id"]
        response = await ac.get(f"/api/v1/storefront/products/{product_id}")

    assert response.status_code == 200
    detail = response.json()["data"]
    # The coherent shop snapshot keeps a richer 12-28 review history per SKU.
    assert 12 <= len(detail["review_items"]) <= 28
    assert detail["product"]["reviews"] == len(detail["review_items"])
