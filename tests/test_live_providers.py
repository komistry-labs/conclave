from io import BytesIO
from urllib.error import HTTPError

import pytest

from conclave.errors import ProviderError, ValidationError
from conclave.live_providers import (
    ClaudeAdapter, GeminiAdapter, OpenAIAdapter, UrllibJsonTransport,
)
from conclave.providers import ProviderRequest


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def request(provider, transport, model="current-model"):
    return ProviderRequest(
        provider=provider,
        model=model,
        transport=transport,
        role="lead",
        prompt="governed prompt",
        context_bundle_hash="sha256:" + "1" * 64,
        max_output_tokens=321,
    )


def test_openai_responses_adapter_normalizes_text_and_usage():
    http = FakeTransport({
        "id": "resp_123",
        "status": "completed",
        "output": [{
            "type": "message",
            "content": [{"type": "output_text", "text": "OpenAI result"}],
        }],
        "usage": {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 25},
            "output_tokens": 40,
            "output_tokens_details": {"reasoning_tokens": 10},
        },
    })
    adapter = OpenAIAdapter(api_key="openai-secret", http=http)
    result = adapter.execute(request("adrian", adapter.transport, "gpt-test"))

    call = http.calls[0]
    assert call["url"] == "https://api.openai.com/v1/responses"
    assert call["headers"]["Authorization"] == "Bearer openai-secret"
    assert call["payload"] == {
        "model": "gpt-test",
        "input": "governed prompt",
        "max_output_tokens": 321,
    }
    assert result.text == "OpenAI result"
    assert result.model == "gpt-test"
    assert result.provider_request_id == "resp_123"
    assert result.usage.input_tokens == 100
    assert result.usage.cached_input_tokens == 25
    assert result.usage.output_tokens == 40
    assert result.usage.reasoning_output_tokens == 10


def test_claude_messages_adapter_normalizes_cache_and_thinking_usage():
    http = FakeTransport({
        "id": "msg_123",
        "stop_reason": "end_turn",
        "content": [
            {"type": "text", "text": "Claude "},
            {"type": "text", "text": "result"},
        ],
        "usage": {
            "input_tokens": 70,
            "cache_creation_input_tokens": 20,
            "cache_read_input_tokens": 10,
            "output_tokens": 30,
            "output_tokens_details": {"thinking_tokens": 5},
        },
    })
    adapter = ClaudeAdapter(api_key="claude-secret", http=http)
    result = adapter.execute(request("claude", adapter.transport, "claude-test"))

    call = http.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "claude-secret"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    assert call["payload"]["messages"] == [
        {"role": "user", "content": "governed prompt"}
    ]
    assert call["payload"]["max_tokens"] == 321
    assert result.text == "Claude result"
    assert result.model == "claude-test"
    assert result.finish_status == "end_turn"
    assert result.usage.input_tokens == 100
    assert result.usage.cached_input_tokens == 10
    assert result.usage.output_tokens == 30
    assert result.usage.reasoning_output_tokens == 5


def test_gemini_adapter_normalizes_all_candidate_text_and_thought_tokens():
    http = FakeTransport({
        "responseId": "gemini-123",
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {"parts": [{"text": "Gemini "}, {"text": "result"}]},
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 80,
            "cachedContentTokenCount": 20,
            "candidatesTokenCount": 25,
            "thoughtsTokenCount": 7,
        },
    })
    adapter = GeminiAdapter(api_key="gemini-secret", http=http)
    result = adapter.execute(
        request("gemini", adapter.transport, "gemini/test model")
    )

    call = http.calls[0]
    assert call["url"].endswith(
        "/models/gemini%2Ftest%20model:generateContent"
    )
    assert call["headers"]["x-goog-api-key"] == "gemini-secret"
    assert call["payload"]["generationConfig"]["maxOutputTokens"] == 321
    assert result.text == "Gemini result"
    assert result.finish_status == "STOP"
    assert result.usage.input_tokens == 80
    assert result.usage.cached_input_tokens == 20
    assert result.usage.output_tokens == 32
    assert result.usage.reasoning_output_tokens == 7


@pytest.mark.parametrize(
    ("adapter", "provider", "environment"),
    [
        (OpenAIAdapter(), "adrian", "OPENAI_API_KEY"),
        (ClaudeAdapter(), "claude", "ANTHROPIC_API_KEY"),
        (GeminiAdapter(), "gemini", "GEMINI_API_KEY"),
    ],
)
def test_missing_credentials_fail_before_http(
    adapter, provider, environment, monkeypatch
):
    monkeypatch.delenv(environment, raising=False)
    http = FakeTransport({})
    adapter.http = http
    with pytest.raises(ProviderError, match=environment):
        adapter.execute(request(provider, adapter.transport))
    assert http.calls == []


def test_adapter_identity_mismatch_fails_before_http():
    http = FakeTransport({})
    adapter = OpenAIAdapter(api_key="secret", http=http)
    with pytest.raises(ValidationError, match="identity"):
        adapter.execute(request("claude", adapter.transport))
    assert http.calls == []


def test_empty_provider_output_is_rejected():
    http = FakeTransport({
        "id": "resp_empty",
        "status": "completed",
        "output": [],
        "usage": {"input_tokens": 1, "output_tokens": 0},
    })
    with pytest.raises(ProviderError, match="no text"):
        OpenAIAdapter(api_key="secret", http=http).execute(
            request("adrian", "openai-responses-api")
        )


def test_http_failure_does_not_expose_provider_response_body(monkeypatch):
    def fail(*args, **kwargs):
        raise HTTPError(
            "https://provider.invalid", 401, "Unauthorized", {},
            BytesIO(b"submitted governed prompt and secret"),
        )

    monkeypatch.setattr("conclave.live_providers.urlopen", fail)
    with pytest.raises(ProviderError) as captured:
        UrllibJsonTransport().post(
            url="https://provider.invalid",
            headers={"Authorization": "Bearer secret"},
            payload={"input": "submitted governed prompt"},
            timeout_seconds=1,
        )
    message = str(captured.value)
    assert "401" in message
    assert "governed prompt" not in message
    assert "secret" not in message


def test_invalid_http_json_is_rejected(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"not-json"

    monkeypatch.setattr(
        "conclave.live_providers.urlopen", lambda *args, **kwargs: Response()
    )
    with pytest.raises(ProviderError, match="invalid JSON"):
        UrllibJsonTransport().post(
            url="https://provider.invalid",
            headers={},
            payload={},
            timeout_seconds=1,
        )
