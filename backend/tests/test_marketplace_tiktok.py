"""TikTok Shop adapter: signing, the shop cipher, parsing and failure handling.

The signature tests recompute the HMAC by hand from TikTok's documented base
string rather than asserting against a value this code produced. A test that
compares the implementation to itself passes just as happily when the base
string is wrong, and a wrong base string is the single most likely defect here:
TikTok answers every mis-signed request with a generic error that names nothing.

The cipher tests exist because TikTok is the only marketplace that needs a
second piece of state on every call. Forgetting it produces rejections that read
like an expired token, which sends people re-authorising instead of fixing the
actual problem.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import settings
from app.services.marketplace import tiktok as tt
from app.services.marketplace.base import (
    AdapterError,
    AuthorisationError,
    Cred,
    RateLimitedError,
)

APP_KEY = "6kvjtestappkey"
APP_SECRET = "tiktok-test-app-secret"
SHOP_ID = "7495000000000000000"
CIPHER = "TTP_test_cipher_value"
SERVICE_ID = "SVC-1005678"


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    monkeypatch.setattr(settings, "TIKTOK_APP_KEY", APP_KEY)
    monkeypatch.setattr(settings, "TIKTOK_APP_SECRET", APP_SECRET)
    monkeypatch.setattr(settings, "TIKTOK_SERVICE_ID", SERVICE_ID)
    yield


def _cred(**over) -> Cred:
    base = {
        "external_shop_id": SHOP_ID,
        "access_token": "ACCESS_TOKEN_123",
        "region": "VN",
        "extra": {"shop_cipher": CIPHER},
    }
    base.update(over)
    return Cred(**base)


def _expected_sign(path: str, params: dict, body: str | None = None) -> str:
    """TikTok's documented base string, assembled independently of the adapter."""
    signable = {k: v for k, v in params.items() if k not in ("sign", "access_token")}
    joined = "".join(f"{k}{signable[k]}" for k in sorted(signable))
    base = f"{path}{joined}"
    if body:
        base += body
    wrapped = f"{APP_SECRET}{base}{APP_SECRET}"
    return hmac.new(APP_SECRET.encode(), wrapped.encode(), hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------- #
# signing
# --------------------------------------------------------------------------- #

def test_signature_matches_hand_computation():
    params = {"app_key": APP_KEY, "timestamp": 1_754_000_000, "page_size": 50}
    assert tt.adapter._sign(tt.PATH_SHOPS, params) == _expected_sign(tt.PATH_SHOPS, params)


def test_signature_includes_body_for_post_calls():
    params = {"app_key": APP_KEY, "timestamp": 1_754_000_000, "shop_cipher": CIPHER}
    body = json.dumps({"create_time_ge": 1}, separators=(",", ":"))
    got = tt.adapter._sign(tt.PATH_ORDER_SEARCH, params, body)
    assert got == _expected_sign(tt.PATH_ORDER_SEARCH, params, body)
    # A body that is signed must change the signature; if it did not, the body
    # would be unprotected and this whole argument would be decorative.
    assert got != tt.adapter._sign(tt.PATH_ORDER_SEARCH, params)


def test_signature_sorts_params_regardless_of_insertion_order():
    ordered = {"app_key": APP_KEY, "page_size": 50, "timestamp": 1_754_000_000}
    shuffled = {"timestamp": 1_754_000_000, "app_key": APP_KEY, "page_size": 50}
    assert tt.adapter._sign(tt.PATH_SHOPS, ordered) == tt.adapter._sign(
        tt.PATH_SHOPS, shuffled
    )


def test_signature_excludes_access_token_and_sign():
    """access_token travels as a header, so signing it would break every call."""
    without = {"app_key": APP_KEY, "timestamp": 1_754_000_000}
    with_extra = {**without, "access_token": "ACCESS_TOKEN_123", "sign": "stale"}
    assert tt.adapter._sign(tt.PATH_SHOPS, with_extra) == tt.adapter._sign(
        tt.PATH_SHOPS, without
    )


def test_signature_changes_when_path_changes():
    params = {"app_key": APP_KEY, "timestamp": 1_754_000_000}
    assert tt.adapter._sign(tt.PATH_SHOPS, params) != tt.adapter._sign(
        tt.PATH_ORDER_SEARCH, params
    )


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #

def test_unconfigured_adapter_names_the_missing_settings(monkeypatch):
    monkeypatch.setattr(settings, "TIKTOK_APP_KEY", None)
    monkeypatch.setattr(settings, "TIKTOK_APP_SECRET", None)
    assert not tt.adapter.configured()
    assert tt.adapter.missing_settings() == ["TIKTOK_APP_KEY", "TIKTOK_APP_SECRET"]
    with pytest.raises(AdapterError) as exc:
        tt.adapter.authorize_url("state123", "https://example.test/cb")
    assert "TIKTOK_APP_KEY" in str(exc.value)


def test_missing_service_id_is_named_even_when_app_key_is_set(monkeypatch):
    """service_id is distinct from the App Key; falling back to the App Key
    produces "This service does not exist" from TikTok, an error that names
    nothing. The check has to name the real cause instead.
    """
    monkeypatch.setattr(settings, "TIKTOK_SERVICE_ID", None)
    assert not tt.adapter.configured()
    assert tt.adapter.missing_settings() == ["TIKTOK_SERVICE_ID"]
    with pytest.raises(AdapterError) as exc:
        tt.adapter.authorize_url("state123", "https://example.test/cb")
    assert "TIKTOK_SERVICE_ID" in str(exc.value)


def test_authorize_url_carries_state_and_the_configured_service_id():
    url = tt.adapter.authorize_url("state123", "https://example.test/cb")
    assert url.startswith(tt.AUTHORIZE_URL)
    assert "state=state123" in url
    assert f"service_id={SERVICE_ID}" in url


def test_authorize_url_never_falls_back_to_the_app_key():
    """Regression guard for the actual bug: App Key and service_id must never
    collide, since TikTok validates them against different records.
    """
    url = tt.adapter.authorize_url("s", "https://example.test/cb")
    assert f"service_id={APP_KEY}" not in url


# --------------------------------------------------------------------------- #
# the shop cipher
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_post_without_cipher_raises_authorisation_error():
    """A missing cipher must not surface as a generic failure.

    Every shop-scoped call is rejected without it, and TikTok's error does not
    explain why — so the adapter has to.
    """
    with pytest.raises(AuthorisationError) as exc:
        await tt.adapter.fetch_orders(
            _cred(extra={}), datetime.now(UTC) - timedelta(days=7), None
        )
    assert "shop_cipher" in str(exc.value)


@pytest.mark.asyncio
async def test_post_puts_cipher_and_signature_on_the_wire(monkeypatch):
    """Stubs the HTTP client rather than `_post`, so the real request is inspected.

    Everything above this asserts on `_post`'s arguments; this is the one test
    that checks what actually leaves the process.
    """
    seen: dict = {}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, params=None, content=None, headers=None, **kw):
            seen.update(url=url, params=params, content=content, headers=headers)
            return _Resp({"code": 0, "data": {"orders": []}})

    monkeypatch.setattr(tt.httpx, "AsyncClient", lambda *a, **k: _Client())
    await tt.adapter.fetch_orders(_cred(), datetime.now(UTC) - timedelta(days=1), None)

    assert seen["params"]["shop_cipher"] == CIPHER
    assert seen["headers"]["x-tts-access-token"] == "ACCESS_TOKEN_123"
    # The signature must match the body actually sent, byte for byte.
    assert seen["params"]["sign"] == _expected_sign(
        tt.PATH_ORDER_SEARCH,
        {k: v for k, v in seen["params"].items() if k != "sign"},
        seen["content"],
    )


