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


def test_fashion_and_accessories_are_not_mapped() -> None:
    """The accessible rows carry no clothing, so those categories must not
    resolve — borrowing a cosmetics median would be worse than the demo."""
    supported = btc_market.supported_categories()

    assert "Mỹ phẩm" in supported
    assert "Thời trang" not in supported
    assert "Phụ kiện" not in supported


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
        PricingRequest(product_name="Áo khoác", category="Thời trang", current_price=300_000)
    )

    assert "Shopee" in observed.rationale and "4 nhà bán" in observed.rationale
    assert "mô phỏng" in simulated.rationale
    assert "Shopee" not in simulated.rationale


@pytest.mark.asyncio
async def test_unreachable_database_falls_back_to_the_snapshot(monkeypatch, tmp_path) -> None:
    """A demo must not drop back to synthetic numbers over someone else's outage."""
    snapshot = tmp_path / "btc_price_reference.json"
    snapshot.write_text(
        json.dumps({
            "generated_at": "2026-07-21T00:00:00+00:00",
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
    snapshot = tmp_path / "btc_price_reference.json"
    snapshot.write_text(
        json.dumps({
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
    monkeypatch.setattr(btc_market, "_SNAPSHOT_PATH", tmp_path / "absent.json")

    async def _no_live(_category: str):
        return None

    monkeypatch.setattr(btc_market, "_query_live", _no_live)

    assert await btc_market.price_reference("Mỹ phẩm") is None


@pytest.mark.asyncio
async def test_pricing_still_works_with_no_dataset_configured() -> None:
    """With the dataset switched off entirely, pricing keeps working."""
    result = await insights.recommend_price(
        PricingRequest(product_name="Áo khoác", category="Thời trang", current_price=468_000)
    )

    assert result.data_source == "demo"
    assert result.sample_size > 0
    assert result.recommended_price > 0
