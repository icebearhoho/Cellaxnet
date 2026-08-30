"""OpenAI client — REST, streaming via SSE.

Hits ``/v1/chat/completions`` directly. No SDK dependency — keeps
install fast and predictable across CI / Vercel / Railway.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import settings
from app.core.exceptions import UpstreamUnavailableError
from app.services.genai.base import ChatChunk, LlmClient, LlmMessage, LlmResponse


def _convert_messages(messages: list[LlmMessage]) -> list[dict]:
    """OpenAI uses the same role names as our internal model."""
    return [{"role": m.role, "content": m.content} for m in messages]


class OpenAIClient(LlmClient):
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        base_url = settings.OPENAI_BASE_URL.rstrip("/")
        # Ollama Cloud exposes an OpenAI-compatible endpoint, but authenticates
        # with the Ollama key.  Keeping an older OPENAI_API_KEY in .env must not
        # make requests to ollama.com fail with a misleading 401.
        provider_key = (
            settings.OLLAMA_API_KEY
            if "ollama.com" in base_url.lower()
            else settings.OPENAI_API_KEY
        )
        self._api_key = api_key or provider_key
        self.model = model or settings.OPENAI_MODEL
        if not self._api_key:
            raise UpstreamUnavailableError(
                "OPENAI_API_KEY is not configured.",
                code="LLM_NOT_CONFIGURED",
                status_code=503,
            )
        # Base URL is configurable so this OpenAI-compatible client can also talk
        # to Groq / OpenRouter / any /v1/chat/completions endpoint (open-source
        # models via a free API). Default stays OpenAI.
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(settings.LLM_REQUEST_TIMEOUT_SECONDS, connect=8.0),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    def _payload(self, messages: list[LlmMessage], *, temperature: float, max_tokens: int | None, stream: bool) -> dict:
        body = {
            "model": self.model,
            "messages": _convert_messages(messages),
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        return body

    async def chat(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LlmResponse:
        body = self._payload(messages, temperature=temperature, max_tokens=max_tokens, stream=False)
        try:
            r = await self._http.post("/v1/chat/completions", json=body)
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(
                f"OpenAI transport error: {exc}", code="LLM_TRANSPORT_ERROR"
            ) from exc

        if r.status_code >= 400:
            raise UpstreamUnavailableError(
                f"OpenAI returned {r.status_code}: {r.text[:300]}",
                code="LLM_UPSTREAM_ERROR",
            )

        data = r.json()
        choice = data["choices"][0]
        return LlmResponse(
            content=choice["message"]["content"],
            model=data.get("model", self.model),
            usage=data.get("usage", {}),
            raw=data,
        )

    async def chat_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = 600,
    ) -> dict:
        """Function-calling turn. `messages` are raw OpenAI-format dicts (so the
        caller can append assistant tool_calls + tool results). Returns the raw
        assistant message dict (may contain `content` and/or `tool_calls`)."""
        body: dict = {"model": self.model, "messages": messages, "tools": tools,
                      "temperature": temperature}
        if max_tokens:
            body["max_tokens"] = max_tokens
        try:
            r = await self._http.post("/v1/chat/completions", json=body)
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(
                f"OpenAI transport error: {exc}", code="LLM_TRANSPORT_ERROR"
            ) from exc
        if r.status_code >= 400:
            raise UpstreamUnavailableError(
                f"OpenAI returned {r.status_code}: {r.text[:300]}", code="LLM_UPSTREAM_ERROR"
            )
        data = r.json()
        msg: dict = data["choices"][0]["message"]
        return msg

    async def stream(
        self,
        messages: list[LlmMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[ChatChunk]:
        body = self._payload(messages, temperature=temperature, max_tokens=max_tokens, stream=True)
        try:
            async with self._http.stream("POST", "/v1/chat/completions", json=body) as r:
                if r.status_code >= 400:
                    raw = await r.aread()
                    raise UpstreamUnavailableError(
                        f"OpenAI returned {r.status_code}: {raw[:300]!r}",
                        code="LLM_UPSTREAM_ERROR",
                    )
                async for line in r.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[len("data:") :].strip()
                    if payload == "[DONE]":
                        yield ChatChunk(delta="", finish_reason="stop")
                        return
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    for choice in chunk.get("choices", []):
                        delta = choice.get("delta", {}).get("content")
                        if delta:
                            yield ChatChunk(delta=delta)
                        finish = choice.get("finish_reason")
                        if finish:
                            yield ChatChunk(delta="", finish_reason=finish)
        except httpx.HTTPError as exc:
            raise UpstreamUnavailableError(
                f"OpenAI transport error: {exc}", code="LLM_TRANSPORT_ERROR"
            ) from exc
