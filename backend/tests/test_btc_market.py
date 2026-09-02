"""Pricing against the organisers' observed Shopee dataset.

The dataset is optional and partial, so the rules worth protecting are about
*when it is not used*: an unmapped category, too small a sample, or an
unreachable database must all fall back to the demo catalogue and label
themselves honestly, rather than pricing a jacket off a cosmetics median.
"""

from __future__ import annotations

import json

import pytest

from app.core.config import settings
from app.schemas.insights import PricingRequest
from app.services import btc_market, insights


@pytest.fixture(autouse=True)
def _isolated_dataset(monkeypatch):
    """Keep every test off the real database and off each other's state.

    The snapshot is process-cached, and a developer with BTC_DATABASE_URL in
    .env would otherwise query the organisers' RDS from a unit test. Each test
    opts back in to whichever source it is actually exercising.
    """
    monkeypatch.setattr(settings, "BTC_DATABASE_URL", None)
    btc_market._snapshot = None  # noqa: SLF001
    yield
    btc_market._snapshot = None  # noqa: SLF001


def _reference(**over) -> btc_market.PriceReference:
    base = dict(
        category="Mỹ phẩm", sample_size=141, shop_count=4, min_price=29_000,
        p25=44_900, median=67_900, p75=98_300, max_price=295_400, source="btc_live",
    )
    return btc_market.PriceReference(**{**base, **over})


def test_the_vietnamese_market_prices_none_of_the_app_categories() -> None:
    """The Vietnamese shops in reach sell confectionery, not what the app prices.

    Cosmetics data exists in the dataset, but only under country_code "id".
    Serving it to a Vietnamese seller would advise cutting prices by a quarter
    to two-fifths toward a market they do not sell in, so no category resolves
    here and all three fall back.
    """
    assert btc_market.supported_categories() == ()


def test_another_market_maps_what_it_actually_carries(monkeypatch) -> None:
    """The Indonesian rows do cover cosmetics — for a seller in that market."""
    monkeypatch.setattr(settings, "BTC_MARKET", "id")

    supported = btc_market.supported_categories()

    assert "Mỹ phẩm" in supported
    assert "Thời trang" not in supported


@pytest.mark.asyncio
async def test_unmapped_category_never_queries_the_dataset(monkeypatch) -> None:
    called = False

    async def _fail(*_a, **_kw):
        nonlocal called
        called = True
        raise AssertionError("must not query for an unmapped category")

    monkeypatch.setattr(btc_market, "_query_live", _fail)
    monkeypatch.setattr(btc_market, "_load_snapshot", dict)

    assert await btc_market.price_reference("Thời trang") is None
    assert called is False


@pytest.mark.asyncio
async def test_observed_reference_replaces_the_demo_median(monkeypatch) -> None:
    async def _ref(category: str):
        return _reference() if category == "Mỹ phẩm" else None

    monkeypatch.setattr(btc_market, "price_reference", _ref)

    result = await insights.recommend_price(
        PricingRequest(product_name="Serum", category="Mỹ phẩm", current_price=300_000)
    )

    assert result.data_source == "btc_live"
    assert result.category_median == 67_900
    assert result.sample_size == 141
    assert result.shop_count == 4
    # 300,000₫ sits far above the observed median, so the advice is to come down.
    assert result.recommended_price < 300_000


@pytest.mark.asyncio
async def test_rationale_states_which_data_it_used(monkeypatch) -> None:
    """A seller acting on the number must be able to see where it came from."""
    async def _ref(category: str):
        return _reference() if category == "Mỹ phẩm" else None

    monkeypatch.setattr(btc_market, "price_reference", _ref)

    observed = await insights.recommend_price(
        PricingRequest(product_name="Serum", category="Mỹ phẩm", current_price=300_000)
    )
    simulated = await insights.recommend_price(
        PricingRequest(product_name="Bông tai bạc 925", category="Phụ kiện",
                       current_price=300_000)
    )

    assert "Shopee" in observed.rationale and "4 nhà bán" in observed.rationale
    # Vietnamese thousands separator, not Python's default comma.
    assert "67.900₫" in observed.rationale
    # The catalogue fallback names no source. It used to say "mô phỏng", which
    # was removed from the copy; what still has to hold is that it never
    # claims Shopee for numbers that did not come from there.
    assert "Shopee" not in simulated.rationale
    assert simulated.market_label is None


