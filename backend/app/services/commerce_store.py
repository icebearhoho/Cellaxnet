"""Rich single-shop commerce dataset — the shared knowledge base the upgraded
intelligence features and the Copilot reason over.

Deterministically generated (seeded) so tests/CI reproduce exactly. Models the
entities the Đề bài care about and their relationships: Product ↔ SKU ↔ Brand ↔
Category ↔ Promotion ↔ Content/Creator ↔ Sales, plus competitors. This is demo
data standing in for a real seller DB; every field is plausible for a
small/medium Vietnamese fashion & cosmetics shop.
"""

from __future__ import annotations

import random
import unicodedata
from functools import lru_cache

Category = str  # "Thời trang" | "Mỹ phẩm" | "Phụ kiện"

# --- fabricated review pool (deterministic per product, not real customers) - #
_REVIEWER_NAMES = [
    "Minh Anh", "Thảo Vy", "Quốc Huy", "Ngọc Hân", "Bảo Trâm", "Hoàng Nam",
    "Thu Hiền", "Đức Anh", "Lan Chi", "Gia Bảo", "Phương Linh", "Minh Khang",
    "Tuấn Kiệt", "Hải Yến", "Kim Ngân", "Anh Tuấn", "Diệu Linh", "Xuân Mai",
]
_REVIEW_TEMPLATES_5 = [
    "Chất lượng {name} rất tốt, đúng như hình, đóng gói kỹ. Sẽ ủng hộ shop tiếp!",
    "{Name} đẹp hơn mình tưởng, {brand} làm ăn uy tín. Giao nhanh, đóng gói cẩn thận.",
    "Dùng được một thời gian rồi vẫn ưng, chất lượng xứng giá tiền. Recommend mọi người!",
    "Mua tặng người nhà cũng thích lắm, chắc sẽ quay lại mua thêm ở shop.",
    "Y như hình, chất liệu ưng ý, {brand} đóng gói kỹ, giao đúng hẹn.",
]
_REVIEW_TEMPLATES_4 = [
    "Sản phẩm ổn, đúng mô tả, chỉ hơi lâu giao (4-5 ngày) so với dự kiến.",
    "Chất lượng tốt so với giá tiền, trừ 1 sao vì hộp hơi móp lúc nhận hàng.",
    "Ưng chất liệu {name}, đóng gói cẩn thận, sẽ cân nhắc mua thêm màu khác.",
    "Nhìn chung ok, giao hàng đúng hẹn, {name} dùng tạm hài lòng.",
]
_REVIEW_TEMPLATES_3 = [
    "Tạm được, không xuất sắc như review khác nói nhưng cũng không tệ.",
    "Giao hơi trễ, sản phẩm {name} ổn, không có gì nổi bật.",
    "Chất lượng ở mức trung bình, đúng giá tiền thôi.",
]


def _gen_reviews(rng: random.Random, product_name: str, brand: str) -> list[dict]:
    n = rng.randint(5, 8)
    reviews: list[dict] = []
    for _ in range(n):
        # Skew toward positive, matching a shop with mostly-good ratings.
        r = rng.choices([5, 4, 3], weights=[0.55, 0.32, 0.13])[0]
        tmpl = rng.choice({5: _REVIEW_TEMPLATES_5, 4: _REVIEW_TEMPLATES_4, 3: _REVIEW_TEMPLATES_3}[r])
        text = tmpl.format(name=product_name.lower(), Name=product_name, brand=brand)
        reviews.append({
            "author": rng.choice(_REVIEWER_NAMES),
            "rating": r,
            "text": text,
            "days_ago": rng.randint(1, 120),
        })
    reviews.sort(key=lambda r: r["days_ago"])
    return reviews

