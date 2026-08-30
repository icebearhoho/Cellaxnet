"""Seller workspace onboarding and tenant-isolation contract tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.security import create_access_token, decode_access_token
from app.main import app
from app.services import marketplace_shop_service, workspace_service


@dataclass
class _Workspace:
    id: int
    name: str
    slug: str
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class _Membership:
    workspace_id: int
    user_id: int
    role: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class _User:
    id: int
    email: str
    name: str | None = "Seller"
    role: str = "seller"


@dataclass
class _Shop:
    id: int
    workspace_id: int
    platform: str
    external_shop_id: str
    shop_name: str
    status: str = "connected"
    token_expires_at: datetime | None = None
    last_synced_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class _FakeWorkspaces:
    def __init__(self) -> None:
        self.rows: dict[int, _Workspace] = {}
        self.members: dict[tuple[int, int], _Membership] = {}
        self.users: dict[int, _User] = {
            2: _User(2, "user2@test.dev"),
            3: _User(3, "user3@test.dev"),
            4: _User(4, "teammate@test.dev"),
        }
        self._next_id = 1
        self.shops: dict[int, _Shop] = {}

    async def create_workspace(self, db, *, user_id, name, slug=None):  # noqa: ANN001, ARG002
        final_slug = slug or f"workspace-{self._next_id}"
        if any(row.slug == final_slug for row in self.rows.values()):
            raise ConflictError("Slug workspace đã được sử dụng.")
        workspace = _Workspace(self._next_id, name, final_slug)
        membership = _Membership(workspace.id, user_id, "owner")
        self.rows[workspace.id] = workspace
        self.members[(workspace.id, user_id)] = membership
        self._next_id += 1
        return workspace, membership, _User(user_id, f"user{user_id}@test.dev")

    async def list_members(self, db, *, workspace_id):  # noqa: ANN001, ARG002
        return [
            (membership, self.users[membership.user_id])
            for membership in self.members.values()
            if membership.workspace_id == workspace_id
        ]

    async def add_member(self, db, *, workspace_id, email, role):  # noqa: ANN001, ARG002
        account = next((user for user in self.users.values() if user.email == email), None)
        if account is None:
            raise NotFoundError("Tài khoản này chưa đăng ký trên hệ thống.")
        key = (workspace_id, account.id)
        if key in self.members:
            raise ConflictError("Tài khoản đã là thành viên của workspace.")
        membership = _Membership(workspace_id, account.id, role)
        self.members[key] = membership
        return membership, account

    async def update_member_role(
        self, db, *, workspace_id, member_user_id, role  # noqa: ANN001, ARG002
    ):
        membership = self.members.get((workspace_id, member_user_id))
        if membership is None:
            raise NotFoundError("Không tìm thấy thành viên trong workspace.")
        membership.role = role
        return membership, self.users[member_user_id]

    async def remove_member(
        self, db, *, workspace_id, member_user_id, acting_user_id  # noqa: ANN001, ARG002
    ):
        if member_user_id == acting_user_id:
            from app.core.exceptions import BusinessRuleError

            raise BusinessRuleError("Không thể tự xóa mình khỏi workspace tại đây.")
        if self.members.pop((workspace_id, member_user_id), None) is None:
            raise NotFoundError("Không tìm thấy thành viên trong workspace.")

    async def list_shops(self, db, *, workspace_id):  # noqa: ANN001, ARG002
        return [shop for shop in self.shops.values() if shop.workspace_id == workspace_id]

    async def disconnect_shop(self, db, *, workspace_id, shop_id):  # noqa: ANN001, ARG002
        shop = self.shops.get(shop_id)
        if shop is None or shop.workspace_id != workspace_id:
            raise NotFoundError("Không tìm thấy shop trong workspace.")
        shop.status = "revoked"
        return shop

    async def list_accessible_workspaces(
        self, db, *, user_id, is_platform_admin=False  # noqa: ANN001, ARG002
    ):
        if is_platform_admin:
            return [(row, "platform_admin") for row in self.rows.values()]
        return [
            (row, self.members[(row.id, user_id)].role)
            for row in self.rows.values()
            if (row.id, user_id) in self.members
        ]

    async def get_accessible_workspace(
        self, db, *, workspace_id, user_id, is_platform_admin=False  # noqa: ANN001, ARG002
    ):
        workspace = self.rows.get(workspace_id)
        if workspace is None:
            raise NotFoundError("Không tìm thấy workspace.")
        if is_platform_admin:
            return workspace, "platform_admin"
        membership = self.members.get((workspace_id, user_id))
        if membership is None:
            raise NotFoundError("Không tìm thấy workspace.")
        return workspace, membership.role


@pytest.fixture
def fake_workspaces(monkeypatch) -> _FakeWorkspaces:  # noqa: ANN001
    store = _FakeWorkspaces()
    monkeypatch.setattr(workspace_service, "create_workspace", store.create_workspace)
    monkeypatch.setattr(
        workspace_service, "list_accessible_workspaces", store.list_accessible_workspaces
    )
    monkeypatch.setattr(
        workspace_service, "get_accessible_workspace", store.get_accessible_workspace
    )
    monkeypatch.setattr(workspace_service, "list_members", store.list_members)
    monkeypatch.setattr(workspace_service, "add_member", store.add_member)
    monkeypatch.setattr(workspace_service, "update_member_role", store.update_member_role)
    monkeypatch.setattr(workspace_service, "remove_member", store.remove_member)
    monkeypatch.setattr(marketplace_shop_service, "list_shops", store.list_shops)
    monkeypatch.setattr(
        marketplace_shop_service, "disconnect_shop", store.disconnect_shop
    )
    return store


def _headers(user_id: int, role: str = "buyer") -> dict[str, str]:
    token = create_access_token(
        str(user_id),
        extra={"role": role, "email": f"user{user_id}@test.dev", "name": "Seller"},
    )
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_workspace_routes_require_login(fake_workspaces):  # noqa: ARG001
    async with _client() as ac:
        listing = await ac.get("/api/v1/workspaces/")
        creation = await ac.post("/api/v1/workspaces/", json={"name": "Minh Anh"})

    assert listing.status_code == 401
    assert creation.status_code == 401


@pytest.mark.asyncio
async def test_create_workspace_makes_caller_owner(fake_workspaces):  # noqa: ARG001
    async with _client() as ac:
        response = await ac.post(
            "/api/v1/workspaces/",
            headers=_headers(2),
            json={"name": "  Minh   Anh Fashion  ", "slug": "minh-anh-fashion"},
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["workspace"]["name"] == "Minh Anh Fashion"
    assert data["workspace"]["slug"] == "minh-anh-fashion"
    assert data["workspace"]["current_role"] == "owner"
    assert data["auth"]["user"]["role"] == "seller"
    assert decode_access_token(data["auth"]["access_token"])["role"] == "seller"


@pytest.mark.asyncio
async def test_member_only_sees_own_workspaces(fake_workspaces):
    await fake_workspaces.create_workspace(None, user_id=2, name="Workspace A", slug="a-shop")
    await fake_workspaces.create_workspace(None, user_id=3, name="Workspace B", slug="b-shop")

    async with _client() as ac:
        response = await ac.get("/api/v1/workspaces/", headers=_headers(2))

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["data"]] == ["a-shop"]


@pytest.mark.asyncio
async def test_cross_tenant_lookup_is_hidden_as_not_found(fake_workspaces):
    workspace, _, _ = await fake_workspaces.create_workspace(
        None, user_id=3, name="Workspace B", slug="b-shop"
    )

    async with _client() as ac:
        response = await ac.get(
            f"/api/v1/workspaces/{workspace.id}", headers=_headers(2)
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


@pytest.mark.asyncio
async def test_platform_admin_can_inspect_any_workspace(fake_workspaces):
    workspace, _, _ = await fake_workspaces.create_workspace(
        None, user_id=3, name="Workspace B", slug="b-shop"
    )

    async with _client() as ac:
        response = await ac.get(
            f"/api/v1/workspaces/{workspace.id}", headers=_headers(1, "admin")
        )

    assert response.status_code == 200
    assert response.json()["data"]["current_role"] == "platform_admin"


@pytest.mark.asyncio
async def test_workspace_slug_validation_and_conflict(fake_workspaces):  # noqa: ARG001
    headers = _headers(2)
    async with _client() as ac:
        invalid = await ac.post(
            "/api/v1/workspaces/", headers=headers, json={"name": "Shop", "slug": "Bad Slug"}
        )
        first = await ac.post(
            "/api/v1/workspaces/", headers=headers, json={"name": "Shop", "slug": "shop-one"}
        )
        duplicate = await ac.post(
            "/api/v1/workspaces/", headers=headers, json={"name": "Shop 2", "slug": "shop-one"}
        )

    assert invalid.status_code == 422
    assert first.status_code == 200
    assert duplicate.status_code == 409


def test_generated_slug_normalizes_vietnamese_name():
    assert workspace_service._slugify("  Thời Trang Minh Ánh  ") == "thoi-trang-minh-anh"


@pytest.mark.asyncio
async def test_members_endpoint_requires_verified_workspace_header(fake_workspaces):
    workspace, _, _ = await fake_workspaces.create_workspace(
        None, user_id=2, name="Workspace A", slug="a-shop"
    )
    async with _client() as ac:
        missing = await ac.get(
            f"/api/v1/workspaces/{workspace.id}/members", headers=_headers(2)
        )
        other_tenant = await ac.get(
            f"/api/v1/workspaces/{workspace.id}/members",
            headers={**_headers(3), "X-Workspace-ID": str(workspace.id)},
        )

    assert missing.status_code == 422
    assert other_tenant.status_code == 404


@pytest.mark.asyncio
async def test_owner_can_add_update_and_remove_member(fake_workspaces):
    workspace, _, _ = await fake_workspaces.create_workspace(
        None, user_id=2, name="Workspace A", slug="a-shop"
    )
    headers = {**_headers(2, "seller"), "X-Workspace-ID": str(workspace.id)}
    async with _client() as ac:
        added = await ac.post(
            f"/api/v1/workspaces/{workspace.id}/members",
            headers=headers,
            json={"email": "teammate@test.dev", "role": "analyst"},
        )
        updated = await ac.patch(
            f"/api/v1/workspaces/{workspace.id}/members/4",
            headers=headers,
            json={"role": "manager"},
        )
        listing = await ac.get(
            f"/api/v1/workspaces/{workspace.id}/members", headers=headers
        )
        removed = await ac.delete(
            f"/api/v1/workspaces/{workspace.id}/members/4", headers=headers
        )

    assert added.status_code == 200
    assert added.json()["data"]["role"] == "analyst"
    assert updated.status_code == 200
    assert updated.json()["data"]["role"] == "manager"
    assert {item["user_id"] for item in listing.json()["data"]} == {2, 4}
    assert removed.status_code == 200


@pytest.mark.asyncio
async def test_non_owner_cannot_manage_members(fake_workspaces):
    workspace, _, _ = await fake_workspaces.create_workspace(
        None, user_id=2, name="Workspace A", slug="a-shop"
    )
    fake_workspaces.members[(workspace.id, 3)] = _Membership(
        workspace.id, 3, "manager"
    )
    headers = {**_headers(3, "seller"), "X-Workspace-ID": str(workspace.id)}

    async with _client() as ac:
        response = await ac.post(
            f"/api/v1/workspaces/{workspace.id}/members",
            headers=headers,
            json={"email": "teammate@test.dev", "role": "viewer"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_header_and_path_workspace_must_match(fake_workspaces):
    first, _, _ = await fake_workspaces.create_workspace(
        None, user_id=2, name="Workspace A", slug="a-shop"
    )
    second, _, _ = await fake_workspaces.create_workspace(
        None, user_id=2, name="Workspace B", slug="b-shop"
    )
    headers = {**_headers(2, "seller"), "X-Workspace-ID": str(second.id)}

    async with _client() as ac:
        response = await ac.get(
            f"/api/v1/workspaces/{first.id}/members", headers=headers
        )

    assert response.status_code == 404


class _ScalarResult:
    def __init__(self, value) -> None:  # noqa: ANN001
        self.value = value

    def scalar_one_or_none(self):  # noqa: ANN201
        return self.value

    def scalar_one(self):  # noqa: ANN201
        return self.value


class _SequenceDb:
    def __init__(self, results: list[object]) -> None:
        self.results = results
        self.committed = 0

    async def execute(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
        return _ScalarResult(self.results.pop(0))

    async def commit(self) -> None:
        self.committed += 1

    async def refresh(self, _row) -> None:  # noqa: ANN001
        return None


@pytest.mark.asyncio
async def test_cannot_demote_last_workspace_owner():
    membership = _Membership(workspace_id=10, user_id=2, role="owner")
    db = _SequenceDb([membership, 1])

    with pytest.raises(BusinessRuleError, match="ít nhất một chủ sở hữu"):
        await workspace_service.update_member_role(
            db,  # type: ignore[arg-type]
            workspace_id=10,
            member_user_id=2,
            role="manager",
        )

    assert db.committed == 0


@pytest.mark.asyncio
async def test_marketplace_shops_are_workspace_scoped(fake_workspaces):
    first, _, _ = await fake_workspaces.create_workspace(
        None, user_id=2, name="Workspace A", slug="a-shop"
    )
    second, _, _ = await fake_workspaces.create_workspace(
        None, user_id=3, name="Workspace B", slug="b-shop"
    )
    fake_workspaces.shops[1] = _Shop(1, first.id, "shopee", "shop-a", "Shop A")
    fake_workspaces.shops[2] = _Shop(2, second.id, "shopee", "shop-b", "Shop B")
    headers = {**_headers(2, "seller"), "X-Workspace-ID": str(first.id)}

    async with _client() as ac:
        listing = await ac.get(
            f"/api/v1/workspaces/{first.id}/shops", headers=headers
        )
        cross_tenant_disconnect = await ac.delete(
            f"/api/v1/workspaces/{first.id}/shops/2", headers=headers
        )

    assert listing.status_code == 200
    assert [shop["external_shop_id"] for shop in listing.json()["data"]] == ["shop-a"]
    assert cross_tenant_disconnect.status_code == 404


@pytest.mark.asyncio
async def test_manager_can_disconnect_workspace_shop(fake_workspaces):
    workspace, _, _ = await fake_workspaces.create_workspace(
        None, user_id=2, name="Workspace A", slug="a-shop"
    )
    fake_workspaces.members[(workspace.id, 3)] = _Membership(
        workspace.id, 3, "manager"
    )
    fake_workspaces.shops[1] = _Shop(
        1, workspace.id, "shopee", "shop-a", "Shop A"
    )
    headers = {**_headers(3, "seller"), "X-Workspace-ID": str(workspace.id)}

    async with _client() as ac:
        response = await ac.delete(
            f"/api/v1/workspaces/{workspace.id}/shops/1", headers=headers
        )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "revoked"


@pytest.mark.asyncio
async def test_invited_member_with_stale_buyer_token_can_use_workspace_tool(fake_workspaces):
    workspace, _, _ = await fake_workspaces.create_workspace(
        None, user_id=3, name="Workspace B", slug="b-shop"
    )
    headers = {**_headers(3, "buyer"), "X-Workspace-ID": str(workspace.id)}

    async with _client() as ac:
        response = await ac.post(
            "/api/v1/content-generator/",
            headers=headers,
            json={"product_name": "Áo khoác", "features": "Denim bền"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_stale_seller_token_cannot_use_workspace_after_removal(fake_workspaces):
    workspace, _, _ = await fake_workspaces.create_workspace(
        None, user_id=2, name="Workspace A", slug="a-shop"
    )
    headers = {**_headers(3, "seller"), "X-Workspace-ID": str(workspace.id)}

    async with _client() as ac:
        response = await ac.post(
            "/api/v1/content-generator/",
            headers=headers,
            json={"product_name": "Áo khoác", "features": "Denim bền"},
        )

    assert response.status_code == 404
