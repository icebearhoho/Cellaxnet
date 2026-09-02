"""Regression tests for the store-level restock recommendation."""

from __future__ import annotations

from app.schemas.restock import RestockPlanRequest
from app.services import restock


def _product(*, stock: int = 0, daily_sales: float = 1.0) -> dict:
    return {
        "id": "p-1",
        "sku": "SKU-1",
        "name": "Sản phẩm kiểm thử",
        "brand": "Brand",
        "category": "Thời trang",
        "price_vnd": 200_000,
        "cost_vnd": 100_000,
        "stock": stock,
        "daily_sales": daily_sales,
    }


def _market(*, season_index: float = 1.0, competition_multiplier: float = 1.0):
    season = {"Thời trang": {"seasonal_index": {9: season_index}}}
    competition = {
        "Thời trang": {"demand_multiplier": competition_multiplier}
    }
    return season, competition


def test_allocation_uses_each_sku_once_without_hidden_channel_multiplier():
    season, competition = _market()

    plan = restock._allocate(
        [_product()], 2_000_000, 9, season, competition, 10
    )

    assert plan["total_units"] == 10
    assert plan["item_count"] == 1
    assert plan["recommended_budget_vnd"] == 1_000_000
    assert plan["remaining_vnd"] == 1_000_000
    assert plan["budget_status"] == "surplus"
    assert plan["items"][0]["channel_name"] == "Toàn cửa hàng"


def test_google_trends_and_shopping_factors_change_measured_demand():
    base_season, base_competition = _market()
    high_season, _ = _market(season_index=2.0)
    _, strong_competition = _market(competition_multiplier=0.5)

    base = restock._allocate(
        [_product()], 3_000_000, 9, base_season, base_competition, 10
    )
    seasonal = restock._allocate(
        [_product()], 3_000_000, 9, high_season, base_competition, 10
    )
    competitive = restock._allocate(
        [_product()], 3_000_000, 9, base_season, strong_competition, 10
    )

    assert base["total_units"] == 10
    assert seasonal["total_units"] == 20
    assert competitive["total_units"] == 5
    assert seasonal["items"][0]["season_index"] == 2.0
    assert competitive["items"][0]["competition_multiplier"] == 0.5


def test_budget_is_monotonic_until_need_is_funded_then_becomes_surplus():
    season, competition = _market()
    low = restock._allocate(
        [_product()], 400_000, 9, season, competition, 10
    )
    exact = restock._allocate(
        [_product()], 1_000_000, 9, season, competition, 10
    )
    high = restock._allocate(
        [_product()], 1_500_000, 9, season, competition, 10
    )

    assert low["spent_vnd"] <= 400_000
    assert low["total_units"] < exact["total_units"]
    assert low["budget_status"] == "insufficient"
    assert exact["budget_status"] == "fully_funded"
    assert high["total_units"] == exact["total_units"]
    assert high["remaining_vnd"] == 500_000
    assert high["budget_status"] == "surplus"


async def test_real_demo_plan_40m_and_50m_account_for_the_full_difference():
    common = {"month": 9, "horizon_days": 30}
    plan_40 = await restock.build_plan(
        RestockPlanRequest(budget_vnd=40_000_000, **common)
    )
    plan_50 = await restock.build_plan(
        RestockPlanRequest(budget_vnd=50_000_000, **common)
    )

    assert plan_40.budget_status == plan_50.budget_status == "surplus"
    assert plan_40.recommended_budget_vnd == plan_50.recommended_budget_vnd
    assert plan_40.total_units == plan_50.total_units
    assert plan_50.remaining_vnd - plan_40.remaining_vnd == 10_000_000
    assert plan_40.spent_vnd + plan_40.remaining_vnd == 40_000_000
    assert plan_50.spent_vnd + plan_50.remaining_vnd == 50_000_000
    assert len({item.sku for item in plan_50.items}) == plan_50.item_count
    assert plan_50.channels == []
    assert "Google Trends" in plan_50.data_source
    assert "Google Shopping" in plan_50.data_source


async def test_products_without_fulfilled_sales_do_not_create_fake_demand(monkeypatch):
    monkeypatch.setattr(restock.commerce_store, "all_products", lambda: [_product()])
    monkeypatch.setattr(
        restock.commerce_store,
        "product_sales_stats",
        lambda product_id, days: {
            "product_id": product_id,
            "days": days,
            "units_sold": 0,
        },
    )

    plan = await restock.build_plan(
        RestockPlanRequest(budget_vnd=50_000_000, month=9, horizon_days=30)
    )

    assert plan.total_units == 0
    assert plan.spent_vnd == 0
    assert plan.items == []
