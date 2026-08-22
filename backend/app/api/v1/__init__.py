"""All v1 routers aggregated."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    channel_link,
    churn,
    content_generator,
    copilot,
    creator,
    datasets,
    decision,
    dynamic_pricing,
    fake_review,
    flash_sale,
    health,
    ideas,
    inventory_alert,
    journey,
    knowledge,
    kpis,
    market,
    marketplace,
    personal_shopper,
    recsys,
    regret,
    restock,
    return_prediction,
    review_sentiment,
    risk_portfolio,
    segmentation,
    seller_coach,
    storefront,
    supply_chain,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(ideas.router, prefix="/ideas", tags=["ideas"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(kpis.router, prefix="/kpis", tags=["kpis"])
api_router.include_router(
    personal_shopper.router,
    prefix="/personal-shopper",
    tags=["03-personal-shopper"],
)
api_router.include_router(
    content_generator.router,
    prefix="/content-generator",
    tags=["09-content-generator"],
)
api_router.include_router(recsys.router, prefix="/recsys", tags=["11-recsys"])
api_router.include_router(
    # NOTE: "Customer Segmentation" is a bonus feature (from customer_segmentation/
    # offline modeling) and is NOT official idea #13 in the AREA303_17_Ideas brief
    # (#13 there is "Emotion-Aware Flash Sale Optimizer" — see frontend/lib/nav.ts
    # slug "emotion-sale"). Tagged without a number to avoid confusion.
    segmentation.router, prefix="/segmentation", tags=["bonus-customer-segmentation"]
)
api_router.include_router(
    seller_coach.router, prefix="/seller-coach", tags=["17-seller-coach"]
)
api_router.include_router(
    review_sentiment.router, prefix="/review-sentiment", tags=["01-review-sentiment"]
)
api_router.include_router(
    fake_review.router, prefix="/fake-review", tags=["05-fake-review"]
)
api_router.include_router(
    dynamic_pricing.router, prefix="/dynamic-pricing", tags=["02-dynamic-pricing"]
)
api_router.include_router(churn.router, prefix="/churn", tags=["04-churn"])
api_router.include_router(
    # Track 1, Đề 2 — not one of the original 17 ideas.
    journey.router, prefix="/journey", tags=["bonus-customer-journey"]
)
api_router.include_router(
    return_prediction.router, prefix="/return-prediction", tags=["10-return-prediction"]
)
api_router.include_router(regret.router, prefix="/regret", tags=["15-regret-predictor"])
api_router.include_router(
    # Combined view over churn/return/regret — same store.all_customers()
    # source, joined by id. See CONTEXT_HANDOVER discussion: gộp #04+#10+#15
    # into "Customer Risk Intelligence".
    risk_portfolio.router, prefix="/risk-portfolio", tags=["risk-portfolio"]
)
api_router.include_router(
    inventory_alert.router, prefix="/inventory-alert", tags=["08-inventory-alert"]
)
api_router.include_router(
    supply_chain.router, prefix="/supply-chain", tags=["16-supply-chain"]
)
api_router.include_router(
    # Budget-constrained restock quantities. Distinct from #08 (single-SKU buzz
    # alert) and #19 (price positioning): this one allocates capital across the
    # whole catalog using seasonality + live big-brand sale pressure.
    restock.router, prefix="/restock-planner", tags=["restock-planner"]
)
api_router.include_router(
    # Aggregator link (KiotViet): one authorisation carrying several
    # marketplaces. Kept alongside the per-marketplace path below while that one
    # waits on developer-account approval from each platform.
    channel_link.router, prefix="/channel-link", tags=["channel-link"]
)
api_router.include_router(
    # Direct per-marketplace OAuth: seller accounts, shop connections, and the
    # sync of shop / product / order / inventory data.
    marketplace.router, prefix="/marketplace", tags=["marketplace"]
)
api_router.include_router(
    flash_sale.router, prefix="/flash-sale", tags=["13-flash-sale"]
)
# --- Track 2 (Đề bài) intelligence features ---
api_router.include_router(
    knowledge.router, prefix="/product-knowledge", tags=["de1-product-knowledge"]
)
api_router.include_router(
    market.router, prefix="/market-intelligence", tags=["de3-market-intelligence"]
)
api_router.include_router(
    creator.router, prefix="/creator-performance", tags=["de4-creator-performance"]
)
api_router.include_router(
    decision.router, prefix="/decision-intelligence", tags=["de5-decision-intelligence"]
)
# --- Seller Copilot: conversational agent that routes to the features above ---
api_router.include_router(copilot.router, prefix="/copilot", tags=["copilot-agent"])
# --- Buyer storefront catalog ---
api_router.include_router(storefront.router, prefix="/storefront", tags=["storefront"])
