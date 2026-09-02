"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Local development keeps shared secrets/Compose config at repo root,
        # while backend/.env overrides backend-specific values. Absolute paths
        # make this work whether uvicorn starts from root or backend/.
        env_file=(_REPO_ROOT / ".env", _BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "AREA-303 API"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    # Avoid the generic DEBUG environment variable: package managers and build
    # tools commonly set it to non-boolean values such as "release".
    DEBUG: bool = Field(default=True, validation_alias="AREA303_DEBUG")
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # --- Postgres ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "area303"
    POSTGRES_PASSWORD: str = "area303"
    POSTGRES_DB: str = "area303"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    # Managed Postgres (Neon, RDS, ...) requires TLS; local Docker Compose does not.
    POSTGRES_SSL: bool = False

    # --- BTC Shopee market data (read-only, external) ---
    # The competition organisers host an observed Shopee dataset. It is a
    # market *reference*, never Cellaxnet's own store: read-only, its own
    # engine, and every consumer must work when it is unset or unreachable.
    BTC_DATABASE_URL: str | None = None
    BTC_SCHEMA: str = "data_shopee"
    #: Which Shopee marketplace the app prices against. The dataset spans more
    #: than one, and each is a separate market at its own price level — an
    #: Indonesian median is not a cheaper Vietnamese one. Every reference query
    #: filters on this, so widening it needs a deliberate change here.
    BTC_MARKET: str = "vn"
    #: Shopee stores a sentinel price (999,999,999) on some rows; anything
    #: outside this window is treated as missing rather than as a real price.
    BTC_PRICE_MIN_VND: int = 1_000
    BTC_PRICE_MAX_VND: int = 100_000_000
    #: Below this many products a percentile says more about the sample than
    #: about the market, so the caller falls back instead.
    BTC_MIN_SAMPLE: int = 20
    BTC_QUERY_TIMEOUT_S: float = 8.0

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    # Managed Redis (Upstash, ...) requires TLS (rediss://); local Docker Compose does not.
    REDIS_TLS: bool = False

    # --- Auth ---
    JWT_SECRET: str = "change-me-in-production"
    # Fernet key for third-party credentials we hold for a user (their connected
    # Shopee session). Separate from JWT_SECRET on purpose: rotating one
    # shouldn't force rotating the other, and either leaking shouldn't expose
    # both. Unset means the connect feature refuses to store anything rather
    # than falling back to plaintext. Generate with:
    #   python -c "from app.core.crypto import generate_key; print(generate_key())"
    CREDENTIAL_ENCRYPTION_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None

    # --- Misc ---
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # --- GenAI ---
    # Demo mode: when true, all LLM/RAG calls return pre-generated
    # fixtures from `app/services/demo_data.py`. Mandatory for the
    # AREA-303 build so demos never break on quota / network issues.
    DEMO_MODE: bool = True

    # LLM provider — Gemini is primary per the project AI_BRIEFs,
    # OpenAI is the secondary fallback.
    LLM_PROVIDER: Literal["gemini", "openai", "ollama", "mock"] = "mock"
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-pro"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    # OpenAI-compatible base URL. Point at Groq / OpenRouter to run open-source
    # models (Llama 3.3 70B, DeepSeek, Qwen…) via their free API instead of OpenAI.
    OPENAI_BASE_URL: str = "https://api.openai.com"
    # SerpApi — real Google News for Supply Chain early warning.
    SERPAPI_KEY: str | None = None

    # --- Marketplace orders via KiotViet ---
    # The seller links Shopee, Lazada and TikTok Shop to KiotViet once, and
    # KiotViet returns every order stamped with the channel it came from. One
    # set of store API keys replaces three marketplace app approvals, each of
    # which gates on business documents.
    #
    # These come from the seller's own store: Thiết lập cửa hàng → Thiết lập
    # kết nối API. Authentication is an OAuth2 client-credentials grant, so
    # there is no redirect URL and nothing to register with a developer portal.
    # Left as None, the connection card reports "chưa cấu hình" instead of
    # offering a Connect button that cannot possibly complete.
    KIOTVIET_CLIENT_ID: str | None = None
    KIOTVIET_CLIENT_SECRET: str | None = None
    # The store's retailer name; KiotViet rejects API calls without it even
    # when the token is valid.
    KIOTVIET_RETAILER: str | None = None
    # How far back an order sync looks.
    CHANNEL_SYNC_DAYS: int = 60

    # --- Marketplace connections (Shopee / Lazada / TikTok Shop) ------------
    # Each marketplace issues its own app credentials; one app cannot speak to
    # another's API. Left as None, that marketplace reports "chưa cấu hình" and
    # its Connect button stays disabled rather than starting a flow that cannot
    # finish.
    SHOPEE_PARTNER_ID: str | None = None
    SHOPEE_PARTNER_KEY: str | None = None
    # Shopee runs a separate sandbox host. Switching environment is a config
    # change, never a code change.
    SHOPEE_SANDBOX: bool = True

    LAZADA_APP_KEY: str | None = None
    LAZADA_APP_SECRET: str | None = None

    TIKTOK_APP_KEY: str | None = None
    TIKTOK_APP_SECRET: str | None = None
    TIKTOK_SERVICE_ID: str | None = None

    # Where marketplaces send the seller back after authorisation. Must be
    # registered verbatim in each marketplace's app settings.
    OAUTH_REDIRECT_BASE: str = "http://localhost:8000/api/v1/marketplace/callback"
    # How long an authorisation may sit half-finished before its state token
    # stops being accepted.
    OAUTH_STATE_TTL_SECONDS: int = 900

    # Salt for the one-way buyer reference. Buyer identity is never stored, but
    # repeat purchases still need to be recognisable.
    BUYER_REF_SALT: str = "area303-buyer-ref"

    # Cache TTL for LLM responses (seconds).
    LLM_CACHE_TTL_SECONDS: int = 600  # 10 min per project plan
    LLM_REQUEST_TIMEOUT_SECONDS: float = 15.0

    # Seller Autopilot calls Ollama Cloud directly. Numeric impacts remain
    # deterministic; the model only writes concise grounded explanations.
    OLLAMA_API_KEY: str | None = None
    AUTOPILOT_OLLAMA_URL: str = "https://ollama.com"
    AUTOPILOT_OLLAMA_MODEL: str = "gpt-oss:120b"
    AUTOPILOT_LLM_TIMEOUT_SECONDS: float = 60.0

    # Rate limiting — anti spam on GenAI endpoints.
    RATE_LIMIT_PER_MINUTE: int = 30
    GLOBAL_RATE_LIMIT_PER_MINUTE: int = 300
    # Only enable behind a trusted proxy that replaces client-supplied XFF.
    TRUST_PROXY_HEADERS: bool = False

    # --- RAG / Vector store ---
    # Pinecone primary; FAISS local fallback if no key.
    PINECONE_API_KEY: str | None = None
    PINECONE_INDEX: str = "area303-tiki-catalog"
    PINECONE_ENVIRONMENT: str | None = None
    VECTOR_BACKEND: Literal["pinecone", "faiss", "memory"] = "memory"

    # Embedding model for query encoding (CLIP for visual, text-embedding-3
    # for text — defaults to text-only).
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # --- SSE ---
    SSE_HEARTBEAT_SECONDS: float = 15.0

    # --- Competitor tracking: where sales figures come from ---
    # Shopee's `get_shop_base` answers anonymously (followers, rating, product
    # count). Everything carrying sales — search_items, pdp/get_pc, item/get —
    # returns error 90309999 for an anonymous caller, and the shop page itself
    # renders "vui lòng đăng nhập" even in a real browser. Verified Aug 2026
    # against two live shops. So sales need one of the two sources below, and
    # with neither configured the sales fields stay empty by design.
    #
    # 1. A data vendor (Metric.vn, BeeCost, …). Licensed data, no account risk.
    #    Preferred when available — tried first.
    COMPETITOR_VENDOR_BASE_URL: str | None = None
    COMPETITOR_VENDOR_API_KEY: str | None = None
    # 2. A logged-in Shopee session. In the product, each user connects their
    #    OWN account (`scripts/shopee_connect.py` → POST /market/shopee-connection,
    #    stored per user and encrypted), so no shared credential exists and the
    #    two settings below are not involved.
    #
    #    These two are the single-tenant DEV fallback only: one operator-wide
    #    session file, captured with `shopee_connect.py --save-to`. Either way,
    #    Shopee's terms prohibit automated access and the account can be limited
    #    or banned, so this is off unless explicitly enabled.
    COMPETITOR_USE_SESSION: bool = False
    COMPETITOR_SESSION_PATH: str = "var/shopee_session.json"
    #: How many best sellers to read per capture. A trend reading, not a crawl.
    COMPETITOR_TOP_N: int = 20

    @property
    def database_url(self) -> str:
        url = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        return f"{url}?ssl=require" if self.POSTGRES_SSL else url

    @property
    def database_url_sync(self) -> str:
        """psycopg2 variant for Alembic — psycopg2 spells the TLS flag "sslmode"."""
        url = (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        return f"{url}?sslmode=require" if self.POSTGRES_SSL else url

    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        scheme = "rediss" if self.REDIS_TLS else "redis"
        return f"{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
