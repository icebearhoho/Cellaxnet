"""Derived facts for the coherent Mây House demo shop.

Every number in this module is calculated from ``commerce_store`` entities so
dashboard cards, alerts and seller coaching cannot drift into separate stories.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app.services import commerce_store as store


def _delta(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return round((current - previous) / previous * 100, 1)


def _recognized(order: dict) -> bool:
    return order["status"] not in {"cancelled", "returned", "pending"}


def _kpis() -> list[dict]:
    days = store.all_daily_metrics()
    today, yesterday = days[-1], days[-2]
    specs = [
        ("revenue", "Doanh thu hôm nay", "revenue_vnd", "₫"),
        ("orders", "Đơn hàng hôm nay", "orders", None),
        ("conversion", "Tỷ lệ chuyển đổi", "conversion_rate", "%"),
        ("aov", "Giá trị đơn trung bình", "aov_vnd", "₫"),
    ]
    result = []
    for key, label, field, unit in specs:
        result.append({
            "id": key,
            "label": label,
            "value": today[field],
            "unit": unit,
            "delta": _delta(float(today[field]), float(yesterday[field])),
            "spark": [row[field] for row in days[-12:]],
        })
    return result


def _hourly_series() -> list[dict]:
    """Average hourly recognized GMV over the latest 14 days, in VND millions."""
    recent_dates = {row["date"] for row in store.all_daily_metrics()[-14:]}
    buckets: dict[int, dict[str, int]] = defaultdict(
        lambda: {"Thời trang": 0, "Mỹ phẩm": 0, "Phụ kiện": 0}
    )
    for order in store.all_demo_orders():
        if order["created_at"][:10] not in recent_dates or not _recognized(order):
            continue
        hour = datetime.fromisoformat(order["created_at"]).hour
        for line in order["items"]:
            buckets[hour][line["category"]] += line["line_total_vnd"]
    return [
        {
            "t": f"{hour:02d}:00",
            "fashion": round(buckets[hour]["Thời trang"] / 14 / 1_000_000, 2),
            "beauty": round(buckets[hour]["Mỹ phẩm"] / 14 / 1_000_000, 2),
            "accessories": round(buckets[hour]["Phụ kiện"] / 14 / 1_000_000, 2),
        }
        for hour in range(24)
    ]


def _alerts() -> list[dict]:
    products = store.all_products()
    customers = store.all_customers()
    alerts: list[dict] = []
    low_stock = sorted(
        (p for p in products if p["stock_status"] in {"low", "out"}),
        key=lambda p: (p["stock"] > 0, p["stock"] / max(p["daily_sales"], 1)),
    )[:3]
    for index, product in enumerate(low_stock, start=1):
        runway = round(product["stock"] / max(product["daily_sales"], 1), 1)
        alerts.append({
            "id": f"INV-{index:03d}",
            "feature": "sentiment-alert",
            "featureLabel": "Tồn kho",
            "region": store.shop_profile()["warehouse"],
            "severity": "critical" if product["stock"] == 0 else "warning",
            "status": "open",
            "startedAt": store.shop_profile()["data_as_of"][:16].replace("T", " "),
            "message": f"{product['name']} còn {product['stock']} sản phẩm (~{runway} ngày bán)",
            "product_id": product["id"],
        })

    at_risk = [
        customer for customer in customers
        if customer["recency_days"] >= 60 or customer["cart_abandon_rate"] >= 0.7
    ]
    alerts.append({
        "id": "RISK-001",
        "feature": "customer-risk",
        "featureLabel": "Rủi ro khách hàng",
        "region": "Toàn quốc",
        "severity": "warning",
        "status": "monitoring",
        "startedAt": store.shop_profile()["data_as_of"][:16].replace("T", " "),
        "message": f"{len(at_risk)} khách có recency cao hoặc bỏ giỏ ≥70% cần win-back",
    })

    negative_reviews = sum(
        review["rating"] <= 3
        for product in products
        for review in product["reviews_list"]
        if review["days_ago"] <= 30
    )
    alerts.append({
        "id": "REV-001",
        "feature": "review-intelligence",
        "featureLabel": "Đánh giá khách hàng",
        "region": "—",
        "severity": "info",
        "status": "monitoring",
        "startedAt": store.shop_profile()["data_as_of"][:16].replace("T", " "),
        "message": f"{negative_reviews} đánh giá ≤3 sao trong 30 ngày cần phân tích chủ đề",
    })
    return alerts


def _province_nodes() -> list[dict]:
    coords = {
        "Hà Nội": ("north", 21.0285, 105.8542),
        "TP.HCM": ("south", 10.8231, 106.6297),
        "Đà Nẵng": ("central", 16.0544, 108.2022),
        "Cần Thơ": ("south", 10.0452, 105.7469),
        "Bình Dương": ("south", 11.3254, 106.4770),
        "Đồng Nai": ("south", 10.9574, 106.8426),
    }
    orders = store.all_demo_orders()
    counts: dict[str, int] = defaultdict(int)
    problems: dict[str, int] = defaultdict(int)
    for order in orders:
        counts[order["province"]] += 1
        if order["status"] in {"cancelled", "returned"}:
            problems[order["province"]] += 1
    result = []
    for index, (province, (region, lat, lng)) in enumerate(coords.items(), start=1):
        issue_rate = problems[province] / max(counts[province], 1)
        load = round(min(0.95, 0.2 + issue_rate * 3), 2)
        status = "critical" if issue_rate >= 0.18 else ("warn" if issue_rate >= 0.1 else "ok")
        result.append({
            "id": f"p-{index}", "name": province, "region": region,
            "lat": lat, "lng": lng, "status": status, "load": load,
            "orders": counts[province],
        })
    return result


def summary() -> dict:
    products = store.all_products()
    orders = store.all_demo_orders()
    recognized = [o for o in orders if _recognized(o)]
    return {
        "shop": store.shop_profile(),
        "counts": {
            "products": len(products),
            "customers": len(store.all_customers()),
            "orders": len(orders),
            "recognized_revenue_vnd": sum(o["total_vnd"] for o in recognized),
            "creators": len(store.all_creators()),
            "reviews": sum(len(p["reviews_list"]) for p in products),
        },
        "kpis": _kpis(),
        "timeseries": _hourly_series(),
        "alerts": _alerts(),
        "provinces": _province_nodes(),
        "demo_mode": True,
        "provenance": "commerce_store: products ↔ customers ↔ orders ↔ reviews ↔ creators",
    }
