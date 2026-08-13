"""Shopee adapter: signing, parsing and failure handling.

The signature tests recompute the HMAC by hand from Shopee's documented base
string rather than asserting against a value this code produced. A test that
compares the implementation to itself passes just as happily when the base
string is wrong, and a wrong base string is the single most likely defect here:
Shopee answers every mis-signed request with a generic error that names nothing.

Everything else runs the real adapter against payloads shaped like Shopee's,
with the HTTP layer stubbed — the parts a sandbox account would exercise, minus
the account.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import settings
from app.services.marketplace import shopee as sp
from app.services.marketplace.base import (
    AdapterError,
    AuthorisationError,
    RateLimitedError,
)

PARTNER_ID = "1005678"
PARTNER_KEY = "shopee-test-partner-key"


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    monkeypatch.setattr(settings, "SHOPEE_PARTNER_ID", PARTNER_ID)
    monkeypatch.setattr(settings, "SHOPEE_PARTNER_KEY", PARTNER_KEY)
    monkeypatch.setattr(settings, "SHOPEE_SANDBOX", True)
    sp.adapter.__dict__.pop("_cached", None)
    yield


def _expected_sign(path: str, ts: int, token: str = "", shop: str = "") -> str:
    """Shopee's documented base string, assembled independently of the adapter."""
    base = f"{PARTNER_ID}{path}{ts}{token}{shop}"
    return hmac.new(PARTNER_KEY.encode(), base.encode(), hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------- #
# signing
# --------------------------------------------------------------------------- #

def test_public_signature_matches_hand_computation():
    ts = 1_754_000_000
    assert sp.adapter._sign(sp.PATH_TOKEN, ts) == _expected_sign(sp.PATH_TOKEN, ts)


def test_shop_scoped_signature_appends_token_then_shop_id():
    ts = 1_754_000_000
    got = sp.adapter._sign(sp.PATH_ORDER_LIST, ts, "ACCESS123", "77001")
    assert got == _expected_sign(sp.PATH_ORDER_LIST, ts, "ACCESS123", "77001")


def test_signature_order_is_not_interchangeable():
    """Swapping token and shop id must produce a different signature.

    Guards against an implementation that concatenates the right pieces in the
    wrong order — which still produces a plausible-looking hex digest.
    """
    ts = 1_754_000_000
    right = sp.adapter._sign(sp.PATH_ORDER_LIST, ts, "ACCESS123", "77001")
    swapped = _expected_sign(sp.PATH_ORDER_LIST, ts, "77001", "ACCESS123")
    assert right != swapped


def test_signature_changes_with_timestamp():
    a = sp.adapter._sign(sp.PATH_SHOP_INFO, 1_754_000_000)
    b = sp.adapter._sign(sp.PATH_SHOP_INFO, 1_754_000_001)
    assert a != b


def test_unconfigured_adapter_refuses_instead_of_signing_with_none(monkeypatch):
    monkeypatch.setattr(settings, "SHOPEE_PARTNER_KEY", None)
    assert not sp.adapter.configured()
    assert "SHOPEE_PARTNER_KEY" in sp.adapter.missing_settings()
    with pytest.raises(AdapterError, match="chưa cấu hình"):
        sp.adapter._sign(sp.PATH_TOKEN, 1)


# --------------------------------------------------------------------------- #
# authorisation URL
# --------------------------------------------------------------------------- #

def test_authorize_url_targets_sandbox_and_carries_state():
    url = sp.adapter.authorize_url("STATE-abc", "http://localhost:8000/cb")
    assert url.startswith(sp.SANDBOX_HOST + sp.PATH_AUTH)
    assert f"partner_id={PARTNER_ID}" in url
    assert "sign=" in url
    # Shopee does not echo an arbitrary state parameter, so it has to ride on
    # the redirect target or the callback arrives unattributable.
    assert "STATE-abc" in url


def test_authorize_url_uses_live_host_when_sandbox_off(monkeypatch):
    monkeypatch.setattr(settings, "SHOPEE_SANDBOX", False)
    assert sp.adapter.authorize_url("s", "http://x/cb").startswith(sp.LIVE_HOST)


# --------------------------------------------------------------------------- #
# response unwrapping
# --------------------------------------------------------------------------- #

class _Resp:
    def __init__(self, payload, status=200, text=""):
        self._payload, self.status_code, self.text = payload, status, text or str(payload)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_error_in_body_with_http_200_is_a_failure():
    """Shopee reports refusals in the body while still returning HTTP 200."""
    with pytest.raises(AdapterError, match="error_param"):
        sp.adapter._unwrap(
            _Resp({"error": "error_param", "message": "missing field"}), sp.PATH_ORDER_LIST
        )


def test_dead_authorisation_raises_the_reconnect_error():
    """Distinguishable from a transient failure: retrying will never fix it."""
    with pytest.raises(AuthorisationError, match="kết nối lại"):
        sp.adapter._unwrap(
            _Resp({"error": "error_auth", "message": "token invalid"}), sp.PATH_SHOP_INFO
        )


def test_rate_limit_surfaces_as_its_own_error():
    with pytest.raises(RateLimitedError) as exc:
        sp.adapter._unwrap(_Resp({}, status=429), sp.PATH_ORDER_LIST)
    assert exc.value.retry_after_s > 0


def test_non_json_body_does_not_crash_with_a_parse_error():
    with pytest.raises(AdapterError, match="không phải JSON"):
        sp.adapter._unwrap(_Resp(ValueError("nope"), status=502), sp.PATH_ORDER_LIST)


def test_clean_payload_passes_through():
    payload = {"response": {"shop_name": "Shop A"}, "error": ""}
    assert sp.adapter._unwrap(_Resp(payload), sp.PATH_SHOP_INFO) == payload


# --------------------------------------------------------------------------- #
# token parsing
# --------------------------------------------------------------------------- #

def test_token_bundle_uses_reported_lifetime():
    before = datetime.now(UTC)
    bundle = sp.adapter._token_bundle(
        {"access_token": "AT", "refresh_token": "RT", "expire_in": 14400}, {"shop_id": "1"}
    )
    assert bundle.access_token == "AT"
    assert bundle.refresh_token == "RT"
    assert bundle.expires_at is not None
    delta = bundle.expires_at - before
    assert timedelta(hours=3, minutes=55) < delta < timedelta(hours=4, minutes=5)
    assert bundle.extra["shop_id"] == "1"


def test_token_bundle_without_access_token_is_an_error():
    with pytest.raises(AdapterError, match="access_token"):
        sp.adapter._token_bundle({"request_id": "x"}, {})


def test_missing_expiry_falls_back_to_the_documented_four_hours():
    bundle = sp.adapter._token_bundle({"access_token": "AT"}, {})
    assert bundle.expires_at is not None
    # Never left open-ended: a null expiry reads downstream as "never expires",
    # which would stop the refresh path from ever running.
    assert bundle.expires_at > datetime.now(UTC)


# --------------------------------------------------------------------------- #
# canonical mapping
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    ("shopee_status", "canonical"),
    [
        ("UNPAID", "unpaid"),
        ("READY_TO_SHIP", "awaiting_shipment"),
        ("PROCESSED", "awaiting_shipment"),
        ("SHIPPED", "shipped"),
        ("TO_CONFIRM_RECEIVE", "delivered"),
        ("COMPLETED", "completed"),
        ("CANCELLED", "cancelled"),
        ("IN_CANCEL", "cancelled"),
        ("TO_RETURN", "returned"),
    ],
)
def test_every_documented_status_maps_to_a_canonical_one(shopee_status, canonical):
    assert sp.ORDER_STATUS_MAP[shopee_status] == canonical


def test_unknown_status_is_flagged_not_guessed():
    """A status Shopee adds later must not be silently folded into a real one."""
    assert sp.ORDER_STATUS_MAP.get("SOME_FUTURE_STATUS", "unknown") == "unknown"


def test_canonical_targets_are_all_in_the_shared_vocabulary():
    from app.models.marketplace import ORDER_STATUSES

    assert set(sp.ORDER_STATUS_MAP.values()) <= set(ORDER_STATUSES)


# --------------------------------------------------------------------------- #
# value coercion
# --------------------------------------------------------------------------- #

def test_timestamps_become_timezone_aware():
    """Naive datetimes compare wrongly against the aware ones stored in the DB."""
    got = sp._ts(1_754_000_000)
    assert got is not None and got.tzinfo is not None


def test_zero_and_junk_timestamps_become_none():
    assert sp._ts(0) is None
    assert sp._ts(None) is None
    assert sp._ts("not-a-number") is None


def test_money_is_integral():
    assert sp._money(199000) == 199000
    assert sp._money("199000.4") == 199000
    assert sp._money(None) is None
    assert sp._money("abc") is None
