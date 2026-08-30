"""Voucher Booster business-rule and honest execution-state tests."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import BusinessRuleError
from app.schemas.voucher import CampaignCreateRequest
from app.services import commerce_store, voucher_booster


def _plan(product: dict, *, discount: int = 5, budget_vnd: int = 10_000_000,
          platform: str = "shopee", promotion_type: str = "seller_voucher"):
    start = datetime.now(UTC) + timedelta(hours=2)
    return CampaignCreateRequest(
        name="Campaign có rule", platform=platform, promotion_type=promotion_type,
        objective="grow_revenue", product_id=product["id"],
        discount_type="percentage", discount_value=discount,
        max_discount_vnd=round(product["price_vnd"] * discount / 100),
        min_order_vnd=product["price_vnd"], quantity=min(product["stock"], 40),
        budget_vnd=budget_vnd, starts_at=start, ends_at=start + timedelta(days=3),
    )


def test_recommendations_are_grounded_and_not_arbitrary() -> None:
    rows = voucher_booster.recommendations(datetime(2026, 8, 28, tzinfo=UTC))

    assert {row["plan"]["platform"] for row in rows} == {"shopee", "tiktok_shop"}
    assert all(row["baseline"]["data_source"] == "commerce_snapshot" for row in rows)
    assert all(row["simulation"]["voucher_cost_vnd"] <= row["plan"]["budget_vnd"] for row in rows)
    assert all(row["guardrails"]["checks"] for row in rows)
    assert all(row["guardrails"]["passed"] for row in rows)
    assert all(row["simulation"]["incremental_profit_vnd"] > 0 for row in rows)


def test_margin_and_budget_guardrails_block_unsafe_discount() -> None:
    product = max(commerce_store.all_products(), key=lambda item: item["stock"])
    plan = _plan(product, discount=55, budget_vnd=100_000)

    _baseline, _simulation, guardrails = voucher_booster.simulate_business_case(plan, product)

    assert guardrails["passed"] is False
    failed = {item["code"] for item in guardrails["checks"] if not item["passed"]}
    assert "discount_cap" in failed
    assert "budget" in failed or "margin_floor" in failed


def test_tiktok_seller_voucher_is_explicit_manual_handoff() -> None:
    execution = voucher_booster._execution("tiktok_shop", "seller_voucher", True)  # noqa: SLF001

    assert execution["mode"] == "seller_center_confirmation"
    assert execution["can_publish"] is False
    assert "Seller Center" in execution["message"]


def test_campaign_end_must_be_after_start() -> None:
    product = max(commerce_store.all_products(), key=lambda item: item["stock"])
    plan = _plan(product)

    with pytest.raises(ValueError, match="kết thúc phải sau"):
        CampaignCreateRequest.model_validate({
            **plan.model_dump(),
            "ends_at": plan.starts_at,
        })


class _Db:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0

    def add(self, value) -> None:  # noqa: ANN001
        self.added.append(value)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _value) -> None:  # noqa: ANN001
        return None


@pytest.mark.asyncio
async def test_approval_refuses_campaign_that_failed_guardrails(monkeypatch) -> None:
    class _Campaign:
        id = 9
        status = "simulated"
        guardrails = {"passed": False, "violations": ["Biên lợi nhuận dưới sàn."]}

    async def fake_get(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return _Campaign()

    monkeypatch.setattr(voucher_booster, "_get", fake_get)

    with pytest.raises(BusinessRuleError, match="guardrail"):
        await voucher_booster.decide(
            _Db(),  # type: ignore[arg-type]
            campaign_id=9, workspace_id=3, actor_user_id=1,
            decision="approve", note=None,
        )