# --- brand + product vocabulary per category ------------------------------- #
_CATALOG_SPEC: dict[str, dict] = {
    "Thời trang": {
        "brands": ["Local Brand HANOI", "Coolmate", "YODY", "Routine", "IVY moda"],
        "items": [
            ("Áo thun cotton unisex", (180000, 320000), {"chất liệu": "cotton", "form": "rộng"}, "tshirt"),
            ("Áo khoác dù 2 lớp", (280000, 520000), {"chất liệu": "dù", "form": "regular"}, "bomber_jacket"),
            ("Váy hoa nhí midi", (250000, 450000), {"chất liệu": "voan", "form": "xoè"}, "skirt"),
            ("Đầm suông linen", (320000, 600000), {"chất liệu": "linen", "form": "suông"}, "dress"),
            ("Quần jean ống rộng", (300000, 550000), {"chất liệu": "denim", "form": "ống rộng"}, "jeans"),
            ("Áo sơ mi oversize", (220000, 400000), {"chất liệu": "kate", "form": "oversize"}, "dress_shirt"),
            ("Hoodie nỉ bông", (280000, 480000), {"chất liệu": "nỉ", "form": "rộng"}, "hoodie"),
            ("Chân váy tennis", (190000, 350000), {"chất liệu": "poly", "form": "chữ A"}, "skirt"),
            ("Áo croptop gân", (120000, 250000), {"chất liệu": "gân", "form": "ôm"}, "crop_top"),
            ("Quần short kaki", (160000, 300000), {"chất liệu": "kaki", "form": "regular"}, "shorts"),
            ("Blazer linen", (450000, 850000), {"chất liệu": "linen", "form": "regular"}, "blazer"),
            ("Áo len tăm cổ lọ", (260000, 460000), {"chất liệu": "len", "form": "ôm"}, "knitwear"),
        ],
    },
    "Mỹ phẩm": {
        "brands": ["NUDESTIX", "Bourjois", "Laneige", "Cocoon", "The Ordinary"],
        "items": [
            ("Serum Vitamin C 15%", (280000, 720000), {"loại": "serum", "công dụng": "sáng da"}, "serum"),
            ("Kem chống nắng SPF50", (150000, 320000), {"loại": "kcn", "spf": "50"}, "sunscreen"),
            ("Son tint lì velvet", (150000, 350000), {"loại": "son", "finish": "lì"}, "lipstick"),
            ("Toner cấp ẩm", (120000, 300000), {"loại": "toner", "công dụng": "cấp ẩm"}, "toner"),
            ("Sữa rửa mặt dịu nhẹ", (110000, 260000), {"loại": "srm", "da": "nhạy cảm"}, "face_wash"),
            ("Mặt nạ ngủ dưỡng ẩm", (180000, 650000), {"loại": "mask", "công dụng": "cấp ẩm"}, "face_mask"),
            ("Cushion che khuyết điểm", (250000, 550000), {"loại": "cushion", "finish": "căng bóng"}, "foundation"),
            ("Retinol 0.5%", (220000, 480000), {"loại": "serum", "công dụng": "chống lão hoá"}, "serum"),
            ("Tẩy trang dầu", (130000, 290000), {"loại": "tẩy trang", "da": "mọi loại"}, "face_wash"),
            ("Kem dưỡng ẩm ban đêm", (200000, 450000), {"loại": "kem dưỡng", "công dụng": "phục hồi"}, "moisturizer"),
            ("Mascara làm dày mi", (160000, 330000), {"loại": "mascara", "finish": "dày"}, "mascara"),
            ("Niacinamide 10%", (180000, 360000), {"loại": "serum", "công dụng": "giảm thâm"}, "serum"),
        ],
    },
    "Phụ kiện": {
        "brands": ["Bag House", "Casio VN", "Local Studio", "Daily Basics", "OEM"],
        "items": [
            ("Túi tote canvas", (120000, 250000), {"chất liệu": "canvas", "kiểu": "tote"}, "tote_bag"),
            ("Túi đeo chéo da PU", (200000, 420000), {"chất liệu": "da pu", "kiểu": "đeo chéo"}, "crossbody_bag"),
            ("Balo laptop chống nước", (300000, 650000), {"chất liệu": "poly", "kiểu": "balo"}, "backpack"),
            ("Ví cầm tay nữ", (150000, 320000), {"chất liệu": "da pu", "kiểu": "ví"}, "wallet"),
            ("Kính mát gọng vuông", (180000, 400000), {"kiểu": "vuông", "chống": "uv400"}, "sunglasses"),
            ("Đồng hồ dây da", (350000, 900000), {"dây": "da", "kiểu": "classic"}, "watch"),
            ("Mũ bucket", (90000, 200000), {"chất liệu": "kaki", "kiểu": "bucket"}, "cap"),
            ("Thắt lưng da", (160000, 350000), {"chất liệu": "da", "kiểu": "bản nhỏ"}, "belt"),
            ("Vòng tay charm", (80000, 180000), {"chất liệu": "thép", "kiểu": "charm"}, "bracelet"),
            ("Tất cổ trung combo", (60000, 130000), {"chất liệu": "cotton", "kiểu": "combo"}, "leggings"),
            ("Khăn lụa vuông", (110000, 240000), {"chất liệu": "lụa", "kiểu": "vuông"}, "scarf"),
            ("Kẹp tóc ngọc trai", (50000, 120000), {"chất liệu": "ngọc trai", "kiểu": "kẹp"}, "earrings"),
        ],
    },
}

