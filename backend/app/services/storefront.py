"""Storefront catalog service — buyer-facing view of the commerce store.

Exposes only buyer-safe fields (no cost), with a deterministic rating/reviews
derived from the product id so the catalog looks real and is stable across runs.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.storefront import (
    ReviewItem,
    StoreDetailResponse,
    StoreListResponse,
    StoreProduct,
)
from app.services import commerce_store as store
from app.services import inventory_service, review_service
from app.services.genai.demo_data import image_urls_for_type

log = get_logger("app.services.storefront")

# The catalogue is intentionally able to run from bundled demo data when the
# database is unavailable.  Avoid paying the database connect timeout for every
# best-effort stock/review query while it is known to be down.
_DB_DOWN_UNTIL: float = 0.0
_DB_DOWN_COOLDOWN = 30.0


def _database_available() -> bool:
    return settings.APP_ENV == "test" or time.monotonic() >= _DB_DOWN_UNTIL


def _mark_database_unavailable() -> None:
    global _DB_DOWN_UNTIL
    if settings.APP_ENV != "test":
        _DB_DOWN_UNTIL = time.monotonic() + _DB_DOWN_COOLDOWN


async def _attach_stock(products: list[StoreProduct], db: AsyncSession) -> None:
    """Fill in live stock, in place. Fails open: on a DB error `stock` stays
    None and the UI treats availability as unknown rather than sold out."""
    if not products or not _database_available():
        return
    try:
        levels = await inventory_service.stock_map(db, [p.id for p in products])
    except Exception as exc:  # noqa: BLE001 — stock display is best-effort
        _mark_database_unavailable()
        log.warning("storefront.stock_unavailable", error=str(exc))
        return
    for p in products:
        p.stock = levels.get(p.id)


def _to_product(p: dict) -> StoreProduct:
    image_urls = image_urls_for_type(p["type_key"], p["id"])
    reviews = p.get("reviews_list", [])
    rating = sum(review["rating"] for review in reviews) / max(len(reviews), 1)
    return StoreProduct(
        id=p["id"], sku=p["sku"], name=p["name"], brand=p["brand"], category=p["category"],
        price_vnd=p["price_vnd"], rating=round(rating, 1), reviews=len(reviews),
        trend=p["trend"], image_url=image_urls[0], image_urls=image_urls,
        attributes=p.get("attributes", {}),
    )


def list_products(q: str | None = None, category: str | None = None) -> StoreListResponse:
    items = store.all_products()
    if category:
        items = [p for p in items if p["category"] == category]
    if q:
        low = q.lower()
        items = [
            p for p in items
            if low in p["name"].lower() or low in p["brand"].lower()
            or any(low in v.lower() for v in p.get("attributes", {}).values())
        ]
    products = [_to_product(p) for p in items]
    return StoreListResponse(products=products, total=len(products))


def get_product(pid: str) -> StoreDetailResponse:
    p = next((x for x in store.all_products() if x["id"] == pid), None)
    if not p:
        return StoreDetailResponse(product=None, similar=[])
    similar = [_to_product(s) for s in store.similar_products(p, 4)]
    review_items = [ReviewItem(**r) for r in p.get("reviews_list", [])]
    return StoreDetailResponse(product=_to_product(p), similar=similar, review_items=review_items)


def _real_review_to_item(row) -> ReviewItem:
    days_ago = max(0, (datetime.now(UTC) - row.created_at).days)
    return ReviewItem(author=row.author_name, rating=row.rating, text=row.text, days_ago=days_ago)


async def list_products_with_stock(
    db: AsyncSession, q: str | None = None, category: str | None = None
) -> StoreListResponse:
    """Catalogue listing with live stock levels attached."""
    data = list_products(q=q, category=category)
    await _attach_stock(data.products, db)
    return data


async def get_product_with_reviews(pid: str, db: AsyncSession) -> StoreDetailResponse:
    """Same as :func:`get_product`, plus real published buyer reviews merged
    in (newest first, ahead of the fabricated demo reviews) and live stock.
    Fails open on a DB hiccup — the demo catalog must never break because
    reviews or stock are unavailable."""
    data = get_product(pid)
    if data.product is None:
        return data
    await _attach_stock([data.product, *data.similar], db)
    if not _database_available():
        return data
    try:
        real_rows = await review_service.list_published_reviews(db, pid)
    except Exception as exc:  # noqa: BLE001 — real reviews are best-effort
        _mark_database_unavailable()
        log.warning("storefront.real_reviews_unavailable", product_id=pid, error=str(exc))
        return data
    if not real_rows:
        return data
    real_items = [_real_review_to_item(r) for r in real_rows]
    data.review_items = [*real_items, *data.review_items]
    data.product.reviews += len(real_items)
    return data
