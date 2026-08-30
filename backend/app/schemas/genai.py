"""Pydantic schemas for the 4 fullstack features (#03, #09, #11, #17)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --------------------------------------------------------------------- #
# Shared
# --------------------------------------------------------------------- #


class ProductCard(BaseModel):
    id: str
    name: str
    brand: str
    category: str
    platform: str
    price_vnd: int
    rating: float
    reviews: int
    similarity: float = Field(ge=0.0, le=1.0)
    image_hue: int = Field(default=215, ge=0, lt=360)
    image_url: str | None = None


# --------------------------------------------------------------------- #
# #03 Personal Shopper
# --------------------------------------------------------------------- #


class ShopperRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=8, ge=1, le=20)
    stream: bool = True


class ShopperProductsResponse(BaseModel):
    products: list[ProductCard]
    sources: list[dict]  # retrieved docs metadata
    demo_mode: bool = True


# --------------------------------------------------------------------- #
# #09 Content Generator
# --------------------------------------------------------------------- #


Platform = Literal["Shopee", "Tiki", "TikTok Shop"]
_DEFAULT_PLATFORMS: list[Platform] = ["Shopee", "Tiki", "TikTok Shop"]


class ContentGeneratorRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    features: str = Field(min_length=1, max_length=1000)
    platforms: list[Platform] = Field(default_factory=lambda: list(_DEFAULT_PLATFORMS))


class ContentVariant(BaseModel):
    platform: Platform
    title: str
    body: str
    predicted_ctr: float = Field(ge=0.0, le=1.0)
    rationale: str


class ContentGeneratorResponse(BaseModel):
    variants: list[ContentVariant]
    model: str
    demo_mode: bool


# --------------------------------------------------------------------- #
# #11 Recsys
# --------------------------------------------------------------------- #


class RecsysRequest(BaseModel):
    user_id: str | None = None
    signals: dict[str, str] = Field(default_factory=dict)
    top_k: int = Field(default=4, ge=1, le=20)


class Recommendation(BaseModel):
    product_id: str
    name: str
    brand: str
    category: str
    platform: str
    price_vnd: int
    rating: float
    reviews: int
    similarity: float = Field(ge=0.0, le=1.0)
    reason: str
    image_url: str | None = None
    image_hue: int = Field(default=215, ge=0, lt=360)


class RecsysResponse(BaseModel):
    mode: Literal["traditional", "ai"]
    items: list[Recommendation]
    metrics: dict[str, float]
    model: str
    demo_mode: bool = True


# --------------------------------------------------------------------- #
# #17 Seller Coach
# --------------------------------------------------------------------- #


class AuditStep(BaseModel):
    id: str
    label: str
    score: int = Field(ge=0, le=100)
    tip: str


class RoadmapWeek(BaseModel):
    week: int
    title: str
    bullets: list[str]


class SellerCoachRequest(BaseModel):
    seller_id: str | None = None


class SellerCoachResponse(BaseModel):
    overall: int
    audit: list[AuditStep]
    roadmap: list[RoadmapWeek]
    demo_mode: bool