_TRENDS = ["rising", "rising", "stable", "stable", "cooling", "cooling"]
_STOCK_STATUS = ["ok", "ok", "ok", "low", "out"]

# --- synthetic per-session timestamps (for real dwell/cart-abandon metrics) - #
# S4 ends on "cart" with nothing after it and is meant to demo an abandoned
# cart ("nguy cơ rời") — checked a long while later, on purpose. Every other
# session (including S1, which also ends on "cart" but means "just added,
# about to buy") is checked moments after it ends, so it reads as fresh.
_ABANDON_CHECK_DELAY_OVERRIDES = {"S4": 20 * 60}
_DEFAULT_CHECK_DELAY_SECONDS = 8


def _attach_synthetic_timestamps(rng: random.Random, sessions: list[dict]) -> None:
    base = 1_700_000_000_000  # arbitrary anchor; only deltas/gaps matter
    for s in sessions:
        t = base
        for e in s["events"]:
            e["ts"] = t
            t += rng.randint(3_000, 45_000)
        last_ts = s["events"][-1]["ts"] if s["events"] else base
        delay = _ABANDON_CHECK_DELAY_OVERRIDES.get(s["id"], _DEFAULT_CHECK_DELAY_SECONDS)
        s["checked_at_ms"] = last_ts + delay * 1000
        base += 3_600_000  # stagger sessions well apart from each other


def _slug(name: str, i: int) -> str:
    # Fold Vietnamese diacritics to ASCII so product ids are clean URL segments.
    lowered = name.lower().replace("đ", "d")  # đ doesn't NFD-decompose; map first
    ascii_name = unicodedata.normalize("NFD", lowered).encode("ascii", "ignore").decode("ascii")
    base = "".join(c for c in ascii_name.replace(" ", "-") if c.isalnum() or c == "-")
    return f"{base[:24]}-{i:02d}"


