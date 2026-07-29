"""Live provider adapters with normalized responses and credential-safe I/O.

The adapters implement only the provider boundary. Governance, egress
authorization, context sealing, route ordering, and token ceilings remain in
the execution engine. API credentials are read from the environment at call
time and are never written to a CONCLAVE artifact.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .errors import ProviderError, ValidationError
from .providers import ProviderRequest, ProviderResponse, ProviderUsage


class JsonTransport(Protocol):
    def post(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]: ...


@dataclass
class UrllibJsonTransport:
    """Small stdlib JSON transport; deliberately has no retry policy."""

    def post(
        self,
        *,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            # Do not include response bodies: providers may echo submitted context.
            raise ProviderError(
                f"provider HTTP request failed with status {exc.code}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProviderError("provider HTTP request failed") from exc
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("provider returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("provider returned a non-object JSON response")
        return parsed


def _credential(explicit: str | None, environment_name: str) -> str:
    value = explicit if explicit is not None else os.environ.get(environment_name)
    if not value or not value.strip():
        raise ProviderError(
            f"missing provider credential in environment variable {environment_name}"
        )
    return value.strip()


def _validate_identity(
    request: ProviderRequest, *, provider: str, transport: str
) -> None:
    if request.provider != provider or request.transport != transport:
        raise ValidationError("request does not match live adapter identity")


def _integer(value: Any, *, field: str) -> int:
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProviderError(f"provider returned invalid token count for {field}")
    return value


def _mapping(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ProviderError(f"provider returned invalid object for {field}")
    return value


@dataclass
class OpenAIAdapter:
    """OpenAI Responses API adapter for the configured Adrian provider."""

    provider: str = "adrian"
    transport: str = "openai-responses-api"
    api_key: str | None = None
    timeout_seconds: float = 120.0
    http: JsonTransport | None = None

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        _validate_identity(request, provider=self.provider, transport=self.transport)
        key = _credential(self.api_key, "OPENAI_API_KEY")
        http = self.http or UrllibJsonTransport()
        response = http.post(
            url="https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": request.model,
                "input": request.prompt,
                "max_output_tokens": request.max_output_tokens,
            },
            timeout_seconds=self.timeout_seconds,
        )
        usage = _mapping(response.get("usage"), field="usage")
        input_details = _mapping(
            usage.get("input_tokens_details"), field="usage.input_tokens_details"
        )
        output_details = _mapping(
            usage.get("output_tokens_details"), field="usage.output_tokens_details"
        )
        text = response.get("output_text")
        if not isinstance(text, str):
            fragments: list[str] = []
            output = response.get("output", [])
            if not isinstance(output, list):
                raise ProviderError("OpenAI response output is not a list")
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    value = block.get("text")
                    if block.get("type") in {"output_text", "text"} and isinstance(
                        value, str
                    ):
                        fragments.append(value)
            text = "".join(fragments)
        if not text:
            raise ProviderError("OpenAI response contained no text output")
        return ProviderResponse(
            provider=self.provider,
            model=request.model,
            transport=self.transport,
            text=text,
            usage=ProviderUsage(
                input_tokens=_integer(
                    usage.get("input_tokens"), field="usage.input_tokens"
                ),
                cached_input_tokens=_integer(
                    input_details.get("cached_tokens"),
                    field="usage.input_tokens_details.cached_tokens",
                ),
                output_tokens=_integer(
                    usage.get("output_tokens"), field="usage.output_tokens"
                ),
                reasoning_output_tokens=_integer(
                    output_details.get("reasoning_tokens"),
                    field="usage.output_tokens_details.reasoning_tokens",
                ),
            ),
            finish_status=str(response.get("status") or "unknown"),
            provider_request_id=(
                str(response["id"]) if response.get("id") is not None else None
            ),
        )


@dataclass
class ClaudeAdapter:
    """Anthropic Messages API adapter for the configured Claude provider."""

    provider: str = "claude"
    transport: str = "anthropic-messages-api"
    api_key: str | None = None
    timeout_seconds: float = 120.0
    http: JsonTransport | None = None
    anthropic_version: str = "2023-06-01"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        _validate_identity(request, provider=self.provider, transport=self.transport)
        key = _credential(self.api_key, "ANTHROPIC_API_KEY")
        http = self.http or UrllibJsonTransport()
        response = http.post(
            url="https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": self.anthropic_version,
                "Content-Type": "application/json",
            },
            payload={
                "model": request.model,
                "max_tokens": request.max_output_tokens,
                "messages": [{"role": "user", "content": request.prompt}],
            },
            timeout_seconds=self.timeout_seconds,
        )
        content = response.get("content", [])
        if not isinstance(content, list):
            raise ProviderError("Claude response content is not a list")
        text = "".join(
            block["text"]
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        )
        if not text:
            raise ProviderError("Claude response contained no text output")
        usage = _mapping(response.get("usage"), field="usage")
        uncached = _integer(usage.get("input_tokens"), field="usage.input_tokens")
        cache_creation = _integer(
            usage.get("cache_creation_input_tokens"),
            field="usage.cache_creation_input_tokens",
        )
        cached = _integer(
            usage.get("cache_read_input_tokens"),
            field="usage.cache_read_input_tokens",
        )
        output = _integer(usage.get("output_tokens"), field="usage.output_tokens")
        output_details = _mapping(
            usage.get("output_tokens_details"), field="usage.output_tokens_details"
        )
        return ProviderResponse(
            provider=self.provider,
            model=request.model,
            transport=self.transport,
            text=text,
            usage=ProviderUsage(
                input_tokens=uncached + cache_creation + cached,
                cached_input_tokens=cached,
                output_tokens=output,
                reasoning_output_tokens=_integer(
                    output_details.get("thinking_tokens"),
                    field="usage.output_tokens_details.thinking_tokens",
                ),
            ),
            finish_status=str(response.get("stop_reason") or "unknown"),
            provider_request_id=(
                str(response["id"]) if response.get("id") is not None else None
            ),
        )


@dataclass
class GeminiAdapter:
    """Gemini generateContent API adapter."""

    provider: str = "gemini"
    transport: str = "gemini-generate-content-api"
    api_key: str | None = None
    timeout_seconds: float = 120.0
    http: JsonTransport | None = None

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        _validate_identity(request, provider=self.provider, transport=self.transport)
        key = _credential(self.api_key, "GEMINI_API_KEY")
        http = self.http or UrllibJsonTransport()
        model = quote(request.model, safe="")
        response = http.post(
            url=(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent"
            ),
            headers={
                "x-goog-api-key": key,
                "Content-Type": "application/json",
            },
            payload={
                "contents": [{"parts": [{"text": request.prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": request.max_output_tokens,
                },
            },
            timeout_seconds=self.timeout_seconds,
        )
        candidates = response.get("candidates", [])
        if not isinstance(candidates, list):
            raise ProviderError("Gemini response candidates is not a list")
        fragments: list[str] = []
        finish_reasons: list[str] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("finishReason") is not None:
                finish_reasons.append(str(candidate["finishReason"]))
            content = candidate.get("content", {})
            if not isinstance(content, dict):
                continue
            parts = content.get("parts", [])
            if not isinstance(parts, list):
                continue
            fragments.extend(
                str(part["text"])
                for part in parts
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
        text = "".join(fragments)
        if not text:
            raise ProviderError("Gemini response contained no text output")
        usage = _mapping(response.get("usageMetadata"), field="usageMetadata")
        candidate_tokens = _integer(
            usage.get("candidatesTokenCount"),
            field="usageMetadata.candidatesTokenCount",
        )
        thought_tokens = _integer(
            usage.get("thoughtsTokenCount"),
            field="usageMetadata.thoughtsTokenCount",
        )
        return ProviderResponse(
            provider=self.provider,
            model=request.model,
            transport=self.transport,
            text=text,
            usage=ProviderUsage(
                input_tokens=_integer(
                    usage.get("promptTokenCount"),
                    field="usageMetadata.promptTokenCount",
                ),
                cached_input_tokens=_integer(
                    usage.get("cachedContentTokenCount"),
                    field="usageMetadata.cachedContentTokenCount",
                ),
                output_tokens=candidate_tokens + thought_tokens,
                reasoning_output_tokens=thought_tokens,
            ),
            finish_status=",".join(finish_reasons) or "unknown",
            provider_request_id=(
                str(response["responseId"])
                if response.get("responseId") is not None
                else None
            ),
        )
