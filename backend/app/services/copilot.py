"""Seller Copilot — conversational AI agent over a demo seller knowledge base.

Flow: an OpenAI *router* classifies the question into a skill + target product;
we pull that product's structured data from the KB and call the SAME service
functions the feature endpoints use (product-knowledge / market / creator /
decision); an OpenAI *synthesis* step writes the business answer, with a
deterministic templated fallback if the LLM is unavailable. The briefing engine
scans the whole KB and ranks today's actions by estimated VND impact.
"""

from __future__ import annotations

import json
from typing import Any, cast

from app.core.logging import get_logger
from app.schemas.copilot import (
    AgentStep,
    BriefingAction,
    BriefingResponse,
    CopilotAgentResponse,
    CopilotResponse,
)
from app.schemas.creator import ContentItem, CorrelationRequest, CreatorRequest
from app.schemas.decision import DecisionRequest, PastDecision, PlaybookRequest
from app.schemas.knowledge import ProductKnowledgeRequest
from app.schemas.market import MarketRequest, MarketScanRequest
from app.schemas.product_graph import ProductGraphRequest
from app.services import commerce_store as store
from app.services import creator as creator_svc
from app.services import decision as decision_svc
from app.services import knowledge as knowledge_svc
from app.services import market as market_svc
from app.services import product_graph as graph_svc
from app.services.llm_reasoning import get_llm_client, llm_ready, reason_json

log = get_logger("app.services.copilot")

# --------------------------------------------------------------------------- #
# Demo seller knowledge base — a small/medium fashion+cosmetics shop. Each
# product carries the fields the analytical services need, plus inventory
# signals for the briefing. (In production this would be the seller's DB.)
# --------------------------------------------------------------------------- #
PRODUCTS: list[dict] = [
    {
        "name": "Áo khoác dù unisex", "category": "Thời trang",
        "price_vnd": 320000, "cost_vnd": 180000, "sales_prev": 210, "sales_curr": 340,
        "stock": 45, "daily_sales": 22, "stock_status": "low", "trend": "rising",
        "price_change_pct": 0, "traffic_change_pct": 35, "promotion_active": False,
        "competitor_promo": False, "competitor_name": "Shop Outdoor",
        "competitor_price_vnd": 350000, "competitor_discount_pct": 0,
    },
    {
        "name": "Kem chống nắng SPF50 50ml", "category": "Mỹ phẩm",
        "price_vnd": 189000, "cost_vnd": 90000, "sales_prev": 300, "sales_curr": 280,
        "stock": 600, "daily_sales": 18, "stock_status": "ok", "trend": "cooling",
        "price_change_pct": 0, "traffic_change_pct": -8, "promotion_active": False,
        "competitor_promo": True, "competitor_name": "Beauty Zone",
        "competitor_price_vnd": 210000, "competitor_discount_pct": 30,
    },
    {
        "name": "Váy hoa nhí", "category": "Thời trang",
        "price_vnd": 250000, "cost_vnd": 120000, "sales_prev": 500, "sales_curr": 320,
        "stock": 220, "daily_sales": 12, "stock_status": "ok", "trend": "cooling",
        "price_change_pct": 12, "traffic_change_pct": -15, "promotion_active": False,
        "competitor_promo": True, "competitor_name": "Local Boutique",
        "competitor_price_vnd": 230000, "competitor_discount_pct": 0,
    },
    {
        "name": "Túi tote canvas", "category": "Phụ kiện",
        "price_vnd": 150000, "cost_vnd": 60000, "sales_prev": 180, "sales_curr": 260,
        "stock": 8, "daily_sales": 15, "stock_status": "out", "trend": "rising",
        "price_change_pct": 0, "traffic_change_pct": 40, "promotion_active": False,
        "competitor_promo": False, "competitor_name": "Bag House",
        "competitor_price_vnd": 165000, "competitor_discount_pct": 0,
    },
    {
        "name": "Serum Vitamin C", "category": "Mỹ phẩm",
        "price_vnd": 260000, "cost_vnd": 130000, "sales_prev": 260, "sales_curr": 250,
        "stock": 400, "daily_sales": 9, "stock_status": "ok", "trend": "cooling",
        "price_change_pct": 0, "traffic_change_pct": -5, "promotion_active": True,
        "competitor_promo": False, "competitor_name": "Glow Store",
        "competitor_price_vnd": 250000, "competitor_discount_pct": 10,
    },
]

