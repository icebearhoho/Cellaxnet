"""Personal Shopper service — RAG + LLM with SSE-friendly streaming."""

from __future__ import annotations

import re
import unicodedata

from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.schemas.genai import ProductCard, ShopperProductsResponse
from app.services.genai import (
    INTENT_CLASSIFICATION_PROMPT,
    PERSONAL_SHOPPER_SYSTEM,
    llm_cache,
)
from app.services.genai.base import LlmMessage
from app.services.genai.demo_data import (
    DEMO_CATALOG,
    SHOPPER_DEMO_PRODUCT_IDS,
    SHOPPER_DEMO_REPLY,
    get_product_image_url,
)
from app.services.genai.factory import get_llm_client, get_rag

log = get_logger("app.services.shopper")

_PRODUCT_INDEX = {p["id"]: p for p in DEMO_CATALOG}

# --------------------------------------------------------------------- #
# Stopwords tiếng Việt - loại bỏ khi build keyword index
# --------------------------------------------------------------------- #
_STOPWORDS = {
    "cho", "và", "là", "có", "được", "với", "của", "trong", "một", "các",
    "từ", "để", "về", "ra", "hay", "nào", "thì", "như", "ở", "qua", "phù",
    "hợp", "dành", "theo", "mà", "size", "màu", "bộ", "gói", "hộp",
    "s", "m", "l", "xl", "xxl",
}

# --------------------------------------------------------------------- #
# Build keyword index từ catalog - map keyword -> product_ids
# --------------------------------------------------------------------- #


def _normalize_vietnamese(s: str) -> str:
    """Loại bỏ dấu tiếng Việt để so sánh."""
    return unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode('ascii')


def _extract_max_price(query: str) -> int | None:
    """Read common Vietnamese budget phrases such as 'dưới 400k' or 'tối đa 1 triệu'."""
    normalized = _normalize_vietnamese(query)
    match = re.search(
        r"(?:duoi|toi da|khong qua)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu|m)?",
        normalized,
    )
    if not match:
        return None
    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2)
    if unit in {"trieu", "m"}:
        amount *= 1_000_000
    elif unit in {"k", "nghin", "ngan"} or amount < 10_000:
        amount *= 1_000
    return int(amount)


def _build_keyword_index(catalog: list[dict]) -> dict[str, set[str]]:
    """Build index: keyword -> set of product ids that contain this keyword.
    
    Keywords are normalized (no diacritics) for matching.
    """
    import re
    index: dict[str, set[str]] = {}
    for item in catalog:
        # Extract words and normalize (remove diacritics)
        words = set(re.findall(r"[^\W\d_]+", item["title"].lower(), flags=re.UNICODE))
        for word in words:
            if len(word) >= 2 and word not in _STOPWORDS:
                # Store both original and normalized forms
                normalized = _normalize_vietnamese(word)
                if normalized not in index:
                    index[normalized] = set()
                index[normalized].add(item["id"])
                # Also store original if different
                if word != normalized and word not in index:
                    index[word] = set()
                    index[word].add(item["id"])
    return index

# Keyword index từ catalog - dùng global để cache
_KEYWORD_INDEX: dict[str, set[str]] | None = None

def _get_keyword_index() -> dict[str, set[str]]:
    global _KEYWORD_INDEX
    if _KEYWORD_INDEX is None:
        _KEYWORD_INDEX = _build_keyword_index(DEMO_CATALOG)
    return _KEYWORD_INDEX

def reset_keyword_index():
    """Reset keyword index cache - useful for testing."""
    global _KEYWORD_INDEX
    _KEYWORD_INDEX = None


def _build_context_block(docs: list) -> str:
    """Render retrieved docs as a compact context block."""
    lines = ["CONTEXT (từ catalog nội bộ):"]
    for i, d in enumerate(docs, start=1):
        meta = d.metadata or {}
        lines.append(
            f"{i}. [{d.id}] {d.title} — {meta.get('category', '?')} · "
            f"{meta.get('platform', '?')} · {meta.get('price_vnd', 0):,}₫\n   {d.text}"
        )
    return "\n".join(lines)


def _card(item: dict, score: float, image_url: str | None = None) -> ProductCard:
    meta = item.get("metadata", {})
    # Generate image URL based on product title, unless the caller already
    # has an exact one (e.g. a commerce_store product's type_key lookup).
    img_url = image_url or get_product_image_url(item["title"])
    return ProductCard(
        id=item["id"],
        name=item["title"],
        brand=meta.get("brand", "OEM"),
        category=meta.get("category", "Thời trang"),
        platform=meta.get("platform", "Shopee"),
        price_vnd=meta.get("price_vnd", 0),
        rating=round(4.0 + (hash(item["id"]) % 10) / 10, 1),
        reviews=120 + (hash(item["id"]) % 4000),
        similarity=score,
        image_hue=200 + (hash(item["id"]) % 160),
        image_url=img_url,
    )