@lru_cache(maxsize=1)
def _build() -> dict:
    rng = random.Random(303)
    products: list[dict] = []
    pid = 0
    for category, spec in _CATALOG_SPEC.items():
        brands = spec["brands"]
        for name, (lo, hi), attrs, type_key in spec["items"]:
            pid += 1
            price = int(round(rng.randint(lo, hi) / 1000) * 1000)
            cost = int(round(price * rng.uniform(0.42, 0.6) / 1000) * 1000)
            brand = brands[pid % len(brands)]
            trend = _TRENDS[pid % len(_TRENDS)]
            stock_status = _STOCK_STATUS[pid % len(_STOCK_STATUS)]
            daily = rng.randint(4, 30)
            stock = 0 if stock_status == "out" else (
                daily * rng.randint(1, 3) if stock_status == "low" else daily * rng.randint(15, 60))

            # 4-period sales history shaped by trend.
            base = rng.randint(120, 600)
            step = {"rising": 1.18, "cooling": 0.82, "stable": 1.0}[trend]
            noise = lambda: rng.uniform(0.95, 1.05)  # noqa: E731
            hist = []
            v = float(base)
            for _ in range(4):
                hist.append(int(v * noise()))
                v *= step
            sales_prev, sales_curr = hist[-2], hist[-1]

            # Optional promotion with a measured lift.
            promo = None
            if pid % 3 == 0:
                promo = {
                    "name": rng.choice(["Sale 11.11 -20%", "Freeship + tặng quà", "Flash sale cuối tuần -15%"]),
                    "discount_pct": rng.choice([10, 15, 20]),
                    "lift_pct": rng.choice([8, 14, 22, 30]),
                }

            # 1-2 competitors around our price.
            n_comp = 1 + (pid % 2)
            competitors = []
            comp_names = ["Shop " + c for c in ("BestPrice", "Mega Store", "Outlet VN", "Deal Zone")]
            for c in range(n_comp):
                cp = int(round(price * rng.uniform(0.82, 1.15) / 1000) * 1000)
                competitors.append({
                    "name": comp_names[(pid + c) % len(comp_names)],
                    "price_vnd": cp,
                    "discount_pct": rng.choice([0, 0, 10, 20, 30]),
                })

            products.append({
                "id": _slug(name, pid),
                "sku": f"{category[:2].upper()}-{brand[:3].upper()}-{pid:03d}",
                "name": name,
                "brand": brand,
                "category": category,
                "type_key": type_key,
                "price_vnd": price,
                "cost_vnd": cost,
                "stock": stock,
                "stock_status": stock_status,
                "daily_sales": daily,
                "trend": trend,
                "attributes": attrs,
                "sales_history": hist,
                "sales_prev": sales_prev,
                "sales_curr": sales_curr,
                "promotion": promo,
                "competitors": competitors,
                "reviews_list": _gen_reviews(rng, name, brand),
            })

    # --- creators with multi-campaign history (for Đề 4 correlation) --------- #
    creators: list[dict] = []
    creator_defs = [
        ("Hà Linh Official", "Mỹ phẩm", "livestream", 0.9),
        ("Chan Review", "Mỹ phẩm", "video", 0.6),
        ("Mai Beauty", "Mỹ phẩm", "post", 0.4),
        ("Trang Fashionista", "Thời trang", "video", 0.8),
        ("Style By An", "Thời trang", "livestream", 0.85),
        ("Daily Look", "Phụ kiện", "post", 0.5),
    ]
    for name, cat, ctype, eff in creator_defs:
        campaigns = []
        for m in (9, 10, 11, 12):
            views = rng.randint(20000, 180000)
            # sales correlate with views * creator efficiency (+noise) → measurable correlation
            sales = int(views * eff * rng.uniform(180, 320))
            campaigns.append({
                "month": m, "content_type": ctype, "views": views,
                "engagements": int(views * rng.uniform(0.03, 0.12)),
                "attributed_sales_vnd": sales,
            })
        creators.append({"creator": name, "category": cat, "campaigns": campaigns})

    # --- past operating decisions (for Đề 5) -------------------------------- #
    decisions = [
        {"kind": "ad", "description": "Đẩy ads TikTok tháng 12", "metric": "ROAS", "value": 5.1, "month": 12, "category": "Mỹ phẩm"},
        {"kind": "promo", "description": "Sale 11.11 giảm 20%", "metric": "ROAS", "value": 4.2, "month": 11, "category": "Thời trang"},
        {"kind": "promo", "description": "Freeship toàn shop", "metric": "sales_lift_pct", "value": 18.0, "month": 6, "category": "Phụ kiện"},
        {"kind": "price", "description": "Giảm giá 10% ngày thường", "metric": "ROAS", "value": 2.3, "month": None, "category": "Mỹ phẩm"},
        {"kind": "ad", "description": "Ads Facebook mùa hè", "metric": "ROAS", "value": 3.4, "month": 6, "category": "Thời trang"},
        {"kind": "inventory", "description": "Nhập sỉ áo khoác trước mùa lạnh", "metric": "sell_through_pct", "value": 92.0, "month": 10, "category": "Thời trang"},
        {"kind": "promo", "description": "Combo mua 2 tặng 1", "metric": "sales_lift_pct", "value": 25.0, "month": 8, "category": "Mỹ phẩm"},
        {"kind": "ad", "description": "Ads Tết Nguyên đán", "metric": "ROAS", "value": 4.8, "month": 1, "category": "Phụ kiện"},
    ]

    # --- customers (for churn / return / regret auto-analysis) -------------- #
    cust_names = [
        "Nguyễn Thu Hà", "Trần Minh Quân", "Lê Bảo Ngọc", "Phạm Gia Huy",
        "Vũ Khánh Linh", "Đặng Tuấn Anh", "Bùi Phương Thảo", "Hoàng Nhật Nam",
        "Đỗ Mỹ Duyên", "Ngô Thành Đạt",
    ]
    trends3 = ["declining", "stable", "growing"]
    customers: list[dict] = []
    for i, nm in enumerate(cust_names):
        prod = products[(i * 3) % len(products)]
        recency = rng.choice([5, 12, 20, 40, 65, 95, 140])
        customers.append({
            "id": f"C{i + 1:03d}",
            "name": nm,
            "recency_days": recency,
            "frequency_orders": rng.randint(1, 14),
            "sessions_last_month": rng.randint(0, 12),
            "cart_abandon_rate": round(rng.uniform(0.1, 0.9), 2),
            "trend": trends3[i % 3],
            "last_product": prod["name"],
            "last_category": prod["category"],
            "last_order_value_vnd": prod["price_vnd"],
            # signals for return/regret on the last order
            "reviews_read": rng.randint(0, 8),
            "is_first_purchase": recency > 90 or rng.random() < 0.3,
            "has_size_variants": prod["category"] == "Thời trang",
            "decision_seconds": rng.choice([15, 30, 45, 90, 180]),
            "revisits_before_buy": rng.randint(0, 4),
            "purchase_hour": rng.choice([9, 13, 18, 22, 23, 1]),
            "discount_driven": rng.random() < 0.5,
        })

    # --- pre-built demo shopping sessions (replayable, not live recordings) - #
    sessions: list[dict] = [
        {"id": "S1", "label": "Săn serum — vừa thêm giỏ", "video_url": "/demo-videos/s1-serum.webm", "events": [
            {"type": "search", "category": "Mỹ phẩm", "query": "serum vitamin c"},
            {"type": "click", "category": "Mỹ phẩm"}, {"type": "view", "category": "Mỹ phẩm"},
            {"type": "review", "category": "Mỹ phẩm"},
            {"type": "livestream", "category": "Mỹ phẩm"}, {"type": "cart", "category": "Mỹ phẩm"}]},
        {"id": "S2", "label": "Lướt thời trang — chưa quyết", "video_url": "/demo-videos/s2-vay.webm", "events": [
            {"type": "search", "category": "Thời trang", "query": "váy hoa nhí"},
            {"type": "view", "category": "Thời trang"}, {"type": "view", "category": "Thời trang"},
            {"type": "click", "category": "Thời trang"}]},
        {"id": "S3", "label": "Mua xong — có thể cross-sell", "video_url": "/demo-videos/s3-cushion-purchase.webm", "events": [
            {"type": "view", "category": "Mỹ phẩm"}, {"type": "review", "category": "Mỹ phẩm"},
            {"type": "cart", "category": "Mỹ phẩm"}, {"type": "purchase", "category": "Mỹ phẩm"}]},
        {"id": "S4", "label": "Bỏ giỏ giữa chừng — nguy cơ rời", "video_url": "/demo-videos/s4-tui-abandon.webm", "events": [
            {"type": "click", "category": "Phụ kiện"}, {"type": "view", "category": "Phụ kiện"},
            {"type": "cart", "category": "Phụ kiện"}]},
        {"id": "S5", "label": "Fan livestream thời trang", "video_url": "/demo-videos/s5-ao-len-hoodie.webm", "events": [
            {"type": "livestream", "category": "Thời trang"}, {"type": "livestream", "category": "Thời trang"},
            {"type": "cart", "category": "Thời trang"}, {"type": "view", "category": "Thời trang"}]},
        {"id": "S6", "label": "Phụ kiện — chốt đơn nhanh", "video_url": "/demo-videos/s6-tui-cheo-purchase.webm", "events": [
            {"type": "search", "category": "Phụ kiện", "query": "túi đeo chéo"},
            {"type": "view", "category": "Phụ kiện"}, {"type": "review", "category": "Phụ kiện"},
            {"type": "cart", "category": "Phụ kiện"}, {"type": "purchase", "category": "Phụ kiện"}]},
        {"id": "S7", "label": "So sánh giá mỹ phẩm — chưa chốt", "video_url": "/demo-videos/s7-kem-chong-nang-compare.webm", "events": [
            {"type": "search", "category": "Mỹ phẩm", "query": "kem chống nắng"},
            {"type": "click", "category": "Mỹ phẩm"}, {"type": "view", "category": "Mỹ phẩm"},
            {"type": "click", "category": "Mỹ phẩm"}, {"type": "view", "category": "Mỹ phẩm"}]},
        {"id": "S8", "label": "Khách mới ghé qua — nguy cơ rời ngay", "video_url": "/demo-videos/s8-blazer-bounce.webm", "events": [
            {"type": "view", "category": "Thời trang"}]},
        {"id": "S9", "label": "Gom nhiều món rồi thanh toán", "video_url": "/demo-videos/s9-multi-item-checkout.webm", "events": [
            {"type": "view", "category": "Thời trang"}, {"type": "cart", "category": "Thời trang"},
            {"type": "view", "category": "Thời trang"}, {"type": "cart", "category": "Thời trang"},
            {"type": "purchase", "category": "Thời trang"}]},
        {"id": "S10", "label": "Khách cũ quay lại xem thêm", "video_url": "/demo-videos/s10-vong-tay-then-dong-ho.webm", "events": [
            {"type": "purchase", "category": "Phụ kiện"}, {"type": "search", "category": "Phụ kiện", "query": "đồng hồ"},
            {"type": "view", "category": "Phụ kiện"}]},
    ]

    _attach_synthetic_timestamps(rng, sessions)

    return {"products": products, "creators": creators, "decisions": decisions,
            "customers": customers, "sessions": sessions}


