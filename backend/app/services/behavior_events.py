"""Best-effort persistence of real tracked events — decoupled from analysis
(``journey.analyze_journey`` stays pure/DB-free) so a DB hiccup never breaks
the seller's "predict next action" UX."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.behavior_event import BehaviorEvent
from app.schemas.journey import JourneyEvent


def _to_datetime(ts: int | None) -> datetime:
    if ts is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(ts / 1000, tz=UTC)


async def persist_events(
    db: AsyncSession, *, session_id: str, customer_id: str | None, events: list[JourneyEvent]
) -> int:
    rows = [
        BehaviorEvent(
            session_id=session_id,
            customer_id=customer_id,
            event_type=e.type,
            category=e.category,
            query=e.query,
            occurred_at=_to_datetime(e.ts),
        )
        for e in events
    ]
    db.add_all(rows)
    await db.commit()
    return len(rows)
