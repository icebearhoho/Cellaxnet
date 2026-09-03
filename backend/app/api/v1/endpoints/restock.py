"""Smart Restock Planner — budget-constrained restock quantities per SKU."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.responses import ApiResponse, PageMeta
from app.schemas.restock import RestockPlanRequest, RestockPlanResponse
from app.services import restock

router = APIRouter()


@router.post("/", response_model=ApiResponse[RestockPlanResponse])
async def plan(
    req: RestockPlanRequest,
) -> ApiResponse[RestockPlanResponse]:
    data = await restock.build_plan(req)
    return ApiResponse[RestockPlanResponse](
        success=True, data=data, meta=PageMeta(), error=None
    )


@router.get("/market", response_model=ApiResponse[dict])
async def market() -> ApiResponse[dict]:
    """The two measured signals on their own — seasonality and brand sale.

    Lets the panel render the market view before the seller has entered a
    budget, and makes the data provenance inspectable without running a plan.
    """
    snap = restock._snapshot()
    return ApiResponse[dict](
        success=True,
        data={
            "meta": snap.get("meta", {}),
            "season": snap.get("season", {}),
            "competition": snap.get("competition", {}),
        },
        meta=PageMeta(),
        error=None,
    )
