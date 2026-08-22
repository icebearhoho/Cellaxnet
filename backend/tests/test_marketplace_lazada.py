"""Lazada adapter: signing, region routing, parsing and failure handling.

The signature tests recompute the HMAC by hand from Lazada's documented base
string rather than asserting against a value this code produced. A test that
compares the implementation to itself passes just as happily when the base
string is wrong, and a wrong base string is the single most likely defect here:
Lazada answers every mis-signed request with a generic error that names nothing.

Two Lazada-specific traps have tests of their own, because both fail silently
rather than loudly: `code` arriving as the string "0" (comparing it to the
integer 0 makes every success look like a failure), and `access_token` being
part of the signed material (Shopee and TikTok both exclude it).
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import settings
from app.services.marketplace import lazada as lz
from app.services.marketplace.base import (
    AdapterError,
    AuthorisationError,
    Cred,
    RateLimitedError,
)

APP_KEY = "141401"
APP_SECRET = "lazada-test-app-secret"
SELLER_ID = "800123456"


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    monkeypatch.setattr(settings, "LAZADA_APP_KEY", APP_KEY)
    monkeypatch.setattr(settings, "LAZADA_APP_SECRET", APP_SECRET)
    yield


def _cred(**over) -> Cred:
    base = {
        "external_shop_id": SELLER_ID,
        "access_token": "ACCESS_TOKEN_123",
        "region": "VN",
        "extra": {},
    }
    base.update(over)
    return Cred(**base)


def _expected_sign(path: str, params: dict) -> str:
    """Lazada's documented base string, assembled independently of the adapter."""
    signable = {k: v for k, v in params.items() if k != "sign"}
    joined = "".join(f"{k}{signable[k]}" for k in sorted(signable))
    base = f"{path}{joined}"
    return hmac.new(
        APP_SECRET.encode(), base.encode(), hashlib.sha256
    ).hexdigest().upper()


# --------------------------------------------------------------------------- #
# signing
# --------------------------------------------------------------------------- #

def test_signature_matches_hand_computation():
    params = {"app_key": APP_KEY, "timestamp": 1_754_000_000_000, "limit": 50}
    assert lz.adapter._sign(lz.PATH_ORDERS, params) == _expected_sign(
        lz.PATH_ORDERS, params
    )


def test_signature_is_upper_case():
    """Lazada rejects a lower-case digest, and the failure names nothing."""
    params = {"app_key": APP_KEY, "timestamp": 1_754_000_000_000}
    got = lz.adapter._sign(lz.PATH_ORDERS, params)
    assert got == got.upper()
    assert got != got.lower()


def test_signature_includes_access_token():
    """Unlike Shopee and TikTok, Lazada signs the access token."""
    without = {"app_key": APP_KEY, "timestamp": 1_754_000_000_000}
    with_token = {**without, "access_token": "ACCESS_TOKEN_123"}
    assert lz.adapter._sign(lz.PATH_ORDERS, with_token) != lz.adapter._sign(
        lz.PATH_ORDERS, without
    )


def test_signature_excludes_only_sign():
    params = {"app_key": APP_KEY, "timestamp": 1_754_000_000_000}
    assert lz.adapter._sign(lz.PATH_ORDERS, {**params, "sign": "stale"}) == (
        lz.adapter._sign(lz.PATH_ORDERS, params)
    )


def test_signature_sorts_params_regardless_of_insertion_order():
    a = {"app_key": APP_KEY, "limit": 50, "timestamp": 1_754_000_000_000}
    b = {"timestamp": 1_754_000_000_000, "app_key": APP_KEY, "limit": 50}
    assert lz.adapter._sign(lz.PATH_ORDERS, a) == lz.adapter._sign(lz.PATH_ORDERS, b)


def test_signature_changes_with_path():
    params = {"app_key": APP_KEY, "timestamp": 1_754_000_000_000}
    assert lz.adapter._sign(lz.PATH_ORDERS, params) != lz.adapter._sign(
        lz.PATH_PRODUCTS, params
    )


def test_signature_is_not_wrapped_in_the_secret():
    """Guards against pasting TikTok's algorithm in by mistake."""
    params = {"app_key": APP_KEY, "timestamp": 1_754_000_000_000}
    joined = "".join(f"{k}{params[k]}" for k in sorted(params))
    wrapped = f"{APP_SECRET}{lz.PATH_ORDERS}{joined}{APP_SECRET}"
    tiktok_style = hmac.new(
        APP_SECRET.encode(), wrapped.encode(), hashlib.sha256
    ).hexdigest().upper()
    assert lz.adapter._sign(lz.PATH_ORDERS, params) != tiktok_style


