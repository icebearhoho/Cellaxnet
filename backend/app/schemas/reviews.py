"""Real buyer-submitted review write path — gated by review_moderation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.storefront import ReviewItem

ReviewStatus = Literal["pending", "published", "flagged", "rejected"]


class ReviewCreateRequest(BaseModel):
    author_name: str = Field(min_length=1, max_length=80)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=1, max_length=2000)


class ReviewSubmitResponse(BaseModel):
    status: ReviewStatus
    message: str
    review: ReviewItem | None = None  # set only when status == "published"


class ReviewQueueItem(BaseModel):
    id: int
    product_id: str
    product_name: str
    author_name: str
    rating: int
    text: str
    status: ReviewStatus
    moderation_reason: str | None
    moderation_confidence: float | None
    created_at: str


# --- Seller-side review intelligence ---------------------------------------
class ScoredReview(BaseModel):
    """One review with its sentiment already scored."""

    author: str
    rating: int
    text: str
    days_ago: int | None = None
    sentiment: Literal["positive", "neutral", "negative"]
    #: True for reviews customers submitted through the storefront, as opposed
    #: to the seeded catalogue ones. Worth separating: a seller reads their own
    #: buyers' words differently from sample data.
    from_customers: bool = False


class ProductReviews(BaseModel):
    """Every review on one product, with the shape of the feedback summarised.

    The screen used to take one pasted review at a time, which answered "what
    does this sentence say" — a question the seller could already answer. The
    useful one is "what are people saying about this product", and that needs
    the whole set.
    """

    product_id: str
    product_name: str
    total: int
    positive: int
    neutral: int
    negative: int
    avg_rating: float
    reviews: list[ScoredReview]
