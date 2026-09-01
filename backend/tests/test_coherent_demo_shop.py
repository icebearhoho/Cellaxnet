"""Cross-feature integrity tests for the connected Mây House demo shop."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.schemas.genai import RecsysRequest, SellerCoachRequest
from app.schemas.insights import PricingRequest
from app.services import commerce_store as store
from app.services import insights, recsys, seller_coach, shop_analytics, storefront


def test_demo_shop_has_realistic_connected_volume() -> None:
    assert store.shop_profile()["name"] == "Mây House Official"
    assert len(store.all_products()) == 60
    assert len(store.all_customers()) == 120
    assert len(store.all_demo_orders()) == 540
    assert len(store.all_daily_metrics()) == 90
    assert len(store.all_creators()) == 12
    assert sum(len(product["reviews_list"]) for product in store.all_products()) >= 720
    assert len({customer["name"] for customer in store.all_customers()}) == 120
    assert len({customer["email"] for customer in store.all_customers()}) == 120


def test_every_demo_order_references_valid_customer_and_products() -> None:
    product_ids = {product["id"] for product in store.all_products()}
    customer_ids = {customer["id"] for customer in store.all_customers()}

    for order in store.all_demo_orders():
        assert order["customer_id"] in customer_ids
        assert order["items"]
        assert all(line["product_id"] in product_ids for line in order["items"])
        subtotal = sum(line["unit_price_vnd"] * line["qty"] for line in order["items"])
        assert order["subtotal_vnd"] == subtotal
        assert order["total_vnd"] == subtotal - order["discount_vnd"] + order["shipping_vnd"]


def test_product_velocity_is_recomputed_from_the_same_order_lines() -> None:
    orders = store.all_demo_orders()
    for product in store.all_products():
        expected = [0, 0, 0, 0]
        for order in orders:
            if order["status"] in {"cancelled", "pending", "returned"}:
                continue
            age = (
                datetime.fromisoformat(str(store.SHOP_PROFILE["data_as_of"]))
                - datetime.fromisoformat(order["created_at"])
            ).days
            bucket = 3 - min(3, age // 45)
            expected[bucket] += sum(
                line["qty"]
                for line in order["items"]
                if line["product_id"] == product["id"]
            )

        assert product["sales_history"] == expected
        assert product["sales_curr"] == expected[-1]
        assert product["sales_prev"] == expected[-2]


def test_customer_risk_features_trace_back_to_latest_order() -> None:
    orders_by_no = {order["order_no"]: order for order in store.all_demo_orders()}
    for customer in store.all_customers():
        order = orders_by_no[customer["last_order_no"]]
        assert order["customer_id"] == customer["id"]
        assert customer["last_product_id"] in {
            line["product_id"] for line in order["items"]
        }
        assert customer["last_order_value_vnd"] == order["total_vnd"]


def test_creator_campaigns_reference_catalog_products_and_matching_category() -> None:
    products = {product["id"]: product for product in store.all_products()}
    for creator in store.all_creators():
        for campaign in creator["campaigns"]:
            product = products[campaign["product_id"]]
            assert product["category"] == creator["category"]
            assert product["name"] == campaign["product_name"]


def test_dashboard_kpis_are_derived_from_daily_fact_table() -> None:
    result = shop_analytics.summary()
    today = store.all_daily_metrics()[-1]
    kpis = {item["id"]: item for item in result["kpis"]}

    assert kpis["revenue"]["value"] == today["revenue_vnd"]
    assert kpis["orders"]["value"] == today["orders"]
    assert kpis["conversion"]["value"] == today["conversion_rate"]
    assert kpis["aov"]["value"] == today["aov_vnd"]
    assert result["counts"]["orders"] == len(store.all_demo_orders())


def test_storefront_rating_is_the_same_review_average() -> None:
    source = store.all_products()[0]
    view = storefront.get_product(source["id"])
    expected = round(
        sum(review["rating"] for review in source["reviews_list"])
        / len(source["reviews_list"]),
        1,
    )

    assert view.product is not None
    assert view.product.rating == expected
    assert view.product.reviews == len(source["reviews_list"])


@pytest.mark.asyncio
async def test_dynamic_pricing_falls_back_to_the_storefront_catalog(monkeypatch) -> None:
    """With no market reference available, pricing reads the demo catalogue.

    The reference is stubbed out rather than left to the environment: a
    developer with BTC_DATABASE_URL set in .env would otherwise hit the real
    database here, making the test both slow and dependent on someone else's
    uptime.
    """
    async def _no_reference(_category: str):
        return None

    monkeypatch.setattr("app.services.btc_market.price_reference", _no_reference)
    monkeypatch.setattr(
        "app.services.shopee_listings.reference_for_product", lambda _name, _cat: None
    )

    category = "Mỹ phẩm"
    result = await insights.recommend_price(
        PricingRequest(product_name="Test", category=category, current_price=300_000)
    )

    assert result.data_source == "demo"
    assert result.sample_size == len(store.products_by_category(category))
    assert result.shop_count is None


@pytest.mark.asyncio
async def test_recsys_returns_only_live_catalog_items_and_filters_stockouts() -> None:
    result = await recsys.recommend(
        RecsysRequest(
            user_id="C001",
            signals={"intent": "serum dưỡng ẩm", "preferred_channel": "Shopee"},
            top_k=8,
        )
    )
    products = {product["id"]: product for product in store.all_products()}

    assert len(result.items) == 8
    assert all(item.product_id in products for item in result.items)
    assert all(products[item.product_id]["stock"] > 0 for item in result.items)


@pytest.mark.asyncio
async def test_seller_coach_scores_are_calculated_from_the_same_shop() -> None:
    result = await seller_coach.coach(SellerCoachRequest(seller_id="shop-may-001"))

    assert result.demo_mode is True
    assert len(result.audit) == 5
    assert any("60" in step.tip for step in result.audit)
    assert any("review" in step.tip.lower() for step in result.audit)
