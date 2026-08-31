"""#01 Review Sentiment — what customers said about a product, scored.

``/`` still classifies a single pasted sentence; ``/products/{id}`` answers the
question a seller actually has, which is what the reviews on one product add up
to rather than what one of them means.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, PageMeta
from app.db.session import get_db
from app.schemas.insights import SentimentRequest
from app.services import insights, review_service

router = APIRouter()


@router.get("/products/{product_id}", response_model=ApiResponse[dict])
async def product_reviews(
    product_id: str, db: AsyncSession = Depends(get_db)
) -> ApiResponse[dict]:
    """Every review on one product, sentiment-scored, newest first."""
    data = await review_service.product_reviews(db, product_id)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.post("/", response_model=ApiResponse[dict])
async def classify(req: SentimentRequest) -> ApiResponse[dict]:
    data = await insights.analyze_sentiment(req)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)
