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
from app.services import btc_market, insights, shopee_listings


@pytest.fixture(autouse=True)
def _demo_market(monkeypatch):
    """Pin the market side so these tests only move the cost side."""
    async def _no_reference(_category: str):
        return None

    monkeypatch.setattr(btc_market, "price_reference", _no_reference)
    # Captured Shopee listings would otherwise supply the cosmetics market
    # these tests name, and they are about the cost side, not the market one.
    monkeypatch.setattr(
        shopee_listings, "reference_for_product", lambda _name, _cat: None
    )
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
async def test_an_unreachable_marker_keeps_the_market_price() -> None:
    """The marker shows where the market is, not where the seller can go.

    Replacing it with the floor collapsed all three onto one figure and hid the
    market entirely — worst precisely when the seller most needs to see how far
    below it they are.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=180_000, min_margin_pct=35, channel="shopee")
    )

    blocked = [s for s in result.strategies if s.below_cost_floor]
    assert blocked, "this cost should rule out the cheap end"
    assert len({s.price for s in result.strategies}) == 3, "markers must stay distinct"
    assert [s.price for s in result.strategies] == [
        result.market_p25, result.category_median, result.market_p75,
    ]
    # A price below the floor loses money, and the margin says so.
    for strategy in blocked:
        assert strategy.margin_pct is not None and strategy.margin_pct < 35


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
    assert all(not s.below_cost_floor for s in result.strategies)


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


@pytest.mark.asyncio
async def test_the_reasons_walk_from_market_to_floor_to_price() -> None:
    """"Why 223,000₫ and not 210,000₫" is the question a price invites."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=183_000,
                       unit_cost=120_000, min_margin_pct=35, channel="shopee")
    )

    joined = " ".join(result.reasons)
    assert "trung vị" in joined
    assert "mức thấp nhất" in joined.lower()
    assert "Biên lợi nhuận" in joined
    assert len(result.reasons) >= 3


@pytest.mark.asyncio
async def test_accepting_the_advice_does_not_produce_more_advice() -> None:
    """The recommendation must be stable under its own output.

    The rule used to average the current price with the median, so each
    accepted suggestion moved the input closer to the median and produced a
    fresh one: 183,000₫ → 223,000₫ → 258,000₫ → 275,000₫, raising a seller's
    price four times toward a target they could have been given at once.
    """
    price = 183_000
    seen = []
    for _ in range(4):
        result = await insights.recommend_price(
            PricingRequest(product_name="X", category="Mỹ phẩm", current_price=price,
                           unit_cost=120_000, min_margin_pct=35, channel="shopee")
        )
        seen.append(result.recommended_price)
        price = result.recommended_price

    assert len(set(seen)) == 1, f"suggestion drifted: {seen}"


@pytest.mark.asyncio
async def test_the_target_is_the_market_not_the_current_price() -> None:
    """Same product, same market, same answer — wherever the seller starts."""
    cheap = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=100_000)
    )
    dear = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=900_000)
    )

    assert cheap.recommended_price == dear.recommended_price
    assert cheap.direction == "raise"
    assert dear.direction == "lower"


@pytest.mark.asyncio
async def test_a_dearer_product_is_priced_higher() -> None:
    """Cost shapes the price, it does not merely veto it.

    Anchoring purely to the market made every product with a floor below the
    median get the same suggestion, so a seller who corrected their cost saw
    nothing move and assumed the field was ignored.
    """
    cheap = await insights.recommend_price(
        PricingRequest(product_name="X", category="Thời trang", unit_cost=90_000,
                       min_margin_pct=49, channel="shopee")
    )
    dear = await insights.recommend_price(
        PricingRequest(product_name="X", category="Thời trang", unit_cost=150_000,
                       min_margin_pct=49, channel="shopee")
    )

    assert dear.recommended_price > cheap.recommended_price
    assert dear.price_floor is not None and cheap.price_floor is not None
    assert dear.recommended_price >= dear.price_floor


@pytest.mark.asyncio
async def test_the_reasons_name_the_binding_constraint() -> None:
    """When cost is low the market decides, and the panel has to say so —
    otherwise an unchanged price reads as an ignored input."""
    market_bound = await insights.recommend_price(
        PricingRequest(product_name="X", category="Thời trang", unit_cost=20_000,
                       min_margin_pct=30, channel="shopee")
    )
    cost_bound = await insights.recommend_price(
        PricingRequest(product_name="X", category="Thời trang", unit_cost=150_000,
                       min_margin_pct=49, channel="shopee")
    )

    assert any("quyết định bởi giá thị trường" in r for r in market_bound.reasons)
    assert any("Giá vốn cao" in r for r in cost_bound.reasons)


@pytest.mark.asyncio
async def test_cost_never_pushes_past_the_top_of_the_market() -> None:
    """Above p75 the reference has too little to say, so the floor governs
    alone rather than the headroom rule compounding on top of it."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Thời trang", unit_cost=250_000,
                       min_margin_pct=49, channel="shopee")
    )

    assert result.price_floor is not None
    assert result.recommended_price == max(result.market_p75 or 0, result.price_floor)


@pytest.mark.asyncio
async def test_a_product_with_no_price_yet_is_not_told_to_keep_it() -> None:
    """"Giá hiện tại đã hợp lý" about a blank field is wrong.

    Costing a new product is a real use for this screen — the seller has a cost
    and a margin target and no price at all — and it needs its own verdict.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", unit_cost=120_000,
                       min_margin_pct=35, channel="shopee")
    )

    assert result.direction == "new"
    assert result.change_vnd is None
    assert result.price_floor is not None


