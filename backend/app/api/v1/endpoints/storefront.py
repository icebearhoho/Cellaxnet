"""Buyer storefront — catalogue, reviews and the order/checkout path.

Mixed audience, so this router is NOT gated wholesale in :mod:`app.api.v1`:
browsing, submitting a review and placing an order stay open to anonymous
shoppers, while the moderation queue and the all-orders view are admin-only
per-route. Reading *your own* orders needs a login (there'd be no way to scope
the query otherwise), which is why it uses `get_current_user` rather than
`require_admin`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_current_user_optional,
    get_db_dep,
    require_admin,
)
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.responses import ApiResponse, PageMeta
from app.schemas.orders import (
    CheckoutRequest,
    OrderItemOut,
    OrderOut,
    StatusUpdateRequest,
)
from app.schemas.reviews import ReviewCreateRequest, ReviewQueueItem, ReviewSubmitResponse
from app.schemas.storefront import ReviewItem
from app.services import commerce_store as store
from app.services import order_service, review_service
from app.services import storefront as service

log = get_logger("app.api.storefront")

router = APIRouter()

_STATUS_MESSAGE = {
    "published": "Cảm ơn bạn đã đánh giá! Đánh giá của bạn đã được hiển thị.",
    "pending": "Cảm ơn bạn, đánh giá của bạn đang được duyệt và sẽ hiển thị sau khi được kiểm tra.",
    "flagged": "Cảm ơn bạn, đánh giá của bạn đang được duyệt và sẽ hiển thị sau khi được kiểm tra.",
    "rejected": "Đánh giá chưa thể đăng do có dấu hiệu nội dung không phù hợp. Vui lòng thử lại với nội dung chi tiết hơn.",
}


def _order_out(order) -> dict:  # noqa: ANN001 — app.models.order.Order
    return OrderOut(
        order_no=order.order_no,
        status=order.status,
        customer_name=order.customer_name,
        email=order.email,
        total_vnd=order.total_vnd,
        created_at=order.created_at.isoformat(),
        items=[
            OrderItemOut(
                product_id=i.product_id,
                product_name=i.product_name,
                brand=i.brand,
                unit_price_vnd=i.unit_price_vnd,
                qty=i.qty,
                line_total_vnd=i.unit_price_vnd * i.qty,
            )
            for i in order.items
        ],
    ).model_dump()


def _demo_order_out(order: dict) -> dict:
    products = {product["id"]: product for product in store.all_products()}
    status = {
        "delivered": "shipped", "returned": "cancelled",
    }.get(order["status"], order["status"])
    customer = next(
        (row for row in store.all_customers() if row["id"] == order["customer_id"]),
        None,
    )
    return {
        "order_no": order["order_no"], "status": status,
        "customer_name": order["customer_name"],
        "email": customer.get("email") if customer else None,
        "total_vnd": order["total_vnd"], "created_at": order["created_at"],
        "channel": order["channel"], "demo_order": True,
        "items": [
            {
                "product_id": line["product_id"],
                "product_name": line["product_name"],
                "brand": products[line["product_id"]]["brand"],
                "unit_price_vnd": line["unit_price_vnd"], "qty": line["qty"],
                "line_total_vnd": line["line_total_vnd"],
            }
            for line in order["items"]
        ],
    }


@router.get("/products", response_model=ApiResponse[dict])
async def products(
    q: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    data = await service.list_products_with_stock(db, q=q, category=category)
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


# --- Orders -----------------------------------------------------------------
# Checkout is intentionally open to anonymous shoppers, matching the rest of the
# buyer flow. There is NO payment gateway: an order is created as "pending" and
# a seller moves it forward by hand.


@router.post("/checkout", response_model=ApiResponse[dict])
async def checkout(
    req: CheckoutRequest,
    user: dict | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db_dep),
) -> ApiResponse[dict]:
    # Attach the order to an account when the caller happens to be signed in,
    # but never require it — a guest must still be able to buy.
    customer_id = str(user["sub"]) if user else None
    order = await order_service.create_order(db, req, customer_id=customer_id)
    return ApiResponse[dict](
        success=True, data=_order_out(order), meta=PageMeta(), error=None
    )


@router.get("/orders", response_model=ApiResponse[list[dict]])
async def my_orders(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db_dep)
) -> ApiResponse[list[dict]]:
    """The caller's own orders. Needs a login — there's nothing to scope by
    otherwise (guest orders are only retrievable by their order number)."""
    rows = await order_service.list_for_customer(db, str(user["sub"]))
    items = [_order_out(o) for o in rows]
    return ApiResponse[list[dict]](
        success=True, data=items, meta=PageMeta(total=len(items)), error=None
    )


@router.get(
    "/orders/all",
    response_model=ApiResponse[list[dict]],
    dependencies=[Depends(require_admin)],
)
async def all_orders(db: AsyncSession = Depends(get_db_dep)) -> ApiResponse[list[dict]]:
    try:
        rows = await order_service.list_all(db)
    except Exception as exc:  # noqa: BLE001 — the seller dashboard must not crash on a DB hiccup
        log.warning("storefront.orders_unavailable", error=str(exc))
        rows = []
    items = [_order_out(o) for o in rows]
    if not items:
        items = [_demo_order_out(order) for order in store.all_demo_orders()[:100]]
    return ApiResponse[list[dict]](
        success=True, data=items, meta=PageMeta(total=len(items)), error=None
    )


@router.post(
    "/orders/{order_no}/status",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_admin)],
)
async def update_order_status(
    order_no: str, req: StatusUpdateRequest, db: AsyncSession = Depends(get_db_dep)
) -> ApiResponse[dict]:
    order = await order_service.set_status(db, order_no, req.status)
    return ApiResponse[dict](
        success=True, data=_order_out(order), meta=PageMeta(), error=None
    )


@router.get(
    "/reviews/queue",
    response_model=ApiResponse[list[dict]],
    dependencies=[Depends(require_admin)],
)
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


@router.post(
    "/reviews/{review_id}/approve",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_admin)],
)
async def approve_review(review_id: int, db: AsyncSession = Depends(get_db_dep)) -> ApiResponse[dict]:
    row = await review_service.set_status(db, review_id, "published")
    return ApiResponse[dict](success=True, data={"id": row.id, "status": row.status}, meta=PageMeta(), error=None)


@router.post(
    "/reviews/{review_id}/reject",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_admin)],
)
async def reject_review(review_id: int, db: AsyncSession = Depends(get_db_dep)) -> ApiResponse[dict]:
    row = await review_service.set_status(db, review_id, "rejected")
    return ApiResponse[dict](success=True, data={"id": row.id, "status": row.status}, meta=PageMeta(), error=None)
