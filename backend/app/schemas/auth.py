"""Auth request/response shapes.

Email is a regex-validated ``str`` rather than pydantic's ``EmailStr`` on
purpose: ``EmailStr`` needs the ``email-validator`` package, which isn't a
dependency here, and it would raise at import time if missing. The regex is
deliberately permissive — it rejects obvious typos, not exotic-but-valid
addresses.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Role = Literal["admin", "seller", "buyer"]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# bcrypt silently ignores anything past 72 bytes, so refuse longer passwords
# outright instead of accepting one the user can't fully reproduce.
_PASSWORD_MAX = 72
_PASSWORD_MIN = 8


def _normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValueError("Email không hợp lệ.")
    return value


def _validate_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > _PASSWORD_MAX:
        raise ValueError("Mật khẩu không được vượt quá 72 byte UTF-8.")
    return value


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=_PASSWORD_MIN, max_length=_PASSWORD_MAX)
    name: str | None = Field(default=None, max_length=80)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _normalize_email(v)

    @field_validator("password")
    @classmethod
    def _password_bytes(cls, v: str) -> str:
        return _validate_password_bytes(v)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    # No min_length here — a short stored password from before a rule change
    # should still be able to log in; only registration enforces strength.
    password: str = Field(min_length=1, max_length=_PASSWORD_MAX)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _normalize_email(v)

    @field_validator("password")
    @classmethod
    def _password_bytes(cls, v: str) -> str:
        return _validate_password_bytes(v)


class UserOut(BaseModel):
    id: int
    email: str
    name: str | None
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
