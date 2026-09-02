"""Product performance and similarity computed from synced marketplace data.

The demo source is adapted from ``commerce_store``; connected shops use
``ShopProduct``, ``ShopOrder`` and ``ShopOrderItem`` records. Rankings,
explanations, and comparisons are deterministic and never call an LLM.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.marketplace import (
    ShopConnection,
    ShopOrder,
    ShopOrderItem,
    ShopProduct,
)
from app.schemas.product_graph import (
    CategoryPerformance,
    GraphDataSource,
    ProductGraphOverview,
    ProductGraphRequest,
    ProductGraphResponse,
    ProductPerformance,
    ShopSourceOption,
    SimilarProduct,
)
from app.services import commerce_store as demo_store
from app.services.genai.demo_data import image_urls_for_type

_REVENUE_STATUSES = {"awaiting_shipment", "shipped", "delivered", "completed"}
_REVENUE_DEFINITION = (
    "Tổng thành tiền của từng dòng hàng (subtotal; nếu sàn không trả subtotal thì "
    "dùng đơn giá × số lượng) thuộc đơn chờ giao, đang giao, đã giao hoặc hoàn tất. "
    "Không tính đơn chưa thanh toán, đã huỷ, hoàn trả hay trạng thái chưa ánh xạ; "
    "phí/giảm giá cấp đơn không được phân bổ vào sản phẩm."
)
_DEMO_REVENUE_DEFINITION = (
    "Dữ liệu demo của Mây House Official: tổng line_total_vnd của từng dòng hàng "
    "thuộc đơn delivered, shipped hoặc paid. Không tính đơn pending, cancelled hay returned. "
    "Đây là dữ liệu mô phỏng cố định của shop demo, không phải doanh thu lấy từ sàn."
)
_DEMO_SHOP_ID = -1
_TOKEN_RE = re.compile(r"[0-9a-zA-ZÀ-ỹ]+", re.UNICODE)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _iso(value: datetime | None) -> str | None:
    aware = _aware(value)
    return aware.isoformat() if aware else None


def _category(path: str | None) -> str:
    if not path or not path.strip():
        return "Chưa phân loại"
    parts = re.split(r"\s*(?:>|/|\|)\s*", path.strip())
    return next((part for part in parts if part), path.strip())


def _tokens(value: str) -> set[str]:
    ignored = {"va", "và", "cho", "cua", "của", "the", "with", "san", "sản", "pham", "phẩm"}
    return {token.lower() for token in _TOKEN_RE.findall(value) if len(token) > 1 and token.lower() not in ignored}


def _line_revenue(item: ShopOrderItem) -> int:
    subtotal = int(item.subtotal or 0)
    return subtotal if subtotal > 0 else int(item.unit_price or 0) * int(item.quantity or 0)


async def _count(db: AsyncSession, statement: Any) -> int:
    return int((await db.scalar(statement)) or 0)


async def _shop_options(db: AsyncSession) -> list[ShopSourceOption]:
    shops = list((await db.scalars(select(ShopConnection).order_by(ShopConnection.id))).all())
    options: list[ShopSourceOption] = []
    for shop in shops:
        product_count = await _count(
            db,
            select(func.count(ShopProduct.id)).where(ShopProduct.shop_connection_id == shop.id),
        )
        order_count = await _count(
            db,
            select(func.count(ShopOrder.id)).where(ShopOrder.shop_connection_id == shop.id),
        )
        options.append(
            ShopSourceOption(
                id=shop.id,
                platform=shop.platform,
                shop_name=shop.shop_name or f"{shop.platform.title()} shop {shop.external_shop_id}",
                status=shop.status,
                last_synced_at=_iso(shop.last_synced_at),
                product_records=product_count,
                order_records=order_count,
            )
        )
    return options


def _demo_option() -> ShopSourceOption:
    profile = demo_store.shop_profile()
    return ShopSourceOption(
        id=_DEMO_SHOP_ID,
        platform="demo",
        shop_name=profile["name"],
        status="demo",
        last_synced_at=profile["data_as_of"],
        product_records=len(demo_store.all_products()),
        order_records=len(demo_store.all_demo_orders()),
    )


def _demo_dataset(days: int) -> tuple[dict[str, Any], GraphDataSource]:
    """Adapt the shared Mây House demo catalog/order history to graph rows."""
    profile = demo_store.shop_profile()
    catalog = demo_store.all_products()
    orders = demo_store.all_demo_orders()
    period_end = datetime.fromisoformat(str(profile["data_as_of"]))
    period_start = period_end - timedelta(days=days)
    previous_start = period_start - timedelta(days=days)

    products: dict[str, dict[str, Any]] = {}
    for product in catalog:
        products[product["id"]] = {
            "id": product["id"],
            "external_product_id": product["id"],
            "sku": product["sku"],
            "name": product["name"],
            "brand": product["brand"],
            "category": product["category"],
            "price_vnd": int(product["price_vnd"]),
            "image_url": image_urls_for_type(product["type_key"], product["id"], count=1)[0],
            "type_key": product.get("type_key"),
            "attributes": product.get("attributes", {}),
            "current_revenue": 0,
            "current_units": 0,
            "current_orders": set(),
            "previous_revenue": 0,
            "previous_units": 0,
            "previous_orders": set(),
        }

    recognized = {"delivered", "shipped", "paid"}
    for order in orders:
        placed_at = datetime.fromisoformat(order["created_at"])
        if order["status"] not in recognized or placed_at < previous_start or placed_at > period_end:
            continue
        period_key = "current" if placed_at >= period_start else "previous"
        for line in order["items"]:
            row = products.get(line["product_id"])
            if row is None:
                continue
            row[f"{period_key}_revenue"] += int(line["line_total_vnd"])
            row[f"{period_key}_units"] += int(line["qty"])
            row[f"{period_key}_orders"].add(order["id"])

    source = GraphDataSource(
        kind="demo_shop",
        shop_connection_id=_DEMO_SHOP_ID,
        platform="demo",
        shop_name=profile["name"],
        status="demo",
        last_synced_at=str(profile["data_as_of"]),
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        period_days=days,
        product_records=len(catalog),
        order_records=len(orders),
        order_item_records=sum(len(order["items"]) for order in orders),
        demo_data_used=True,
        revenue_definition=_DEMO_REVENUE_DEFINITION,
    )
    return products, source


async def _choose_shop(
    db: AsyncSession, shop_connection_id: int | None
) -> tuple[ShopConnection | None, list[ShopSourceOption]]:
    options = await _shop_options(db)
    if not options:
        return None, options

    if shop_connection_id is not None:
        shop = await db.get(ShopConnection, shop_connection_id)
        return shop, options

    preferred = next(
        (option for option in options if option.product_records > 0 and option.order_records > 0),
        next((option for option in options if option.product_records > 0), options[0]),
    )
    return await db.get(ShopConnection, preferred.id), options


async def _dataset(
    db: AsyncSession, shop: ShopConnection, days: int
) -> tuple[dict[str, Any], GraphDataSource]:
    variants = list(
        (
            await db.scalars(
                select(ShopProduct)
                .where(ShopProduct.shop_connection_id == shop.id)
                .order_by(ShopProduct.id)
            )
        ).all()
    )
    total_orders = await _count(
        db, select(func.count(ShopOrder.id)).where(ShopOrder.shop_connection_id == shop.id)
    )
    total_items = await _count(
        db,
        select(func.count(ShopOrderItem.id))
        .join(ShopOrder, ShopOrder.id == ShopOrderItem.order_id)
        .where(ShopOrder.shop_connection_id == shop.id),
    )
    latest_order = await db.scalar(
        select(func.max(ShopOrder.placed_at)).where(ShopOrder.shop_connection_id == shop.id)
    )
    anchors = [value for value in (_aware(shop.last_synced_at), _aware(latest_order)) if value]
    period_end = max(anchors) if anchors else datetime.now(UTC)
    period_start = period_end - timedelta(days=days)
    previous_start = period_start - timedelta(days=days)

    orders = list(
        (
            await db.scalars(
                select(ShopOrder)
                .where(
                    ShopOrder.shop_connection_id == shop.id,
                    ShopOrder.status.in_(_REVENUE_STATUSES),
                    ShopOrder.placed_at.is_not(None),
                    ShopOrder.placed_at >= previous_start,
                    ShopOrder.placed_at <= period_end,
                )
                .options(selectinload(ShopOrder.items))
            )
        ).unique().all()
    )

    source = GraphDataSource(
        kind="marketplace_sync",
        shop_connection_id=shop.id,
        platform=shop.platform,
        shop_name=shop.shop_name or f"{shop.platform.title()} shop {shop.external_shop_id}",
        status=shop.status,
        last_synced_at=_iso(shop.last_synced_at),
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        period_days=days,
        product_records=len(variants),
        order_records=total_orders,
        order_item_records=total_items,
        demo_data_used=False,
        revenue_definition=_REVENUE_DEFINITION,
    )

    products: dict[str, dict[str, Any]] = {}
    sku_to_product: dict[str, str] = {}
    for variant in variants:
        product_id = variant.external_product_id
        row = products.setdefault(
            product_id,
            {
                "id": product_id,
                "external_product_id": product_id,
                "sku": variant.sku,
                "name": variant.name,
                "brand": variant.brand,
                "category": _category(variant.category_path),
                "price_values": [],
                "image_url": variant.image_url,
                "current_revenue": 0,
                "current_units": 0,
                "current_orders": set(),
                "previous_revenue": 0,
                "previous_units": 0,
                "previous_orders": set(),
            },
        )
        if variant.price is not None:
            row["price_values"].append(int(variant.price))
        if not row["image_url"] and variant.image_url:
            row["image_url"] = variant.image_url
        if variant.sku:
            sku_to_product[variant.sku] = product_id
        if variant.external_sku_id:
            sku_to_product[variant.external_sku_id] = product_id

    for order in orders:
        placed_at = _aware(order.placed_at)
        if placed_at is None:
            continue
        period_key = "current" if placed_at >= period_start else "previous"
        for item in order.items:
            order_product_id: str | None = item.external_product_id
            if not order_product_id or order_product_id not in products:
                order_product_id = (
                    sku_to_product.get(item.sku or "")
                    or sku_to_product.get(item.external_sku_id or "")
                )
            if not order_product_id or order_product_id not in products:
                continue
            row = products[order_product_id]
            row[f"{period_key}_revenue"] += _line_revenue(item)
            row[f"{period_key}_units"] += int(item.quantity or 0)
            row[f"{period_key}_orders"].add(order.id)

    for row in products.values():
        prices = row.pop("price_values")
        row["price_vnd"] = min(prices) if prices else None

    return products, source


def _growth(current: int, previous: int) -> float | None:
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _rank_maps(products: dict[str, dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    ranked = sorted(
        products.values(),
        key=lambda row: (-row["current_revenue"], -row["current_units"], row["name"].lower()),
    )
    overall = {row["id"]: index + 1 for index, row in enumerate(ranked)}
    category_ranks: dict[str, int] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ranked:
        grouped[row["category"]].append(row)
    for rows in grouped.values():
        for index, row in enumerate(rows):
            category_ranks[row["id"]] = index + 1
    return overall, category_ranks


def _highlight_reason(row: dict[str, Any], category_rank: int, days: int) -> str:
    growth = _growth(row["current_revenue"], row["previous_revenue"])
    facts = [f"Hạng {category_rank} doanh thu trong danh mục {row['category']}"]
    facts.append(
        f"{row['current_units']} sản phẩm từ {len(row['current_orders'])} đơn hợp lệ trong {days} ngày"
    )
    if growth is not None:
        direction = "tăng" if growth >= 0 else "giảm"
        facts.append(f"doanh thu {direction} {abs(growth):.1f}% so với {days} ngày liền trước")
    else:
        facts.append("chưa có doanh thu kỳ trước để tính tăng trưởng")
    return "; ".join(facts) + "."


def _performance(
    row: dict[str, Any], overall_rank: dict[str, int], category_rank: dict[str, int],
    category_total: dict[str, int], days: int,
) -> ProductPerformance:
    category_revenue = category_total.get(row["category"], 0)
    share = round(row["current_revenue"] / category_revenue * 100, 1) if category_revenue else 0.0
    return ProductPerformance(
        id=row["id"],
        external_product_id=row["external_product_id"],
        sku=row["sku"],
        name=row["name"],
        brand=row["brand"],
        category=row["category"],
        price_vnd=row["price_vnd"],
        image_url=row["image_url"],
        revenue_vnd=row["current_revenue"],
        units_sold=row["current_units"],
        orders_count=len(row["current_orders"]),
        revenue_rank=overall_rank[row["id"]],
        category_rank=category_rank[row["id"]],
        category_revenue_share_pct=share,
        sales_change_pct=_growth(row["current_revenue"], row["previous_revenue"]),
        highlight_reason=_highlight_reason(row, category_rank[row["id"]], days),
    )


def _similarity(reference: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, str]:
    score = 0.30  # candidates are constrained to the same category
    reasons = [f"cùng danh mục {reference['category']}"]
    if reference.get("type_key") and reference.get("type_key") == candidate.get("type_key"):
        score += 0.30
        reasons.append("cùng loại sản phẩm")
    if reference["brand"] and candidate["brand"] and reference["brand"].lower() == candidate["brand"].lower():
        score += 0.15
        reasons.append(f"cùng thương hiệu {reference['brand']}")

    reference_tokens = _tokens(reference["name"])
    candidate_tokens = _tokens(candidate["name"])
    union = reference_tokens | candidate_tokens
    token_score = len(reference_tokens & candidate_tokens) / len(union) if union else 0.0
    score += token_score * 0.15
    if token_score >= 0.2:
        reasons.append("tên sản phẩm có thuộc tính chung")

    reference_price = reference["price_vnd"]
    candidate_price = candidate["price_vnd"]
    if reference_price and candidate_price:
        price_distance = abs(reference_price - candidate_price) / max(reference_price, candidate_price)
        score += max(0.0, 1 - price_distance) * 0.10
        if price_distance <= 0.2:
            reasons.append("mức giá gần nhau")
    return round(min(score, 1.0) * 100, 1), "; ".join(reasons)


def _comparison(reference: dict[str, Any], candidate: dict[str, Any]) -> str:
    reference_revenue = reference["current_revenue"]
    candidate_revenue = candidate["current_revenue"]
    revenue_gap = candidate_revenue - reference_revenue
    formatted_gap = f"{abs(revenue_gap):,}₫".replace(",", ".")
    if revenue_gap == 0:
        revenue_text = "cùng mức doanh thu"
    elif revenue_gap > 0:
        revenue_text = f"doanh thu cao hơn {formatted_gap}"
    else:
        revenue_text = f"doanh thu thấp hơn {formatted_gap}"
    unit_gap = candidate["current_units"] - reference["current_units"]
    if unit_gap == 0:
        unit_text = "cùng số lượng bán"
    elif unit_gap > 0:
        unit_text = f"bán nhiều hơn {unit_gap} sản phẩm"
    else:
        unit_text = f"bán ít hơn {abs(unit_gap)} sản phẩm"
    return f"{revenue_text}; {unit_text}."


def _missing_overview(
    source: GraphDataSource | None, options: list[ShopSourceOption], reason: str
) -> ProductGraphOverview:
    return ProductGraphOverview(
        data_available=False,
        source=source,
        available_shops=options,
        categories=[],
        top_products=[],
        summary="Chưa thể xếp hạng sản phẩm bằng dữ liệu thật.",
        missing_reason=reason,
    )


async def _resolve_dataset(
    db: AsyncSession, shop_connection_id: int | None, days: int
) -> tuple[dict[str, Any], GraphDataSource, list[ShopSourceOption]]:
    """Choose real synced data when available, otherwise the shared demo shop."""
    real_options = await _shop_options(db)
    options = [_demo_option(), *real_options]
    has_complete_real_source = any(
        option.product_records > 0 and option.order_records > 0 for option in real_options
    )
    if shop_connection_id == _DEMO_SHOP_ID or (
        shop_connection_id is None and not has_complete_real_source
    ):
        products, source = _demo_dataset(days)
        return products, source, options

    shop, _ = await _choose_shop(db, shop_connection_id)
    if shop is None:
        products, source = _demo_dataset(days)
        return products, source, options
    products, source = await _dataset(db, shop, days)
    return products, source, options


async def overview(
    db: AsyncSession, shop_connection_id: int | None = None, days: int = 30
) -> ProductGraphOverview:
    products, source, options = await _resolve_dataset(db, shop_connection_id, days)
    if not products:
        return _missing_overview(
            source,
            options,
            "Cửa hàng này chưa có sản phẩm được đồng bộ. Hệ thống không dùng sản phẩm mẫu để thay thế.",
        )
    if source.order_item_records == 0:
        return _missing_overview(
            source,
            options,
            "Cửa hàng này chưa có dòng đơn hàng được đồng bộ. Hệ thống không tạo doanh thu giả.",
        )

    rows = list(products.values())
    current_rows = [row for row in rows if row["current_revenue"] > 0 or row["current_units"] > 0]
    if not current_rows:
        return _missing_overview(
            source,
            options,
            f"Không có dòng hàng thuộc đơn hợp lệ trong kỳ {days} ngày đang xét.",
        )

    overall_rank, category_rank = _rank_maps(products)
    category_total: dict[str, int] = defaultdict(int)
    category_units: dict[str, int] = defaultdict(int)
    category_orders: dict[str, set[Any]] = defaultdict(set)
    category_previous: dict[str, int] = defaultdict(int)
    category_products: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        category = row["category"]
        category_total[category] += row["current_revenue"]
        category_units[category] += row["current_units"]
        category_orders[category].update(row["current_orders"])
        category_previous[category] += row["previous_revenue"]
        category_products[category].append(row)

    total_revenue = sum(category_total.values())
    category_names = sorted(category_products, key=lambda name: (-category_total[name], name.lower()))
    categories: list[CategoryPerformance] = []
    for index, category in enumerate(category_names):
        ranked = sorted(
            category_products[category],
            key=lambda row: (-row["current_revenue"], -row["current_units"], row["name"].lower()),
        )
        top = ranked[0]
        categories.append(
            CategoryPerformance(
                category=category,
                rank=index + 1,
                revenue_vnd=category_total[category],
                units_sold=category_units[category],
                orders_count=len(category_orders[category]),
                revenue_share_pct=(
                    round(category_total[category] / total_revenue * 100, 1) if total_revenue else 0.0
                ),
                growth_pct=_growth(category_total[category], category_previous[category]),
                product_count=len(ranked),
                top_product_id=top["id"],
                top_product_name=top["name"],
                top_product_image_url=top["image_url"],
                top_product_names=[row["name"] for row in ranked[:3]],
            )
        )

    ranked_rows = sorted(
        rows,
        key=lambda row: (-row["current_revenue"], -row["current_units"], row["name"].lower()),
    )
    top_products = [
        _performance(row, overall_rank, category_rank, category_total, days)
        for row in ranked_rows
    ]
    leader = categories[0]
    return ProductGraphOverview(
        data_available=True,
        source=source,
        available_shops=options,
        categories=categories,
        top_products=top_products,
        summary=(
            f"{leader.category} đứng đầu theo doanh thu dòng hàng trong kỳ, chiếm "
            f"{leader.revenue_share_pct:.1f}% doanh thu hợp lệ của shop."
        ),
    )


async def detail(
    db: AsyncSession, product_id: str, shop_connection_id: int | None = None, days: int = 30
) -> ProductGraphResponse:
    products, source, _ = await _resolve_dataset(db, shop_connection_id, days)
    row = products.get(product_id)
    if row is None:
        return ProductGraphResponse(
            found=False, data_available=bool(products), source=source, product=None,
            similar_products=[], summary="Không tìm thấy sản phẩm này trong dữ liệu đã đồng bộ.",
        )

    overall_rank, category_rank = _rank_maps(products)
    category_total: dict[str, int] = defaultdict(int)
    for product in products.values():
        category_total[product["category"]] += product["current_revenue"]
    selected = _performance(row, overall_rank, category_rank, category_total, days)

    candidates: list[tuple[float, dict[str, Any], str]] = []
    for candidate in products.values():
        if candidate["id"] == row["id"] or candidate["category"] != row["category"]:
            continue
        similarity_score, relation = _similarity(row, candidate)
        candidates.append((similarity_score, candidate, relation))
    candidates.sort(
        key=lambda entry: (-entry[0], -entry[1]["current_revenue"], entry[1]["name"].lower())
    )

    similar: list[SimilarProduct] = []
    for _similarity_score, candidate, relation in candidates[:6]:
        performance = _performance(candidate, overall_rank, category_rank, category_total, days)
        comparison = _comparison(row, candidate)
        similar.append(
            SimilarProduct(
                **performance.model_dump(),
                relation=relation,
                comparison=comparison,
            )
        )

    return ProductGraphResponse(
        found=True,
        data_available=source.order_item_records > 0,
        source=source,
        product=selected,
        similar_products=similar,
        summary=(
            f"{selected.name} xếp hạng {selected.category_rank} trong {selected.category}. "
            f"Các lựa chọn bên dưới được ghép tự động trong cùng shop và cùng danh mục."
        ),
    )


async def explore(db: AsyncSession, req: ProductGraphRequest) -> ProductGraphResponse:
    """Resolve a synced product by exact id, SKU, or a case-insensitive name match."""
    products, source, _ = await _resolve_dataset(db, req.shop_connection_id, req.days)
    needle = req.query.strip().lower()
    row = next(
        (
            product for product in products.values()
            if product["id"].lower() == needle
            or (product["sku"] and product["sku"].lower() == needle)
            or needle in product["name"].lower()
        ),
        None,
    )
    if row is None:
        return ProductGraphResponse(
            found=False, data_available=bool(products), source=source, product=None,
            similar_products=[], summary="Không tìm thấy sản phẩm trong dữ liệu đã đồng bộ.",
        )
    return await detail(db, row["id"], source.shop_connection_id, req.days)