CREATORS_BY_CATEGORY: dict[str, list[dict]] = {
    "Mỹ phẩm": [
        {"creator": "Hà Linh Official", "content_type": "livestream", "views": 120000, "engagements": 9800, "attributed_sales_vnd": 45000000},
        {"creator": "Chan Review", "content_type": "video", "views": 85000, "engagements": 6200, "attributed_sales_vnd": 22000000},
        {"creator": "Mai Beauty", "content_type": "post", "views": 30000, "engagements": 2100, "attributed_sales_vnd": 7000000},
    ],
    "Thời trang": [
        {"creator": "Trang Fashionista", "content_type": "video", "views": 150000, "engagements": 12000, "attributed_sales_vnd": 38000000},
        {"creator": "Style By An", "content_type": "livestream", "views": 60000, "engagements": 7000, "attributed_sales_vnd": 41000000},
    ],
}

# All ROAS so "best" is an apples-to-apples comparison (the decision service
# ranks by raw value, so mixing metrics here would be misleading).
DECISIONS: list[dict] = [
    {"kind": "promo", "description": "Sale 11/11 giảm 20%", "metric": "ROAS", "value": 4.2, "month": 11},
    {"kind": "ad", "description": "Đẩy ads TikTok tháng 12", "metric": "ROAS", "value": 5.1, "month": 12},
    {"kind": "price", "description": "Giảm giá 10% ngày thường", "metric": "ROAS", "value": 2.3, "month": None},
    {"kind": "promo", "description": "Freeship toàn shop", "metric": "ROAS", "value": 3.8, "month": 6},
]

# Replace the small legacy fixtures above with adapters over the same Mây House
# entities used by storefront, inventory, pricing, risk and dashboard. Keeping
# the public names avoids churn in the copilot routing code below.
PRODUCTS = []
for _product in store.all_products():
    _competitor = _product["competitors"][0]
    PRODUCTS.append({
        "name": _product["name"], "category": _product["category"],
        "price_vnd": _product["price_vnd"], "cost_vnd": _product["cost_vnd"],
        "sales_prev": _product["sales_prev"], "sales_curr": _product["sales_curr"],
        "stock": _product["stock"], "daily_sales": _product["daily_sales"],
        "stock_status": _product["stock_status"], "trend": _product["trend"],
        "price_change_pct": 0.0,
        "traffic_change_pct": {"rising": 28.0, "cooling": -22.0, "stable": 3.0}[_product["trend"]],
        "promotion_active": _product["promotion"] is not None,
        "competitor_promo": _competitor["discount_pct"] > 0,
        "competitor_name": _competitor["name"],
        "competitor_price_vnd": _competitor["price_vnd"],
        "competitor_discount_pct": _competitor["discount_pct"],
    })

CREATORS_BY_CATEGORY = {category: [] for category in store.categories()}
for _creator in store.all_creators():
    for _campaign in _creator["campaigns"]:
        CREATORS_BY_CATEGORY[_creator["category"]].append({
            "creator": _creator["creator"],
            "content_type": _campaign["content_type"],
            "views": _campaign["views"],
            "engagements": _campaign["engagements"],
            "attributed_sales_vnd": _campaign["attributed_sales_vnd"],
        })

DECISIONS = [
    {key: value for key, value in row.items() if key != "category"}
    for row in store.all_decisions()
]

_CATS = ("Thời trang", "Mỹ phẩm", "Phụ kiện")
_VN_CHARS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")


