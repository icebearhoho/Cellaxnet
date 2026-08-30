"""Redis-backed cache for LLM responses.

Wraps a coroutine with a deterministic cache key (SHA-256 of the
serialized args). On hit returns the cached payload without invoking
the function. On miss runs the function, stores the result with a
TTL pulled from settings, and returns it.

Falls back to in-process cache when Redis is unreachable so the
service keeps working in dev / CI without a Redis container.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
from collections.abc import Callable
from typing import Any, get_type_hints

from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("app.services.genai.cache")

# In-process fallback — survives only for the lifetime of the process.
_LOCAL_CACHE: dict[str, tuple[float, Any]] = {}
_LOCAL_LOCK = asyncio.Lock()


def _make_key(prefix: str, args: tuple, kwargs: dict) -> str:
    payload = json.dumps(
        {"prefix": prefix, "args": args, "kwargs": kwargs},
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"area303:llm:{prefix}:{digest}"


def _now() -> float:
    import time

    return time.monotonic()


async def _redis_get(key: str) -> Any | None:
    try:
        from app.db.redis import get_redis

        client = get_redis()
        raw = await client.get(key)
    except Exception as exc:  # pragma: no cover — best-effort
        log.warning("cache.redis_get_failed", error=str(exc))
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def _redis_set(key: str, value: Any, ttl: int) -> None:
    try:
        from app.db.redis import get_redis

        client = get_redis()
        payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        await client.set(key, json.dumps(payload, default=str), ex=ttl)
    except Exception as exc:  # pragma: no cover — best-effort
        log.warning("cache.redis_set_failed", error=str(exc))


def llm_cache(
    *,
    prefix: str,
    ttl: int | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator factory for caching async LLM calls.

    The wrapped function must be ``async def`` and return JSON-safe data.
    The Redis client is consulted first, then the in-process dict,
    then the function is invoked and the result stored.
    """

    cache_ttl = ttl if ttl is not None else settings.LLM_CACHE_TTL_SECONDS

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        try:
            return_type = get_type_hints(fn).get("return")
        except (NameError, TypeError):
            return_type = None

        def restore_cached(value: Any) -> tuple[bool, Any]:
            """Rebuild typed Pydantic responses stored as JSON dictionaries.

            Older versions cached models via ``default=str``. Those entries
            are strings such as ``"variants=[...]"`` and cannot be restored;
            treating them as a miss lets the function compute a valid value
            and replace the stale Redis entry automatically.
            """
            if isinstance(return_type, type) and issubclass(return_type, BaseModel):
                if not isinstance(value, dict):
                    return False, None
                try:
                    return True, return_type.model_validate(value)
                except ValueError:
                    return False, None
            return True, value

        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = _make_key(prefix, args, kwargs)

            cached = await _redis_get(key)
            if cached is not None:
                valid, restored = restore_cached(cached)
                if valid:
                    return restored

            async with _LOCAL_LOCK:
                entry = _LOCAL_CACHE.get(key)
                if entry is not None:
                    expires_at, value = entry
                    if expires_at > _now():
                        return value
                    _LOCAL_CACHE.pop(key, None)

            value = await fn(*args, **kwargs)

            # Try Redis first, then in-process fallback.
            await _redis_set(key, value, cache_ttl)
            async with _LOCAL_LOCK:
                _LOCAL_CACHE[key] = (_now() + cache_ttl, value)
            return value

        return wrapper

    return decorator


async def invalidate_prefix(prefix: str) -> int:
    """Clear every cached entry under ``prefix`` (best effort)."""
    removed = 0
    async with _LOCAL_LOCK:
        for key in list(_LOCAL_CACHE.keys()):
            if f":{prefix}:" in key:
                _LOCAL_CACHE.pop(key, None)
                removed += 1
    try:
        from app.db.redis import get_redis

        client = get_redis()
        async for k in client.scan_iter(match=f"area303:llm:{prefix}:*"):
            await client.delete(k)
            removed += 1
    except Exception as exc:  # pragma: no cover
        log.warning("cache.invalidate_failed", error=str(exc))
    return removed
