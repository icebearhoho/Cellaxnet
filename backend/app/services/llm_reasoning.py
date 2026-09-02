"""Shared OpenAI reasoning helper for the Track-2 intelligence features
(Market / Content-Creator / Product-Knowledge / Decision Intelligence).

These features are numeric at the core (scores, margins, rankings computed by
deterministic heuristics) but benefit from a natural-language *explanation* and
strategic recommendation. That narrative layer runs on the real LLM (OpenAI when
configured) and degrades gracefully: if the LLM is unavailable (demo mode, no
key, timeout, bad JSON) ``reason_json`` returns ``None`` and the caller uses its
own templated fallback text, so the endpoint always answers.
"""

from __future__ import annotations

import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.genai.base import LlmMessage
from app.services.genai.factory import get_llm_client

log = get_logger("app.services.llm_reasoning")

# Prepended to every reasoning prompt so answers match the user's language.
_LANG_RULE = (
    "Reply in the SAME language as the input: if the user's text/question is in "
    "Vietnamese, answer in Vietnamese; if it is in English, answer in English. "
    "When the input has no clear language (only numbers/structured data), default "
    "to Vietnamese.\n\n"
)


def llm_ready() -> bool:
    """True if a real (non-mock) LLM is configured."""
    provider_keys = {
        "gemini": settings.GEMINI_API_KEY,
        "openai": settings.OPENAI_API_KEY,
        "ollama": settings.OLLAMA_API_KEY,
    }
    return (
        not settings.DEMO_MODE
        and settings.LLM_PROVIDER != "mock"
        and bool(provider_keys.get(settings.LLM_PROVIDER))
    )


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].lstrip("json").strip()
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start : end + 1] if start != -1 and end != -1 else raw)


async def reason_json(
    system: str,
    user: str,
    *,
    max_tokens: int = 400,
    temperature: float = 0.2,
    label: str = "reason",
) -> dict | None:
    """Ask the LLM for a compact JSON object. Returns the parsed dict, or None
    on any failure so the caller can fall back to a deterministic narrative."""
    if not llm_ready():
        return None
    try:
        resp = await get_llm_client().chat(
            [
                LlmMessage(role="system", content=_LANG_RULE + system),
                LlmMessage(role="user", content=user),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _parse_json(resp.content)
    except Exception as exc:  # noqa: BLE001 — any LLM failure falls back to heuristic
        log.warning("llm_reasoning.fallback", label=label, error=str(exc))
        return None
