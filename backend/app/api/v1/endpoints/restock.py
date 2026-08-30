"""Smart Restock Planner — budget-constrained restock quantities per SKU."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, PageMeta
from app.db.session import get_db
from app.schemas.restock import RestockPlanRequest, RestockPlanResponse
from app.services import channel_link, restock

router = APIRouter()


@router.post("/", response_model=ApiResponse[RestockPlanResponse])
async def plan(
    req: RestockPlanRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse[RestockPlanResponse]:
    # Channels whose orders have been synced drive their own demand; the rest
    # fall back to the case the seller picked.
    try:
        rates = await channel_link.synced_rates(db)
    except Exception:  # noqa: BLE001 — planning must survive a DB hiccup
        rates = {}
    data = await restock.build_plan(req, rates)
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