_COSMETICS_HINTS = (
    "skincare", "da dầu", "da khô", "mụn", "dưỡng", "serum", "kem", "son", "môi",
    "trang điểm", "makeup", "mặt nạ", "toner", "chống nắng", "spf", "mỹ phẩm",
    "beauty", "cushion", "phấn", "cấp ẩm", "rửa mặt", "sạch da", "bha", "aha",
)
_FASHION_HINTS = (
    "áo", "váy", "đầm", "quần", "jean", "giày", "sneaker", "dép", "sandal", "túi",
    "balo", "ví", "phụ kiện", "thời trang", "đồng hồ", "kính", "mũ", "nón",
    "hoodie", "khoác", "outfit", "mặc",
)

# --------------------------------------------------------------------- #
# Strict keyword sets for fast-path intent classification (no LLM needed)
# These are CLEAR signals - if ANY of these keywords appear, intent is certain
# --------------------------------------------------------------------- #
_COSMETICS_STRICT = frozenset({
    "son", "kem", "mỹ phẩm", "makeup", "skincare", "serum", "toner",
    "cushion", "phấn", "mascara", "eyeliner", "mặt nạ", "dưỡng",
    "chống nắng", "spf", "sữa rửa mặt", "retinol", "bha", "aha",
    "niacinamide", "vitamin", "vc", "môi", "nước hoa", "dưỡng ẩm",
    "laneige", "cerave", "anessa", "paula's choice", "neutrogena", "3ce",
    "bourjois", "nudestix", "trang điểm",
})

_FASHION_STRICT = frozenset({
    "áo", "quần", "váy", "đầm", "giày", "túi", "túi xách", "balo",
    "ví", "kính", "mũ", "nón", "đồng hồ", "dép", "sandal",
    "hoodie", "khoác", "jean", "sneaker", "tote", "outfit",
    "jumpsuit", "len", "sơ mi", "vest", "blazer", "cardigan",
    "phụ kiện", "thời trang", "style", "form", "size", "màu",
    "casio", "denim", "canvas",
})


def _classify_intent_fast(query: str) -> str | None:
    """Fast-path keyword-based intent classification.
    
    Returns:
        - "cosmetic": only cosmetics should be returned
        - "fashion": only fashion + accessories should be returned
        - None: ambiguous, need LLM classification or return both
    """
    q_lower = query.lower()
    q_words = set(q_lower.split())

    # Exact keyword match is strongest signal
    if q_words & _COSMETICS_STRICT and not (q_words & _FASHION_STRICT):
        return "cosmetic"
    if q_words & _FASHION_STRICT and not (q_words & _COSMETICS_STRICT):
        return "fashion"
    
    # Partial match (contains)
    cos_partial = any(h in q_lower for h in _COSMETICS_STRICT)
    fas_partial = any(h in q_lower for h in _FASHION_STRICT)
    
    if cos_partial and not fas_partial:
        return "cosmetic"
    if fas_partial and not cos_partial:
        return "fashion"
    
    # Both or neither - need LLM or return both
    return None


async def _classify_intent_llm(query: str) -> str:
    """Classify intent using LLM (with keyword-based fallback).
    
    Returns:
        - "cosmetic": user wants cosmetics only
        - "fashion": user wants fashion + accessories only
        - "both": neutral query, return products from both categories
    """
    # Fast path: try keyword-based first
    fast_result = _classify_intent_fast(query)
    if fast_result:
        log.debug(f"Intent fast-classified as: {fast_result}")
        return fast_result
    
    # Need LLM for ambiguous queries
    llm = get_llm_client()
    prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
    
    messages = [
        LlmMessage(role="system", content="Bạn là intent classifier. Trả lời CHỈ một từ: cosmetic | fashion | both"),
        LlmMessage(role="user", content=prompt),
    ]
    
    try:
        response = await llm.chat(messages, temperature=0.1, max_tokens=20)
        result = response.content.strip().lower()
        
        # Validate response
        if result in ("cosmetic", "fashion", "both"):
            log.debug(f"Intent LLM-classified as: {result}")
            return result
        
        # Fallback if LLM returns unexpected format
        log.warning(f"Unexpected LLM intent response: {result}, falling back to 'both'")
        return "both"
    except Exception as e:
        log.error(f"LLM intent classification failed: {e}, falling back to 'both'")
        return "both"


