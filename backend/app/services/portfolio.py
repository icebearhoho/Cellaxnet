"""Auto-analysis ("portfolio") services — run the existing scorers over the
store's customers / sessions so the seller gets a ready report instead of
filling forms. Churn / return / regret scan the customer base; journey analyses
pre-built shopping sessions (real data to test, not a manual simulation).
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

from app.core.i18n import t
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


#: Regret scores cluster: on the demo customer base 72 of 120 land in the
#: "high" band and the distribution jumps from 0.20 straight to 0.65, so the
#: score separates almost nobody. It stays as supporting detail on a row the
#: other two scores already flagged, and never lifts a customer into the list
#: on its own — otherwise it alone would mark 60% of the base as urgent.
_LEAD_RISKS = ("churn", "return")


def _lead_risk(churn: dict | None, ret: dict | None, regret: dict | None) -> dict | None:
    """The risk that should drive this row, with its own reason and action.

    Ranked by what it costs the seller to ignore: losing the customer outright
    beats losing one order, and both beat a soft-satisfaction signal.
    """
    candidates = []
    if churn:
        candidates.append({
            "kind": "churn",
            "label": "Nguy cơ rời bỏ",
            "risk": churn["churn_risk"],
            "band": churn["risk_band"],
            "reason": (churn.get("drivers") or [None])[0],
            "action": churn.get("retention_action"),
        })
    if ret:
        candidates.append({
            "kind": "return",
            "label": "Nguy cơ hoàn trả",
            "risk": ret["return_risk"],
            "band": ret["risk_band"],
            "reason": (ret.get("drivers") or [None])[0],
            "action": ret.get("action"),
        })
    if regret:
        candidates.append({
            "kind": "regret",
            "label": "Nguy cơ hối hận",
            "risk": regret["regret_risk"],
            "band": regret["risk_band"],
            "reason": (regret.get("drivers") or [None])[0],
            "action": regret.get("reassurance_message"),
        })

    actionable = [c for c in candidates if c["kind"] in _LEAD_RISKS]
    if not actionable:
        return None
    return max(actionable, key=lambda c: c["risk"])


def risk_portfolio() -> dict:
    """#04+#10+#15 as a work queue: one row per customer, ordered by what is
    at stake, carrying the reason and the action rather than three raw scores.

    Three scores side by side read as if they add up. They do not — churn is
    about the customer's future, return is about one order, regret is about how
    a single purchase felt — so the row leads with whichever risk is most
    expensive to ignore and says what to do about it.
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
        lead = _lead_risk(churn, ret, regret)
        ltv = c.get("lifetime_value_vnd", 0)

        # What walking away actually costs. Churn puts the whole relationship
        # at stake; a return only puts that order at stake.
        if lead and lead["kind"] == "churn":
            at_stake = int(round(ltv * lead["risk"]))
        elif lead and lead["kind"] == "return":
            at_stake = int(round((ret or {}).get("order_value_vnd", 0) * lead["risk"]))
        else:
            at_stake = 0

        rows.append({
            "id": cid,
            "customer": c["name"],
            "last_order_no": c.get("last_order_no"),
            "last_product": c.get("last_product"),
            "lifetime_value_vnd": ltv,
            "preferred_channel": c.get("preferred_channel"),
            "lead_kind": lead["kind"] if lead else None,
            "lead_label": t(lead["label"]) if lead else None,
            "lead_risk": lead["risk"] if lead else None,
            "lead_band": lead["band"] if lead else None,
            "lead_reason": lead["reason"] if lead else None,
            "lead_action": t(lead["action"]) if lead else None,
            "value_at_stake_vnd": at_stake,
            "churn_risk": churn["churn_risk"] if churn else None,
            "churn_band": churn["risk_band"] if churn else None,
            "return_risk": ret["return_risk"] if ret else None,
            "return_band": ret["risk_band"] if ret else None,
            "regret_risk": regret["regret_risk"] if regret else None,
            "regret_band": regret["risk_band"] if regret else None,
        })

    # Money at stake, not score: a 0.62 risk on a 4.7M customer outranks a 0.66
    # on a 330k one, and that is the order a seller should work the list in.
    rows.sort(key=lambda r: r["value_at_stake_vnd"], reverse=True)
    return {
        "customers": rows,
        "groups": _action_groups(rows),
        "total": len(rows),
        "needs_action_count": sum(1 for r in rows if r["lead_band"] == "high"),
        "total_at_stake_vnd": sum(r["value_at_stake_vnd"] for r in rows),
    }


#: Groups defined by the work they imply, not by severity. Severity alone put
#: 48 customers in one "medium" bucket needing two different things — an email
#: for the 30 drifting away, a size guide for the 18 likely to send an order
#: back — so a single suggested action for that bucket would be wrong for one
#: of them. Keyed on (lead_kind, lead_band), which is what decides the action.
_ACTION_GROUPS: tuple[dict, ...] = (
    {
        "key": "high",
        "label": "Rủi ro cao",
        "tone": "danger",
        "action": "Gửi ưu đãi giữ chân (giảm giá hoặc miễn phí vận chuyển) ngay tuần này.",
        "match": lambda r: r["lead_band"] == "high",
    },
    {
        "key": "medium",
        "label": "Trung bình",
        "tone": "warning",
        "action": "Gửi email gợi ý sản phẩm theo lịch sử mua của từng khách.",
        "match": lambda r: r["lead_band"] == "medium",
    },
    {
        "key": "low",
        "label": "An toàn",
        "tone": "success",
        "action": "Chưa cần can thiệp — tiếp tục chăm sóc như hiện tại.",
        "match": lambda r: True,
    },
)


def _action_groups(rows: list[dict]) -> list[dict]:
    """Assign each customer to the first group that claims them.

    Order matters: the groups are tried top to bottom and "steady" matches
    anything, so it must stay last as the catch-all.
    """
    counts: dict[str, int] = {g["key"]: 0 for g in _ACTION_GROUPS}
    stakes: dict[str, int] = {g["key"]: 0 for g in _ACTION_GROUPS}

    for row in rows:
        for group in _ACTION_GROUPS:
            if group["match"](row):
                row["group_key"] = group["key"]
                counts[group["key"]] += 1
                stakes[group["key"]] += row["value_at_stake_vnd"]
                break

    return [
        {
            "key": g["key"],
            "label": t(g["label"]),
            "tone": g["tone"],
            "action": t(g["action"]),
            "count": counts[g["key"]],
            "value_at_stake_vnd": stakes[g["key"]],
        }
        for g in _ACTION_GROUPS
    ]


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
