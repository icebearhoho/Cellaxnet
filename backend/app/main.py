"""FastAPI app factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import CanonicalApiPathMiddleware, RequestContextMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.db.redis import close_redis
from app.db.session import close_database
from app.services import segmentation
from app.services.btc_market import close_btc_engine
from app.services.genai.factory import close_llm_client

log = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("startup", env=settings.APP_ENV, version=__version__)
    # Preload the #13 segmentation model so the first request isn't slow.
    # Safe no-op if the .pkl artifacts aren't present yet.
    segmentation.warmup()
    yield
    await close_llm_client()
    await close_redis()
    await close_btc_engine()
    await close_database()
    log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        # Starlette's default slash-redirect answers with an absolute URL built
        # from the request's own Host header (http://localhost:8000/...). Behind
        # the Next.js rewrite proxy that leaks the backend's origin straight to
        # the browser, which the frontend CSP's connect-src then blocks. The
        # frontend always calls these collection routes with the trailing slash
        # already in place, so disabling the redirect only turns a slash-less
        # request into a 404 instead of a cross-origin redirect.
        redirect_slashes=False,
    )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "x-ratelimit-limit", "x-ratelimit-remaining"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["root"])
    async def root():
        return {
            "success": True,
            "data": {
                "name": settings.APP_NAME,
                "version": __version__,
                "env": settings.APP_ENV,
                "docs": "/docs",
            },
            "meta": None,
            "error": None,
        }

    # Accept both forms for router-root endpoints without FastAPI's external
    # 307 redirect. FastAPI expands included routers lazily, so OpenAPI is the
    # reliable source of the final canonical path set at app construction.
    canonical_slash_paths = frozenset(
        path
        for path in app.openapi()["paths"]
        if path.startswith(settings.API_V1_PREFIX) and path.endswith("/")
    )
    app.add_middleware(
        CanonicalApiPathMiddleware,
        slash_paths=canonical_slash_paths,
    )

    return app


app = create_app()
