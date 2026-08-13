"""API types for seller accounts and marketplace shop connections.

No schema in this file has a token field, and none should ever gain one. The
tokens live in a table these responses are not built from, so a leak would take
a deliberate act rather than an oversight — but the rule is written down because
"add the token so the frontend can debug" is a request that comes up.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.marketplace import PLATFORMS


class SellerAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    business_type: str = Field(default="individual")
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=32)

    @field_validator("business_type")
    @classmethod
    def _known_type(cls, v: str) -> str:
        if v not in {"individual", "company"}:
            raise ValueError("business_type phải là 'individual' hoặc 'company'")
        return v


class SellerAccountOut(BaseModel):
    id: int
    name: str
    business_type: str
    contact_email: str | None = None
    contact_phone: str | None = None
    status: str
    shop_count: int = 0
    created_at: datetime | None = None


class ShopConnectionOut(BaseModel):
    """One row of the connected-shops screen."""

    id: int
    seller_account_id: int
    platform: str
    platform_label: str
    external_shop_id: str
    shop_name: str | None = None
    region: str
    status: str
    status_label: str
    authorized_at: datetime | None = None
    last_synced_at: datetime | None = None
    last_error: str | None = None
    # Counts of what has been pulled, so the screen can show that a connection
    # is live rather than merely authorised.
    products: int = 0
    orders: int = 0


class PlatformOut(BaseModel):
    """What the UI needs to decide whether to offer a Connect button."""

    platform: str
    display_name: str
    configured: bool
    missing_settings: list[str] = Field(default_factory=list)
    console_url: str
    # Implemented but not configured is a different situation from not built
    # yet, and the UI should not conflate them.
    implemented: bool = True


class BeginAuthRequest(BaseModel):
    seller_account_id: int
    platform: str

    @field_validator("platform")
    @classmethod
    def _known_platform(cls, v: str) -> str:
        if v not in PLATFORMS:
            raise ValueError(f"platform phải thuộc {PLATFORMS}")
        return v


class BeginAuthResponse(BaseModel):
    authorize_url: str
    expires_in_seconds: int


class SyncResponse(BaseModel):
    shop_connection_id: int
    products: int
    orders: int
    errors: list[str] = Field(default_factory=list)
