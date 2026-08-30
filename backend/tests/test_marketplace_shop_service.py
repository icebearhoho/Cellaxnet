"""Credential-safety contract for normalized marketplace shop connections."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core import crypto
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.services import marketplace_shop_service as service


class _ScalarResult:
    def __init__(self, value) -> None:  # noqa: ANN001
        self.value = value

    def scalar_one_or_none(self):  # noqa: ANN201
        return self.value


class _FakeDb:
    def __init__(self, selected=None) -> None:  # noqa: ANN001
        self.selected = selected
        self.added: list[object] = []
        self.committed = 0

    async def execute(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
        return _ScalarResult(self.selected)

    def add(self, row: object) -> None:
        self.added.append(row)

    async def commit(self) -> None:
        self.committed += 1

    async def refresh(self, row) -> None:  # noqa: ANN001
        if getattr(row, "id", None) is None:
            row.id = 1
        now = datetime.now(UTC)
        if getattr(row, "created_at", None) is None:
            row.created_at = now
        if getattr(row, "updated_at", None) is None:
            row.updated_at = now


@pytest.mark.asyncio
async def test_oauth_tokens_are_encrypted_before_shop_is_persisted(monkeypatch):
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", crypto.generate_key())
    crypto._fernet.cache_clear()
    db = _FakeDb()

    row = await service.upsert_authorized_shop(
        db,  # type: ignore[arg-type]
        workspace_id=7,
        platform="shopee",
        external_shop_id="9911",
        shop_name="Minh Anh",
        access_token="access-secret",
        refresh_token="refresh-secret",
        token_expires_at=datetime.now(UTC) + timedelta(hours=4),
    )

    assert db.committed == 1
    assert row.access_token_encrypted != "access-secret"
    assert row.refresh_token_encrypted != "refresh-secret"
    assert crypto.decrypt(row.access_token_encrypted or "") == "access-secret"
    assert crypto.decrypt(row.refresh_token_encrypted or "") == "refresh-secret"


@pytest.mark.asyncio
async def test_unsupported_platform_is_rejected_before_database_use(monkeypatch):
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", crypto.generate_key())
    crypto._fernet.cache_clear()
    db = _FakeDb()

    with pytest.raises(ValidationError, match="chưa được hỗ trợ"):
        await service.upsert_authorized_shop(
            db,  # type: ignore[arg-type]
            workspace_id=7,
            platform="facebook",
            external_shop_id="9911",
            shop_name="Minh Anh",
            access_token="access-secret",
            refresh_token=None,
            token_expires_at=None,
        )

    assert db.committed == 0


@pytest.mark.asyncio
async def test_disconnect_erases_credentials_but_keeps_shop_record(monkeypatch):
    from app.models.marketplace_shop import MarketplaceShop

    row = MarketplaceShop(
        id=9,
        workspace_id=7,
        platform="shopee",
        external_shop_id="9911",
        shop_name="Minh Anh",
        status="connected",
        access_token_encrypted="cipher-access",
        refresh_token_encrypted="cipher-refresh",
    )

    async def get_shop(db, *, workspace_id, shop_id):  # noqa: ANN001, ARG001
        assert workspace_id == 7
        assert shop_id == 9
        return row

    monkeypatch.setattr(service, "get_shop", get_shop)
    db = _FakeDb()

    disconnected = await service.disconnect_shop(
        db,  # type: ignore[arg-type]
        workspace_id=7,
        shop_id=9,
    )

    assert disconnected.status == "revoked"
    assert disconnected.access_token_encrypted is None
    assert disconnected.refresh_token_encrypted is None
    assert db.committed == 1
