"""Encryption for stored marketplace credentials, and buyer pseudonymisation.

Two separate jobs, both about not holding data in a form that hurts if the
database leaks:

* Tokens are encrypted *reversibly* — the app has to send them back to the
  marketplace, so it must be able to read them again.
* Buyer identity is hashed *irreversibly* — the app only ever needs to answer
  "is this the same buyer as before", never "who is this", so the plaintext is
  not worth keeping.

Refusing to run without a key is deliberate. The tempting fallback — store
plaintext when no key is configured — produces a system that looks encrypted in
review and is not in production.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialCryptoError(RuntimeError):
    """Encryption is unavailable or a stored value could not be decrypted."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise CredentialCryptoError(
            "CREDENTIAL_ENCRYPTION_KEY chưa cấu hình — không thể lưu token an toàn. "
            "Sinh khoá bằng: python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise CredentialCryptoError(
            "CREDENTIAL_ENCRYPTION_KEY không hợp lệ — phải là khoá Fernet base64 32 byte."
        ) from exc


def available() -> bool:
    """Whether credentials can be stored at all, for the UI to report."""
    try:
        _fernet()
    except CredentialCryptoError:
        return False
    return True


def encrypt(value: str | None) -> bytes | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode("utf-8"))


def decrypt(blob: bytes | None) -> str | None:
    if blob is None:
        return None
    try:
        return _fernet().decrypt(blob).decode("utf-8")
    except InvalidToken as exc:
        # Almost always a rotated or mismatched key. Say so, because the
        # alternative reading — "the token is corrupt" — sends people looking
        # in the wrong place.
        raise CredentialCryptoError(
            "Không giải mã được credential — nhiều khả năng CREDENTIAL_ENCRYPTION_KEY "
            "đã bị đổi. Cần kết nối lại shop."
        ) from exc


def encrypt_json(payload: dict[str, Any] | None) -> bytes | None:
    if not payload:
        return None
    return encrypt(json.dumps(payload, sort_keys=True, default=str))


def decrypt_json(blob: bytes | None) -> dict[str, Any]:
    raw = decrypt(blob)
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def buyer_ref(platform: str, external_buyer_id: str | None) -> str | None:
    """One-way reference for a buyer.

    Salted and scoped per platform so the same id on two marketplaces does not
    collide, and so a rainbow table over a small id space does not reverse it.
    """
    if not external_buyer_id:
        return None
    msg = f"{platform}:{external_buyer_id}".encode()
    return hmac.new(
        settings.BUYER_REF_SALT.encode("utf-8"), msg, hashlib.sha256
    ).hexdigest()[:64]
