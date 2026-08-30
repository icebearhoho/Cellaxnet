"""Cross-feature business invariants found during the product-flow audit."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ConflictError
from app.schemas.decision import DecisionRequest, PastDecision
from app.schemas.flash_sale import FlashSaleRequest
from app.schemas.genai import ContentGeneratorRequest
from app.schemas.insights import InventoryAlertRequest, RegretRequest
from app.schemas.journey import JourneyEvent, JourneyRequest
from app.schemas.market import MarketRequest
from app.schemas.orders import CheckoutRequest
from app.schemas.supply_chain import SupplyChainRequest
from app.services import (
    content_generator,
    decision,
    flash_sale,
    insights,
    inventory_service,
    journey,
    market,
    order_service,
    supply_chain,
)


def test_decision_history_normalizes_incomparable_metrics() -> None:
    request = DecisionRequest(
        situation="Kế hoạch mới",
        category="Thời trang",
        decisions=[
            PastDecision(
                kind="ad", description="Ads hiệu quả", metric="ROAS", value=5.0, month=11
            ),
            PastDecision(
                kind="promo",
                description="Khuyến mãi",
                metric="sales_lift_pct",
                value=30.0,
            ),
        ],
    )

    best, best_month = decision._best(request)  # noqa: SLF001

    assert best.description == "Ads hiệu quả"
    assert best_month == 11


def test_content_fallback_is_grounded_in_submitted_product() -> None:
    request = ContentGeneratorRequest(
        product_name="Serum B5",
        features="30 ml, không hương liệu",
        platforms=["Shopee", "Tiki", "TikTok Shop"],
    )

    variants = [
        content_generator._fallback_variant(request, platform)  # noqa: SLF001
        for platform in request.platforms
    ]

    assert all("Serum B5" in item.title for item in variants)
    assert all("không hương liệu" in item.body for item in variants)
    unsupported_claims = ("freeship", "TikiNOW", "đổi trả 7 ngày", "voucher")
    assert all(
        claim.casefold() not in item.body.casefold()
        for item in variants
        for claim in unsupported_claims
    )


def test_stockout_is_urgent_even_without_social_buzz() -> None:
    result = insights.score_inventory_alert(
        InventoryAlertRequest(
            product_name="SKU-1",
            social_mentions_7d=0,
            social_sentiment=0,
            current_stock=0,
            avg_daily_sales=10,
        )
    )

    assert result.is_trending is False
    assert result.alert_level == "urgent"
    assert "looks fine" not in result.reason


def test_hesitation_does_not_invent_scarcity() -> None:
    result = flash_sale.analyze_hesitation(
        FlashSaleRequest(
            dwell_time_seconds=150,
            scroll_depth_pct=100,
            revisit_count=2,
            cart_opened_no_purchase=False,
            price_vnd=500_000,
        )
    )

    assert result.hesitating is True
    assert result.trigger_now is False
    assert "số lượng giới hạn" not in result.message


@pytest.mark.asyncio
async def test_journey_nudge_does_not_invent_low_stock() -> None:
    result = await journey.analyze_journey(
        JourneyRequest(
            events=[
                JourneyEvent(type="review", category="Mỹ phẩm")
                for _ in range(5)
            ]
        ),
        use_llm_reasoning=False,
    )

    assert result.predicted_next_action == "add_to_cart"
    assert "chỉ còn ít hàng" not in result.nudge


def test_market_action_matches_margin_floor_price_change() -> None:
    result = market._heuristic(  # noqa: SLF001 - direct invariant test
        MarketRequest(
            our_product="A",
            category="Mỹ phẩm",
            our_price_vnd=100_000,
            our_cost_vnd=90_000,
            competitor_name="B",
            competitor_price_vnd=150_000,
            min_margin_pct=20,
        )
    )

    assert result["recommended_price_vnd"] > 100_000
    assert result["recommended_action"] == "protect_margin"
    assert result["margin_pct_at_recommended"] >= 20


def test_regret_message_does_not_promise_an_unconfigured_return_policy() -> None:
    result = insights.score_regret(
        RegretRequest(
            decision_time_seconds=1,
            revisit_count=0,
            purchase_hour=23,
            price_vnd=2_000_000,
            used_discount=True,
        )
    )

    assert result.risk_band == "high"
    assert "7 ngày" not in result.reassurance_message
    assert "chính sách" in result.reassurance_message


@pytest.mark.asyncio
async def test_supply_chain_labels_curated_events_as_scenarios(monkeypatch) -> None:  # noqa: ANN001
    async def no_news(_region: str) -> list[dict]:
        return []

    monkeypatch.setattr(supply_chain, "fetch_supply_news", no_news)
    result = await supply_chain.check_supply_chain(
        SupplyChainRequest(region="Miền Trung", category="Thời trang")
    )

    assert result.scenario_mode is True
    assert result.news_live is False
    assert "kịch bản" in result.summary
    assert "không phải xác nhận" in result.summary


def test_checkout_rejects_whitespace_only_customer_name() -> None:
    with pytest.raises(PydanticValidationError):
        CheckoutRequest(
            items=[{"product_id": "sku-1", "qty": 1}],
            customer_name="   ",
        )


class _ScalarResult:
    def __init__(self, value) -> None:  # noqa: ANN001
        self.value = value

    def scalar_one_or_none(self):  # noqa: ANN201
        return self.value


class _StatusDb:
    def __init__(self, order) -> None:  # noqa: ANN001
        self.order = order
        self.commits = 0

    async def execute(self, _statement):  # noqa: ANN001, ANN202
        return _ScalarResult(self.order)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _order) -> None:  # noqa: ANN001
        return None


@pytest.mark.asyncio
async def test_cancelling_unshipped_order_restores_stock(monkeypatch) -> None:  # noqa: ANN001
    order = SimpleNamespace(
        order_no="AR-1",
        status="paid",
        items=[SimpleNamespace(product_id="sku-1", qty=2)],
    )
    db = _StatusDb(order)
    restored: list[list[tuple[str, int]]] = []

    async def record_restore(_db, items):  # noqa: ANN001, ANN202
        restored.append(items)

    monkeypatch.setattr(inventory_service, "put_back", record_restore)
    result = await order_service.set_status(db, "AR-1", "cancelled")  # type: ignore[arg-type]

    assert result.status == "cancelled"
    assert restored == [[("sku-1", 2)]]
    assert db.commits == 1


@pytest.mark.asyncio
async def test_order_status_cannot_move_backwards() -> None:
    order = SimpleNamespace(order_no="AR-1", status="shipped", items=[])
    db = _StatusDb(order)

    with pytest.raises(ConflictError):
        await order_service.set_status(db, "AR-1", "pending")  # type: ignore[arg-type]

    assert order.status == "shipped"
    assert db.commits == 0