# --------------------------------------------------------------------------- #
# Public query helpers
# --------------------------------------------------------------------------- #
def all_products() -> list[dict]:
    return _build()["products"]


def all_creators() -> list[dict]:
    return _build()["creators"]


def all_decisions() -> list[dict]:
    return _build()["decisions"]


def all_customers() -> list[dict]:
    return _build()["customers"]


def all_sessions() -> list[dict]:
    return _build()["sessions"]


def categories() -> list[str]:
    return list(_CATALOG_SPEC.keys())


def brands(category: str | None = None) -> list[str]:
    seen: list[str] = []
    for p in all_products():
        if (category is None or p["category"] == category) and p["brand"] not in seen:
            seen.append(p["brand"])
    return seen


def find_product(query: str | None) -> dict | None:
    if not query:
        return None
    low = query.lower()
    for p in all_products():
        if p["id"] == low or p["sku"].lower() == low:
            return p
    for p in all_products():
        if p["name"].lower() in low or low in p["name"].lower():
            return p
    best, best_score = None, 0
    for p in all_products():
        toks = set(p["name"].lower().split())
        score = len(toks & set(low.split()))
        if score > best_score:
            best, best_score = p, score
    return best


def products_by_category(category: str) -> list[dict]:
    return [p for p in all_products() if p["category"] == category]


