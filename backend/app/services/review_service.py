"""Real review write path — moderate, then persist."""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.review import Review
from app.schemas.insights import SentimentRequest
from app.schemas.reviews import ProductReviews, ReviewCreateRequest, ScoredReview
from app.services import commerce_store, insights, review_moderation


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


async def product_reviews(db: AsyncSession, product_id: str) -> ProductReviews:
    """Every review on a product, scored, newest first.

    Merges the two sources a seller actually has: reviews buyers submitted
    through the storefront, and the catalogue's own. They are kept
    distinguishable rather than blended — a seller reads their own customers'
    words differently from sample data.

    Sentiment runs through the same scorer the single-review screen used, so
    the two never disagree about the same sentence.
    """
    product = commerce_store.find_product(product_id)
    if product is None:
        raise NotFoundError(f"Không tìm thấy sản phẩm '{product_id}'.")

    rows: list[tuple[str, int, str, int | None, bool]] = [
        (r.author_name, r.rating, r.text, _days_since(r.created_at), True)
        for r in await list_published_reviews(db, product_id)
    ]
    rows += [
        (r["author"], r["rating"], r["text"], r.get("days_ago"), False)
        for r in product.get("reviews_list", [])
    ]
    # Newest first; catalogue entries carry a day offset, submitted ones a
    # timestamp, and None sorts last rather than crashing the comparison.
    rows.sort(key=lambda r: (r[3] is None, r[3] or 0))

    # Scored concurrently: the LLM path is a network round trip each, and a
    # product with two hundred reviews would otherwise wait for two hundred of
    # them in series.
    verdicts = await asyncio.gather(*(
        insights.analyze_sentiment(SentimentRequest(text=text, rating=rating))
        for _, rating, text, _, _ in rows
    ))
    scored = [
        ScoredReview(
            author=author, rating=rating, text=text, days_ago=days_ago,
            sentiment=verdict.sentiment, from_customers=from_customers,
        )
        for (author, rating, text, days_ago, from_customers), verdict
        in zip(rows, verdicts, strict=True)
    ]

    counts = Counter(r.sentiment for r in scored)
    return ProductReviews(
        product_id=product_id,
        product_name=product["name"],
        total=len(scored),
        positive=counts["positive"],
        neutral=counts["neutral"],
        negative=counts["negative"],
        avg_rating=round(sum(r.rating for r in scored) / len(scored), 1) if scored else 0.0,
        reviews=scored,
    )


def _days_since(moment: datetime | None) -> int | None:
    if moment is None:
        return None
    reference = moment if moment.tzinfo else moment.replace(tzinfo=UTC)
    return max(0, (datetime.now(UTC) - reference).days)
