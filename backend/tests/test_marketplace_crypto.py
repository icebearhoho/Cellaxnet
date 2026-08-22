"""Credential encryption and buyer pseudonymisation.

Covers the two properties the storage design depends on: tokens must come back
out intact, and buyer identity must not.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.services.marketplace import crypto


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setattr(
        settings, "CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    crypto._fernet.cache_clear()
    yield
    crypto._fernet.cache_clear()


def test_round_trip_returns_the_original():
    blob = crypto.encrypt("shopee-access-token")
    assert blob is not None
    assert crypto.decrypt(blob) == "shopee-access-token"


def test_ciphertext_does_not_contain_the_plaintext():
    blob = crypto.encrypt("SECRET-TOKEN-VALUE")
    assert b"SECRET-TOKEN-VALUE" not in blob


def test_same_value_encrypts_differently_each_time():
    """Fernet is randomised; identical tokens must not produce identical rows."""
    assert crypto.encrypt("same") != crypto.encrypt("same")


def test_none_passes_through_both_ways():
    assert crypto.encrypt(None) is None
    assert crypto.decrypt(None) is None


def test_json_round_trip_for_marketplace_extras():
    extra = {"shop_cipher": "abc==", "region": "VN"}
    assert crypto.decrypt_json(crypto.encrypt_json(extra)) == extra


def test_empty_extras_store_nothing():
    assert crypto.encrypt_json({}) is None
    assert crypto.decrypt_json(None) == {}


def test_wrong_key_reports_a_key_problem_not_a_corrupt_value(monkeypatch):
    blob = crypto.encrypt("token")
    monkeypatch.setattr(
        settings, "CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode()
    )
    crypto._fernet.cache_clear()
    with pytest.raises(crypto.CredentialCryptoError, match="ENCRYPTION_KEY"):
        crypto.decrypt(blob)


def test_missing_key_refuses_rather_than_storing_plaintext(monkeypatch):
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", None)
    crypto._fernet.cache_clear()
    assert crypto.available() is False
    with pytest.raises(crypto.CredentialCryptoError):
        crypto.encrypt("token")


def test_invalid_key_is_rejected_at_use(monkeypatch):
    monkeypatch.setattr(settings, "CREDENTIAL_ENCRYPTION_KEY", "not-a-fernet-key")
    crypto._fernet.cache_clear()
    with pytest.raises(crypto.CredentialCryptoError, match="không hợp lệ"):
        crypto.encrypt("token")


# --------------------------------------------------------------------------- #
# buyer reference
# --------------------------------------------------------------------------- #

def test_buyer_ref_is_stable_so_repeat_buyers_are_recognisable():
    assert crypto.buyer_ref("shopee", "u-123") == crypto.buyer_ref("shopee", "u-123")


def test_buyer_ref_is_scoped_per_platform():
    """The same id on two marketplaces is two different people."""
    assert crypto.buyer_ref("shopee", "u-1") != crypto.buyer_ref("lazada", "u-1")


def test_buyer_ref_does_not_contain_the_source_id():
    ref = crypto.buyer_ref("shopee", "0912345678")
    assert ref is not None
    assert "0912345678" not in ref


def test_absent_buyer_yields_nothing_to_store():
    assert crypto.buyer_ref("shopee", None) is None
    assert crypto.buyer_ref("shopee", "") is None
