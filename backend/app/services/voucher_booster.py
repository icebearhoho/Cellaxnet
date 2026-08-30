"""Voucher Booster business rules, persistence and honest execution states.

The service never labels a campaign as published unless a marketplace adapter
confirms it. Today it produces a validated, approval-ready campaign and an
explicit handoff state for the external connector or Seller Center.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.marketplace_shop import MarketplaceShop
from app.models.voucher import VoucherCampaign, VoucherCampaignEvent
from app.schemas.voucher import (
    CampaignCreateRequest,
    Objective,
    Platform,
    PromotionType,
)
from app.services import commerce_store as store

MIN_MARGIN_PCT = 12.0
MAX_DISCOUNT_PCT = 30.0
MAX_DURATION_DAYS = 31


def _product(product_id: str | None) -> dict:
    products = store.all_products()
    if product_id:
        product = next((item for item in products if item["id"] == product_id), None)
        if product is None:
            raise NotFoundError("Không tìm thấy sản phẩm trong dữ liệu vận hành.")
        return product
    available = [item for item in products if item["stock"] > 0]
    if not available:
        raise BusinessRuleError("Không có sản phẩm còn hàng để chạy ưu đãi.")
    return max(available, key=lambda item: item["daily_sales"] * item["price_vnd"])


def simulate_business_case(plan: CampaignCreateRequest, product: dict) -> tuple[dict, dict, dict]:
    """Return baseline, forecast and guardrails from deterministic commerce rules."""
    starts_at = plan.starts_at if plan.starts_at.tzinfo else plan.starts_at.replace(tzinfo=UTC)
    ends_at = plan.ends_at if plan.ends_at.tzinfo else plan.ends_at.replace(tzinfo=UTC)
    duration_days = max(1, ceil((ends_at - starts_at).total_seconds() / 86_400))
    price = int(product["price_vnd"])
    cost = int(product["cost_vnd"])
    stock = int(product["stock"])
    daily_sales = float(product["daily_sales"])

    if plan.discount_type == "percentage":
        discount_pct = float(plan.discount_value)
        discount_vnd = round(price * discount_pct / 100)
        if plan.max_discount_vnd:
            discount_vnd = min(discount_vnd, plan.max_discount_vnd)
            discount_pct = round(discount_vnd / price * 100, 2)
    else:
        discount_vnd = int(plan.discount_value)
        discount_pct = round(discount_vnd / price * 100, 2)

    effective_price = max(0, price - discount_vnd)
    unit_margin = effective_price - cost
    margin_pct = round(unit_margin / max(effective_price, 1) * 100, 2)
    baseline_units = min(stock, max(1, round(daily_sales * duration_days)))

    historical = product.get("promotion") or {}
    historical_lift = float(historical.get("lift_pct", 0))
    historical_discount = float(historical.get("discount_pct", 0))
    comparable_lift = historical_lift if abs(historical_discount - discount_pct) <= 5 else 0
    trend_factor = {"rising": 4.0, "stable": 0.0, "cooling": -3.0}.get(product["trend"], 0.0)
    lift_pct = round(max(4.0, min(55.0, max(comparable_lift, discount_pct * 2.8) + trend_factor)), 1)
    forecast_units = min(stock, plan.quantity, max(1, round(baseline_units * (1 + lift_pct / 100))))
    incremental_units = max(0, forecast_units - baseline_units)
    voucher_cost = forecast_units * discount_vnd
    expected_revenue = forecast_units * effective_price
    baseline_profit = baseline_units * (price - cost)
    expected_profit = forecast_units * unit_margin
    incremental_profit = expected_profit - baseline_profit

    checks = [
        {"code": "duration", "passed": 1 <= duration_days <= MAX_DURATION_DAYS,
         "message": f"Thời lượng {duration_days} ngày (tối đa {MAX_DURATION_DAYS})."},
        {"code": "discount_cap", "passed": discount_pct <= MAX_DISCOUNT_PCT,
         "message": f"Mức giảm hiệu dụng {discount_pct}% (trần {MAX_DISCOUNT_PCT}%)."},
        {"code": "margin_floor", "passed": margin_pct >= MIN_MARGIN_PCT,
         "message": f"Biên lợi nhuận sau ưu đãi {margin_pct}% (sàn {MIN_MARGIN_PCT}%)."},
        {"code": "budget", "passed": voucher_cost <= plan.budget_vnd,
         "message": f"Chi phí tối đa {voucher_cost:,}₫ / ngân sách {plan.budget_vnd:,}₫."},
        {"code": "inventory", "passed": plan.product_id is None or forecast_units <= stock,
         "message": f"Dự kiến {forecast_units} lượt dùng / {stock} sản phẩm còn hàng."},
        {"code": "profit", "passed": incremental_profit >= 0 or plan.objective == "clear_stock",
         "message": f"Lợi nhuận tăng thêm dự kiến {incremental_profit:,}₫."},
    ]
    violations = [item["message"] for item in checks if not item["passed"]]
    baseline = {
        "product_id": product["id"], "product_name": product["name"],
        "price_vnd": price, "cost_vnd": cost, "stock": stock,
        "daily_sales": daily_sales, "trend": product["trend"],
        "baseline_units": baseline_units, "baseline_profit_vnd": baseline_profit,
        "data_source": "commerce_snapshot",
    }
    simulation = {
        "duration_days": duration_days, "discount_pct": discount_pct,
        "discount_vnd": discount_vnd, "effective_price_vnd": effective_price,
        "post_discount_margin_pct": margin_pct, "expected_lift_pct": lift_pct,
        "expected_orders": forecast_units, "incremental_orders": incremental_units,
        "expected_revenue_vnd": expected_revenue, "voucher_cost_vnd": voucher_cost,
        "expected_profit_vnd": expected_profit, "incremental_profit_vnd": incremental_profit,
    }
    guardrails = {"passed": not violations, "checks": checks, "violations": violations}
    return baseline, simulation, guardrails


def recommendations(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(UTC)
    products = [p for p in store.all_products() if p["stock"] > 0]
    start = (now + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
    candidates: list[tuple[str, str, Platform, PromotionType, int, int, Objective]] = [
        ("balanced-shopee", "Shopee · tăng trưởng có lãi", "shopee", "seller_voucher", 6, 14, "grow_revenue"),
        ("balanced-tiktok", "TikTok · giảm giá sản phẩm", "tiktok_shop", "product_discount", 7, 21, "grow_revenue"),
        ("clear-stock-tiktok", "TikTok · flash deal xả tồn", "tiktok_shop", "flash_deal", 10, 31, "clear_stock"),
    ]
    output = []
    for rec_id, name, platform, promo_type, discount, days, objective in candidates:
        evaluated = []
        for product in products:
            qty = min(product["stock"], max(20, round(product["daily_sales"] * days * 1.35)))
            budget = round(product["price_vnd"] * discount / 100 * qty * 1.05)
            plan = CampaignCreateRequest(
                name=name, platform=platform, promotion_type=promo_type, objective=objective,
                product_id=product["id"], discount_type="percentage", discount_value=discount,
                max_discount_vnd=round(product["price_vnd"] * discount / 100),
                min_order_vnd=product["price_vnd"], quantity=qty,
                budget_vnd=max(budget, 100_000), starts_at=start,
                ends_at=start + timedelta(days=days),
            )
            baseline, simulation, guardrails = simulate_business_case(plan, product)
            evaluated.append((product, plan, baseline, simulation, guardrails))

        # Recommend the strongest *safe* profit case from the current snapshot.
        # This avoids surfacing a high-runway SKU merely because it is stagnant.
        product, plan, baseline, simulation, guardrails = max(
            evaluated,
            key=lambda item: (
                item[4]["passed"],
                item[3]["incremental_profit_vnd"],
                item[3]["incremental_orders"],
            ),
        )
        gross_margin_pct = round(
            (product["price_vnd"] - product["cost_vnd"]) / product["price_vnd"] * 100,
        )
        output.append({
            "id": rec_id, "why": (
                f"{product['name']} còn {product['stock']} sản phẩm, xu hướng {product['trend']} "
                f"và biên gộp {gross_margin_pct}%. Đây là phương án có lợi nhuận tăng thêm "
                "cao nhất trong các SKU đã qua toàn bộ rule."
            ),
            "plan": plan.model_dump(mode="json"), "baseline": baseline,
            "simulation": simulation, "guardrails": guardrails,
        })
    return output


async def _connected_shop(db: AsyncSession, workspace_id: int, platform: str) -> MarketplaceShop | None:
    result = await db.execute(select(MarketplaceShop).where(
        MarketplaceShop.workspace_id == workspace_id,
        MarketplaceShop.platform == platform,
        MarketplaceShop.status == "connected",
    ).order_by(MarketplaceShop.created_at.desc()))
    return result.scalars().first()


def _execution(platform: str, promotion_type: str, connected: bool) -> dict:
    seller_center_url = (
        "https://seller.shopee.vn/portal/marketing/vouchers"
        if platform == "shopee"
        else "https://seller-vn.tiktok.com/promotion-tools"
    )
    if not connected:
        return {"mode": "needs_connection", "can_publish": False,
                "message": "Cần kết nối shop và cấp quyền promotion trước khi phát hành.",
                "seller_center_url": seller_center_url}
    if platform == "tiktok_shop" and promotion_type == "seller_voucher":
        return {"mode": "seller_center_confirmation", "can_publish": False,
                "message": "TikTok OpenAPI chưa cho tạo seller voucher; cấu hình đã sẵn sàng để xác nhận trong Seller Center.",
                "seller_center_url": seller_center_url}
    return {"mode": "connector_ready", "can_publish": False,
            "message": "Campaign đã qua rule và sẵn sàng cho connector đã được nền tảng phê duyệt; chưa ghi nhận là published.",
            "seller_center_url": seller_center_url}


def serialize(row: VoucherCampaign) -> dict:
    return {
        "id": row.id, "workspace_id": row.workspace_id,
        "marketplace_shop_id": row.marketplace_shop_id, "name": row.name,
        "platform": row.platform, "promotion_type": row.promotion_type,
        "status": row.status, "objective": row.objective, "product_id": row.product_id,
        "discount_type": row.discount_type, "discount_value": row.discount_value,
        "max_discount_vnd": row.max_discount_vnd, "min_order_vnd": row.min_order_vnd,
        "quantity": row.quantity, "budget_vnd": row.budget_vnd,
        "starts_at": row.starts_at, "ends_at": row.ends_at,
        "baseline": row.baseline_snapshot, "simulation": row.simulation,
        "guardrails": row.guardrails, "execution": row.execution,
        "approved_at": row.approved_at, "created_at": row.created_at,
    }


async def create_campaign(db: AsyncSession, *, workspace_id: int, actor_user_id: int,
                          plan: CampaignCreateRequest, source_opportunity_id: int | None = None) -> dict:
    product = _product(plan.product_id)
    baseline, simulation, guardrails = simulate_business_case(plan, product)
    shop = await _connected_shop(db, workspace_id, plan.platform)
    execution = _execution(plan.platform, plan.promotion_type, shop is not None)
    row = VoucherCampaign(
        workspace_id=workspace_id, marketplace_shop_id=shop.id if shop else None,
        source_opportunity_id=source_opportunity_id, name=plan.name,
        platform=plan.platform, promotion_type=plan.promotion_type, status="simulated",
        objective=plan.objective, product_id=plan.product_id,
        discount_type=plan.discount_type, discount_value=plan.discount_value,
        max_discount_vnd=plan.max_discount_vnd, min_order_vnd=plan.min_order_vnd,
        quantity=plan.quantity, budget_vnd=plan.budget_vnd,
        starts_at=plan.starts_at, ends_at=plan.ends_at,
        baseline_snapshot=baseline, simulation=simulation,
        guardrails=guardrails, execution=execution,
    )
    db.add(row)
    await db.flush()
    db.add(VoucherCampaignEvent(
        campaign_id=row.id, workspace_id=workspace_id, actor_user_id=actor_user_id,
        event_type="simulated", payload={"simulation": simulation, "guardrails": guardrails},
    ))
    await db.commit()
    await db.refresh(row)
    return serialize(row)


async def create_from_recommendation(db: AsyncSession, *, workspace_id: int,
                                     actor_user_id: int, recommendation_id: str) -> dict:
    recommendation = next((r for r in recommendations() if r["id"] == recommendation_id), None)
    if recommendation is None:
        raise NotFoundError("Khuyến nghị đã hết hạn hoặc không tồn tại.")
    plan = CampaignCreateRequest.model_validate(recommendation["plan"])
    existing = await db.execute(select(VoucherCampaign).where(
        VoucherCampaign.workspace_id == workspace_id,
        VoucherCampaign.name == plan.name,
        VoucherCampaign.platform == plan.platform,
        VoucherCampaign.product_id == plan.product_id,
        VoucherCampaign.starts_at == plan.starts_at,
        VoucherCampaign.ends_at == plan.ends_at,
        VoucherCampaign.status.in_({
            "simulated", "ready_to_publish", "needs_connection",
            "needs_manual_action", "published",
        }),
    ).order_by(VoucherCampaign.created_at.desc()))
    current = existing.scalars().first()
    if current is not None:
        return serialize(current)
    return await create_campaign(db, workspace_id=workspace_id, actor_user_id=actor_user_id, plan=plan)


async def list_campaigns(db: AsyncSession, workspace_id: int) -> list[dict]:
    result = await db.execute(select(VoucherCampaign).where(
        VoucherCampaign.workspace_id == workspace_id
    ).order_by(VoucherCampaign.created_at.desc()).limit(50))
    return [serialize(row) for row in result.scalars()]


async def _get(db: AsyncSession, campaign_id: int, workspace_id: int) -> VoucherCampaign:
    result = await db.execute(select(VoucherCampaign).where(
        VoucherCampaign.id == campaign_id, VoucherCampaign.workspace_id == workspace_id
    ))
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Không tìm thấy campaign trong workspace.")
    return row


async def decide(db: AsyncSession, *, campaign_id: int, workspace_id: int,
                 actor_user_id: int, decision: str, note: str | None) -> dict:
    row = await _get(db, campaign_id, workspace_id)
    if row.status not in {"draft", "simulated"}:
        raise ConflictError("Campaign đã được quyết định.")
    if decision == "approve" and not row.guardrails.get("passed"):
        raise BusinessRuleError("Campaign vi phạm guardrail nên không thể duyệt.", details={
            "violations": row.guardrails.get("violations", [])
        })
    now = datetime.now(UTC)
    if decision == "reject":
        row.status = "rejected"
    else:
        mode = str(row.execution.get("mode") or "")
        row.status = {
            "needs_connection": "needs_connection",
            "seller_center_confirmation": "needs_manual_action",
        }.get(mode, "ready_to_publish")
        row.approved_by = actor_user_id
        row.approved_at = now
    db.add(VoucherCampaignEvent(
        campaign_id=row.id, workspace_id=workspace_id, actor_user_id=actor_user_id,
        event_type=row.status, payload={"note": note, "execution": row.execution},
    ))
    await db.commit()
    await db.refresh(row)
    return serialize(row)


async def stop(db: AsyncSession, *, campaign_id: int, workspace_id: int,
               actor_user_id: int) -> dict:
    row = await _get(db, campaign_id, workspace_id)
    if row.status in {"rejected", "stopped"}:
        raise ConflictError("Campaign đã kết thúc.")
    row.status = "stopped"
    row.stopped_at = datetime.now(UTC)
    db.add(VoucherCampaignEvent(
        campaign_id=row.id, workspace_id=workspace_id, actor_user_id=actor_user_id,
        event_type="stopped", payload={"previous_execution": row.execution},
    ))
    await db.commit()
    await db.refresh(row)
    return serialize(row)