# --------------------------------------------------------------------------- #
# configuration and region routing
# --------------------------------------------------------------------------- #

def test_unconfigured_adapter_names_the_missing_settings(monkeypatch):
    monkeypatch.setattr(settings, "LAZADA_APP_KEY", None)
    monkeypatch.setattr(settings, "LAZADA_APP_SECRET", None)
    assert not lz.adapter.configured()
    assert lz.adapter.missing_settings() == ["LAZADA_APP_KEY", "LAZADA_APP_SECRET"]
    with pytest.raises(AdapterError) as exc:
        lz.adapter.authorize_url("s", "https://example.test/cb")
    assert "LAZADA_APP_KEY" in str(exc.value)


@pytest.mark.parametrize("region,expected", [
    ("VN", "https://api.lazada.vn/rest"),
    ("vn", "https://api.lazada.vn/rest"),
    ("SG", "https://api.lazada.sg/rest"),
    ("TH", "https://api.lazada.co.th/rest"),
])
def test_region_selects_the_right_host(region, expected):
    assert lz.adapter._host(region) == expected


def test_unknown_region_falls_back_to_vietnam():
    """A wrong host rejects a valid token, so the fallback must be deliberate."""
    assert lz.adapter._host("XX") == lz.REGION_HOSTS["VN"]
    assert lz.adapter._host("") == lz.REGION_HOSTS["VN"]


def test_authorize_url_carries_state_on_the_redirect():
    url = lz.adapter.authorize_url("state123", "https://example.test/cb")
    assert url.startswith(lz.AUTHORIZE_URL)
    assert "state123" in url
    assert f"client_id={APP_KEY}" in url


# --------------------------------------------------------------------------- #
# token exchange
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_exchange_code_reads_seller_id_and_country(monkeypatch):
    """One round trip: Lazada's token response already names the seller."""
    async def fake_auth(path, extra):
        assert path == lz.PATH_TOKEN
        assert extra["code"] == "AUTH_CODE_1"
        return {
            "code": "0",
            "access_token": "AT", "refresh_token": "RT",
            "expires_in": 604_800, "refresh_expires_in": 2_592_000,
            "account": "seller@example.test",
            "country": "vn",
            "country_user_info": [
                {"country": "vn", "seller_id": SELLER_ID, "short_code": "VNXYZ"},
            ],
        }

    monkeypatch.setattr(lz.adapter, "_auth_call", fake_auth)
    bundle = await lz.adapter.exchange_code("AUTH_CODE_1", {})

    assert bundle.access_token == "AT"
    assert bundle.extra["shop_id"] == SELLER_ID
    assert bundle.extra["region"] == "VN"
    assert bundle.expires_at > datetime.now(UTC)
    assert bundle.refresh_expires_at > bundle.expires_at


@pytest.mark.asyncio
async def test_refresh_keeps_shop_identity_when_response_omits_it(monkeypatch):
    """A routine token rotation must not lose which shop the link is for."""
    async def fake_auth(path, extra):
        assert path == lz.PATH_REFRESH
        return {"code": "0", "access_token": "AT2", "refresh_token": "RT2"}

    monkeypatch.setattr(lz.adapter, "_auth_call", fake_auth)
    bundle = await lz.adapter.refresh(
        "RT", _cred(extra={"shop_id": SELLER_ID, "region": "VN"})
    )
    assert bundle.access_token == "AT2"
    assert bundle.extra["shop_id"] == SELLER_ID


