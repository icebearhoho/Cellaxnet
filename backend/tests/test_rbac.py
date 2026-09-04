"""Role gating: tenant-safe seller tools and admin analytics stay separated.

The public-path half of this file is the regression net for "adding auth
didn't break shopping" — those four endpoints back the storefront, the two
buyer GenAI pages and the behaviour-ingest call, and they must answer with no
token at all.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app

# One representative route per gating mechanism:
#   - /kpis/summary                      → workspace-aware router dependency
#   - /dynamic-pricing/                  → admin-only router dependency
#   - /storefront/reviews/queue          → per-route dependency on a mixed router
#   - /journey/sessions                  → per-route dependency on a mixed router
ADMIN_ONLY_GETS = [
    "/api/v1/kpis/summary",
    "/api/v1/storefront/reviews/queue",
    "/api/v1/journey/sessions",
    "/api/v1/users/",
]

# Same list minus the routes whose handler needs a live Postgres. Rejection is
# testable everywhere (the dependency runs before the handler), but "an admin
# gets through" can only be asserted where the handler itself can complete
# without a database — there's no DB fixture in this repo.
ADMIN_ONLY_GETS_NO_DB = [p for p in ADMIN_ONLY_GETS if p != "/api/v1/users/"]


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ADMIN_ONLY_GETS)
async def test_admin_routes_reject_anonymous(path):
    async with _client() as ac:
        r = await ac.get(path)

    assert r.status_code == 401, path
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ADMIN_ONLY_GETS)
async def test_admin_routes_reject_buyer(path, buyer_headers):
    async with _client() as ac:
        r = await ac.get(path, headers=buyer_headers)

    assert r.status_code == 403, path
    assert r.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ADMIN_ONLY_GETS_NO_DB)
async def test_admin_routes_admit_admin(path, admin_headers):
    """Assert only that authorisation passed — some of these then depend on an
    LLM, so the status just must not be 401/403."""
    async with _client() as ac:
        r = await ac.get(path, headers=admin_headers)

    assert r.status_code not in (401, 403), path


@pytest.mark.asyncio
async def test_slashless_router_root_keeps_admin_authorization(admin_headers):
    """A slash mismatch must be routed internally, never redirected.

    Redirecting this request used to drop the browser's Authorization header
    and immediately log the admin out of the customer-risk demo.
    """
    async with _client() as ac:
        response = await ac.get(
            "/api/v1/risk-portfolio",
            headers=admin_headers,
            follow_redirects=False,
        )

    assert response.status_code == 200
    assert response.history == []
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_dynamic_pricing_is_admin_only(buyer_headers, admin_headers):
    """Pricing stays behind the admin gate.

    An earlier revision let any seller price their own catalogue. Upstream
    narrowed it back to admins, leaving content-generator and seller-coach as
    the tenant-safe seller tools, so a seller token must be rejected here.
    """
    seller_token = create_access_token(
        "9",
        extra={"role": "seller", "email": "seller@test.dev", "name": "Seller"},
    )
    seller_headers = {"Authorization": f"Bearer {seller_token}"}
    async with _client() as ac:
        body = {"product_name": "Áo thun", "category": "Thời trang", "current_price": 200000}
        anon = await ac.post("/api/v1/dynamic-pricing/", json=body)
        buyer = await ac.post("/api/v1/dynamic-pricing/", json=body, headers=buyer_headers)
        seller = await ac.post("/api/v1/dynamic-pricing/", json=body, headers=seller_headers)
        admin = await ac.post("/api/v1/dynamic-pricing/", json=body, headers=admin_headers)

    assert anon.status_code == 401
    assert buyer.status_code == 403
    assert seller.status_code == 403
    # Admin clears the role gate; the body may still fail later validation.
    assert admin.status_code not in (401, 403)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ["/api/v1/content-generator/", "/api/v1/seller-coach/"],
)
async def test_tenant_safe_tools_admit_seller_but_reject_buyer(path, buyer_headers):
    seller_token = create_access_token(
        "9",
        extra={"role": "seller", "email": "seller@test.dev", "name": "Seller"},
    )
    seller_headers = {"Authorization": f"Bearer {seller_token}"}
    async with _client() as ac:
        buyer = await ac.post(path, headers=buyer_headers, json={})
        seller = await ac.post(path, headers=seller_headers, json={})

    assert buyer.status_code == 403
    # Invalid input may be 422; the point is that the seller passed the role gate.
    assert seller.status_code not in (401, 403)


@pytest.mark.asyncio
async def test_buyer_flow_stays_public():
    """No token anywhere — this is what an anonymous shopper does."""
    async with _client() as ac:
        health = await ac.get("/api/v1/health")
        listing = await ac.get("/api/v1/storefront/products")
        pid = listing.json()["data"]["products"][0]["id"]
        detail = await ac.get(f"/api/v1/storefront/products/{pid}")
        ingest = await ac.post(
            "/api/v1/journey/events",
            json={"session_id": "anon-1", "events": [{"type": "view", "ts": 1000}]},
        )

    assert health.status_code == 200
    assert listing.status_code == 200
    assert detail.status_code == 200
    assert ingest.status_code == 200


# Anonymous review submission is covered by
# tests/test_review_submission.py — those tests monkeypatch review_service (the
# write path needs Postgres) and pass no Authorization header, which is exactly
# the "a logged-out shopper can still review" assertion.
