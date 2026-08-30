"""Workspace-scoped Seller Autopilot API."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WorkspaceAccess, get_db_dep, get_workspace_access, require_workspace_role
from app.core.responses import ApiResponse, PageMeta
from app.schemas.autopilot import DecideRequest, SimulateRequest
from app.services import autopilot as service

router = APIRouter()
_MANAGER = require_workspace_role("owner", "manager")


def _ok(data: dict | list) -> ApiResponse:
    return ApiResponse(success=True, data=data, meta=PageMeta(), error=None)


@router.get("/opportunities", response_model=ApiResponse[list[dict]])
async def opportunities(access: WorkspaceAccess = Depends(get_workspace_access),
                        db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.list_opportunities(db, access.workspace_id))


@router.post("/refresh", response_model=ApiResponse[list[dict]])
async def refresh(access: WorkspaceAccess = Depends(_MANAGER),
                  db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.refresh(db, workspace_id=access.workspace_id,
                                     actor_user_id=access.user_id))


@router.post("/opportunities/{opportunity_id}/simulate", response_model=ApiResponse[dict])
async def simulate(opportunity_id: int, req: SimulateRequest,
                   access: WorkspaceAccess = Depends(get_workspace_access),
                   db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.simulate(db, opportunity_id=opportunity_id,
        workspace_id=access.workspace_id, actor_user_id=access.user_id,
        option_id=req.option_id))


@router.post("/opportunities/{opportunity_id}/decision", response_model=ApiResponse[dict])
async def decide(opportunity_id: int, req: DecideRequest,
                 access: WorkspaceAccess = Depends(_MANAGER),
                 db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.decide(db, opportunity_id=opportunity_id,
        workspace_id=access.workspace_id, actor_user_id=access.user_id,
        option_id=req.option_id, decision=req.decision, note=req.note))


@router.get("/audit", response_model=ApiResponse[list[dict]])
async def audit(access: WorkspaceAccess = Depends(get_workspace_access),
                db: AsyncSession = Depends(get_db_dep)) -> ApiResponse:
    return _ok(await service.audit_log(db, access.workspace_id))
