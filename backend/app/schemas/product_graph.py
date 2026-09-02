"""Schemas for the seller's product-performance relationship view.

Every numeric field in these responses is derived from marketplace rows stored
by the sync pipeline.  The API deliberately carries its source and calculation
window beside the values so the frontend never has to present an unexplained
number.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProductGraphRequest(BaseModel):
    """Legacy lookup request kept for API compatibility."""

    query: str = Field(min_length=1)
    shop_connection_id: int | None = None
    days: int = Field(default=30, ge=7, le=365)


class ShopSourceOption(BaseModel):
    id: int
    platform: str
    shop_name: str
    status: str
    last_synced_at: str | None
    product_records: int
    order_records: int


class GraphDataSource(BaseModel):
    kind: Literal["marketplace_sync", "demo_shop"]
    shop_connection_id: int | None
    platform: str
    shop_name: str
    status: str
    last_synced_at: str | None
    period_start: str
    period_end: str
    period_days: int
    product_records: int
    order_records: int
    order_item_records: int
    demo_data_used: bool
    revenue_definition: str


class ProductPerformance(BaseModel):
    id: str
    external_product_id: str
    sku: str | None
    name: str
    brand: str | None
    category: str
    price_vnd: int | None
    image_url: str | None
    revenue_vnd: int
    units_sold: int
    orders_count: int
    revenue_rank: int
    category_rank: int
    category_revenue_share_pct: float
    sales_change_pct: float | None
    highlight_reason: str


class SimilarProduct(ProductPerformance):
    relation: str
    comparison: str


class CategoryPerformance(BaseModel):
    category: str
    rank: int
    revenue_vnd: int
    units_sold: int
    orders_count: int
    revenue_share_pct: float
    growth_pct: float | None
    product_count: int
    top_product_id: str
    top_product_name: str
    top_product_image_url: str | None
    top_product_names: list[str]


class ProductGraphOverview(BaseModel):
    data_available: bool
    source: GraphDataSource | None
    available_shops: list[ShopSourceOption]
    categories: list[CategoryPerformance]
    top_products: list[ProductPerformance]
    summary: str
    missing_reason: str | None = None


class ProductGraphResponse(BaseModel):
    found: bool
    data_available: bool
    source: GraphDataSource | None
    product: ProductPerformance | None
    similar_products: list[SimilarProduct]
    summary: str
