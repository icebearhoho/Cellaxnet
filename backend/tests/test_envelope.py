"""Smoke tests for the response envelope contract."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.ideas import IDEAS
from app.core.exceptions import AppError, NotFoundError
from app.core.responses import ApiResponse, ErrorPayload, PageMeta
from app.main import app


# ---------- Envelope model ----------------------------------------------------
def test_envelope_shape_success():
    resp = ApiResponse[dict](
        success=True,
        data={"a": 1},
        meta=PageMeta(page=1, page_size=20, total=1),
        error=None,
    )
    dumped = resp.model_dump()
    assert dumped["success"] is True
    assert dumped["data"] == {"a": 1}
    assert dumped["meta"]["page"] == 1
    assert dumped["error"] is None


def test_error_payload_serializes():
    err = ErrorPayload(code="X", message="m", details={"k": "v"})
    assert err.model_dump() == {"code": "X", "message": "m", "details": {"k": "v"}}


# ---------- Exception taxonomy ----------------------------------------------
def test_app_error_defaults():
    exc = AppError("boom")
    assert exc.status_code == 400
    assert exc.code == "INTERNAL_ERROR"


def test_not_found_error():
    exc = NotFoundError("missing")
    assert exc.status_code == 404
    assert exc.code == "RESOURCE_NOT_FOUND"


# ---------- HTTP integration ------------------------------------------------
@pytest.mark.asyncio
async def test_health_endpoint_returns_envelope():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"success", "data", "meta", "error"}
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["error"] is None


@pytest.mark.asyncio
async def test_cors_allows_both_local_frontend_hosts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
            r = await ac.options(
                "/api/v1/storefront/products",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                },
            )
            assert r.status_code == 200
            assert r.headers["access-control-allow-origin"] == origin


@pytest.mark.asyncio
async def test_unknown_route_returns_envelope():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert "request_id" in (body["meta"] or {})


@pytest.mark.asyncio
async def test_ideas_list_uses_pagination_meta():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/ideas/?page=1&page_size=5")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 5
    assert body["meta"]["total"] == len(IDEAS)
    assert len(body["data"]) == 5


@pytest.mark.asyncio
async def test_ideas_get_missing_raises_envelope():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/ideas/9999")
    assert r.status_code == 404
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_kpis_summary_shape():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/kpis/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "kpis" in body["data"]
    assert len(body["data"]["kpis"]) == 4
