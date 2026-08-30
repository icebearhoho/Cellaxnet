"""Voucher Booster request contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Platform = Literal["shopee", "tiktok_shop"]
PromotionType = Literal["seller_voucher", "product_discount", "flash_deal"]
DiscountType = Literal["percentage", "fixed"]
Objective = Literal["protect_margin", "grow_revenue", "clear_stock", "win_back"]


class CampaignCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    platform: Platform
    promotion_type: PromotionType
    objective: Objective
    product_id: str | None = Field(default=None, max_length=120)
    discount_type: DiscountType
    discount_value: int = Field(gt=0)
    max_discount_vnd: int | None = Field(default=None, gt=0)
    min_order_vnd: int = Field(default=0, ge=0)
    quantity: int = Field(gt=0, le=100_000)
    budget_vnd: int = Field(gt=0, le=1_000_000_000)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_platform_rules(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("Thời gian kết thúc phải sau thời gian bắt đầu.")
        if self.platform == "shopee" and self.promotion_type != "seller_voucher":
            raise ValueError("Shopee Booster hiện chỉ quản lý seller voucher.")
        if self.platform == "tiktok_shop" and self.promotion_type == "seller_voucher":
            # Allowed as an assisted workflow; OpenAPI cannot publish it.
            return self
        if self.promotion_type in {"product_discount", "flash_deal"} and not self.product_id:
            raise ValueError("Khuyến mãi theo sản phẩm cần product_id.")
        return self


class CampaignDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=300)


class RecommendationCreateRequest(BaseModel):
    recommendation_id: str = Field(min_length=3, max_length=100)