@pytest.mark.asyncio
async def test_missing_access_token_is_reported(monkeypatch):
    async def fake_auth(path, extra):
        return {"code": "0"}

    monkeypatch.setattr(lz.adapter, "_auth_call", fake_auth)
    with pytest.raises(AdapterError) as exc:
        await lz.adapter.exchange_code("CODE", {})
    assert "access_token" in str(exc.value)


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_orders_are_normalised_with_line_items(monkeypatch):
    async def fake_get(path, cred, query):
        if path == lz.PATH_ORDERS:
            assert query["sort_by"] == "created_at"
            return {"code": "0", "data": {"countTotal": 1, "orders": [{
                "order_id": 900001,
                "statuses": ["delivered"],
                "price": "459000",
                "payment_method": "COD",
                "created_at": "2026-08-01 10:00:00 +0700",
                "updated_at": "2026-08-02 10:00:00 +0700",
                "customer_id": "CUST_9",
            }]}}
        assert path == lz.PATH_ORDER_ITEMS
        assert query["order_ids"] == "[900001]"
        return {"code": "0", "data": [{
            "order_id": 900001,
            "order_items": [
                {"product_id": "P1", "sku_id": "S1", "sku": "AO-M",
                 "name": "Áo khoác", "paid_price": "229500"},
                {"product_id": "P1", "sku_id": "S1", "sku": "AO-M",
                 "name": "Áo khoác", "paid_price": "229500"},
            ],
        }]}

    monkeypatch.setattr(lz.adapter, "_get", fake_get)
    page = await lz.adapter.fetch_orders(
        _cred(), datetime.now(UTC) - timedelta(days=30), None
    )

    order = page.items[0]
    assert order.external_order_id == "900001"
    assert order.status == "delivered"
    assert order.total_amount == 459_000
    assert order.placed_at is not None and order.placed_at.tzinfo is not None
    assert len(order.items) == 2
    assert order.items[0].unit_price == 229_500


@pytest.mark.asyncio
async def test_statuses_list_is_read_not_stringified(monkeypatch):
    """Lazada reports a list because lines can differ; a naive str() breaks it."""
    async def fake_get(path, cred, query):
        if path == lz.PATH_ORDERS:
            return {"code": "0", "data": {"orders": [
                {"order_id": 1, "statuses": ["shipped", "delivered"], "price": "0"},
            ]}}
        return {"code": "0", "data": []}

    monkeypatch.setattr(lz.adapter, "_get", fake_get)
    page = await lz.adapter.fetch_orders(_cred(), datetime.now(UTC), None)
    assert page.items[0].status == "shipped"
    assert page.items[0].raw_status == "shipped"


@pytest.mark.asyncio
async def test_unknown_order_status_is_flagged_not_guessed(monkeypatch):
    async def fake_get(path, cred, query):
        if path == lz.PATH_ORDERS:
            return {"code": "0", "data": {"orders": [
                {"order_id": 1, "statuses": ["some_new_status"], "price": "0"},
            ]}}
        return {"code": "0", "data": []}

    monkeypatch.setattr(lz.adapter, "_get", fake_get)
    page = await lz.adapter.fetch_orders(_cred(), datetime.now(UTC), None)
    assert page.items[0].status == "unknown"
    assert page.items[0].raw_status == "some_new_status"


def test_every_mapped_status_is_canonical():
    from app.models.marketplace import ORDER_STATUSES

    for canonical in lz.ORDER_STATUS_MAP.values():
        assert canonical in ORDER_STATUSES


@pytest.mark.asyncio
async def test_order_items_failure_does_not_lose_the_orders(monkeypatch):
    """Totals and dates still drive planning; losing the page would be worse."""
    async def fake_get(path, cred, query):
        if path == lz.PATH_ORDERS:
            return {"code": "0", "data": {"orders": [
                {"order_id": 5, "statuses": ["delivered"], "price": "100000"},
            ]}}
        raise AdapterError("items endpoint down")

    monkeypatch.setattr(lz.adapter, "_get", fake_get)
    page = await lz.adapter.fetch_orders(_cred(), datetime.now(UTC), None)
    assert len(page.items) == 1
    assert page.items[0].total_amount == 100_000
    assert page.items[0].items == []


@pytest.mark.asyncio
async def test_products_flatten_to_one_row_per_sku(monkeypatch):
    async def fake_get(path, cred, query):
        return {"code": "0", "data": {"total_products": 1, "products": [{
            "item_id": 700100,
            "status": "active",
            "primary_category": "Thời trang nữ",
            "attributes": {"name": "Áo len nữ", "brand": "NoBrand"},
            "images": ["https://img.test/a.jpg"],
            "skus": [
                {"SkuId": "S1", "SellerSku": "LEN-S", "price": "259000",
                 "special_price": "199000", "quantity": 12},
                {"SkuId": "S2", "SellerSku": "LEN-M", "price": "259000",
                 "quantity": 4},
            ],
        }]}}

    monkeypatch.setattr(lz.adapter, "_get", fake_get)
    page = await lz.adapter.fetch_products(_cred(), None)

    assert len(page.items) == 2
    first, second = page.items
    assert first.external_product_id == "700100"
    assert first.external_sku_id == "S1"
    # A promotion is running: the live price is special_price, the list price
    # stays in original_price so margin maths uses the right one.
    assert first.price == 199_000
    assert first.original_price == 259_000
    # No promotion on the second variant, so both are the list price.
    assert second.price == 259_000
    assert first.category_path == "Thời trang nữ"


