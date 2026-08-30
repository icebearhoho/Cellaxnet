"""Schemas for the seller-side insight features wired from the modeling layer.

#01 Review Sentiment and #05 Fake Review. The backend ships lightweight,
key-free heuristic scorers so the endpoints always respond in a demo; the
offline modeling layer (common/llm_client.py + review_sentiment/, fake_review/)
is the higher-accuracy LLM version evaluated separately.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# --- #01 Review Sentiment -------------------------------------------------
class SentimentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)


class SentimentResponse(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


# --- #05 Fake Review ------------------------------------------------------
class FakeReviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)
    category: str | None = None


class FakeReviewResponse(BaseModel):
    is_fake: bool
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[str]
    reason: str


# --- #02 Dynamic Pricing ---------------------------------------------------
#: Where the percentiles came from. "demo" is the synthetic storefront
#: catalogue; the others are the organisers' observed Shopee dataset, read live
#: or from its committed snapshot. The UI labels the two differently — an
#: observed median must never be presented as a simulated one, or the reverse.
PriceSource = Literal["demo", "btc_live", "btc_snapshot"]


class PricingRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    category: Literal["Thời trang", "Mỹ phẩm", "Phụ kiện"]
    current_price: int | None = Field(default=None, ge=0)


class PricingResponse(BaseModel):
    recommended_price: int
    low: int
    high: int
    category_median: int
    sample_size: int
    rationale: str
    #: Defaulted so an older client that ignores these still parses the body.
    data_source: PriceSource = "demo"
    #: How many distinct shops the observed sample spans; None for "demo".
    #: A handful of shops is a reference, not a market-wide price, and the UI
    #: says so rather than overstating the coverage.
    shop_count: int | None = None


# --- #04 Churn Prediction ---------------------------------------------------
class ChurnRequest(BaseModel):
    recency_days: int = Field(ge=0, le=1000)
    frequency_orders: int = Field(ge=0, le=500)
    sessions_last_month: int = Field(ge=0, le=500)
    cart_abandon_rate: float = Field(ge=0.0, le=1.0)
    trend: Literal["declining", "stable", "growing"] = "stable"


class ChurnResponse(BaseModel):
    churn_risk: float = Field(ge=0.0, le=1.0)
    risk_band: Literal["low", "medium", "high"]
    drivers: list[str]
    retention_action: str


# --- #10 Return/Refund Prediction ------------------------------------------
class ReturnRequest(BaseModel):
    category: Literal["Thời trang", "Mỹ phẩm", "Phụ kiện"]
    price_vnd: int = Field(ge=0)
    is_new_customer: bool = False
    size_related: bool = False
    discount_pct: float = Field(ge=0.0, le=100.0, default=0.0)
    reviews_read: int = Field(ge=0, le=50, default=0)


class ReturnResponse(BaseModel):
    return_risk: float = Field(ge=0.0, le=1.0)
    risk_band: Literal["low", "medium", "high"]
    drivers: list[str]
    action: str


# --- #15 Post-purchase Regret Predictor -------------------------------------
class RegretRequest(BaseModel):
    decision_time_seconds: int = Field(ge=0, le=7200)
    revisit_count: int = Field(ge=0, le=50, default=0)
    purchase_hour: int = Field(ge=0, le=23)
    price_vnd: int = Field(ge=0)
    used_discount: bool = False


class RegretResponse(BaseModel):
    regret_risk: float = Field(ge=0.0, le=1.0)
    risk_band: Literal["low", "medium", "high"]
    drivers: list[str]
    reassurance_message: str


# --- #08 Sentiment-driven Inventory Alert -----------------------------------
class InventoryAlertRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    social_mentions_7d: int = Field(ge=0, le=1_000_000, default=0)
    social_sentiment: float = Field(ge=-1.0, le=1.0, default=0.0)
    current_stock: int = Field(ge=0)
    avg_daily_sales: float = Field(ge=0.0)


class InventoryAlertResponse(BaseModel):
    is_trending: bool
    trend_score: float
    days_of_stock_left: float
    alert_level: Literal["none", "watch", "urgent"]
    recommended_restock_qty: int
    reason: str
