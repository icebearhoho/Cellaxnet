"""Seller Autopilot API contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class SimulateRequest(BaseModel):
    option_id: str = Field(min_length=1, max_length=80)


class DecideRequest(SimulateRequest):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=300)
