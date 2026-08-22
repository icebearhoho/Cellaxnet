"""Smart Restock Planner — central config (paths, brands, keywords, tunables).

Feature: with a given budget, decide WHICH products to restock and HOW MANY
units, using three real signals:
  1. SEASON      — seasonal index learned from 5 years of Google Trends history
  2. MONEY       — the seller's own budget + real cost/price per SKU
  3. TREND       — how deeply the big brands are discounting *right now*

Data policy: every number that describes the market comes from a live API
(SerpApi → Google Trends / Google Shopping). Nothing about the market is
invented. The seller's budget and margins are the seller's own inputs.
"""

from __future__ import annotations

from pathlib import Path

FEATURE_DIR = Path(__file__).resolve().parent
REPO_ROOT = FEATURE_DIR.parent
OUTPUT_DIR = FEATURE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Cached API pulls (so a demo never depends on network or SerpApi quota).
TRENDS_JSON = OUTPUT_DIR / "trends_history.json"
BRAND_SALE_JSON = OUTPUT_DIR / "brand_sale.json"
CHANNEL_MARKET_JSON = OUTPUT_DIR / "channel_market.json"
DEMO_DATA_JSON = OUTPUT_DIR / "demo_data.json"

# The shop's categories — mirrors backend/app/services/commerce_store.py.
CATEGORIES = ["Thời trang", "Mỹ phẩm", "Phụ kiện"]

# Big brands a small VN seller actually competes against. Chosen from the
# brands already in the shop catalog, keeping only ones that are real companies
# (so Google Trends/Shopping return genuine data), plus the global players whose
# sale campaigns visibly move the market.
BIG_BRANDS: dict[str, list[str]] = {
    "Thời trang": ["Uniqlo", "Zara", "H&M", "Coolmate", "YODY"],
    "Mỹ phẩm": ["Laneige", "The Ordinary", "Innisfree", "Cocoon", "Bourjois"],
    "Phụ kiện": ["Casio", "Charles Keith", "Vascara"],
}

# Seasonality is measured per category through these search terms. Vietnamese
# on purpose: the seller's market is VN, and #08 already proved these terms
# return real Google Trends series.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Thời trang": ["thời trang", "áo khoác", "váy"],
    "Mỹ phẩm": ["mỹ phẩm", "kem chống nắng", "son môi"],
    "Phụ kiện": ["túi xách", "đồng hồ", "kính mát"],
}

# --- tunables ------------------------------------------------------------- #

# Google Trends window. 5 years gives 4-5 observations per calendar month,
# enough to average out one-off spikes when building a seasonal index.
TRENDS_WINDOW = "today 5-y"

# How far ahead we plan stock for.
PLANNING_HORIZON_DAYS = 30

# Big-brand discount depth (0-1) is converted to a demand multiplier:
#   multiplier = 1 - COMPETITION_SENSITIVITY * pressure
# 0.5 means "if the big brands averaged a 100% discount, our demand would halve"
# — deliberately conservative; real observed depths sit around 0.2-0.4.
COMPETITION_SENSITIVITY = 0.5

# A seasonal index is clamped to this band so one noisy month cannot dominate.
SEASON_INDEX_MIN = 0.6
SEASON_INDEX_MAX = 1.6

# Diversification cap: no single SKU may absorb more than this share of the
# budget on the first allocation pass. Pure ROI-greedy would sink the whole
# budget into the one highest-margin item — mathematically optimal, terrible
# inventory advice. Leftover money is topped up in a second, uncapped pass.
MAX_SKU_BUDGET_SHARE = 0.25

# SerpApi
SERPAPI_ENDPOINT = "https://serpapi.com/search"
ENV_FILE = FEATURE_DIR / ".env"


def serpapi_key() -> str | None:
    """Read SERPAPI_KEY from this feature's .env, falling back to the process env."""
    import os

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("SERPAPI_KEY="):
                return line.split("=", 1)[1].strip() or None
    return os.getenv("SERPAPI_KEY")
