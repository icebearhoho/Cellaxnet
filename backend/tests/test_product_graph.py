"""Regression tests for demo-backed product ranking and comparisons."""

from __future__ import annotations

from app.services import copilot, product_graph


async def _use_demo_dataset(monkeypatch, days: int = 30):
    products, source = product_graph._demo_dataset(days)
    options = [product_graph._demo_option()]

    async def resolve_dataset(db, shop_connection_id, requested_days):
        assert requested_days == days
        return products, source, options

    monkeypatch.setattr(product_graph, "_resolve_dataset", resolve_dataset)
    return products, source


async def test_overview_reconciles_category_and_product_revenue(monkeypatch):
    products, source = await _use_demo_dataset(monkeypatch)

    result = await product_graph.overview(None, days=30)

    assert result.data_available is True
    assert result.source == source
    assert len(result.categories) == 3
    assert len(result.top_products) == len(products) == source.product_records
    assert [row.rank for row in result.categories] == [1, 2, 3]
    assert [row.revenue_vnd for row in result.categories] == sorted(
        (row.revenue_vnd for row in result.categories), reverse=True
    )
    assert sum(row.revenue_vnd for row in result.categories) == sum(
        row.revenue_vnd for row in result.top_products
    )
    assert round(sum(row.revenue_share_pct for row in result.categories), 1) == 100.0

    for category in result.categories:
        rows = [row for row in result.top_products if row.category == category.category]
        assert len(rows) == category.product_count
        assert sorted(row.category_rank for row in rows) == list(
            range(1, category.product_count + 1)
        )
        assert rows[0].name == category.top_product_name
        assert rows[0].category_rank == 1


async def test_detail_compares_only_products_from_the_same_category(monkeypatch):
    await _use_demo_dataset(monkeypatch)
    overview = await product_graph.overview(None, days=30)
    selected = overview.top_products[0]

    result = await product_graph.detail(None, selected.id, days=30)

    assert result.found is True
    assert result.product is not None
    assert result.product.id == selected.id
    assert 0 < len(result.similar_products) <= 6
    assert all(row.id != selected.id for row in result.similar_products)
    assert all(row.category == selected.category for row in result.similar_products)
    assert all(row.relation and row.comparison for row in result.similar_products)


async def test_detail_reports_an_unknown_product_without_substituting_one(monkeypatch):
    await _use_demo_dataset(monkeypatch)

    result = await product_graph.detail(None, "not-a-product", days=30)

    assert result.found is False
    assert result.product is None
    assert result.similar_products == []


async def test_copilot_dispatch_uses_the_current_product_graph_contract(monkeypatch):
    await _use_demo_dataset(monkeypatch)
    overview = await product_graph.overview(None, days=30)
    selected = overview.top_products[0]

    result, summary = await copilot._dispatch(
        "product_graph", {"product": selected.name}, None
    )

    assert result["name"] == selected.name
    assert result["sales_change_pct"] == selected.sales_change_pct
    assert result["revenue_vnd"] == selected.revenue_vnd
    assert result["units_sold"] == selected.units_sold
    assert result["category_rank"] == selected.category_rank
    assert result["similar"]
    assert selected.name in summary