def _detect_lang(text: str) -> str:
    """vi if the text has Vietnamese diacritics, else en — used to force the
    copilot's answer language (weak models otherwise follow the data's language)."""
    return "vi" if any(c in _VN_CHARS for c in text.lower()) else "en"


def _find_product(name: str | None) -> dict:
    if name:
        low = name.lower()
        for p in PRODUCTS:
            if p["name"].lower() in low or low in p["name"].lower():
                return p
        # loose token overlap
        for p in PRODUCTS:
            if any(tok in p["name"].lower() for tok in low.split() if len(tok) > 2):
                return p
    return PRODUCTS[0]


def _cat(name: str | None, default: str = "Mỹ phẩm") -> str:
    p = _find_product(name)
    return p["category"] if name else default


# --------------------------------------------------------------------------- #
# Copilot: route → dispatch → synthesize
# --------------------------------------------------------------------------- #
_ROUTER_SYSTEM = (
    "You route a Vietnamese e-commerce seller's question to ONE skill and the "
    "product it is about. Skills:\n"
    "- sales_explain: why a product's sales went up/down\n"
    "- competitor: competitor pricing / how to respond to a rival\n"
    "- creator: which KOL/KOC or content to use\n"
    "- decision: what past strategy worked / what to do given a situation\n"
    "- briefing: overview / what should I do today / across all products\n"
    "Reply ONLY JSON: {\"skill\": \"...\", \"product\": \"<product name or null>\"}"
)


def _known_products_hint() -> str:
    return "Known products: " + "; ".join(p["name"] for p in PRODUCTS) + "."


async def ask(question: str) -> CopilotResponse:
    route = await reason_json(
        _ROUTER_SYSTEM, f"{_known_products_hint()}\nQuestion: {question}", label="copilot.route"
    )
    skill = (route or {}).get("skill") or _keyword_route(question)
    product_name = (route or {}).get("product")
    if isinstance(product_name, str) and product_name.lower() in ("null", "none", ""):
        product_name = None

    if skill not in {"sales_explain", "competitor", "creator", "decision", "briefing"}:
        skill = _keyword_route(question)

    if skill == "briefing":
        b = await briefing()
        return CopilotResponse(
            answer=b.summary, skill_used="briefing", entity=None,
            impact_vnd=b.total_impact_vnd, tool_result=b.model_dump(),
        )

    p = _find_product(product_name)
    entity = p["name"]
    impact: int | None = None
    tool_result: dict = {}
    tool_label = ""

    if skill == "sales_explain":
        pk = await knowledge_svc.explain_sales(ProductKnowledgeRequest(
            product=p["name"], category=cast(Any, p["category"]),
            sales_prev=p["sales_prev"], sales_curr=p["sales_curr"],
            price_change_pct=p["price_change_pct"], promotion_active=p["promotion_active"],
            competitor_promo=p["competitor_promo"], stock_status=cast(Any, p["stock_status"]),
            traffic_change_pct=p["traffic_change_pct"],
        ))
        tool_result = pk.model_dump()
        tool_label = "product-knowledge"
        if p["sales_curr"] < p["sales_prev"]:
            impact = (p["sales_prev"] - p["sales_curr"]) * p["price_vnd"]
    elif skill == "competitor":
        mk = await market_svc.analyze_market(MarketRequest(
            our_product=p["name"], category=cast(Any, p["category"]),
            our_price_vnd=p["price_vnd"], our_cost_vnd=p["cost_vnd"],
            competitor_name=p["competitor_name"], competitor_price_vnd=p["competitor_price_vnd"],
            competitor_discount_pct=p["competitor_discount_pct"],
        ))
        tool_result = mk.model_dump()
        tool_label = "market-intelligence"
    elif skill == "creator":
        cat = p["category"] if product_name else _cat(product_name)
        items = CREATORS_BY_CATEGORY.get(cat, CREATORS_BY_CATEGORY["Mỹ phẩm"])
        cr = await creator_svc.analyze_creators(CreatorRequest(
            campaign_category=cast(Any, cat),
            items=[ContentItem(**it) for it in items],
        ))
        tool_result = cr.model_dump()
        tool_label = "creator-performance"
        entity = cat
    elif skill == "decision":
        dc = await decision_svc.recommend_decision(DecisionRequest(
            situation=question, category=cast(Any, p["category"]),
            decisions=[PastDecision(**d) for d in DECISIONS],
        ))
        tool_result = dc.model_dump()
        tool_label = "decision-intelligence"
        entity = None

    answer = await _synthesize(question, tool_label, tool_result, impact)
    return CopilotResponse(
        answer=answer, skill_used=tool_label, entity=entity,
        impact_vnd=impact, tool_result=tool_result,
    )


