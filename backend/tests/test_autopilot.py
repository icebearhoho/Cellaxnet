"""Seller Autopilot grounding and Ollama Cloud contract tests."""

from __future__ import annotations

import json

import pytest

from app.core.config import settings
from app.services import autopilot


def test_candidates_are_grounded_in_shop_snapshot() -> None:
    candidates = autopilot._candidates()  # noqa: SLF001

    assert {item["kind"] for item in candidates} == {
        "inventory", "reviews", "customer_risk"
    }
    inventory = next(item for item in candidates if item["kind"] == "inventory")
    evidence = inventory["evidence"]
    assert evidence["runway_days"] == round(
        evidence["stock"] / evidence["daily_sales"], 1
    )
    assert all(option["impact"] for item in candidates for option in item["options"])


def test_out_of_stock_product_never_recommends_a_price_increase() -> None:
    inventory = next(
        item for item in autopilot._candidates() if item["kind"] == "inventory"  # noqa: SLF001
    )

    if inventory["evidence"]["stock"] == 0:
        option_ids = {option["id"] for option in inventory["options"]}
        assert "raise-price-5" not in option_ids
        assert option_ids == {"restock", "pause-campaigns"}


def test_concise_keeps_model_copy_within_ui_limit() -> None:
    long_copy = "Rủi ro tồn kho cần xử lý ngay. " + ("Hành động hợp lý. " * 30)
    result = autopilot._concise(long_copy)  # noqa: SLF001

    assert len(result) <= 240
    assert result.endswith(".") or result.endswith("…")


@pytest.mark.asyncio
async def test_ollama_cloud_request_uses_bearer_key_and_real_response(monkeypatch) -> None:
    captured: dict = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            content = json.dumps({"items": [{
                "fingerprint": "inventory:SKU-001",
                "explanation": "Chỉ còn 4 ngày tồn kho; nhập thêm hàng để bảo vệ doanh thu.",
            }]}, ensure_ascii=False)
            return {"message": {"content": content}}

    class _Client:
        def __init__(self, **kwargs) -> None:  # noqa: ANN003
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:  # noqa: ANN002
            return None

        async def post(self, path: str, *, json: dict):  # noqa: A002
            captured["path"] = path
            captured["body"] = json
            return _Response()

    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", "ollama-test-key")
    monkeypatch.setattr(settings, "AUTOPILOT_OLLAMA_URL", "https://ollama.com")
    monkeypatch.setattr(settings, "AUTOPILOT_OLLAMA_MODEL", "gpt-oss:120b")
    monkeypatch.setattr(autopilot.httpx, "AsyncClient", _Client)

    candidate = {
        "fingerprint": "inventory:SKU-001", "title": "Sắp hết hàng",
        "evidence": {"stock": 8, "runway_days": 4},
        "options": [{"id": "restock", "label": "Nhập hàng", "impact": {"days": 30}}],
    }
    explanations, used, model = await autopilot._ollama_explain([candidate])  # noqa: SLF001

    assert used is True
    assert model == "gpt-oss:120b"
    assert explanations["inventory:SKU-001"].startswith("Chỉ còn 4 ngày")
    assert captured["client"]["base_url"] == "https://ollama.com"
    assert captured["client"]["headers"] == {"Authorization": "Bearer ollama-test-key"}
    assert captured["path"] == "/api/chat"
    assert captured["body"]["stream"] is False
    assert captured["body"]["think"] is False
    assert captured["body"]["options"]["num_predict"] == 2000


@pytest.mark.asyncio
async def test_missing_key_uses_grounded_fallback_without_network(monkeypatch) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)

    explanations, used, model = await autopilot._ollama_explain([])  # noqa: SLF001

    assert explanations == {}
    assert used is False
    assert model == settings.AUTOPILOT_OLLAMA_MODEL
