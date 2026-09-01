"""Hand-captured Shopee prices as a market reference.

This replaces a comparison that was quietly circular: the demo catalogue was
being used as "the market", so a seller's price was ranked against their own
other products and labelled thị trường. These are competing shops' real
listings, so the ranking finally means what the screen says it means.

Seed data has its own failure modes, and the tests below pin them: a category
nobody captured must fall back rather than borrow, bundles must not drag the
quartiles, and the response must say when the prices were read.
"""

from __future__ import annotations

import pytest

from app.schemas.insights import PricingRequest
from app.services import btc_market, insights, shopee_listings


@pytest.fixture(autouse=True)
def _no_organiser_dataset(monkeypatch):
    """The captured listings are the fallback *after* the organisers' data."""
    async def _none(_category: str):
        return None

    monkeypatch.setattr(btc_market, "price_reference", _none)


def test_a_captured_keyword_yields_a_usable_reference() -> None:
    ref = shopee_listings.reference_for_product("Serum Vitamin C 15%", "Mỹ phẩm")

    assert ref is not None
    assert ref.keyword == "serum vitamin c"
    assert ref.sample_size >= 15
    assert ref.p25 < ref.median < ref.p75


def test_bundles_and_strays_do_not_set_the_quartiles() -> None:
    """Search results mix single products with combos and gift sets.

    A 59,000₫ trial size and a 954,000₫ bundle are both real listings and both
    misleading as the edge of the market, so the extremes are trimmed.
    """
    ref = shopee_listings.reference_for_product("Serum Vitamin C 15%", "Mỹ phẩm")

    assert ref is not None
    assert min(ref.prices) > 59_000
    assert max(ref.prices) < 954_000


def test_an_uncaptured_category_returns_nothing() -> None:
    """Borrowing a cosmetics median for a jacket is the error this whole
    reference exists to remove, so silence is the right answer."""
    assert shopee_listings.reference_for_product("Áo thun cotton", "Thời trang") is None


@pytest.mark.asyncio
async def test_pricing_uses_the_captured_listings() -> None:
    result = await insights.recommend_price(
        PricingRequest(product_name="Serum Vitamin C 15%", category="Mỹ phẩm",
                       current_price=183_000)
    )

    assert result.data_source == "shopee_seed"
    assert result.market_label is not None
    # Seed data ages; the label has to say when it was read.
    assert "quan sát" in result.market_label


@pytest.mark.asyncio
async def test_an_uncaptured_category_falls_back_to_the_catalogue() -> None:
    result = await insights.recommend_price(
        PricingRequest(product_name="Áo thun cotton unisex", category="Thời trang",
                       current_price=200_000)
    )

    assert result.data_source == "demo"
    assert result.market_label is None


@pytest.mark.asyncio
async def test_the_three_markers_come_from_the_captured_prices() -> None:
    """The markers are the reference's own quartiles, not derived twice."""
    ref = shopee_listings.reference_for_product("Serum Vitamin C 15%", "Mỹ phẩm")
    result = await insights.recommend_price(
        PricingRequest(product_name="Serum Vitamin C 15%", category="Mỹ phẩm",
                       current_price=183_000)
    )

    assert ref is not None
    assert [s.price for s in result.strategies] == [ref.p25, ref.median, ref.p75]