def _keyword_route(q: str) -> str:
    low = q.lower()
    if any(k in low for k in ("đối thủ", "cạnh tranh", "giảm giá", "competitor")):
        return "competitor"
    if any(k in low for k in ("kol", "koc", "creator", "livestream", "nội dung", "content")):
        return "creator"
    if any(k in low for k in ("quyết định", "chiến dịch", "roas", "quảng cáo", "ads", "khi nào")):
        return "decision"
    if any(k in low for k in ("vì sao", "tại sao", "giảm", "tăng", "doanh số")):
        return "sales_explain"
    return "briefing"


_SYNTH_SYSTEM = (
    "You are a seller's AI business copilot for a Vietnamese e-commerce shop "
    "(fashion & cosmetics). Given the seller's question and a tool result (JSON), "
    "answer in ONE concise, actionable paragraph (2-4 sentences). Use "
    "the numbers from the tool result; if an estimated VND impact is provided, "
    "mention it. Do not invent data. Reply as JSON: {\"answer\": \"...\"}"
)


async def _synthesize(question: str, tool: str, result: dict, impact: int | None) -> str:
    import json as _json
    payload = f"Question: {question}\nTool ({tool}) result: {_json.dumps(result, ensure_ascii=False)}"
    if impact:
        payload += f"\nEstimated impact: {impact:,}₫."
    data = await reason_json(_SYNTH_SYSTEM, payload, max_tokens=350, label="copilot.synth")
    ans = (data or {}).get("answer") if data else None
    if ans and ans.strip():
        return ans.strip()
    # Deterministic fallback: surface the most useful field from the tool result.
    for key in ("explanation", "reasoning", "insight", "recommended_action", "summary"):
        if result.get(key):
            base = str(result[key])
            return base + (f" (Tác động ước tính ~{impact:,}₫.)" if impact else "")
    return "Đã phân tích xong — xem chi tiết ở kết quả công cụ."


