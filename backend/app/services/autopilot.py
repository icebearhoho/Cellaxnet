"""Seller Autopilot: grounded detection, real Ollama explanation and approval."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.autopilot import AutopilotAuditEvent, AutopilotOpportunity
from app.services import commerce_store as store


def _candidates() -> list[dict]:
    products = store.all_products()
    low = sorted(
        (p for p in products if p["stock_status"] in {"low", "out"}),
        key=lambda p: p["stock"] / max(p["daily_sales"], 0.1),
    )[0]
    runway = round(low["stock"] / max(low["daily_sales"], 0.1), 1)
    lost = round(low["daily_sales"] * low["price_vnd"] * 14)

    if low["stock_status"] == "out":
        inventory_title = f"{low['name']} đã hết hàng"
        inventory_fallback = (
            "Tồn kho đã về 0. Ưu tiên bổ sung hàng hoặc tạm dừng khuyến mãi; "
            "không tăng giá một sản phẩm hiện không thể bán."
        )
        inventory_options = [
            {
                "id": "restock",
                "label": "Tạo nhiệm vụ nhập thêm hàng",
                "risk": "low",
                "impact": {
                    "revenue_protected_vnd": lost,
                    "runway_days": runway + 30,
                },
            },
            {
                "id": "pause-campaigns",
                "label": "Tạm dừng khuyến mãi và quảng cáo",
                "risk": "low",
                "impact": {
                    "wasted_spend_avoided_vnd": round(lost * 0.08),
                    "campaigns_to_review": 1,
                },
            },
        ]
    else:
        inventory_title = f"{low['name']} có nguy cơ hết hàng"
        inventory_fallback = (
            f"Tồn kho chỉ đủ khoảng {runway} ngày; nếu không xử lý, doanh thu "
            "14 ngày có thể bị ảnh hưởng."
        )
        inventory_options = [
            {
                "id": "restock",
                "label": "Tạo nhiệm vụ nhập thêm hàng",
                "risk": "low",
                "impact": {
                    "revenue_protected_vnd": lost,
                    "runway_days": runway + 30,
                },
            },
            {
                "id": "raise-price-5",
                "label": "Lập bản nháp tăng giá 5%",
                "risk": "medium",
                "impact": {
                    "revenue_protected_vnd": round(lost * 0.55),
                    "runway_days": round(runway * 1.18, 1),
                },
            },
            {
                "id": "slow-campaign",
                "label": "Lập nhiệm vụ giảm campaign 20%",
                "risk": "medium",
                "impact": {
                    "revenue_protected_vnd": round(lost * 0.4),
                    "runway_days": round(runway * 1.25, 1),
                },
            },
        ]

    negatives = sum(
        r["rating"] <= 3
        for p in products
        for r in p["reviews_list"]
        if r["days_ago"] <= 30
    )
    at_risk = [
        c for c in store.all_customers()
        if c["recency_days"] >= 60 or c["cart_abandon_rate"] >= 0.7
    ]
    risk_ltv = sum(c.get("lifetime_value_vnd", 0) for c in at_risk)
    return [
        {
            "fingerprint": f"inventory:v2:{low['id']}:{low['stock_status']}", "kind": "inventory",
            "severity": "critical" if runway <= 7 else "warning",
            "title": inventory_title,
            "evidence": {"product_id": low["id"], "product_name": low["name"],
                         "stock": low["stock"], "daily_sales": low["daily_sales"],
                         "runway_days": runway, "revenue_at_risk_vnd": lost},
            "fallback": inventory_fallback,
            "options": inventory_options,
        },
        {
            "fingerprint": "reviews:negative-30d:v2", "kind": "reviews", "severity": "warning",
            "title": f"{negatives} review thấp cần xử lý",
            "evidence": {"negative_reviews_30d": negatives, "products_reviewed": len(products)},
            "fallback": f"Có {negatives} đánh giá từ 3 sao trở xuống trong 30 ngày; nên xử lý chủ đề lặp lại trước khi ảnh hưởng chuyển đổi.",
            "options": [
                {"id": "review-triage", "label": "Tạo hàng đợi phân loại review", "risk": "low",
                 "impact": {"reviews_prioritized": negatives, "response_sla_hours": 24}},
                {"id": "listing-fix", "label": "Tạo checklist sửa listing", "risk": "low",
                 "impact": {"reviews_prioritized": negatives, "response_sla_hours": 48}},
            ],
        },
        {
            "fingerprint": "customers:winback:v2", "kind": "customer_risk", "severity": "info",
            "title": f"{len(at_risk)} khách nên được win-back",
            "evidence": {"customers_at_risk": len(at_risk), "ltv_at_risk_vnd": risk_ltv},
            "fallback": f"Nhóm {len(at_risk)} khách có recency cao hoặc bỏ giỏ nhiều đang mang {risk_ltv:,}₫ LTV lịch sử.",
            "options": [
                {"id": "voucher-draft", "label": "Lập voucher 8% chờ duyệt", "risk": "medium",
                 "impact": {"customers_targeted": len(at_risk), "expected_reactivation_pct": 12}},
                {"id": "winback-segment", "label": "Tạo phân khúc win-back", "risk": "low",
                 "impact": {"customers_targeted": len(at_risk), "expected_reactivation_pct": 8}},
            ],
        },
    ]


async def _ollama_explain(candidates: list[dict]) -> tuple[dict[str, str], bool, str]:
    model = settings.AUTOPILOT_OLLAMA_MODEL
    api_key = settings.OLLAMA_API_KEY
    if settings.APP_ENV == "test" or settings.DEMO_MODE or not api_key:
        return {}, False, model
    evidence = [
        {"fingerprint": c["fingerprint"], "title": c["title"], "evidence": c["evidence"],
         "options": [{"id": o["id"], "label": o["label"], "impact": o["impact"]} for o in c["options"]]}
        for c in candidates
    ]
    prompt = (
        "Bạn là cố vấn vận hành TMĐT cho seller Việt Nam. Chỉ dùng số trong evidence, "
        "không bịa dữ kiện. Với mỗi item, viết explanation thuyết phục nhưng tối đa 2 câu "
        "và 240 ký tự, nêu rủi ro rồi giải thích đúng phương án đầu tiên trong options "
        "(đó là hành động được đề xuất). Trả JSON đúng dạng "
        '{"items":[{"fingerprint":"...","explanation":"..."}]}.\nDATA=' +
        json.dumps(evidence, ensure_ascii=False)
    )
    try:
        async with httpx.AsyncClient(
            base_url=settings.AUTOPILOT_OLLAMA_URL.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(settings.AUTOPILOT_LLM_TIMEOUT_SECONDS, connect=3),
        ) as client:
            response = await client.post("/api/chat", json={
                "model": model,
                "messages": [{"role": "system", "content": "Output valid JSON only."},
                             {"role": "user", "content": prompt}],
                "format": "json", "stream": False, "think": False,
                # gpt-oss accounts for hidden reasoning inside num_predict even
                # with think disabled. A small cap can return HTTP 200 with an
                # empty/truncated content field, so leave enough room for all
                # three concise explanations.
                "options": {"temperature": 0.15, "num_predict": 2000},
            })
            response.raise_for_status()
            parsed = json.loads(response.json()["message"]["content"])
            items = parsed.get("items", [])
            result = {
                str(item["fingerprint"]): _concise(str(item["explanation"]))
                for item in items if item.get("fingerprint") and item.get("explanation")
            }
            return result, bool(result), model
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {}, False, model


def _concise(value: str, limit: int = 240) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    sentence_end = text.rfind(". ", 0, limit - 1)
    if sentence_end >= 80:
        return text[: sentence_end + 1]
    return text[: limit - 1].rstrip(" ,;:") + "…"


def serialize(row: AutopilotOpportunity) -> dict:
    return {
        "id": row.id, "workspace_id": row.workspace_id, "kind": row.kind,
        "severity": row.severity, "status": row.status, "title": row.title,
        "explanation": row.explanation, "evidence": row.evidence,
        "options": row.options, "model": row.model_name, "llm_used": row.llm_used,
        "provider": "ollama_cloud" if row.llm_used else "deterministic_fallback",
        "selected_option_id": row.selected_option_id,
        "created_at": row.created_at, "updated_at": row.updated_at,
        "applied_at": row.applied_at,
    }


async def refresh(db: AsyncSession, *, workspace_id: int, actor_user_id: int) -> list[dict]:
    candidates = _candidates()
    explanations, llm_used, model = await _ollama_explain(candidates)
    existing = await db.execute(select(AutopilotOpportunity).where(
        AutopilotOpportunity.workspace_id == workspace_id
    ))
    by_fingerprint = {row.fingerprint: row for row in existing.scalars()}
    output = []
    for candidate in candidates:
        row = by_fingerprint.get(candidate["fingerprint"])
        if row is None:
            row = AutopilotOpportunity(workspace_id=workspace_id, fingerprint=candidate["fingerprint"])
            db.add(row)
        if row.status not in {"applied", "rejected"}:
            row.kind = candidate["kind"]
            row.severity = candidate["severity"]
            row.status = "detected"
            row.title = candidate["title"]
            row.explanation = explanations.get(candidate["fingerprint"], candidate["fallback"])
            row.evidence = candidate["evidence"]
            row.options = candidate["options"]
            row.model_name = model
            row.llm_used = llm_used and candidate["fingerprint"] in explanations
        output.append(row)
    await db.commit()
    for row in output:
        await db.refresh(row)
    return [serialize(row) for row in output]


async def list_opportunities(db: AsyncSession, workspace_id: int) -> list[dict]:
    result = await db.execute(select(AutopilotOpportunity).where(
        AutopilotOpportunity.workspace_id == workspace_id
    ).order_by(AutopilotOpportunity.created_at.desc()))
    return [serialize(row) for row in result.scalars()]


async def _get(db: AsyncSession, opportunity_id: int, workspace_id: int) -> AutopilotOpportunity:
    result = await db.execute(select(AutopilotOpportunity).where(
        AutopilotOpportunity.id == opportunity_id,
        AutopilotOpportunity.workspace_id == workspace_id,
    ))
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Không tìm thấy opportunity.")
    return row


def _option(row: AutopilotOpportunity, option_id: str) -> dict:
    option = next((item for item in row.options if item["id"] == option_id), None)
    if option is None:
        raise ValidationError("Phương án không thuộc opportunity này.")
    return option


async def simulate(db: AsyncSession, *, opportunity_id: int, workspace_id: int,
                   actor_user_id: int, option_id: str) -> dict:
    row = await _get(db, opportunity_id, workspace_id)
    if row.status in {"applied", "rejected"}:
        raise ConflictError("Opportunity đã kết thúc, không thể mô phỏng lại.")
    option = _option(row, option_id)
    row.status = "simulated"
    row.selected_option_id = option_id
    event = AutopilotAuditEvent(opportunity_id=row.id, workspace_id=workspace_id,
        actor_user_id=actor_user_id, event_type="simulated",
        payload={"option_id": option_id, "impact": option["impact"], "assumption": "deterministic demo snapshot"})
    db.add(event)
    await db.commit()
    await db.refresh(row)
    return {"opportunity": serialize(row), "simulation": option["impact"],
            "risk": option["risk"], "disclaimer": "Ước tính kịch bản, chưa phải cam kết doanh thu."}


async def decide(db: AsyncSession, *, opportunity_id: int, workspace_id: int,
                 actor_user_id: int, option_id: str, decision: str, note: str | None) -> dict:
    row = await _get(db, opportunity_id, workspace_id)
    if row.status in {"applied", "rejected"}:
        raise ConflictError("Opportunity đã được quyết định.")
    option = _option(row, option_id)
    now = datetime.now(UTC)
    row.selected_option_id = option_id
    row.approved_by = actor_user_id if decision == "approve" else None
    row.status = "applied" if decision == "approve" else "rejected"
    row.applied_at = now if decision == "approve" else None
    payload = {"option_id": option_id, "option_label": option["label"], "note": note,
               "execution_mode": "workflow_draft", "impact": option["impact"]}
    db.add(AutopilotAuditEvent(opportunity_id=row.id, workspace_id=workspace_id,
        actor_user_id=actor_user_id, event_type=row.status, payload=payload))
    await db.commit()
    await db.refresh(row)
    return {"opportunity": serialize(row), "execution": payload}


async def audit_log(db: AsyncSession, workspace_id: int) -> list[dict]:
    result = await db.execute(select(AutopilotAuditEvent).where(
        AutopilotAuditEvent.workspace_id == workspace_id
    ).order_by(AutopilotAuditEvent.created_at.desc()).limit(100))
    return [{"id": e.id, "opportunity_id": e.opportunity_id, "actor_user_id": e.actor_user_id,
             "event_type": e.event_type, "payload": e.payload, "created_at": e.created_at}
            for e in result.scalars()]
