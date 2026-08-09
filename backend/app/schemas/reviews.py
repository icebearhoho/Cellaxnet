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
