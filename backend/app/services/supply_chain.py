"""#16 Supply Chain Disruption Early Warning service.

Curated demo events grounded in real recurring Vietnam logistics disruption
patterns (typhoon season impacts on central/northern ports, southern port
congestion) — see module docstring in schemas/supply_chain.py for sourcing.
"""

from __future__ import annotations

from typing import Literal, cast

from app.schemas.supply_chain import (
    DisruptionAlert,
    NewsArticle,
    SupplyChainRequest,
    SupplyChainResponse,
)
from app.services.supply_news import fetch_supply_news

DISRUPTION_EVENTS: list[dict] = [
    {
        "title": "Mùa bão nhiệt đới (7–11) tác động cảng miền Trung — theo mô hình bão Yagi, Kalmaegi gần đây",
        "region": "Miền Trung",
        "severity": "high",
        "estimated_delay_days": 5,
        "contingency": "Chuyển hàng qua cảng Đà Nẵng làm điểm trung chuyển thay thế; dự trù thêm 5-7 ngày cho đơn hàng miền Trung trong mùa bão.",
    },
    {
        "title": "Ùn tắc cảng Cát Lái — phí lưu container (demurrage) tăng ~30%",
        "region": "Miền Nam",
        "severity": "medium",
        "estimated_delay_days": 2,
        "contingency": "Ưu tiên xử lý chứng từ sớm; cân nhắc tuyến phụ qua cảng Cái Mép để giảm thời gian chờ.",
    },
    {
        "title": "Nhu cầu vận chuyển cao điểm cuối năm (11/11, 12/12, Tết)",
        "region": "Miền Bắc",
        "severity": "medium",
        "estimated_delay_days": 3,
        "contingency": "Đặt slot vận chuyển sớm 1-2 tuần; thông báo khách hàng thời gian giao hàng có thể kéo dài.",
    },
    {
        "title": "Ảnh hưởng gián tiếp từ căng thẳng vận tải biển quốc tế",
        "region": "Miền Nam",
        "severity": "low",
        "estimated_delay_days": 1,
        "contingency": "Theo dõi lịch tàu quốc tế; ưu tiên nguồn hàng nội địa nếu có thể.",
    },
]

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2}


async def check_supply_chain(req: SupplyChainRequest) -> SupplyChainResponse:
    matched = [e for e in DISRUPTION_EVENTS if e["region"] == req.region]
    overall = max((e["severity"] for e in matched), key=lambda s: _SEVERITY_RANK[s], default="low")

    # Real Google News feed (SerpApi) — best-effort; empty if key/quota absent.
    articles = await fetch_supply_news(req.region)

    if matched:
        max_delay = max(e["estimated_delay_days"] for e in matched)
        summary = (f"{len(matched)} kịch bản rủi ro tham chiếu cho {req.region}; độ trễ "
                  f"giả định tối đa {max_delay} ngày với hàng {req.category}. "
                  "Đây không phải xác nhận rằng sự cố đang diễn ra.")
    else:
        summary = f"Không có kịch bản tham chiếu nào được cấu hình cho {req.region}."
    if articles:
        summary += f" Đã tải {len(articles)} tin liên quan để người bán đối chiếu trước khi hành động."

    return SupplyChainResponse(
        alerts=[DisruptionAlert(**e) for e in matched],
        overall_risk=cast(Literal["low", "medium", "high"], overall), summary=summary,
        news=[NewsArticle(**a) for a in articles], news_live=bool(articles),
        scenario_mode=True,
    )