# --------------------------------------------------------------------------- #
# Briefing: scan the KB, rank today's actions by estimated VND impact
# --------------------------------------------------------------------------- #
def _build_actions() -> list[BriefingAction]:
    actions: list[BriefingAction] = []
    for p in PRODUCTS:
        eff_comp = p["competitor_price_vnd"] * (1 - p["competitor_discount_pct"] / 100.0)
        # 1) Rising + low/out of stock -> restock (avoid a week of lost revenue)
        if p["trend"] == "rising" and p["stock_status"] in ("low", "out"):
            impact = int(p["daily_sales"] * p["price_vnd"] * 7)
            actions.append(BriefingAction(
                kind="restock", title=f"Nhập thêm {p['name']}", product=p["name"],
                priority="high" if p["stock_status"] == "out" else "medium", impact_vnd=impact,
                detail=(f"Xu hướng tăng, tồn kho {p['stock_status']} ({p['stock']} sp), bán ~"
                        f"{p['daily_sales']}/ngày. Nhập gấp để không mất ~{impact:,}₫ doanh thu/tuần."),
            ))
        # 2) Sales dropped sharply -> investigate
        if p["sales_prev"] > 0 and (p["sales_prev"] - p["sales_curr"]) / p["sales_prev"] >= 0.2:
            impact = int((p["sales_prev"] - p["sales_curr"]) * p["price_vnd"])
            actions.append(BriefingAction(
                kind="investigate", title=f"Điều tra doanh số {p['name']} giảm", product=p["name"],
                priority="high" if impact > 20_000_000 else "medium", impact_vnd=impact,
                detail=(f"Doanh số {p['sales_prev']}→{p['sales_curr']} "
                        f"(-{round((p['sales_prev']-p['sales_curr'])/p['sales_prev']*100)}%), "
                        f"mất ~{impact:,}₫. Dùng Product Knowledge để tìm nguyên nhân."),
            ))
        # 3) Competitor materially cheaper -> reprice
        if eff_comp < p["price_vnd"] * 0.9:
            impact = int(p["daily_sales"] * p["price_vnd"] * 7 * 0.3)  # ~30% share at risk
            actions.append(BriefingAction(
                kind="reprice", title=f"Cân nhắc hạ giá {p['name']}", product=p["name"],
                priority="medium", impact_vnd=impact,
                detail=(f"{p['competitor_name']} bán ~{int(eff_comp):,}₫ (rẻ hơn ~"
                        f"{round((1-eff_comp/p['price_vnd'])*100)}%). Rủi ro mất ~{impact:,}₫/tuần thị phần."),
            ))
        # 4) Cooling + heavy stock -> promote/reduce
        days_left = p["stock"] / p["daily_sales"] if p["daily_sales"] else 999
        if p["trend"] == "cooling" and days_left > 30:
            impact = int(p["stock"] * p["cost_vnd"] * 0.02)  # ~2%/mo holding cost proxy
            actions.append(BriefingAction(
                kind="promote", title=f"Xả/đẩy khuyến mãi {p['name']}", product=p["name"],
                priority="low", impact_vnd=impact,
                detail=(f"Xu hướng giảm nhưng còn {p['stock']} sp (~{int(days_left)} ngày bán). "
                        f"Đẩy KM để giải phóng vốn tồn (~{impact:,}₫ phí lưu kho/tháng)."),
            ))
    # Any very high-money action is high priority regardless of kind, so the
    # priority label never contradicts the money ordering.
    for a in actions:
        if a.impact_vnd >= 30_000_000:
            a.priority = "high"
    actions.sort(key=lambda a: a.impact_vnd, reverse=True)
    return actions


async def briefing(narrate: bool = True) -> BriefingResponse:
    actions = _build_actions()
    total = sum(a.impact_vnd for a in actions)
    top = actions[:3]
    top_txt = "; ".join(f"{a.title} (~{a.impact_vnd:,}₫)" for a in top)
    data = await reason_json(
        "You are a seller's AI copilot. Summarize today's top actions in ONE short "
        "sentence (motivating, concrete). Reply JSON: {\"summary\": \"...\"}",
        f"Top actions: {top_txt}. Total impact ~{total:,}₫ across {len(actions)} items.",
        label="copilot.briefing",
    ) if narrate else None
    summary = (data or {}).get("summary") if data else None
    if not (summary and summary.strip()):
        summary = (f"Hôm nay có {len(actions)} việc nên làm, tổng tác động ~{total:,}₫. "
                   f"Ưu tiên: {top[0].title}." if actions else "Không có cảnh báo nào — mọi thứ ổn định.")
    return BriefingResponse(summary=summary.strip(), total_impact_vnd=total, actions=actions)


