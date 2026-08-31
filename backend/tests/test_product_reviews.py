"""Reading a product's reviews as a set.

The screen used to score one pasted sentence, which answers "what does this
say" — something the seller could already tell. What they cannot do by hand is
read two hundred reviews and notice the shape of them, so the unit here is the
product, not the sentence.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import commerce_store


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _product_id() -> str:
    return commerce_store.all_products()[0]["id"]


async def _fetch(product_id: str, headers: dict[str, str]) -> dict:
    async with _client() as ac:
        response = await ac.get(
            f"/api/v1/review-sentiment/products/{product_id}", headers=headers
        )
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_a_product_returns_all_of_its_reviews_scored(admin_headers) -> None:
    data = await _fetch(_product_id(), admin_headers)

    assert data["total"] == len(data["reviews"])
    assert data["total"] > 0
    assert all(r["sentiment"] in {"positive", "neutral", "negative"} for r in data["reviews"])
    assert all(r["text"] for r in data["reviews"])


@pytest.mark.asyncio
async def test_the_counts_reconcile_with_the_list(admin_headers) -> None:
    """The summary sits above the reviews it summarises; if the two disagree
    the reader has no way to tell which is wrong."""
    data = await _fetch(_product_id(), admin_headers)

    assert data["positive"] + data["neutral"] + data["negative"] == data["total"]
    assert data["positive"] == sum(1 for r in data["reviews"] if r["sentiment"] == "positive")
    assert data["negative"] == sum(1 for r in data["reviews"] if r["sentiment"] == "negative")


@pytest.mark.asyncio
async def test_reviews_are_ordered_newest_first(admin_headers) -> None:
    """A seller scanning for a problem reads down from the top."""
    data = await _fetch(_product_id(), admin_headers)
    ages = [r["days_ago"] for r in data["reviews"] if r["days_ago"] is not None]

    assert ages == sorted(ages)


@pytest.mark.asyncio
async def test_the_average_rating_matches_the_reviews_shown(admin_headers) -> None:
    data = await _fetch(_product_id(), admin_headers)
    expected = round(sum(r["rating"] for r in data["reviews"]) / len(data["reviews"]), 1)

    assert data["avg_rating"] == expected


@pytest.mark.asyncio
async def test_an_unknown_product_is_an_error_not_an_empty_list(admin_headers) -> None:
    """Silence would read as "this product has no reviews", which is a
    different fact from "no such product"."""
    async with _client() as ac:
        response = await ac.get(
            "/api/v1/review-sentiment/products/khong-ton-tai-99", headers=admin_headers
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_customer_submitted_reviews_stay_distinguishable(admin_headers) -> None:
    """A seller reads their own buyers' words differently from sample data, so
    the two sources are merged but never blended."""
    data = await _fetch(_product_id(), admin_headers)

    assert all(isinstance(r["from_customers"], bool) for r in data["reviews"])