@pytest.mark.asyncio
async def test_exchange_code_resolves_shop_id_and_cipher(monkeypatch):
    """The token response says who authorised, not which shop — hence two calls."""
    now = int(datetime.now(UTC).timestamp())

    async def fake_auth(path, query):
        assert query["grant_type"] == "authorized_code"
        assert query["auth_code"] == "AUTH_CODE_1"
        return {"code": 0, "data": {
            "access_token": "AT", "refresh_token": "RT",
            "access_token_expire_in": now + 604_800,
            "refresh_token_expire_in": now + 31_536_000,
            "seller_name": "Shop Thoi Trang",
        }}

    async def fake_get(path, token, query):
        assert path == tt.PATH_SHOPS
        return {"code": 0, "data": {"shops": [
            {"id": SHOP_ID, "cipher": CIPHER, "name": "Shop Thoi Trang", "region": "VN"},
        ]}}

    monkeypatch.setattr(tt.adapter, "_auth_call", fake_auth)
    monkeypatch.setattr(tt.adapter, "_get", fake_get)

    bundle = await tt.adapter.exchange_code("AUTH_CODE_1", {})
    assert bundle.access_token == "AT"
    assert bundle.refresh_token == "RT"
    assert bundle.extra["shop_id"] == SHOP_ID
    assert bundle.extra["shop_cipher"] == CIPHER
    assert bundle.expires_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_refresh_keeps_the_existing_cipher(monkeypatch):
    """Refreshing does not change which shop the token is for."""
    async def fake_auth(path, query):
        assert query["grant_type"] == "refresh_token"
        return {"code": 0, "data": {"access_token": "AT2", "refresh_token": "RT2"}}

    monkeypatch.setattr(tt.adapter, "_auth_call", fake_auth)
    bundle = await tt.adapter.refresh("RT", _cred())
    assert bundle.access_token == "AT2"
    assert bundle.extra["shop_cipher"] == CIPHER


