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
    assert profit / result.price_floor >= 0.30


@pytest.mark.asyncio
async def test_worked_example_cost_520k_shopee_20pct() -> None:
    """A hand-checkable case: 520,000₫ at 5% commission and a 20% margin.

    520,000 / (1 - 0.05 - 0.20) = 693,333₫, rounded up to the next 1,000₫.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=600_000,
                       unit_cost=520_000, min_margin_pct=20, channel="shopee")
    )

    assert result.price_floor == 694_000
    # Rounding up lands at or just above the request, never below it.
    assert result.margin_pct_at_recommended is not None
    assert 20.0 <= result.margin_pct_at_recommended <= 20.3


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


@pytest.mark.asyncio
async def test_stock_that_turns_over_quickly_is_left_alone() -> None:
    """Discounting stock that clears in three weeks just gives away margin."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       stock_units=100, daily_sales=5)
    )

    assert result.stock_runway_days == 20
    assert result.price_action is None


@pytest.mark.asyncio
async def test_slow_stock_is_discounted_in_two_steps() -> None:
    """Sixty days earns a nudge, ninety a firmer one — capital sitting still
    costs more the longer it sits."""
    mild = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       stock_units=130, daily_sales=2)
    )
    deep = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       stock_units=120, daily_sales=1)
    )

    assert mild.price_action == "clearance"
    assert deep.price_action == "clearance"
    assert deep.recommended_price < mild.recommended_price
    assert "quay vòng vốn" in deep.rationale


@pytest.mark.asyncio
async def test_the_margin_floor_outranks_clearance() -> None:
    """Turnover is worth less than the margin it would cost.

    Slow stock and a cost that leaves no room point opposite ways; the floor
    wins, and the response says so rather than quoting a clearance price it
    then overrode.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=250_000, min_margin_pct=50, channel="shopee",
                       stock_units=120, daily_sales=1)
    )

    assert result.stock_runway_days == 120
    assert result.price_action == "margin"
    assert result.recommended_price == result.price_floor


@pytest.mark.asyncio
async def test_no_stock_figures_means_no_clearance_verdict() -> None:
    """The rule is opt-in: without both numbers there is no runway to judge."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       stock_units=500)
    )

    assert result.stock_runway_days is None
    assert result.price_action is None


@pytest.mark.asyncio
async def test_three_strategies_sit_at_the_market_quartiles() -> None:
    """Pricing is a choice, and the options are real market positions.

    p25 / median / p75 come from the reference itself, so "cheaper than three
    quarters of the market" is a fact about competitors rather than a discount
    invented for the screen.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000)
    )

    assert [s.key for s in result.strategies] == ["volume", "balanced", "margin"]
    assert [s.price for s in result.strategies] == [
        result.market_p25, result.category_median, result.market_p75,
    ]


@pytest.mark.asyncio
async def test_a_strategy_that_cannot_be_sold_at_a_profit_is_lifted() -> None:
    """An option below the floor is not an option.

    With a cost that rules out the cheaper end, those strategies move up to the
    floor and say so — quietly quoting a losing price would be worse than
    offering fewer choices.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=180_000, min_margin_pct=35, channel="shopee")
    )

    lifted = [s for s in result.strategies if s.lifted_by_floor]
    assert lifted, "a high cost should push the cheap end up to the floor"
    for strategy in result.strategies:
        assert strategy.price >= (result.price_floor or 0)
    for strategy in lifted:
        assert strategy.price == result.price_floor


@pytest.mark.asyncio
async def test_strategy_margins_are_reported_after_commission() -> None:
    """The margin beside each option is what the seller keeps at that price."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=50_000, min_margin_pct=20, channel="shopee")
    )

    margins = [s.margin_pct for s in result.strategies]
    assert all(m is not None for m in margins)
    # Dearer options keep more per unit; that is the trade being offered.
    assert margins == sorted(margins)


@pytest.mark.asyncio
async def test_strategies_need_no_cost_to_be_offered() -> None:
    """Without a cost there is no margin to show, but the positions still hold."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Thời trang", current_price=400_000)
    )

    assert len(result.strategies) == 3
    assert all(s.margin_pct is None for s in result.strategies)
    assert all(not s.lifted_by_floor for s in result.strategies)


@pytest.mark.asyncio
async def test_the_verdict_is_one_word() -> None:
    """A seller reads the direction before any number, so it has to be right."""
    under = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=100_000)
    )
    over = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=600_000)
    )

    assert under.direction == "raise"
    assert under.change_vnd is not None and under.change_vnd > 0
    assert over.direction == "lower"
    assert over.change_vnd is not None and over.change_vnd < 0


@pytest.mark.asyncio
async def test_a_move_too_small_to_matter_says_keep() -> None:
    """Advising a 1% change on a reference price is worse than saying nothing."""
    priced_at_median = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000)
    )
    nudged = await insights.recommend_price(
        PricingRequest(
            product_name="X", category="Mỹ phẩm",
            current_price=priced_at_median.recommended_price,
        )
    )

    assert nudged.direction == "keep"


@pytest.mark.asyncio
async def test_the_price_is_rounded_to_thousands() -> None:
    """The inputs are references; 222,900₫ implies precision they do not have."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=183_000)
    )

    assert result.recommended_price % 1000 == 0


@pytest.mark.asyncio
async def test_rounding_never_drops_below_the_floor() -> None:
    """Rounding down through the floor would undo the guarantee it makes."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=100_000,
                       unit_cost=190_000, min_margin_pct=35, channel="shopee")
    )

    assert result.price_floor is not None
    assert result.recommended_price >= result.price_floor


@pytest.mark.asyncio
async def test_impact_shows_what_changes_per_unit() -> None:
    """"You keep 41% instead of 29%" is the reason to act on the advice."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=183_000,
                       unit_cost=120_000, min_margin_pct=35, channel="shopee")
    )

    assert result.margin_pct_now is not None
    assert result.margin_pct_at_recommended is not None
    assert result.profit_per_unit_now is not None
    assert result.profit_per_unit_at_recommended is not None
    # Raising the price raises both, and the pair has to move together.
    assert result.profit_per_unit_at_recommended > result.profit_per_unit_now
    assert result.margin_pct_at_recommended > result.margin_pct_now


@pytest.mark.asyncio
async def test_strategy_names_describe_position_not_outcome() -> None:
    """Total profit is quantity x margin, and nothing here models quantity.

    Naming the top quartile "maximum profit" would assert what the system
    cannot know: it may sell to nobody at that price.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000)
    )

    labels = " ".join(s.label for s in result.strategies)
    assert "Tối đa lợi nhuận" not in labels
    assert "Tăng doanh số" not in labels
