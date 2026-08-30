"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

_engine_options: dict = {"pool_pre_ping": True, "future": True}
if settings.APP_ENV == "test":
    # pytest creates function-scoped event loops. A global asyncpg pool can
    # retain connections owned by a closed loop and leak Connection._cancel
    # coroutines during garbage collection.
    _engine_options["poolclass"] = NullPool
else:
    _engine_options.update(
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )

engine = create_async_engine(settings.database_url, **_engine_options)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_database() -> None:
    """Release pooled connections during application shutdown."""
    await engine.dispose()
