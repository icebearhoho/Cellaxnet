"""Workspace-scoped Voucher Booster API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceAccess, get_db_dep, get_workspace_access, require_workspace_role
from app.core.responses import ApiResponse, PageMeta
from app.schemas.voucher import (
    CampaignCreateRequest,
    CampaignDecisionRequest,
    RecommendationCreateRequest,
)
from app.services import voucher_booster as service

router = APIRouter()
_MANAGER = require_workspace_role("owner", "manager")


def _ok(data: dict | list) -> ApiResponse:
    return ApiResponse(success=True, data=data, meta=PageMeta(), error=None)


@router.get("/recommendations", response_model=ApiResponse[list[dict]])
async def recommendations(access: WorkspaceAccess = Depends(get_workspace_access)) -> ApiResponse:
    return _ok(service.recommendations())


@router.get("/campaigns", response_model=ApiResponse[list[dict]])
async def campaigns(access: WorkspaceAccess = Depends(get_workspace_access),
                    db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.list_campaigns(db, access.workspace_id))


@router.post("/campaigns", response_model=ApiResponse[dict])
async def create(req: CampaignCreateRequest, access: WorkspaceAccess = Depends(_MANAGER),
                 db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.create_campaign(db, workspace_id=access.workspace_id,
        actor_user_id=access.user_id, plan=req))


@router.post("/campaigns/from-recommendation", response_model=ApiResponse[dict])
async def from_recommendation(req: RecommendationCreateRequest,
                              access: WorkspaceAccess = Depends(_MANAGER),
                              db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.create_from_recommendation(db,
        workspace_id=access.workspace_id, actor_user_id=access.user_id,
        recommendation_id=req.recommendation_id))


@router.post("/campaigns/{campaign_id}/decision", response_model=ApiResponse[dict])
async def decide(campaign_id: int, req: CampaignDecisionRequest,
                 access: WorkspaceAccess = Depends(_MANAGER),
                 db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.decide(db, campaign_id=campaign_id,
        workspace_id=access.workspace_id, actor_user_id=access.user_id,
        decision=req.decision, note=req.note))


@router.post("/campaigns/{campaign_id}/stop", response_model=ApiResponse[dict])
async def stop(campaign_id: int, access: WorkspaceAccess = Depends(_MANAGER),
               db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.stop(db, campaign_id=campaign_id,
        workspace_id=access.workspace_id, actor_user_id=access.user_id))
