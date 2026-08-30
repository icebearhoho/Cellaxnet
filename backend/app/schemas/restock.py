"""Smart Restock Planner — budget-constrained restock quantities.

Answers "with this much capital, which SKUs do I restock this month and how
many units", from three signals:

  SEASON  a 12-month seasonal index per category, learned from 5 years of
          Google Trends history (SerpApi, TIMESERIES) — see restock_planner/
  TREND   how deeply the big brands are discounting right now, read off live
          Google Shopping listings (current price vs struck-through price)
  MONEY   the seller's own budget, cost and price per SKU

Market numbers are measured, not assumed. The one policy knob is
`competition_sensitivity` (how much a rival's sale dents our demand), which the
caller may override per request — it is a business judgement, not a measurement,
and is labelled as such in the response.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal["Thời trang", "Mỹ phẩm", "Phụ kiện"]
Outlook = Literal["expand", "hold", "contract"]
PressureLevel = Literal["low", "medium", "high"]
ChannelId = Literal["shopee", "lazada", "tiktok", "own"]
CaseId = Literal["hot", "slow", "seasonal", "dead"]


class RestockPlanRequest(BaseModel):
    budget_vnd: float = Field(50_000_000, gt=0, description="Vốn nhập hàng khả dụng")
    month: int = Field(0, ge=0, le=12, description="Tháng lập kế hoạch; 0 = tháng hiện tại")
    horizon_days: int = Field(30, ge=7, le=120, description="Số ngày cần phủ tồn kho")
    categories: list[Category] = Field(
        default_factory=list, description="Lọc theo ngành; rỗng = tất cả"
    )
    competition_sensitivity: float | None = Field(
        None, ge=0.0, le=2.0,
        description="Cầu nhạy thế nào với sale của big brand (mặc định 0.5)",
    )
    scenario_pressure: float | None = Field(
        None, ge=0.0, le=1.0,
        description="Kịch bản giả định: ép mức áp lực sale (vd 0.3 = mùa 11.11). "
                    "Bỏ trống để dùng số đo thật.",
    )
    refresh_live: bool = Field(
        False, description="Gọi lại Google Shopping để lấy mức sale mới nhất"
    )
    channel_cases: dict[ChannelId, CaseId] | None = Field(
        None,
        description="Gán hồ sơ bán hàng cho từng kênh, vd {'shopee':'hot'}. "
                    "Bỏ trống = dùng mặc định.",
    )
    channel_fees: dict[ChannelId, float] | None = Field(
        None, description="Ghi đè phí sàn (%) từng kênh, 0-50. Bỏ trống = dùng mặc định.",
    )

    @field_validator("channel_fees")
    @classmethod
    def _fees_in_range(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        """Reject an out-of-range fee instead of quietly falling back.

        The service used to skip any value outside 0-50, so a caller sending
        -5 got a plan computed at the default 5% and no indication their
        override had been thrown away.
        """
        for channel, pct in (v or {}).items():
            if not 0.0 <= float(pct) <= 50.0:
                raise ValueError(
                    f"Phí sàn của '{channel}' phải trong khoảng 0-50%, nhận {pct}"
                )
        return v


class ChannelMarketRow(BaseModel):
    """Measured presence of one platform in one category (Google Shopping).

    `listings` = 0 is a real reading, not a gap: TikTok Shop does not feed
    Google Shopping, so its market share is genuinely unmeasurable this way and
    the UI must say so rather than imply the platform is empty.
    """

    category: str
    listings: int
    share_pct: float
    median_price_vnd: int
    on_sale: int
    avg_discount: float


class ChannelResult(BaseModel):
    channel: ChannelId
    name: str
    kind: Literal["marketplace", "own"]
    case: CaseId
    case_label: str
    case_desc: str
    commission_pct: float
    # Demand shaping, split so the seller can see which part moved the number.
    volume_factor: float
    season_adj: float
    trend_adj: float
    demand_factor: float
    # Allocation outcome for this channel.
    expected_demand: int
    order_qty: int
    spend_vnd: int
    expected_revenue_vnd: int
    expected_profit_vnd: int
    commission_cost_vnd: int
    budget_share_pct: float
    sku_count: int
    verdict: str
    measured: list[ChannelMarketRow] = Field(default_factory=list)
    measurable: bool = True
    # True when this channel's own synced order history set `volume_factor`,
    # rather than the case the seller picked by hand.
    volume_from_orders: bool = False


class PlanItem(BaseModel):
    sku: str
    name: str
    brand: str
    category: str
    channel: ChannelId
    channel_name: str
    price_vnd: int
    cost_vnd: int
    stock: int
    days_of_stock_left: float
    season_index: float
    competition_multiplier: float
    baseline_demand: int
    expected_demand: int
    need_qty: int
    order_qty: int
    partial: bool
    spend_vnd: int
    expected_revenue_vnd: int
    expected_profit_vnd: int
    unit_margin_vnd: int
    roi: float
    urgency: float
    reason: str


class SkippedItem(BaseModel):
    sku: str
    name: str
    category: str
    need_qty: int
    cost_vnd: int
    reason: str


class CategoryOutlook(BaseModel):
    category: str
    season_index: float
    season_index_prev: float
    season_change_pct: float
    momentum: float
    direction: str
    competition_multiplier: float
    competition_level: str
    combined_factor: float
    outlook: Outlook
    advice: str
    peak_month: int | None = None
    low_month: int | None = None
    # Full 12-month curve (Jan..Dec) so the panel can chart seasonality without
    # a second round-trip.
    monthly_index: list[float] = Field(default_factory=list)


class BrandSale(BaseModel):
    brand: str
    category: str
    offers_seen: int
    offers_on_sale: int
    sale_ratio: float
    avg_discount: float
    pressure: float


class CompetitionReading(BaseModel):
    category: str
    pressure: float
    demand_multiplier: float
    level: PressureLevel
    note: str
    brands_on_sale: int
    brands_checked: int
    avg_discount: float
    leader_brand: str | None = None


class RestockPlanResponse(BaseModel):
    month: int
    horizon_days: int
    budget_vnd: int
    spent_vnd: int
    remaining_vnd: int
    budget_used_pct: float
    item_count: int
    skipped_count: int
    total_units: int
    expected_revenue_vnd: int
    expected_profit_vnd: int
    expected_margin_pct: float
    roi_pct: float
    items: list[PlanItem]
    skipped: list[SkippedItem]
    outlook: list[CategoryOutlook]
    channels: list[ChannelResult] = Field(default_factory=list)
    channel_market_fetched_at: str | None = None
    competition: list[CompetitionReading]
    brands: list[BrandSale]
    summary: str
    # Provenance so the UI can be honest about where each number came from.
    data_source: str
    trends_window: str | None = None
    weeks_of_history: int = 0
    trends_fetched_at: str | None = None
    brand_sale_fetched_at: str | None = None
    live_refresh: bool = False
    scenario: bool = False
    competition_sensitivity: float = 0.5
