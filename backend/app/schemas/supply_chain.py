"""#16 Supply Chain Disruption Early Warning.

Demo disruption events are curated from real, recurring Vietnam logistics
patterns (2024-2026 typhoon season impacts — Yagi, Kalmaegi, Yinxing, Toraji —
and southern port congestion at Cát Lái), not a live news/weather feed. A
production version would replace DISRUPTION_EVENTS with NewsAPI + OpenWeather
per the original AI_BRIEF.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Region = Literal["Miền Bắc", "Miền Trung", "Miền Nam"]


class SupplyChainRequest(BaseModel):
    region: Region
    category: Literal["Thời trang", "Mỹ phẩm", "Phụ kiện"]


class DisruptionAlert(BaseModel):
    title: str
    region: Region
    severity: Literal["low", "medium", "high"]
    estimated_delay_days: int
    contingency: str


class NewsArticle(BaseModel):
    title: str
    source: str
    link: str
    date: str
    snippet: str


class SupplyChainResponse(BaseModel):
    alerts: list[DisruptionAlert]
    overall_risk: Literal["low", "medium", "high"]
    summary: str
    news: list[NewsArticle] = []
    news_live: bool = False
    scenario_mode: bool = True