def _get_categories_for_intent(intent: str) -> tuple[list[str], list[str]]:
    """Get category filters based on intent.
    
    Returns:
        tuple of (primary_categories, fallback_categories)
    """
    if intent == "cosmetic":
        return (["Mỹ phẩm"], ["Mỹ phẩm"])  # Only cosmetics
    elif intent == "fashion":
        return (["Thời trang", "Phụ kiện"], ["Thời trang", "Phụ kiện"])  # Fashion + accessories
    else:  # "both"
        return (["Thời trang", "Mỹ phẩm", "Phụ kiện"], ["Thời trang", "Mỹ phẩm", "Phụ kiện"])


def _tokens(s: str) -> set[str]:
    import re
    return set(re.findall(r"[^\W\d_]+", s.lower(), flags=re.UNICODE))


def _find_matching_products(qtokens: set[str], catalog: list[dict]) -> tuple[list[dict], list[str]]:
    """Tìm sản phẩm match với query keywords từ catalog index.

    Returns:
        tuple of (matching_products, matched_keywords)
    """
    index = _get_keyword_index()

    # Tìm keyword từ query (cả original và normalized) có trong catalog
    matched_keywords = []
    for word in qtokens:
        # Check original form
        if word in index and len(word) >= 2:
            matched_keywords.append(word)
        # Check normalized form
        normalized = _normalize_vietnamese(word)
        if normalized != word and normalized in index and len(normalized) >= 2:
            matched_keywords.append(normalized)

    if not matched_keywords:
        return [], []

    # Tìm tất cả product_ids match với keywords
    matching_ids: set[str] = set()
    for kw in matched_keywords:
        matching_ids.update(index[kw])

    matching_products = [it for it in catalog if it["id"] in matching_ids]
    return matching_products, matched_keywords


def _relevance_v2(item: dict, matched_keywords: list[str]) -> int:
    """Relevance scoring dựa trên keyword match trong catalog.

    - +10 điểm cho mỗi keyword match trong title/text
    - +5 điểm bonus nếu keyword nằm ở đầu title (quan trọng hơn)
    """
    title_lower = item["title"].lower()
    text_lower = (title_lower + " " + item.get("text", "")).lower()
    score = 0

    for kw in matched_keywords:
        normalized_kw = _normalize_vietnamese(kw)
        # Check both original and normalized forms
        if kw in text_lower or normalized_kw in text_lower:
            score += 10
            # Bonus nếu keyword nằm ở đầu title
            if title_lower.startswith(kw) or title_lower.startswith(normalized_kw):
                score += 5

    return score


def _relevance(item: dict, qtokens: set[str], q: str, cos: bool, fas: bool) -> int:
    meta = item.get("metadata", {})
    cat = meta.get("category", "")
    text = f"{item['title']} {item.get('text', '')} {cat}".lower()
    score = len(qtokens & _tokens(text))          # keyword overlap
    score += sum(1 for h in _COSMETICS_HINTS if h in q and h in text)
    score += sum(1 for h in _FASHION_HINTS if h in q and h in text)
    if cos and cat == "Mỹ phẩm":
        score += 3                                  # reduced: was +6
    if fas and cat in ("Thời trang", "Phụ kiện"):
        score += 3                                  # reduced: was +6
    return score


@llm_cache(prefix="shopper_intent")
async def _classify_intent_cached(query: str) -> str:
    """Cached intent classification to avoid repeated LLM calls."""
    return await _classify_intent_llm(query)