def products_by_brand(brand: str) -> list[dict]:
    return [p for p in all_products() if p["brand"] == brand]


def similar_products(product: dict, k: int = 5) -> list[dict]:
    """Rank other products by relatedness: same concrete type (dominant) + same
    category + same brand + price proximity + shared attribute values.

    ``type_key`` (e.g. "dress", "serum") is the strongest signal — it's what
    stops a dress being "similar to" a jacket just because both are Thời
    trang at a similar price."""
    scored: list[tuple[float, dict]] = []
    p_attrs = set(product.get("attributes", {}).values())
    for q in all_products():
        if q["id"] == product["id"]:
            continue
        score = 0.0
        if q["type_key"] == product["type_key"]:
            score += 4.0
        if q["category"] == product["category"]:
            score += 2.0
        if q["brand"] == product["brand"]:
            score += 1.5
        price_ratio = min(q["price_vnd"], product["price_vnd"]) / max(q["price_vnd"], product["price_vnd"])
        score += price_ratio  # 0..1, closer price → higher
        score += 0.5 * len(p_attrs & set(q.get("attributes", {}).values()))
        scored.append((score, q))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [q for _, q in scored[:k]]


def creators_for_category(category: str) -> list[dict]:
    return [c for c in all_creators() if c["category"] == category]