@pytest.mark.asyncio
async def test_exchange_code_without_shops_explains_why(monkeypatch):
    async def fake_auth(path, query):
        return {"code": 0, "data": {"access_token": "AT"}}

    async def fake_get(path, token, query):
        return {"code": 0, "data": {"shops": []}}

    monkeypatch.setattr(tt.adapter, "_auth_call", fake_auth)
    monkeypatch.setattr(tt.adapter, "_get", fake_get)
    with pytest.raises(AdapterError) as exc:
        await tt.adapter.exchange_code("CODE", {})
    assert "cửa hàng" in str(exc.value)


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_orders_are_normalised_and_paged(monkeypatch):
    async def fake_post(path, cred, query, body):
        assert path == tt.PATH_ORDER_SEARCH
        assert cred.extra["shop_cipher"] == CIPHER
        assert body["create_time_ge"] < body["create_time_lt"]
        return {"code": 0, "data": {
            "next_page_token": "CURSOR_2",
            "orders": [{
                "id": "5770000000",
                "status": "COMPLETED",
                "payment": {"total_amount": "459000", "currency": "VND"},
                "create_time": 1_754_000_000,
                "update_time": 1_754_100_000,
                "user_id": "BUYER_9",
                "payment_method_name": "COD",
                "line_items": [
                    {"product_id": "P1", "sku_id": "S1", "seller_sku": "AO-M",
                     "product_name": "Áo khoác", "sale_price": "229500"},
                    {"product_id": "P1", "sku_id": "S1", "seller_sku": "AO-M",
                     "product_name": "Áo khoác", "sale_price": "229500"},
                ],
            }],
        }}

    monkeypatch.setattr(tt.adapter, "_post", fake_post)
    page = await tt.adapter.fetch_orders(
        _cred(), datetime.now(UTC) - timedelta(days=30), None
    )

    assert page.next_cursor == "CURSOR_2"
    order = page.items[0]
    assert order.external_order_id == "5770000000"
    assert order.status == "completed"
    assert order.raw_status == "COMPLETED"
    assert order.total_amount == 459_000
    assert order.placed_at == datetime.fromtimestamp(1_754_000_000, tz=UTC)
    # TikTok returns one line per unit sold, so two lines is two units.
    assert len(order.items) == 2
    assert order.items[0].unit_price == 229_500


@pytest.mark.asyncio
async def test_unknown_order_status_is_flagged_not_guessed(monkeypatch):
    async def fake_post(path, cred, query, body):
        return {"code": 0, "data": {"orders": [
            {"id": "1", "status": "SOME_NEW_STATUS", "payment": {}},
        ]}}

    monkeypatch.setattr(tt.adapter, "_post", fake_post)
    page = await tt.adapter.fetch_orders(_cred(), datetime.now(UTC), None)
    assert page.items[0].status == "unknown"
    assert page.items[0].raw_status == "SOME_NEW_STATUS"


@pytest.mark.asyncio
async def test_every_mapped_status_is_canonical():
    from app.models.marketplace import ORDER_STATUSES

    for canonical in tt.ORDER_STATUS_MAP.values():
        assert canonical in ORDER_STATUSES