@pytest.mark.asyncio
async def test_unreachable_database_falls_back_to_the_snapshot(monkeypatch, tmp_path) -> None:
    """A demo must not drop back to synthetic numbers over someone else's outage."""
    monkeypatch.setattr(settings, "BTC_MARKET", "id")
    snapshot = tmp_path / "btc_price_reference.json"
    snapshot.write_text(
        json.dumps({
            "generated_at": "2026-07-21T00:00:00+00:00",
            "market": "id",
            "categories": {
                "Mỹ phẩm": {
                    "sample_size": 141, "shop_count": 4, "min_price": 29_000,
                    "p25": 44_900, "median": 67_900, "p75": 98_300, "max_price": 295_400,
                }
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(btc_market, "_SNAPSHOT_PATH", snapshot)

    async def _no_live(_category: str):
        return None

    monkeypatch.setattr(btc_market, "_query_live", _no_live)

    ref = await btc_market.price_reference("Mỹ phẩm")

    assert ref is not None
    assert ref.source == "btc_snapshot"
    assert ref.median == 67_900


@pytest.mark.asyncio
async def test_a_sample_too_small_to_be_a_reference_is_ignored(monkeypatch, tmp_path) -> None:
    """Percentiles over a handful of rows describe the sample, not the market."""
    monkeypatch.setattr(settings, "BTC_MARKET", "id")
    snapshot = tmp_path / "btc_price_reference.json"
    snapshot.write_text(
        json.dumps({
            "market": "id",
            "categories": {
                "Mỹ phẩm": {
                    "sample_size": 3, "shop_count": 1, "min_price": 29_000,
                    "p25": 30_000, "median": 31_000, "p75": 32_000, "max_price": 33_000,
                }
            },
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(btc_market, "_SNAPSHOT_PATH", snapshot)

    async def _no_live(_category: str):
        return None

    monkeypatch.setattr(btc_market, "_query_live", _no_live)

    assert await btc_market.price_reference("Mỹ phẩm") is None


@pytest.mark.asyncio
async def test_missing_snapshot_file_is_not_an_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "BTC_MARKET", "id")
    monkeypatch.setattr(btc_market, "_SNAPSHOT_PATH", tmp_path / "absent.json")

    async def _no_live(_category: str):
        return None

    monkeypatch.setattr(btc_market, "_query_live", _no_live)

    assert await btc_market.price_reference("Mỹ phẩm") is None


@pytest.mark.asyncio
async def test_pricing_still_works_with_no_dataset_configured() -> None:
    """With the dataset switched off entirely, pricing keeps working."""
    result = await insights.recommend_price(
        PricingRequest(product_name="Bông tai bạc 925", category="Phụ kiện",
                       current_price=468_000)
    )

    assert result.data_source == "demo"
    assert result.sample_size > 0
    assert result.recommended_price > 0


@pytest.mark.asyncio
async def test_price_is_placed_within_the_observed_distribution(monkeypatch) -> None:
    """A gap to the median says how far; the percentile says how unusual.

    502,000₫ against a 67,900₫ median reads as "3.5x over", which sounds like
    an error. "Dearer than nearly everything on sale" is the same fact stated
    so a seller can act on it.
    """
    async def _ref(category: str):
        return _reference(prices=tuple(range(10_000, 210_000, 10_000))) \
            if category == "Mỹ phẩm" else None

    monkeypatch.setattr(btc_market, "price_reference", _ref)

    top = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=500_000)
    )
    middle = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=100_000)
    )

    assert top.price_percentile == 100
    assert "gần như toàn bộ" in top.rationale
    assert middle.price_percentile == 50
    assert "đắt hơn 50%" in middle.rationale


def test_percentile_declines_to_answer_without_prices() -> None:
    """An older snapshot carries no price list; guessing one would be worse."""
    assert _reference(prices=()).percentile_of(50_000) is None


def test_percentile_counts_prices_at_or_below() -> None:
    ref = _reference(prices=(10, 20, 30, 40))

    assert ref.percentile_of(5) == 0
    assert ref.percentile_of(20) == 50
    assert ref.percentile_of(40) == 100


@pytest.mark.asyncio
async def test_quartiles_travel_with_the_response(monkeypatch) -> None:
    """The spread a median hides: same median, very different categories."""
    async def _ref(category: str):
        return _reference() if category == "Mỹ phẩm" else None

    monkeypatch.setattr(btc_market, "price_reference", _ref)

    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=100_000)
    )

    assert result.market_p25 == 44_900
    assert result.market_p75 == 98_300


@pytest.mark.asyncio
async def test_the_label_names_the_market_actually_measured(monkeypatch) -> None:
    """Shopee runs a marketplace per country, each at its own price level.

    The accessible cosmetics rows are Indonesian, so calling them "Shopee" in a
    Vietnamese UI would read as the seller's own market and quietly misprice
    every recommendation drawn from them.
    """
    async def _ref(category: str):
        return _reference(countries=("id",)) if category == "Mỹ phẩm" else None

    monkeypatch.setattr(btc_market, "price_reference", _ref)

    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=183_000)
    )

    assert result.market_label == "Shopee Indonesia"
    assert "Shopee Indonesia" in result.rationale


@pytest.mark.asyncio
async def test_a_blended_sample_names_every_market(monkeypatch) -> None:
    """Percentiles spanning two markets must not claim to describe one."""
    async def _ref(category: str):
        return _reference(countries=("id", "vn")) if category == "Mỹ phẩm" else None

    monkeypatch.setattr(btc_market, "price_reference", _ref)

    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Mỹ phẩm", current_price=183_000)
    )

    assert result.market_label == "Shopee Indonesia + Shopee Việt Nam"


@pytest.mark.asyncio
async def test_the_demo_catalogue_claims_no_market(monkeypatch) -> None:
    async def _no_reference(_category: str):
        return None

    monkeypatch.setattr(btc_market, "price_reference", _no_reference)

    result = await insights.recommend_price(
        PricingRequest(product_name="X", category="Thời trang", current_price=468_000)
    )

    assert result.market_label is None
