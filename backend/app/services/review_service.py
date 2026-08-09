"""Real review write path — moderate, then persist."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.review import Review
from app.schemas.reviews import ReviewCreateRequest
from app.services import review_moderation


async def create_review(
    db: AsyncSession, *, product_id: str, req: ReviewCreateRequest, category: str | None
) -> Review:
    decision = await review_moderation.moderate(req.text, req.rating, category)
    row = Review(
        product_id=product_id,
        author_name=req.author_name,
        rating=req.rating,
        text=req.text,
        status=decision.status,
        moderation_reason=decision.reason,
        moderation_confidence=decision.confidence,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_published_reviews(db: AsyncSession, product_id: str) -> list[Review]:
    result = await db.execute(
        select(Review)
        .where(Review.product_id == product_id, Review.status == "published")
        .order_by(Review.created_at.desc())
    )
    return list(result.scalars().all())


async def list_queue(db: AsyncSession) -> list[Review]:
    result = await db.execute(
        select(Review)
        .where(Review.status.in_(["pending", "flagged"]))
        .order_by(Review.created_at.asc())
    )
    return list(result.scalars().all())


async def set_status(db: AsyncSession, review_id: int, status: str) -> Review:
    row = await db.get(Review, review_id)
    if row is None:
        raise NotFoundError(f"Review {review_id} not found.")
    row.status = status
    await db.commit()
    await db.refresh(row)
    return row
