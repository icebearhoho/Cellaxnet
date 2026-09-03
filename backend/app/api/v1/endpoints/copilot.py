"""Seller Copilot — conversational AI agent + daily action briefing."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import ApiResponse, PageMeta
from app.db.session import get_db
from app.schemas.copilot import CopilotAgentRequest, CopilotRequest
from app.services import copilot as service

router = APIRouter()


@router.post("/ask", response_model=ApiResponse[dict])
async def ask(req: CopilotRequest) -> ApiResponse[dict]:
    data = await service.ask(req.question)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.post("/agent", response_model=ApiResponse[dict])
async def agent(
    req: CopilotAgentRequest, db: AsyncSession = Depends(get_db)
) -> ApiResponse[dict]:
    """Multi-step agent: OpenAI function-calling over the store-grounded tools."""
    data = await service.agent_ask(
        req.question, db, [h.model_dump() for h in req.history]
    )
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.get("/briefing", response_model=ApiResponse[dict])
async def briefing() -> ApiResponse[dict]:
    data = await service.briefing()
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)
