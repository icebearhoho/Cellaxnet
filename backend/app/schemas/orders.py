"""Checkout + order shapes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

OrderStatus = Literal["pending", "paid", "shipped", "cancelled"]


class CheckoutItem(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    qty: int = Field(ge=1, le=99)


class CheckoutRequest(BaseModel):
    # Prices are NOT accepted from the client — the server re-reads them from
    # the catalogue so a tampered cart can't change what's charged.
    items: list[CheckoutItem] = Field(min_length=1, max_length=50)
    customer_name: str = Field(min_length=1, max_length=80)
    email: str | None = Field(default=None, max_length=255)

    @field_validator("customer_name")
    @classmethod
    def normalize_customer_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("customer_name must not be blank")
        return value


class OrderItemOut(BaseModel):
    product_id: str
    product_name: str
    brand: str
    unit_price_vnd: int
    qty: int
    line_total_vnd: int


class OrderOut(BaseModel):
    order_no: str
    status: OrderStatus
    customer_name: str
    email: str | None
    total_vnd: int
    created_at: str
    items: list[OrderItemOut]


class StatusUpdateRequest(BaseModel):
    status: OrderStatus
