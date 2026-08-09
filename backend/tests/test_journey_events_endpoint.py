"""POST /journey/events — best-effort persistence, fails open on DB errors.

No DB fixture exists in this repo yet (see backend/tests/conftest.py), so
``behavior_events.persist_events`` is monkeypatched rather than hitting a
real Postgres — this test verifies the endpoint's contract/fail-open
behaviour, not the SQL itself.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import behavior_events


@pytest.mark.asyncio
async def test_track_events_persists_and_returns_count(monkeypatch):
    async def fake_persist(db, *, session_id, customer_id, events):
        assert session_id == "sess-1"
        return len(events)

    monkeypatch.setattr(behavior_events, "persist_events", fake_persist)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/journey/events",
            json={"session_id": "sess-1", "events": [{"type": "view", "ts": 1000}]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["persisted"] == 1


@pytest.mark.asyncio
async def test_track_events_requires_session_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/journey/events",
            json={"events": [{"type": "view", "ts": 1000}]},
        )

    assert response.status_code == 422
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_track_events_fails_open_on_db_error(monkeypatch):
    async def broken_persist(db, *, session_id, customer_id, events):
        raise RuntimeError("db is down")

    monkeypatch.setattr(behavior_events, "persist_events", broken_persist)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/journey/events",
            json={"session_id": "sess-1", "events": [{"type": "view", "ts": 1000}]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["persisted"] == 0
