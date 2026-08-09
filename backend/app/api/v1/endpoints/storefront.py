"""Buyer storefront catalog — list + detail from the commerce store, plus the
real review write path (submit / moderation queue / approve / reject)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_dep
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.responses import ApiResponse, PageMeta
from app.schemas.reviews import ReviewCreateRequest, ReviewQueueItem, ReviewSubmitResponse
from app.schemas.storefront import ReviewItem
from app.services import commerce_store as store
from app.services import review_service
from app.services import storefront as service

log = get_logger("app.api.storefront")

router = APIRouter()

_STATUS_MESSAGE = {
    "published": "Cảm ơn bạn đã đánh giá! Đánh giá của bạn đã được hiển thị.",
    "pending": "Cảm ơn bạn, đánh giá của bạn đang được duyệt và sẽ hiển thị sau khi được kiểm tra.",
    "flagged": "Cảm ơn bạn, đánh giá của bạn đang được duyệt và sẽ hiển thị sau khi được kiểm tra.",
    "rejected": "Đánh giá chưa thể đăng do có dấu hiệu nội dung không phù hợp. Vui lòng thử lại với nội dung chi tiết hơn.",
}


@router.get("/products", response_model=ApiResponse[dict])
async def products(q: str | None = None, category: str | None = None) -> ApiResponse[dict]:
    data = service.list_products(q=q, category=category)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.get("/products/{pid}", response_model=ApiResponse[dict])
async def product_detail(pid: str, db: AsyncSession = Depends(get_db_dep)) -> ApiResponse[dict]:
    data = await service.get_product_with_reviews(pid, db)
    return ApiResponse[dict](success=True, data=data.model_dump(), meta=PageMeta(), error=None)


@router.post("/products/{pid}/reviews", response_model=ApiResponse[dict])
async def submit_review(
    pid: str, req: ReviewCreateRequest, db: AsyncSession = Depends(get_db_dep)
) -> ApiResponse[dict]:
    product = next((p for p in store.all_products() if p["id"] == pid), None)
    if product is None:
        raise NotFoundError(f"Product {pid} not found.")

    row = await review_service.create_review(db, product_id=pid, req=req, category=product["category"])
    resp = ReviewSubmitResponse(
        status=row.status,  # type: ignore[arg-type]
        message=_STATUS_MESSAGE[row.status],
        review=ReviewItem(author=row.author_name, rating=row.rating, text=row.text, days_ago=0)
        if row.status == "published" else None,
    )
    return ApiResponse[dict](success=True, data=resp.model_dump(), meta=PageMeta(), error=None)


@router.get("/reviews/queue", response_model=ApiResponse[list[dict]])
async def review_queue(db: AsyncSession = Depends(get_db_dep)) -> ApiResponse[list[dict]]:
    try:
        rows = await review_service.list_queue(db)
    except Exception as exc:  # noqa: BLE001 — the seller dashboard must not crash on a DB hiccup
        log.warning("storefront.review_queue_unavailable", error=str(exc))
        rows = []
    products_by_id = {p["id"]: p["name"] for p in store.all_products()}
    items = [
        ReviewQueueItem(
            id=r.id, product_id=r.product_id, product_name=products_by_id.get(r.product_id, r.product_id),
            author_name=r.author_name, rating=r.rating, text=r.text, status=r.status,  # type: ignore[arg-type]
            moderation_reason=r.moderation_reason, moderation_confidence=r.moderation_confidence,
            created_at=r.created_at.isoformat(),
        ).model_dump()
        for r in rows
    ]
    return ApiResponse[list[dict]](success=True, data=items, meta=PageMeta(total=len(items)), error=None)


@router.post("/reviews/{review_id}/approve", response_model=ApiResponse[dict])
async def approve_review(review_id: int, db: AsyncSession = Depends(get_db_dep)) -> ApiResponse[dict]:
    row = await review_service.set_status(db, review_id, "published")
    return ApiResponse[dict](success=True, data={"id": row.id, "status": row.status}, meta=PageMeta(), error=None)


@router.post("/reviews/{review_id}/reject", response_model=ApiResponse[dict])
async def reject_review(review_id: int, db: AsyncSession = Depends(get_db_dep)) -> ApiResponse[dict]:
    row = await review_service.set_status(db, review_id, "rejected")
    return ApiResponse[dict](success=True, data={"id": row.id, "status": row.status}, meta=PageMeta(), error=None)
