"""LLM + RAG client factories.

Resolution order:

1. If ``settings.DEMO_MODE=true`` → :class:`MockLlmClient`. Always.
2. Else pick the provider named in ``settings.LLM_PROVIDER``.
3. If that provider has no API key, fall back to mock (log a warning).
   This keeps the demo alive even when keys are absent at runtime.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger
from app.services.genai.base import LlmClient
from app.services.genai.rag import BaseRetriever, InMemoryRetriever

log = get_logger("app.services.genai.factory")


@lru_cache(maxsize=1)
def get_llm_client() -> LlmClient:
    if settings.DEMO_MODE:
        log.info("llm_client.demo_mode")
        from app.services.genai.mock_client import MockLlmClient

        return MockLlmClient()

    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            log.warning("llm_client.gemini.no_key_fallback_mock")
            from app.services.genai.mock_client import MockLlmClient

            return MockLlmClient()
        from app.services.genai.gemini_client import GeminiClient

        return GeminiClient()
    if provider in {"openai", "ollama"}:
        provider_key = (
            settings.OLLAMA_API_KEY if provider == "ollama" else settings.OPENAI_API_KEY
        )
        if not provider_key:
            log.warning("llm_client.provider.no_key_fallback_mock", provider=provider)
            from app.services.genai.mock_client import MockLlmClient

            return MockLlmClient()
        from app.services.genai.openai_client import OpenAIClient

        return OpenAIClient()

    # Default = mock — never throw at import time.
    log.info("llm_client.default_mock", provider=provider)
    from app.services.genai.mock_client import MockLlmClient

    return MockLlmClient()


async def close_llm_client() -> None:
    """Close the cached provider transport without instantiating a new one."""
    if get_llm_client.cache_info().currsize == 0:
        return
    client = get_llm_client()
    close = getattr(client, "aclose", None)
    if close is not None:
        await close()
    get_llm_client.cache_clear()


@lru_cache(maxsize=1)
def get_rag() -> BaseRetriever:
    """Return the configured retriever.

    For the demo we ship an in-memory retriever seeded with a small
    Tiki catalog slice.  Swap to Pinecone when ``VECTOR_BACKEND=pinecone``
    and a key is configured.
    """
    backend = settings.VECTOR_BACKEND.lower()
    if backend == "memory":
        return InMemoryRetriever()
    if backend == "pinecone":
        if not settings.PINECONE_API_KEY:
            log.warning("rag.pinecone.no_key_fallback_memory")
            return InMemoryRetriever()
        # Lazily imported so the dep is optional.
        from app.services.genai.pinecone_retriever import PineconeRetriever

        return PineconeRetriever()
    # "faiss" is a follow-up; fall back to memory for now.
    log.warning("rag.backend_fallback_memory", backend=backend)
    return InMemoryRetriever()