# --------------------------------------------------------------------------- #
# Copilot AGENT — multi-step OpenAI function-calling over the store-grounded
# tools. The model may call several tools for one question, then synthesize.
# Falls back to the single-step ask() if the LLM/tool-calling isn't available.
# --------------------------------------------------------------------------- #
_TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "product_graph",
        "description": "Quan hệ 1 sản phẩm: SKU tương tự, brand, danh mục, khuyến mãi, và vì sao doanh số thay đổi.",
        "parameters": {"type": "object", "properties": {"product": {"type": "string", "description": "Tên hoặc SKU sản phẩm"}}, "required": ["product"]}}},
    {"type": "function", "function": {
        "name": "market_scan",
        "description": "Quét đa đối thủ cho 1 sản phẩm: vị thế giá trên thị trường + giá đề xuất giữ biên lợi nhuận.",
        "parameters": {"type": "object", "properties": {"product": {"type": "string"}}, "required": ["product"]}}},
    {"type": "function", "function": {
        "name": "creator_correlation",
        "description": "Xếp hạng KOL/KOC theo độ tương quan giữa nội dung và doanh số cho 1 danh mục.",
        "parameters": {"type": "object", "properties": {"category": {"type": "string", "enum": ["Thời trang", "Mỹ phẩm", "Phụ kiện"]}}, "required": ["category"]}}},
    {"type": "function", "function": {
        "name": "decision_playbook",
        "description": "Gợi ý chiến lược từ lịch sử quyết định (ROAS, thời điểm đẩy ads) cho 1 tình huống + danh mục.",
        "parameters": {"type": "object", "properties": {"situation": {"type": "string"}, "category": {"type": "string", "enum": ["Thời trang", "Mỹ phẩm", "Phụ kiện"]}}, "required": ["situation", "category"]}}},
    {"type": "function", "function": {
        "name": "daily_briefing",
        "description": "Danh sách việc cần làm hôm nay trên toàn shop, xếp theo tác động doanh thu.",
        "parameters": {"type": "object", "properties": {}}}},
]

_AGENT_SYSTEM = (
    "You are the AI Copilot for a Vietnamese e-commerce seller (fashion & cosmetics). "
    "Use the provided tools to fetch the shop's REAL data before answering.\n\n"
    "TOOL BUDGET: call the FEWEST tools needed. A question about ONE topic/product "
    "usually needs exactly ONE tool. Only call several tools when the question clearly "
    "spans multiple distinct topics (e.g. 'why did sales drop AND how should I price it', "
    "or 'which KOL AND when to run ads'). Never call a tool you don't need.\n\n"
    "After you have the data, give a CONCISE answer (≤120 words: a few short bullets or "
    "2-3 sentences) with the key numbers and impact. Do not invent numbers.\n\n"
    "CRITICAL LANGUAGE RULE: Answer in the SAME language as the user's question, NOT "
    "the language of the tool data. If the question is in English, answer in English "
    "(even though product names/data are Vietnamese). If the question is in Vietnamese, "
    "answer in Vietnamese."
)


async def _dispatch(name: str, args: dict) -> tuple[dict, str]:
    """Run a tool; return (compact_result_for_model, human_summary_for_ui)."""
    if name == "product_graph":
        rg = await graph_svc.explore(ProductGraphRequest(query=args.get("product", "")), narrate=False)
        if not rg.found or rg.product is None:
            return {"found": False}, f"Không tìm thấy sản phẩm '{args.get('product', '')}'"
        return (
            {"name": rg.product.name, "sku": rg.product.sku, "trend": rg.product.trend,
             "sales_change_pct": rg.sales.change_pct if rg.sales else None,
             "similar": [s.name for s in rg.similar_products[:4]]},
            f"Product graph: {rg.product.name} (SKU {rg.product.sku})",
        )
    if name == "market_scan":
        rm = await market_svc.scan_market(MarketScanRequest(query=args.get("product", "")), narrate=False)
        return (
            {"product": rm.product_name, "our_rank": rm.our_rank, "of_total": rm.of_total,
             "recommended_price_vnd": rm.recommended_price_vnd, "margin_pct": rm.margin_pct_at_recommended},
            f"Market scan: {rm.product_name} (rank {rm.our_rank}/{rm.of_total})",
        )
    if name == "creator_correlation":
        rc = await creator_svc.analyze_correlation(
            CorrelationRequest(category=cast(Any, args.get("category", "Mỹ phẩm"))), narrate=False)
        return (
            {"best_creator": rc.best_creator,
             "ranked": [{"creator": c.creator, "correlation": c.correlation} for c in rc.ranked[:3]]},
            f"Creator correlation: best {rc.best_creator}",
        )
    if name == "decision_playbook":
        rd = await decision_svc.playbook(PlaybookRequest(
            situation=args.get("situation", "n/a"), category=cast(Any, args.get("category", "Thời trang"))), narrate=False)
        return (
            {"best": rd.best.description, "metric": rd.best.metric, "value": rd.best.value,
             "best_ad_month": rd.best_ad_month},
            f"Decision playbook: {rd.best.description}",
        )
    if name == "daily_briefing":
        rb = await briefing(narrate=False)
        return (
            {"total_impact_vnd": rb.total_impact_vnd,
             "top": [{"title": a.title, "impact_vnd": a.impact_vnd} for a in rb.actions[:3]]},
            f"Briefing: {len(rb.actions)} việc, tổng {rb.total_impact_vnd:,}₫",
        )
    return {"error": "unknown tool"}, f"unknown tool {name}"


