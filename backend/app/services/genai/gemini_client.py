"""Google Gemini client — REST, streaming via SSE.

No SDK dependency on ``google-generativeai``; we hit the public REST
endpoint directly. This keeps the dependency surface small and avoids
the long install of the SDK in CI.

Spec reference:
https://ai.google.dev/api/generate-content#streamGenerateContent
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import UpstreamUnavailableError
from app.services.genai.base import ChatChunk, LlmClient, LlmMessage, LlmResponse


def _convert_messages(messages: list[LlmMessage]) -> tuple[dict | None, list[dict]]:
    """Convert :class:`LlmMessage` to Gemini's ``contents`` shape.

    Gemini uses ``system_instruction`` for system prompts and ``contents``
    for the rest.  We pair adjacent user/assistant messages into turns.
    """
    system: dict | None = None
    contents: list[dict] = []

    for m in messages:
        if m.role == "system":
            system = {"parts": [{"text": m.content}]}
            continue
        role = "model" if m.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m.content}]})

    return system, contents


class GeminiClient(LlmClient):
    """Streaming Gemini client.  Requires ``GEMINI_API_KEY``."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        if not self._api_key:
            raise UpstreamUnavailableError(
                "GEMINI_API_KEY is not configured.",
                code="LLM_NOT_CONFIGURED",
                status_code=503,
            )
        self._base = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:streamGenerateContent?alt=sse"
        )
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.LLM_REQUEST_TIMEOUT_SECONDS, connect=8.0)
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    def _payload(self, messages: list[LlmMessage], *, temperature: float, max_tokens: int | None) -> dict[str, Any]:
        system, contents = _convert_messages(messages)
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = system
        if max_tokens:
            body["generationConfig"]["maxOutputTokens"] = max_tokens
        return body

    async def chat(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LlmResponse:
        body = self._payload(messages, temperature=temperature, max_tokens=max_tokens)
        try:
            r = await self._http.post(
                self._base,
                params={"key": self._api_key},
                json=body,
            )
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(
                f"Gemini transport error: {exc}",
                code="LLM_TRANSPORT_ERROR",
            ) from exc

        if r.status_code >= 400:
            raise UpstreamUnavailableError(
                f"Gemini returned {r.status_code}: {r.text[:300]}",
                code="LLM_UPSTREAM_ERROR",
            )

        # Non-streaming response: concat parts.
        text = "".join(
            part.get("text", "")
            for cand in r.json().get("candidates", [])
            for part in cand.get("content", {}).get("parts", [])
        )
        return LlmResponse(content=text, model=self.model)

    async def stream(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[ChatChunk]:
        body = self._payload(messages, temperature=temperature, max_tokens=max_tokens)
        try:
            async with self._http.stream(
                "POST",
                self._base,
                params={"key": self._api_key},
                json=body,
            ) as r:
                if r.status_code >= 400:
                    body_bytes = await r.aread()
                    raise UpstreamUnavailableError(
                        f"Gemini returned {r.status_code}: {body_bytes[:300]!r}",
                        code="LLM_UPSTREAM_ERROR",
                    )
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[len("data:") :].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    for cand in chunk.get("candidates", []):
                        parts = cand.get("content", {}).get("parts", [])
                        for part in parts:
                            delta = part.get("text")
                            if delta:
                                yield ChatChunk(delta=delta)
                        finish = cand.get("finishReason")
                        if finish:
                            yield ChatChunk(delta="", finish_reason=finish)
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(
                f"Gemini transport error: {exc}",
                code="LLM_TRANSPORT_ERROR",
            ) from exc
