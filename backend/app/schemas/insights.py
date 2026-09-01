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
PriceSource = Literal["demo", "btc_live", "btc_snapshot", "shopee_seed"]

class PricingRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    category: Literal["Thời trang", "Mỹ phẩm", "Phụ kiện"]
    current_price: int | None = Field(default=None, ge=0)
    #: Landed cost per unit. Optional — with it the recommendation is held
    #: above a price that still earns `min_margin_pct` after the channel's
    #: commission, so following the market can never quietly sell at a loss.
    unit_cost: int | None = Field(default=None, ge=0)
    #: Margin on *revenue* ((price - cost) / price), the same basis Market
    #: Intelligence uses. Not markup on cost — at 30% those differ by a third.
    min_margin_pct: float = Field(default=20.0, ge=0, le=90)
    #: Selling channel, for its commission. Unknown ids fall back to no fee.
    channel: str | None = Field(default=None, max_length=32)


class PriceStrategy(BaseModel):
    """One way to price this product, with what it costs and buys.

    The three sit at the market's own quartiles rather than at arbitrary
    percentages off a single number: p25 is where a quarter of the market is
    cheaper, p75 where a quarter is dearer, so each option is a real position
    among competitors instead of a discount invented for the UI.
    """

    key: Literal["volume", "balanced", "margin"]
    label: str
    #: Where the figure came from, named as a statistic a reviewer can check
    #: against the data rather than a label chosen for the screen.
    source: str
    #: What choosing this costs, said plainly. Every option trades margin
    #: against how easily the product sells, and stating one side without the
    #: other is how a reference turns into a recommendation by accident.
    tradeoff: str
    price: int
    #: Margin on revenue after commission; None when no cost was supplied.
    margin_pct: float | None = None
    #: Share of observed products priced at or below this, when known.
    percentile: int | None = None
    #: True when the seller's cost rules this price out. The figure still shows
    #: the market's own level — replacing it with the floor made all three
    #: markers identical and hid where the market actually sits, which is worth
    #: most precisely when the seller cannot reach it.
    below_cost_floor: bool = False


#: What the seller should do, as one word. The screen leads with this: a
#: recommendation nobody can act on in three seconds is a report, not advice.
#: "new" covers a product with no price yet: there is nothing to raise, lower
#: or keep, and saying "giá hiện tại đã hợp lý" about a blank field is wrong.
PriceDirection = Literal["raise", "lower", "keep", "new"]


class PricingResponse(BaseModel):
    recommended_price: int
    low: int
    high: int
    category_median: int
    sample_size: int
    rationale: str
    #: Observed quartiles, so the panel can show the spread a single median
    #: hides — a category can be tight or five-fold wide at the same median.
    market_p25: int | None = None
    market_p75: int | None = None
    #: Share of observed products priced at or below the seller's current
    #: price. Says *where* they sit, which a bare gap to the median does not.
    price_percentile: int | None = None
    #: Lowest price that still clears `min_margin_pct` after commission, or
    #: None when no cost was supplied. The recommendation never sits below it.
    price_floor: int | None = None
    #: Margin on revenue actually achieved at `recommended_price`, after
    #: commission — the number to check before accepting the suggestion.
    margin_pct_at_recommended: float | None = None
    #: Raise, lower or keep — the headline verdict.
    direction: PriceDirection = "keep"
    #: Gap between the current price and the recommendation, for the headline.
    change_vnd: int | None = None
    change_pct: float | None = None
    #: True when the suggestion is a large move from the current price. The
    #: market says where the price could sit; nothing here says buyers will
    #: follow it there, so a big jump is worth taking in steps.
    large_move: bool = False
    #: True when no cost was supplied: the price can be placed against the
    #: market, but nothing here checked whether it earns anything.
    margin_unverified: bool = False
    #: Margin at the *current* price, so the panel can show what changes.
    margin_pct_now: float | None = None
    #: Profit per unit after cost and commission, now and at the suggestion.
    profit_per_unit_now: int | None = None
    profit_per_unit_at_recommended: int | None = None
    #: Three positions in the market, cheapest first. Same product, same
    #: floor — what changes is which end of the market it sits at.
    strategies: list[PriceStrategy] = []
    #: The steps behind the recommendation, in the order they constrain it.
    #: "Why 223,000₫ and not 210,000₫" is the question a price invites, and a
    #: verdict that cannot answer it reads as a guess.
    reasons: list[str] = []
    #: Shopee market(s) the reference came from, already localised —
    #: "Shopee Indonesia" rather than a bare "Shopee" the reader will take
    #: to mean their own.
    market_label: str | None = None
    #: Commission applied, so the floor can be traced back to a rate.
    channel_name: str | None = None
    channel_commission_pct: float | None = None
    #: True when the market median sits below the floor: matching the market
    #: would lose money, so the floor is quoted instead.
    floor_above_market: bool = False
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
