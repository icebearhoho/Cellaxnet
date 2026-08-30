"""Auto-analysis ("portfolio") services — run the existing scorers over the
store's customers / sessions so the seller gets a ready report instead of
filling forms. Churn / return / regret scan the customer base; journey analyses
pre-built shopping sessions (real data to test, not a manual simulation).
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

from app.schemas.insights import ChurnRequest, RegretRequest, ReturnRequest
from app.schemas.journey import JourneyEvent, JourneyRequest
from app.services import commerce_store as store
from app.services import insights
from app.services import journey as journey_svc


def churn_portfolio() -> dict:
    rows = []
    for c in store.all_customers():
        r = insights.score_churn(ChurnRequest(
            recency_days=c["recency_days"], frequency_orders=c["frequency_orders"],
            sessions_last_month=c["sessions_last_month"], cart_abandon_rate=c["cart_abandon_rate"],
            trend=cast(Any, c["trend"]),
        ))
        rows.append({"id": c["id"], "customer": c["name"], "recency_days": c["recency_days"],
                     **r.model_dump()})
    rows.sort(key=lambda x: x["churn_risk"], reverse=True)
    return {"customers": rows, "total": len(rows),
            "at_risk_count": sum(1 for r in rows if r["risk_band"] == "high")}


def return_portfolio() -> dict:
    rows = []
    for c in store.all_customers():
        r = insights.score_return(ReturnRequest(
            category=cast(Any, c["last_category"]), price_vnd=c["last_order_value_vnd"],
            is_new_customer=c["is_first_purchase"], size_related=c["has_size_variants"],
            discount_pct=20 if c["discount_driven"] else 0, reviews_read=c["reviews_read"],
        ))
        rows.append({"id": c["id"], "customer": c["name"], "product": c["last_product"],
                     "order_value_vnd": c["last_order_value_vnd"], **r.model_dump()})
    rows.sort(key=lambda x: x["return_risk"], reverse=True)
    return {"orders": rows, "total": len(rows),
            "high_risk_count": sum(1 for r in rows if r["risk_band"] == "high")}


def regret_portfolio() -> dict:
    rows = []
    for c in store.all_customers():
        r = insights.score_regret(RegretRequest(
            decision_time_seconds=c["decision_seconds"], revisit_count=c["revisits_before_buy"],
            purchase_hour=c["purchase_hour"], price_vnd=c["last_order_value_vnd"],
            used_discount=c["discount_driven"],
        ))
        rows.append({"id": c["id"], "customer": c["name"], "product": c["last_product"],
                     **r.model_dump()})
    rows.sort(key=lambda x: x["regret_risk"], reverse=True)
    return {"orders": rows, "total": len(rows),
            "high_risk_count": sum(1 for r in rows if r["risk_band"] == "high")}


def risk_portfolio() -> dict:
    """#04+#10+#15 combined — one row per customer with all three risk scores,
    joined on customer id (all three scan the same store.all_customers() list).
    """
    churn_by_id = {r["id"]: r for r in churn_portfolio()["customers"]}
    return_by_id = {r["id"]: r for r in return_portfolio()["orders"]}
    regret_by_id = {r["id"]: r for r in regret_portfolio()["orders"]}

    rows = []
    for c in store.all_customers():
        cid = c["id"]
        churn = churn_by_id.get(cid)
        ret = return_by_id.get(cid)
        regret = regret_by_id.get(cid)
        high_count = sum(
            1 for r in (churn, ret, regret) if r and r["risk_band"] == "high"
        )
        rows.append({
            "id": cid,
            "customer": c["name"],
            "last_order_no": c.get("last_order_no"),
            "last_product": c.get("last_product"),
            "lifetime_value_vnd": c.get("lifetime_value_vnd", 0),
            "preferred_channel": c.get("preferred_channel"),
            "churn_risk": churn["churn_risk"] if churn else None,
            "churn_band": churn["risk_band"] if churn else None,
            "return_risk": ret["return_risk"] if ret else None,
            "return_band": ret["risk_band"] if ret else None,
            "regret_risk": regret["regret_risk"] if regret else None,
            "regret_band": regret["risk_band"] if regret else None,
            "high_risk_count": high_count,
        })
    rows.sort(key=lambda x: x["high_risk_count"], reverse=True)
    return {
        "customers": rows,
        "total": len(rows),
        "critical_count": sum(1 for r in rows if r["high_risk_count"] >= 2),
    }


async def journey_sessions() -> dict:
    sessions = store.all_sessions()
    # Each analysis makes its own LLM narration call — run them concurrently
    # instead of sequentially, so N sample sessions cost ~1 round-trip, not N.
    results = await asyncio.gather(*(
        journey_svc.analyze_journey(
            JourneyRequest(events=[JourneyEvent(**e) for e in s["events"]]),
            use_llm_reasoning=False,
            now_ms=s.get("checked_at_ms"),
        )
        for s in sessions
    ))
    return {
        "sessions": [
            {"id": s["id"], "label": s["label"], "events": s["events"],
             "video_url": s.get("video_url"), "analysis": res.model_dump()}
            for s, res in zip(sessions, results, strict=True)
        ],
        "total": len(sessions),
    }