@llm_cache(prefix="shopper_products")
async def _retrieve_products(query: str, top_k: int) -> ShopperProductsResponse:
    """Rank the catalog by relevance to the query and return the top_k.

    Hybrid approach (Hướng C):
    1. Classify intent (fast-path keywords OR LLM)
    2. Retrieve products using RAG/semantic search
    3. Filter by intent category
    4. Fallback to keyword matching if no semantic results
    """
    q = query.lower()
    qtokens = _tokens(query)
    cos = any(h in q for h in _COSMETICS_HINTS)
    fas = any(h in q for h in _FASHION_HINTS)

    # Step 1: Intent classification (hybrid - fast path + LLM fallback)
    intent = await _classify_intent_cached(query)
    allowed_categories, _ = _get_categories_for_intent(intent)

    log.debug(f"Query: '{query}' -> Intent: {intent}, Categories: {allowed_categories}")

    # Step 2: Catalog-driven matching (keyword index)
    matching, matched_kws = _find_matching_products(qtokens, DEMO_CATALOG)

    if matched_kws:
        # Sort matching products by relevance
        scored = sorted(matching, key=lambda it: _relevance_v2(it, matched_kws), reverse=True)

        # Fill remaining slots only with products sharing the same keywords
        if len(scored) < top_k:
            keyword_index = _get_keyword_index()
            extra_ids = set()
            for kw in matched_kws:
                extra_ids.update(keyword_index.get(kw, set()))

            extra = [it for it in DEMO_CATALOG if it["id"] in extra_ids and it["id"] not in {it2["id"] for it2 in scored}]
            extra_sorted = sorted(extra, key=lambda it: _relevance_v2(it, matched_kws), reverse=True)

            scored.extend(extra_sorted[:top_k - len(scored)])

        picks = scored[:top_k]
        has_matched_kws = True
    else:
        # No keyword match -> use RAG semantic search
        rag = get_rag()
        rag_docs = await rag.retrieve(query, top_k=top_k * 2)  # Get more to filter
        
        # Map RAG docs back to catalog items
        rag_ids = [d.id for d in rag_docs]
        scored = [it for it in DEMO_CATALOG if it["id"] in rag_ids]
        
        # Sort by RAG score
        rag_scores = {d.id: d.score for d in rag_docs}
        scored.sort(key=lambda it: rag_scores.get(it["id"], 0), reverse=True)
        
        # Fallback to category-based scoring if RAG returned nothing useful
        if not scored:
            scored = sorted(
                DEMO_CATALOG,
                key=lambda it: _relevance(it, qtokens, q, cos, fas),
                reverse=True,
            )
        
        picks = scored[:top_k]
        has_matched_kws = False

    # Step 3: Filter by intent category
    picks = [it for it in picks if it["metadata"].get("category") in allowed_categories]

    # Respect an explicit ceiling instead of recommending an attractive item
    # that the shopper already said is outside their budget.
    max_price = _extract_max_price(query)
    if max_price is not None:
        affordable = [
            it for it in picks
            if int(it["metadata"].get("price_vnd", 0)) <= max_price
        ]
        seen = {it["id"] for it in affordable}
        refill = [
            it for it in DEMO_CATALOG
            if it["id"] not in seen
            and it["metadata"].get("category") in allowed_categories
            and int(it["metadata"].get("price_vnd", 0)) <= max_price
        ]
        refill.sort(key=lambda it: _relevance(it, qtokens, q, cos, fas), reverse=True)
        picks = (affordable + refill)[:top_k]
    
    # If filtering removed all products, fall back to original picks
    if not picks and max_price is None:
        # Re-run without category filter but limit top_k
        if matched_kws:
            scored_full = sorted(matching, key=lambda it: _relevance_v2(it, matched_kws), reverse=True)
        else:
            scored_full = sorted(DEMO_CATALOG, key=lambda it: _relevance(it, qtokens, q, cos, fas), reverse=True)
        picks = scored_full[:top_k]
        log.warning(f"Intent filter removed all products for query: '{query}', returning top matches")

    # Calculate max relevance for normalization
    if has_matched_kws:
        max_rel = max(_relevance_v2(it, matched_kws) for it in picks) if picks else 1
    else:
        max_rel = None

    def _calc_score(it: dict) -> float:
        if has_matched_kws:
            rel = _relevance_v2(it, matched_kws)
            # Normalize về 0.55-0.98 dựa trên max của batch
            # P004 (rel=30) / P009 (rel=10) với max_rel=30 sẽ cho: 0.98 vs 0.69
            if max_rel and max_rel > 0:
                return 0.55 + (rel / max_rel) * 0.43
            return max(0.55, min(0.98, 0.6 + rel * 0.05))
        else:
            return 0.75  # Default cho RAG fallback

    products = [_card(it, _calc_score(it)) for it in picks]
    return ShopperProductsResponse(
        products=products,
        sources=[{"id": it["id"], "title": it["title"], "score": 1.0} for it in picks],
    )


async def stream_reply(query: str, top_k: int = 4):
    """Yield ChatChunk objects for the SSE endpoint."""
    if not query.strip():
        raise ValidationError("query must not be empty")

    # Warm the product cache so /products endpoint is hot by the
    # time the user reads the streamed reply.
    await _retrieve_products(query, top_k)
    rag = get_rag()
    docs = await rag.retrieve(query, top_k=top_k)

    llm = get_llm_client()
    messages = [
        LlmMessage(role="system", content=PERSONAL_SHOPPER_SYSTEM),
        LlmMessage(role="user", content=f"{_build_context_block(docs)}\n\nUser: {query}"),
    ]

    async for chunk in llm.stream(messages, temperature=0.6):
        yield chunk


async def products_for(query: str, top_k: int = 4) -> ShopperProductsResponse:
    return await _retrieve_products(query, top_k)


def demo_reply() -> tuple[str, list[str]]:
    """Pure fallback for the absolute worst case (LLM disabled, cache empty)."""
    return SHOPPER_DEMO_REPLY, SHOPPER_DEMO_PRODUCT_IDS
