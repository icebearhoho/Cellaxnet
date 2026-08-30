"""Order placement and lookup."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.order import Order, OrderItem
from app.schemas.orders import CheckoutRequest
from app.services import commerce_store as store
from app.services import inventory_service

_ORDER_NO_ATTEMPTS = 5
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"paid", "cancelled"},
    "paid": {"shipped", "cancelled"},
    "shipped": set(),
    "cancelled": set(),
}


def _new_order_no() -> str:
    """Human-readable and unique enough to say out loud: AR-20260807-A3F9C1."""
    day = datetime.now(UTC).strftime("%Y%m%d")
    return f"AR-{day}-{secrets.token_hex(3).upper()}"


async def create_order(
    db: AsyncSession, req: CheckoutRequest, *, customer_id: str | None = None
) -> Order:
    """Place an order: price it from the catalogue, take stock, write it down.

    Runs as one transaction, so a stock shortfall on the third line leaves no
    half-written order and no silently decremented stock for the first two.
    """
    catalogue = {p["id"]: p for p in store.all_products()}

    # Collapse duplicate lines first — otherwise two entries for the same
    # product would each pass their own stock check while together exceeding it.
    wanted: dict[str, int] = {}
    for item in req.items:
        if item.product_id not in catalogue:
            raise NotFoundError(f"Sản phẩm {item.product_id} không tồn tại.")
        wanted[item.product_id] = wanted.get(item.product_id, 0) + item.qty

    if not wanted:
        raise ValidationError("Giỏ hàng trống.")

    await inventory_service.take(db, list(wanted.items()))

    item_specs: list[dict[str, object]] = []
    total = 0
    for product_id, qty in wanted.items():
        p = catalogue[product_id]
        # Price comes from the catalogue, never from the request body.
        unit = int(p["price_vnd"])
        total += unit * qty
        item_specs.append({
            "product_id": product_id,
            "product_name": p["name"],
            "brand": p["brand"],
            "unit_price_vnd": unit,
            "qty": qty,
        })

    # order_no collisions are astronomically unlikely but cheap to survive.
    for attempt in range(_ORDER_NO_ATTEMPTS):
        if attempt:
            # The failed commit was rolled back, including the stock decrement.
            # Reserve it again before retrying the order insert.
            await inventory_service.take(db, list(wanted.items()))
        order = Order(
            order_no=_new_order_no(),
            customer_id=customer_id,
            customer_name=req.customer_name.strip(),
            email=(req.email or "").strip().lower() or None,
            total_vnd=total,
            status="pending",
            items=[OrderItem(**spec) for spec in item_specs],
        )
        db.add(order)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            if attempt == _ORDER_NO_ATTEMPTS - 1:
                raise
            continue
        await db.refresh(order)
        return order

    raise RuntimeError("unreachable")  # pragma: no cover


async def get_by_order_no(db: AsyncSession, order_no: str) -> Order:
    result = await db.execute(select(Order).where(Order.order_no == order_no))
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError(f"Không tìm thấy đơn {order_no}.")
    return order


async def list_for_customer(
    db: AsyncSession, customer_id: str, limit: int = 50
) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_all(db: AsyncSession, limit: int = 100) -> list[Order]:
    result = await db.execute(
        select(Order).order_by(Order.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def set_status(db: AsyncSession, order_no: str, status: str) -> Order:
    result = await db.execute(
        select(Order).where(Order.order_no == order_no).with_for_update()
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError(f"Không tìm thấy đơn {order_no}.")
    if status == order.status:
        return order
    if status not in _ALLOWED_TRANSITIONS.get(order.status, set()):
        raise ConflictError(
            f"Không thể chuyển đơn từ '{order.status}' sang '{status}'."
        )
    if status == "cancelled":
        await inventory_service.put_back(
            db, [(item.product_id, item.qty) for item in order.items]
        )
    order.status = status
    await db.commit()
    await db.refresh(order)
    return order