@pytest.mark.asyncio
async def test_product_without_variants_still_yields_a_row(monkeypatch):
    async def fake_get(path, cred, query):
        return {"code": "0", "data": {"products": [
            {"item_id": 1, "attributes": {"name": "Set quà"}, "skus": []},
        ]}}

    monkeypatch.setattr(lz.adapter, "_get", fake_get)
    page = await lz.adapter.fetch_products(_cred(), None)
    assert len(page.items) == 1
    assert page.items[0].external_sku_id == ""


@pytest.mark.asyncio
async def test_inventory_comes_from_the_product_payload(monkeypatch):
    async def fake_get(path, cred, query):
        return {"code": "0", "data": {"products": [{
            "item_id": 5, "attributes": {"name": "Quần jean"},
            "skus": [
                {"SkuId": "S9", "quantity": 12, "occupied_quantity": 2,
                 "warehouse_code": "W1"},
            ],
        }]}}

    monkeypatch.setattr(lz.adapter, "_get", fake_get)
    page = await lz.adapter.fetch_inventory(_cred(), None)
    assert page.items[0].quantity_available == 12
    assert page.items[0].quantity_reserved == 2
    assert page.items[0].warehouse_id == "W1"


# --------------------------------------------------------------------------- #
# paging
# --------------------------------------------------------------------------- #

def test_short_page_ends_pagination():
    assert lz._next_offset(0, 10, 100) is None


def test_full_page_continues_from_the_new_offset():
    assert lz._next_offset(0, lz.PAGE_SIZE, 500) == str(lz.PAGE_SIZE)


def test_pagination_stops_once_total_is_reached():
    assert lz._next_offset(50, lz.PAGE_SIZE, 100) is None


def test_empty_page_ends_pagination():
    assert lz._next_offset(0, 0, 100) is None


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


def test_string_zero_code_is_treated_as_success():
    """The trap: `code` is "0", not 0. An int comparison fails every success."""
    assert lz.adapter._unwrap(_Resp({"code": "0", "data": {"ok": 1}}), "/x")["data"] == {
        "ok": 1
    }


def test_non_zero_code_raises_even_on_http_200():
    with pytest.raises(AdapterError) as exc:
        lz.adapter._unwrap(_Resp({"code": "E501", "message": "bad param"}), "/x")
    assert "E501" in str(exc.value)


def test_dead_auth_code_raises_authorisation_error():
    """Distinct from a transient failure: retrying will never help."""
    with pytest.raises(AuthorisationError):
        lz.adapter._unwrap(
            _Resp({"code": "IllegalAccessToken", "message": "expired"}), "/x"
        )


def test_rate_limit_carries_retry_after():
    with pytest.raises(RateLimitedError) as exc:
        lz.adapter._unwrap(_Resp({}, status=429), "/x")
    assert exc.value.retry_after_s > 0


def test_non_json_body_is_reported_clearly():
    with pytest.raises(AdapterError) as exc:
        lz.adapter._unwrap(_Resp(ValueError("nope"), status=502), "/x")
    assert "JSON" in str(exc.value)


# --------------------------------------------------------------------------- #
# helpers and registration
# --------------------------------------------------------------------------- #

def test_naive_timestamps_are_made_aware():
    """A naive value stored in a tz-aware column silently becomes UTC."""
    parsed = lz._parse_dt("2026-08-01 10:00:00")
    assert parsed is not None and parsed.tzinfo is not None


def test_offset_timestamps_are_converted_to_utc():
    parsed = lz._parse_dt("2026-08-01T10:00:00+07:00")
    assert parsed is not None
    assert parsed.hour == 3  # 10:00 +07:00 is 03:00 UTC


def test_adapter_is_registered_under_its_platform():
    from app.services.marketplace import get_adapter

    assert get_adapter("lazada") is lz.adapter


def test_adapter_satisfies_the_protocol():
    from app.services.marketplace.base import MarketplaceAdapter

    assert isinstance(lz.adapter, MarketplaceAdapter)
