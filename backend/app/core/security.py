"""Security helpers: password hashing, JWT issuance & verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings
from app.core.exceptions import ErrorCode, UnauthorizedError


def hash_password(plain: str) -> str:
    """Hash a UTF-8 password with bcrypt without passlib's broken probe.

    passlib 1.7.4 is incompatible with bcrypt 5.x: its backend self-test sends
    a password longer than bcrypt's 72-byte limit, so hashing *any* password
    raises before the real input is processed. Calling bcrypt directly keeps
    the same ``$2b$`` hash format and remains compatible with existing rows.
    """
    encoded = plain.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        encoded = plain.encode("utf-8")
        if len(encoded) > 72:
            return False
        return bcrypt.checkpw(encoded, hashed.encode("ascii"))
    except (TypeError, ValueError):
        return False


def create_access_token(
    subject: str | int,
    *,
    expires_minutes: int | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise UnauthorizedError(
            "Invalid or expired token.", code=ErrorCode.TOKEN_EXPIRED
        ) from exc
    except JWTError as exc:
        raise UnauthorizedError("Invalid token.") from exc
