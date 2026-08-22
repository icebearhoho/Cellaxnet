"""Application settings loaded from environment variables / .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "AREA-303 API"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = True
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

    # --- Redis ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # --- Auth ---
    JWT_SECRET: str = "change-me-in-production"
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
    LLM_PROVIDER: Literal["gemini", "openai", "mock"] = "mock"
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

    # Fernet key for encrypting stored tokens at rest. Generated per deployment
    # with Fernet.generate_key(). Absent, the app refuses to store credentials
    # rather than writing them in the clear — a missing key is a configuration
    # error, not a reason to downgrade security silently.
    CREDENTIAL_ENCRYPTION_KEY: str | None = None
    # Salt for the one-way buyer reference. Buyer identity is never stored, but
    # repeat purchases still need to be recognisable.
    BUYER_REF_SALT: str = "area303-buyer-ref"

    # Cache TTL for LLM responses (seconds).
    LLM_CACHE_TTL_SECONDS: int = 600  # 10 min per project plan

    # Rate limiting — anti spam on GenAI endpoints.
    RATE_LIMIT_PER_MINUTE: int = 30

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

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
