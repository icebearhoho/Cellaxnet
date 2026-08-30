"""Track 2, Đề 5 — E-commerce Decision Intelligence service.

Heuristic core (deterministic): metrics use different units, so values are
normalized to a 0..1 impact score before decisions are compared. The best month
to push ads is the month of the best normalized `ad` decision (falls back to
None if no ad decisions carry a month). The narrative uses an LLM with a
templated fallback.
"""

from __future__ import annotations

from app.schemas.decision import (
    BestDecision,
    DecisionRequest,
    DecisionResponse,
    PastDecision,
    PlaybookRequest,
    PlaybookResponse,
    ScoredDecision,
)
from app.services import commerce_store as _store
from app.services.llm_reasoning import reason_json

_MONTHS_VI = {
    1: "Tháng 1", 2: "Tháng 2", 3: "Tháng 3", 4: "Tháng 4", 5: "Tháng 5", 6: "Tháng 6",
    7: "Tháng 7", 8: "Tháng 8", 9: "Tháng 9", 10: "Tháng 10", 11: "Tháng 11", 12: "Tháng 12",
}

# Fixed reference maxima so different metrics map to a comparable 0..1 score.
_METRIC_REF = {
    "ROAS": 6.0,
    "sales_lift_pct": 40.0,
    "margin_pct": 100.0,
    "sell_through_pct": 100.0,
}


def _impact_score(metric: str, value: float) -> float:
    ref = _METRIC_REF.get(metric, 100.0)
    return round(min(1.0, max(0.0, value / ref)), 3)


def _best(req: DecisionRequest) -> tuple[PastDecision, int | None]:
    best = max(req.decisions, key=lambda d: _impact_score(d.metric, d.value))
    ad_decisions = [d for d in req.decisions if d.kind == "ad" and d.month is not None]
    best_ad_month = (
        max(ad_decisions, key=lambda d: _impact_score(d.metric, d.value)).month
        if ad_decisions
        else None
    )
    return best, best_ad_month


_SYSTEM = (
    "You are an operations-strategy agent for a Vietnamese e-commerce seller. "
    "Given the current situation, a category, and the single best-performing past "
    "decision (with its metric), recommend ONE concrete next action in a short "
    "paragraph (2-3 sentences), grounded in that past result. "
    'Reply as JSON: {"recommended_action": "...", "reasoning": "..."}'
)


def _fallback(req: DecisionRequest, best: PastDecision, ad_month: int | None) -> tuple[str, str]:
    timing = f" Thời điểm đẩy quảng cáo tốt nhất: {_MONTHS_VI[ad_month]}." if ad_month else ""
    action = (
        f"Lặp lại chiến lược '{best.description}' ({best.kind}) — nó đạt "
        f"{best.metric} = {best.value:g}, tốt nhất trong lịch sử.{timing}"
    )
    reasoning = (
        f"Với tình huống hiện tại ({req.situation[:80]}), quyết định quá khứ hiệu quả "
        f"nhất theo {best.metric} là '{best.description}'. Ưu tiên tái áp dụng cách làm này "
        f"cho ngành {req.category}."
    )
    return action, reasoning


async def recommend_decision(req: DecisionRequest) -> DecisionResponse:
    best, ad_month = _best(req)
    hist = "; ".join(f"{d.kind}:'{d.description}' {d.metric}={d.value:g}" for d in req.decisions[:12])
    data = await reason_json(
        _SYSTEM,
        f"Situation: {req.situation}\nCategory: {req.category}\n"
        f"Best past decision: {best.kind} '{best.description}' ({best.metric}={best.value:g}).\n"
        f"Full history: {hist}."
        + (f"\nBest ad month observed: {ad_month}." if ad_month else ""),
        label="decision",
    )
    action = (data or {}).get("recommended_action") if data else None
    reasoning = (data or {}).get("reasoning") if data else None
    fb_action, fb_reason = _fallback(req, best, ad_month)
    return DecisionResponse(
        best_decision=BestDecision(
            kind=best.kind, description=best.description, metric=best.metric, value=best.value
        ),
        best_ad_month=ad_month,
        recommended_action=(action or "").strip() or fb_action,
        reasoning=(reasoning or "").strip() or fb_reason,
    )


# --------------------------------------------------------------------------- #
# Đề 5 — playbook: normalize metrics to a comparable impact score + seasonality
# --------------------------------------------------------------------------- #
async def playbook(req: PlaybookRequest, narrate: bool = True) -> PlaybookResponse:
    decisions = [d for d in _store.all_decisions() if d["category"] == req.category] or _store.all_decisions()
    scored = [
        ScoredDecision(
            kind=d["kind"], description=d["description"], metric=d["metric"], value=d["value"],
            impact_score=_impact_score(d["metric"], d["value"]), month=d["month"],
        )
        for d in decisions
    ]
    scored.sort(key=lambda s: s.impact_score, reverse=True)
    best = scored[0]

    # Seasonality: average ROAS of ad decisions by month (across the whole log).
    by_month: dict[str, list[float]] = {}
    for d in _store.all_decisions():
        if d["kind"] == "ad" and d["metric"] == "ROAS" and d["month"] is not None:
            by_month.setdefault(str(d["month"]), []).append(d["value"])
    seasonality = {m: round(sum(v) / len(v), 2) for m, v in by_month.items()}
    best_ad_month = int(max(seasonality, key=lambda m: seasonality[m])) if seasonality else None

    data = await reason_json(
        "You are an operations-strategy agent for a Vietnamese e-commerce shop. Given the "
        "current situation and the best past decision (by a normalized impact score across "
        "metrics) plus the best ad month, recommend ONE concrete next action in a short "
        'paragraph (2-3 sentences). Reply as JSON: {"recommended_action": "...", "reasoning": "..."}',
        f"Situation: {req.situation}. Category: {req.category}. Best: {best.description} "
        f"({best.metric}={best.value}, score {best.impact_score}). Best ad month: {best_ad_month}. "
        f"Seasonality (month→ROAS): {seasonality}.",
        label="decision_playbook",
    ) if narrate else None
    action = (data or {}).get("recommended_action") if data else None
    reasoning = (data or {}).get("reasoning") if data else None
    if not (action and action.strip()):
        action = f"Ưu tiên tái áp dụng '{best.description}' (impact {best.impact_score})."
    if not (reasoning and reasoning.strip()):
        reasoning = (f"Theo lịch sử ngành {req.category}, quyết định tốt nhất là '{best.description}' "
                     f"({best.metric}={best.value:g}). "
                     + (f"Thời điểm đẩy ads tốt nhất: tháng {best_ad_month}." if best_ad_month else ""))
    return PlaybookResponse(
        best=best, ranked=scored, best_ad_month=best_ad_month, seasonality=seasonality,
        recommended_action=action.strip(), reasoning=reasoning.strip(),
    )
