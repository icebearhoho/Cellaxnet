"""All v1 routers aggregated.

Authorisation lives here rather than on individual endpoints: seller-only
feature areas are gated wholesale with
``include_router(..., dependencies=[Depends(require_admin)])``, so adding a
new seller endpoint inherits the guard automatically.

Deliberately left public:
  * ``health``, ``auth`` — infrastructure / the way in.
  * ``personal_shopper``, ``recsys`` — these back the buyer pages
    ``/shop/personal-shopper`` and ``/shop/recsys``.

Two routers serve both audiences and are therefore gated per-route inside
their own modules (see ``endpoints/storefront.py`` and ``endpoints/journey.py``):
buyers read the catalogue and submit reviews while only admins reach the
moderation queue and the journey analytics.
"""

from fastapi import APIRouter, Depends

from app.api.deps import require_admin, require_seller_workspace_or_admin
from app.api.v1.endpoints import (
    auth,
    autopilot,
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
    voucher_booster,
    workspaces,
)

api_router = APIRouter()

# Reused on every seller-only router below.
_ADMIN_ONLY = [Depends(require_admin)]
_SELLER_OR_ADMIN = [Depends(require_seller_workspace_or_admin)]

# --- Public: infrastructure + the login flow itself ---
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(autopilot.router, prefix="/autopilot", tags=["seller-autopilot"])
api_router.include_router(voucher_booster.router, prefix="/voucher-booster", tags=["voucher-booster"])

# Marketplace connectors from Cellaxnet main are retained behind the admin
# boundary until their legacy tables are migrated to workspace ownership.
api_router.include_router(
    restock.router, prefix="/restock-planner", tags=["restock-planner"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    channel_link.router, prefix="/channel-link", tags=["channel-link"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    marketplace.router, prefix="/marketplace", tags=["marketplace"],
    dependencies=_ADMIN_ONLY,
)

# --- Public: buyer-facing GenAI features (/shop/personal-shopper, /shop/recsys) ---
api_router.include_router(
    personal_shopper.router,
    prefix="/personal-shopper",
    tags=["03-personal-shopper"],
)
api_router.include_router(recsys.router, prefix="/recsys", tags=["11-recsys"])

# --- Mixed audience: gated per-route inside the module, not here ---
api_router.include_router(storefront.router, prefix="/storefront", tags=["storefront"])
api_router.include_router(
    # Track 1, Đề 2 — not one of the original 17 ideas.
    journey.router, prefix="/journey", tags=["bonus-customer-journey"]
)

# --- Admin only: the whole seller portal ---
api_router.include_router(
    users.router, prefix="/users", tags=["users"], dependencies=_ADMIN_ONLY
)
api_router.include_router(
    ideas.router, prefix="/ideas", tags=["ideas"], dependencies=_ADMIN_ONLY
)
api_router.include_router(
    datasets.router, prefix="/datasets", tags=["datasets"], dependencies=_ADMIN_ONLY
)
api_router.include_router(
    kpis.router, prefix="/kpis", tags=["kpis"], dependencies=_SELLER_OR_ADMIN
)
api_router.include_router(
    content_generator.router,
    prefix="/content-generator",
    tags=["09-content-generator"],
    dependencies=_SELLER_OR_ADMIN,
)
api_router.include_router(
    # NOTE: "Customer Segmentation" is a bonus feature (from customer_segmentation/
    # offline modeling) and is NOT official idea #13 in the AREA303_17_Ideas brief
    # (#13 there is "Emotion-Aware Flash Sale Optimizer" — see frontend/lib/nav.ts
    # slug "emotion-sale"). Tagged without a number to avoid confusion.
    segmentation.router,
    prefix="/segmentation",
    tags=["bonus-customer-segmentation"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    seller_coach.router,
    prefix="/seller-coach",
    tags=["17-seller-coach"],
    dependencies=_SELLER_OR_ADMIN,
)
api_router.include_router(
    review_sentiment.router,
    prefix="/review-sentiment",
    tags=["01-review-sentiment"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    fake_review.router,
    prefix="/fake-review",
    tags=["05-fake-review"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    dynamic_pricing.router,
    prefix="/dynamic-pricing",
    tags=["02-dynamic-pricing"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    churn.router, prefix="/churn", tags=["04-churn"], dependencies=_ADMIN_ONLY
)
api_router.include_router(
    return_prediction.router,
    prefix="/return-prediction",
    tags=["10-return-prediction"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    regret.router,
    prefix="/regret",
    tags=["15-regret-predictor"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    # Combined view over churn/return/regret — same store.all_customers()
    # source, joined by id. See CONTEXT_HANDOVER discussion: gộp #04+#10+#15
    # into "Customer Risk Intelligence".
    risk_portfolio.router,
    prefix="/risk-portfolio",
    tags=["risk-portfolio"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    inventory_alert.router,
    prefix="/inventory-alert",
    tags=["08-inventory-alert"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    supply_chain.router,
    prefix="/supply-chain",
    tags=["16-supply-chain"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    flash_sale.router,
    prefix="/flash-sale",
    tags=["13-flash-sale"],
    dependencies=_ADMIN_ONLY,
)
# --- Track 2 (Đề bài) intelligence features ---
api_router.include_router(
    knowledge.router,
    prefix="/product-knowledge",
    tags=["de1-product-knowledge"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    market.router,
    prefix="/market-intelligence",
    tags=["de3-market-intelligence"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    creator.router,
    prefix="/creator-performance",
    tags=["de4-creator-performance"],
    dependencies=_ADMIN_ONLY,
)
api_router.include_router(
    decision.router,
    prefix="/decision-intelligence",
    tags=["de5-decision-intelligence"],
    dependencies=_ADMIN_ONLY,
)
# --- Seller Copilot: conversational agent that routes to the features above ---
api_router.include_router(
    copilot.router, prefix="/copilot", tags=["copilot-agent"], dependencies=_ADMIN_ONLY
)
