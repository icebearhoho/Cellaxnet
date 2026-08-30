"""#02 Dynamic Pricing — recommend a competitive price (seller insight)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.responses import ApiResponse, PageMeta
from app.schemas.insights import PricingRequest
from app.services import insights

router = APIRouter()


@router.post("/", response_model=ApiResponse[dict])
async def recommend(req: PricingRequest) -> ApiResponse[dict]:
    data = await insights.recommend_price(req)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)
