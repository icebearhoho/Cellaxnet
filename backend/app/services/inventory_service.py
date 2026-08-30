"""Live stock levels, lazily seeded from the deterministic catalogue.

`commerce_store` regenerates the same numbers on every process start, so it
can't hold state. This module owns the mutable half: the first time a product
is read it copies the catalogue value into `product_stock`, and from then on
that row is the truth.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.product_stock import ProductStock
from app.services import commerce_store as store


async def ensure_seeded(db: AsyncSession, product_ids: list[str]) -> None:
    """Copy catalogue stock into the table for any product not tracked yet.

    ON CONFLICT DO NOTHING keeps this safe to call concurrently — two requests
    racing to seed the same product both succeed, neither overwrites a level
    that has already been decremented by a sale.
    """
    if not product_ids:
        return
    catalogue = {p["id"]: p for p in store.all_products()}
    rows = [
        {"product_id": pid, "stock": catalogue[pid]["stock"]}
        for pid in product_ids
        if pid in catalogue
    ]
    if not rows:
        return
    await db.execute(
        pg_insert(ProductStock).values(rows).on_conflict_do_nothing(
            index_elements=["product_id"]
        )
    )
    await db.commit()


async def stock_map(db: AsyncSession, product_ids: list[str]) -> dict[str, int]:
    """Current stock per product. Seeds first so every id gets an answer."""
    if not product_ids:
        return {}
    await ensure_seeded(db, product_ids)
    result = await db.execute(
        select(ProductStock.product_id, ProductStock.stock).where(
            ProductStock.product_id.in_(product_ids)
        )
    )
    return {pid: qty for pid, qty in result.all()}


async def take(db: AsyncSession, items: list[tuple[str, int]]) -> None:
    """Decrement stock for (product_id, qty) pairs, or raise.

    The guard lives in the UPDATE's WHERE clause rather than in a read-then-write
    check, so two simultaneous checkouts for the last unit can't both succeed:
    whichever runs second matches no row and we raise. Caller owns the
    transaction — this does not commit.
    """
    ids = [pid for pid, _ in items]
    await ensure_seeded(db, ids)

    for product_id, qty in items:
        # The `stock >= qty` guard is part of the UPDATE, not a prior SELECT, so
        # the database arbitrates. `updated_at` is refreshed by the column's
        # onupdate default, which Core UPDATEs honour.
        result = await db.execute(
            update(ProductStock)
            .where(ProductStock.product_id == product_id, ProductStock.stock >= qty)
            .values(stock=ProductStock.stock - qty)
        )
        if cast(CursorResult, result).rowcount == 0:
            # Either the product isn't tracked, or there isn't enough left.
            current = await db.execute(
                select(ProductStock.stock).where(ProductStock.product_id == product_id)
            )
            left = current.scalar_one_or_none()
            if left is None:
                raise NotFoundError(f"Sản phẩm {product_id} không tồn tại.")
            raise ConflictError(
                f"Không đủ hàng: chỉ còn {left} sản phẩm."
            )


async def put_back(db: AsyncSession, items: list[tuple[str, int]]) -> None:
    """Return previously reserved units to stock without committing.

    Used when an unshipped order is cancelled. The caller owns the transaction
    so the order-state change and stock restoration succeed or fail together.
    """
    for product_id, qty in items:
        result = await db.execute(
            update(ProductStock)
            .where(ProductStock.product_id == product_id)
            .values(stock=ProductStock.stock + qty)
        )
        if cast(CursorResult, result).rowcount == 0:
            raise NotFoundError(f"Sản phẩm {product_id} không tồn tại trong kho.")
