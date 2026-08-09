"""Customer Journey Intelligence — Track 1, Đề 2 (not one of the original 17 ideas)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_dep
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.core.responses import ApiResponse, PageMeta
from app.schemas.journey import JourneyRequest
from app.services import behavior_events, portfolio
from app.services import journey as service

log = get_logger("app.api.journey")

router = APIRouter()


@router.post("/", response_model=ApiResponse[dict])
async def analyze(req: JourneyRequest) -> ApiResponse[dict]:
    data = await service.analyze_journey(req)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.post("/events", response_model=ApiResponse[dict])
async def track_events(
    req: JourneyRequest, db: AsyncSession = Depends(get_db_dep)
) -> ApiResponse[dict]:
    """Persist real tracked events for later analytics. Best-effort: a DB
    hiccup must never break the live journey UX, so failures fail open."""
    if not req.session_id:
        raise ValidationError("session_id is required.")
    try:
        n = await behavior_events.persist_events(
            db, session_id=req.session_id, customer_id=None, events=req.events,
        )
    except Exception as exc:  # noqa: BLE001 — persistence is best-effort
        log.warning("journey.events.persist_failed", session_id=req.session_id, error=str(exc))
        n = 0
    return ApiResponse[dict](success=True, data={"persisted": n}, meta=PageMeta(), error=None)


@router.get("/sessions", response_model=ApiResponse[dict])
async def sessions() -> ApiResponse[dict]:
    """Pre-built demo shopping sessions with replay videos, ready to test."""
    data = await portfolio.journey_sessions()
    return ApiResponse[dict](success=True, data=data, meta=PageMeta(), error=None)
