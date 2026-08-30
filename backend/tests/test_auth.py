"""Register / login / me contract tests.

`user_service` is monkeypatched with an in-memory store (the pattern
`test_review_submission.py` uses) because there's no DB fixture in this repo.
The fake still calls the real `hash_password`/`verify_password`, so these
tests genuinely exercise the bcrypt path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import decode_access_token, hash_password, verify_password
from app.main import app
from app.services import user_service


@dataclass
class _FakeUser:
    id: int
    email: str
    password_hash: str
    name: str | None
    role: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class _FakeUsers:
    def __init__(self) -> None:
        self.rows: dict[str, _FakeUser] = {}
        self._next_id = 1

    async def get_by_email(self, db, email):  # noqa: ANN001, ARG002
        return self.rows.get(email.strip().lower())

    async def get_by_id(self, db, user_id):  # noqa: ANN001, ARG002
        return next((row for row in self.rows.values() if row.id == user_id), None)

    async def create_user(self, db, *, email, password, name=None, role="buyer"):  # noqa: ANN001, ARG002
        email = email.strip().lower()
        if email in self.rows:
            raise ConflictError("Email đã được sử dụng.")
        row = _FakeUser(
            id=self._next_id,
            email=email,
            password_hash=hash_password(password),
            name=name,
            role=role,
        )
        self.rows[email] = row
        self._next_id += 1
        return row

    async def authenticate(self, db, *, email, password):  # noqa: ANN001, ARG002
        row = self.rows.get(email.strip().lower())
        if row is None or not verify_password(password, row.password_hash):
            raise UnauthorizedError("Email hoặc mật khẩu không đúng.")
        return row


@pytest.fixture
def fake_users(monkeypatch) -> _FakeUsers:  # noqa: ANN001
    store = _FakeUsers()
    monkeypatch.setattr(user_service, "get_by_email", store.get_by_email)
    monkeypatch.setattr(user_service, "get_by_id", store.get_by_id)
    monkeypatch.setattr(user_service, "create_user", store.create_user)
    monkeypatch.setattr(user_service, "authenticate", store.authenticate)
    return store


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_register_creates_buyer_and_returns_token(fake_users):  # noqa: ARG001
    async with _client() as ac:
        r = await ac.post(
            "/api/v1/auth/register",
            json={"email": "New@Test.dev", "password": "buyer12345", "name": "Người mua"},
        )

    assert r.status_code == 200
    data = r.json()["data"]
    assert data["user"]["role"] == "buyer"
    assert data["user"]["email"] == "new@test.dev"  # normalised to lowercase
    assert data["token_type"] == "bearer"
    assert decode_access_token(data["access_token"])["role"] == "buyer"


@pytest.mark.asyncio
async def test_register_ignores_client_supplied_role(fake_users):  # noqa: ARG001
    """Mass-assignment guard: asking for admin must not grant it."""
    async with _client() as ac:
        r = await ac.post(
            "/api/v1/auth/register",
            json={"email": "sneaky@test.dev", "password": "buyer12345", "role": "admin"},
        )

    assert r.status_code == 200
    assert r.json()["data"]["user"]["role"] == "buyer"
    assert decode_access_token(r.json()["data"]["access_token"])["role"] == "buyer"


@pytest.mark.asyncio
async def test_register_duplicate_email_conflicts(fake_users):  # noqa: ARG001
    async with _client() as ac:
        body = {"email": "dup@test.dev", "password": "buyer12345"}
        first = await ac.post("/api/v1/auth/register", json=body)
        second = await ac.post("/api/v1/auth/register", json=body)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "RESOURCE_CONFLICT"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"email": "short@test.dev", "password": "1234567"},  # 7 chars
        {"email": "unicode@test.dev", "password": "á" * 40},  # 80 UTF-8 bytes
        {"email": "not-an-email", "password": "buyer12345"},
        {"email": "spaced out@test.dev", "password": "buyer12345"},
    ],
)
async def test_register_validation_errors(fake_users, body):  # noqa: ARG001
    async with _client() as ac:
        r = await ac.post("/api/v1/auth/register", json=body)

    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_success_then_wrong_password(fake_users):  # noqa: ARG001
    async with _client() as ac:
        await ac.post(
            "/api/v1/auth/register",
            json={"email": "who@test.dev", "password": "buyer12345"},
        )
        ok = await ac.post(
            "/api/v1/auth/login",
            json={"email": "who@test.dev", "password": "buyer12345"},
        )
        bad = await ac.post(
            "/api/v1/auth/login",
            json={"email": "who@test.dev", "password": "wrong-one"},
        )
        unknown = await ac.post(
            "/api/v1/auth/login",
            json={"email": "ghost@test.dev", "password": "buyer12345"},
        )

    assert ok.status_code == 200
    assert decode_access_token(ok.json()["data"]["access_token"])["sub"]
    assert bad.status_code == 401
    assert unknown.status_code == 401
    # Same message for both, so responses can't be used to enumerate accounts.
    assert bad.json()["error"]["message"] == unknown.json()["error"]["message"]


@pytest.mark.asyncio
async def test_me_echoes_claims(admin_headers):
    async with _client() as ac:
        r = await ac.get("/api/v1/auth/me", headers=admin_headers)

    assert r.status_code == 200
    assert r.json()["data"]["role"] == "admin"
    assert r.json()["data"]["email"] == "admin@test.dev"


@pytest.mark.asyncio
async def test_refresh_reissues_role_from_current_account(fake_users):
    async with _client() as ac:
        registered = await ac.post(
            "/api/v1/auth/register",
            json={"email": "invited@test.dev", "password": "buyer12345"},
        )
        old_token = registered.json()["data"]["access_token"]
        fake_users.rows["invited@test.dev"].role = "seller"
        refreshed = await ac.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {old_token}"},
        )

    assert refreshed.status_code == 200
    data = refreshed.json()["data"]
    assert data["user"]["role"] == "seller"
    assert decode_access_token(data["access_token"])["role"] == "seller"


@pytest.mark.asyncio
async def test_me_rejects_missing_and_garbage_tokens():
    async with _client() as ac:
        missing = await ac.get("/api/v1/auth/me")
        garbage = await ac.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
        )

    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "UNAUTHORIZED"
    assert garbage.status_code == 401
    assert garbage.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_me_classifies_expired_token_separately():
    from app.core.security import create_access_token

    expired = create_access_token("2", expires_minutes=-1, extra={"role": "buyer"})
    async with _client() as ac:
        response = await ac.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_EXPIRED"