@pytest.mark.asyncio
async def test_products_flatten_to_one_row_per_sku(monkeypatch):
    async def fake_post(path, cred, query, body):
        assert path == tt.PATH_PRODUCT_SEARCH
        return {"code": 0, "data": {"next_page_token": "", "products": [{
            "id": "P100",
            "title": "Áo len nữ",
            "status": "ACTIVATE",
            "main_images": [{"urls": ["https://img.test/a.jpg"]}],
            "brand": {"name": "NoBrand"},
            "category_chains": [
                {"local_name": "Thời trang"}, {"local_name": "Áo len"},
            ],
            "skus": [
                {"id": "S1", "seller_sku": "LEN-S",
                 "price": {"sale_price": "199000", "original_price": "259000",
                           "currency": "VND"}},
                {"id": "S2", "seller_sku": "LEN-M",
                 "price": {"sale_price": "199000", "currency": "VND"}},
            ],
        }]}}

    monkeypatch.setattr(tt.adapter, "_post", fake_post)
    page = await tt.adapter.fetch_products(_cred(), None)

    assert len(page.items) == 2
    assert page.next_cursor is None  # empty token means end of data
    first = page.items[0]
    assert first.external_product_id == "P100"
    assert first.external_sku_id == "S1"
    assert first.price == 199_000
    assert first.original_price == 259_000
    assert first.category_path == "Thời trang > Áo len"
    assert first.image_url == "https://img.test/a.jpg"


@pytest.mark.asyncio
async def test_product_without_variants_still_yields_a_row(monkeypatch):
    """Empty string, not NULL: NULL never equals NULL in the unique constraint."""
    async def fake_post(path, cred, query, body):
        return {"code": 0, "data": {"products": [
            {"id": "P200", "title": "Set quà tặng", "status": "ACTIVATE", "skus": []},
        ]}}

    monkeypatch.setattr(tt.adapter, "_post", fake_post)
    page = await tt.adapter.fetch_products(_cred(), None)
    assert len(page.items) == 1
    assert page.items[0].external_sku_id == ""


@pytest.mark.asyncio
async def test_inventory_comes_from_the_product_payload(monkeypatch):
    async def fake_post(path, cred, query, body):
        return {"code": 0, "data": {"products": [{
            "id": "P300", "title": "Quần jean", "status": "ACTIVATE",
            "skus": [{"id": "S9", "inventory": [
                {"warehouse_id": "W1", "quantity": 12},
                {"warehouse_id": "W2", "quantity": 3},
            ]}],
        }]}}

    monkeypatch.setattr(tt.adapter, "_post", fake_post)
    page = await tt.adapter.fetch_inventory(_cred(), None)

    assert len(page.items) == 2
    assert {r.warehouse_id for r in page.items} == {"W1", "W2"}
    assert sum(r.quantity_available for r in page.items) == 15


# --------------------------------------------------------------------------- #
# failure handling
# --------------------------------------------------------------------------- #

class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status
        self.text = str(payload)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_non_zero_code_raises_even_on_http_200():
    """TikTok reports refusals in the body; status code alone says nothing."""
    with pytest.raises(AdapterError) as exc:
        tt.adapter._unwrap(_Resp({"code": 12345, "message": "invalid param"}), "/x")
    assert "12345" in str(exc.value)


def test_dead_auth_code_raises_authorisation_error():
    """Distinct from a transient failure: retrying will never help."""
    with pytest.raises(AuthorisationError):
        tt.adapter._unwrap(_Resp({"code": 105000, "message": "token invalid"}), "/x")


def test_rate_limit_carries_retry_after():
    with pytest.raises(RateLimitedError) as exc:
        tt.adapter._unwrap(_Resp({}, status=429), "/x")
    assert exc.value.retry_after_s > 0


def test_non_json_body_is_reported_clearly():
    with pytest.raises(AdapterError) as exc:
        tt.adapter._unwrap(_Resp(ValueError("not json"), status=502), "/x")
    assert "JSON" in str(exc.value)


def test_success_code_zero_passes_through():
    assert tt.adapter._unwrap(_Resp({"code": 0, "data": {"ok": 1}}), "/x")["data"] == {"ok": 1}


# --------------------------------------------------------------------------- #
# registration
# --------------------------------------------------------------------------- #

def test_adapter_is_registered_under_its_platform():
    from app.services.marketplace import get_adapter

    assert get_adapter("tiktok") is tt.adapter


def test_adapter_satisfies_the_protocol():
    from app.services.marketplace.base import MarketplaceAdapter

    assert isinstance(tt.adapter, MarketplaceAdapter)
