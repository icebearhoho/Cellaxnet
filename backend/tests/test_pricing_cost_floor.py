"""The margin floor under a price recommendation.

Following the market is only useful while it still pays. These tests pin the
part that is easy to get subtly wrong: the channel's commission is a deduction
from the same sticker price the margin is measured against, so a floor built
from cost and margin alone is too low and quietly under-delivers on every
order.
"""

from __future__ import annotations

import pytest

from app.schemas.insights import PricingRequest
from app.services import btc_market, insights


@pytest.fixture(autouse=True)
def _demo_market(monkeypatch):
    """Pin the market side so these tests only move the cost side."""
    async def _no_reference(_category: str):
        return None

    monkeypatch.setattr(btc_market, "price_reference", _no_reference)
    monkeypatch.setattr(insights, "_category_price_stats", lambda _c: insights._PriceStats(  # noqa: SLF001
        median=200_000, p25=150_000, p75=260_000, sample_size=20, source="demo",
    ))


@pytest.mark.asyncio
async def test_without_a_cost_nothing_changes() -> None:
    """The floor is opt-in: a seller who gives no cost still gets advice."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000)
    )

    assert result.price_floor is None
    assert result.margin_pct_at_recommended is None
    assert result.channel_commission_pct is None


@pytest.mark.asyncio
async def test_commission_raises_the_floor() -> None:
    """Shopee keeps 5%, so the same cost and margin need a higher price."""
    args = dict(product_name="X", category="Mỹ phẩm", current_price=200_000,
                unit_cost=80_000, min_margin_pct=30)

    no_channel = await insights.recommend_price(PricingRequest(**args))
    on_shopee = await insights.recommend_price(PricingRequest(**args, channel="shopee"))

    assert no_channel.price_floor is not None and on_shopee.price_floor is not None
    assert on_shopee.price_floor > no_channel.price_floor
    assert on_shopee.channel_commission_pct == 5.0
    assert on_shopee.channel_name == "Shopee"


@pytest.mark.asyncio
async def test_the_floor_delivers_the_margin_it_promises() -> None:
    """Priced at the floor, profit must be the requested share of that price.

    Margin is taken on the sticker price, matching market.py, so commission is
    just another deduction: cost / (1 - commission - margin). Solving instead
    for a margin on post-commission revenue lands ~1.3 points low here, which
    a seller would never spot from the number alone.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=90_000,
                       unit_cost=80_000, min_margin_pct=30, channel="shopee")
    )

    assert result.price_floor is not None
    profit = result.price_floor * (1 - 0.05) - 80_000
    assert profit / result.price_floor == pytest.approx(0.30, abs=0.01)


@pytest.mark.asyncio
async def test_worked_example_cost_520k_shopee_20pct() -> None:
    """A hand-checkable case: 520,000₫ at 5% commission and a 20% margin.

    520,000 / (1 - 0.05 - 0.20) = 693,333₫, rounded up to the next 100₫.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=600_000,
                       unit_cost=520_000, min_margin_pct=20, channel="shopee")
    )

    assert result.price_floor == 693_400
    assert result.margin_pct_at_recommended == pytest.approx(20.0, abs=0.1)


@pytest.mark.asyncio
async def test_a_price_below_the_floor_is_lifted_to_it() -> None:
    """The market says 200,000₫; the cost says that is a loss. Cost wins."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=190_000, min_margin_pct=30, channel="shopee")
    )

    assert result.floor_above_market is True
    assert result.recommended_price == result.price_floor
    assert result.recommended_price > 200_000
    assert "giá vốn" in result.rationale


@pytest.mark.asyncio
async def test_a_comfortable_margin_leaves_the_recommendation_alone() -> None:
    """A floor well under the market must not drag the suggestion upward."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=20_000, min_margin_pct=30, channel="shopee")
    )

    assert result.floor_above_market is False
    assert result.recommended_price > result.price_floor
    assert result.margin_pct_at_recommended > 30


@pytest.mark.asyncio
async def test_reported_margin_is_net_of_commission() -> None:
    """The margin shown is what the seller keeps, not what the price implies."""
    with_fee = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=50_000, min_margin_pct=10, channel="shopee")
    )
    without_fee = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=50_000, min_margin_pct=10)
    )

    assert with_fee.recommended_price == without_fee.recommended_price
    assert with_fee.margin_pct_at_recommended < without_fee.margin_pct_at_recommended


@pytest.mark.asyncio
async def test_an_unknown_channel_charges_no_fee_rather_than_guessing() -> None:
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=80_000, min_margin_pct=30, channel="khong-ton-tai")
    )

    assert result.channel_commission_pct == 0.0
    assert result.channel_name is None


@pytest.mark.asyncio
async def test_own_storefront_is_cheaper_than_a_marketplace() -> None:
    """2% against 5% — the floor should reflect the channel actually chosen."""
    args = dict(product_name="X", category="Mỹ phẩm", current_price=200_000,
                unit_cost=80_000, min_margin_pct=30)

    own = await insights.recommend_price(PricingRequest(**args, channel="own"))
    shopee = await insights.recommend_price(PricingRequest(**args, channel="shopee"))

    assert own.price_floor < shopee.price_floor