@pytest.mark.asyncio
async def test_a_price_without_a_cost_says_it_was_not_profit_checked() -> None:
    """Placed against competitors, not against the seller's own economics.

    Silence here is the dangerous case: a seller whose cost is 230,000₫ would
    be advised toward 277,000₫ with a margin they never asked anyone to check.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=183_000)
    )

    assert result.margin_unverified is True
    assert result.price_floor is None
    assert any("chưa kiểm tra được" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_a_cost_makes_the_recommendation_profit_checked() -> None:
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=183_000,
                       unit_cost=120_000, min_margin_pct=35, channel="shopee")
    )

    assert result.margin_unverified is False
    assert result.margin_pct_at_recommended is not None
    assert not any("chưa kiểm tra được" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_a_large_move_is_flagged_as_one() -> None:
    """The market says where the price could sit, not that buyers follow it.

    Going from 183,000₫ to 277,000₫ is a 51% rise with no conversion history
    behind it, so it is worth naming as a big step rather than presenting it
    like a 3% correction.
    """
    big = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=100_000,
                       unit_cost=80_000, min_margin_pct=35, channel="shopee")
    )
    small = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=190_000,
                       unit_cost=80_000, min_margin_pct=35, channel="shopee")
    )

    assert big.large_move is True
    assert small.large_move is False


@pytest.mark.asyncio
async def test_no_current_price_means_no_move_to_flag() -> None:
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", unit_cost=80_000,
                       min_margin_pct=35, channel="shopee")
    )

    assert result.large_move is False


@pytest.mark.asyncio
async def test_reference_labels_share_one_vocabulary() -> None:
    """They are points on a distribution, not three rival recommendations, so
    they are named after where they sit rather than what they achieve."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000)
    )

    labels = [s.label for s in result.strategies]
    assert labels == ["Nhóm giá thấp", "Trung vị thị trường", "Nhóm giá cao"]


@pytest.mark.asyncio
async def test_cost_moves_the_price_across_the_ordinary_range() -> None:
    """Cost has to bind at everyday values, not only at the extreme.

    The previous rule kept fixed headroom above the floor, which only bound
    once cost passed roughly half the median — so two cosmetics costing
    120,000₫ and 180,000₫ came back priced identically. Cost now slides the
    price across the observed range.
    """
    mid = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=110_000, min_margin_pct=35, channel="shopee")
    )
    high = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=140_000, min_margin_pct=35, channel="shopee")
    )

    assert high.recommended_price > mid.recommended_price


@pytest.mark.asyncio
async def test_a_floor_under_the_cheap_end_leaves_the_market_in_charge() -> None:
    """Below the cheapest quartile, cost is genuinely not the constraint.

    The price should not move, and the reasons have to say why — an unchanged
    number with no explanation is what makes the input look ignored.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=20_000, min_margin_pct=35, channel="shopee")
    )

    assert result.price_floor is not None
    assert result.market_p25 is not None
    assert result.price_floor < result.market_p25
    assert any("quyết định bởi giá thị trường" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_what_the_seller_keeps_always_tracks_their_cost() -> None:
    """Even when the price holds, margin and per-unit profit must not."""
    cheap = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=20_000, min_margin_pct=35, channel="shopee")
    )
    dearer = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000,
                       unit_cost=70_000, min_margin_pct=35, channel="shopee")
    )

    assert cheap.price_floor is not None and dearer.price_floor is not None
    assert dearer.price_floor > cheap.price_floor
    assert dearer.margin_pct_at_recommended < cheap.margin_pct_at_recommended
    assert dearer.profit_per_unit_at_recommended < cheap.profit_per_unit_at_recommended
    # The reference options carry the same truth in their own margins.
    assert dearer.strategies[0].margin_pct < cheap.strategies[0].margin_pct


@pytest.mark.asyncio
async def test_each_reference_price_names_its_statistic() -> None:
    """"Where does 189,000₫ come from" has to be answerable from the card.

    A price with a label and no provenance reads as a recommendation whose
    reason is being withheld; naming the percentile makes it checkable against
    the data.
    """
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000)
    )

    sources = [s.source for s in result.strategies]
    assert "Phân vị 25" in sources[0]
    assert "Phân vị 50" in sources[1]
    assert "Phân vị 75" in sources[2]


@pytest.mark.asyncio
async def test_each_reference_price_states_what_it_costs() -> None:
    """Every option trades margin against how easily the product sells, and
    stating one side without the other turns a reference into advice."""
    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=200_000)
    )

    for strategy in result.strategies:
        assert strategy.tradeoff
    # The cheap end sells more easily; the dear end earns more. Both are said.
    assert "lợi nhuận mỗi đơn thấp nhất" in result.strategies[0].tradeoff
    assert "cao nhất" in result.strategies[2].tradeoff