async def agent_ask(question: str, history: list[dict] | None = None) -> CopilotAgentResponse:
    client = get_llm_client()
    if not llm_ready() or not hasattr(client, "chat_tools"):
        # Fallback: single-step router (still a working answer).
        r = await ask(question)
        return CopilotAgentResponse(
            answer=r.answer, tools_used=[r.skill_used] if r.skill_used else [],
            steps=[AgentStep(tool=r.skill_used or "router", args={}, summary=r.skill_used or "")],
            multi_step=False,
        )

    # Force the answer language from a code-side detection (weak models drift to
    # the tool data's language otherwise).
    directive = ("\n\nYou MUST write the final answer in ENGLISH ONLY."
                 if _detect_lang(question) == "en"
                 else "\n\nBạn PHẢI viết câu trả lời cuối cùng HOÀN TOÀN bằng tiếng Việt.")
    messages: list[dict] = [{"role": "system", "content": _AGENT_SYSTEM + directive}]
    for h in history or []:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})

    steps: list[AgentStep] = []
    tools_used: list[str] = []
    answer = ""
    for _ in range(4):  # bounded agent loop
        msg = await client.chat_tools(messages, _TOOL_SPECS, max_tokens=420)
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            answer = (msg.get("content") or "").strip()
            break
        messages.append(msg)  # assistant turn carrying the tool_calls
        for tc in tool_calls:
            fn = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            # A weaker model may pass invalid args (e.g. a product name where a
            # category is expected). Never let that crash the request — return an
            # error to the model so it can correct itself on the next turn.
            try:
                result, summary = await _dispatch(fn, args)
            except Exception as exc:  # noqa: BLE001 — tool errors are recoverable
                result = {"error": f"invalid arguments for {fn}: {exc}"}
                summary = f"{fn}: lỗi tham số"
                log.warning("copilot.tool_error", tool=fn, args=args, error=str(exc))
            tools_used.append(fn)
            steps.append(AgentStep(tool=fn, args=args, summary=summary))
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": json.dumps(result, ensure_ascii=False)})

    if not answer:
        # Loop hit the cap without a final text — ask once more for a plain answer.
        try:
            final = await client.chat_tools(messages + [
                {"role": "user", "content": "Tổng hợp câu trả lời cuối cùng bằng đúng ngôn ngữ của câu hỏi."}],
                [], max_tokens=420)
            answer = (final.get("content") or "").strip()
        except Exception:  # noqa: BLE001
            answer = ""
    if not answer:
        answer = "Mình đã thu thập dữ liệu nhưng chưa tổng hợp được câu trả lời — thử lại nhé."
    return CopilotAgentResponse(
        answer=answer, tools_used=list(dict.fromkeys(tools_used)), steps=steps,
        multi_step=len(steps) > 1,
    )
