import json
import urllib.error
import urllib.request
from typing import Any

import pytest

from kodalo.core.ai import GenerateRequest, Generation, clients
from kodalo.core.settings.ai import AiConnectionError
from tests.core.ai.test_clients import _fail, _serve


def _request(provider: str, **changes: Any) -> GenerateRequest:
    values: dict[str, Any] = {
        "provider": provider,
        "base_url": "https://example.test",
        "api_key": "k",
        "model": "m",
        "system": "Answer in JSON.",
        "prompt": "Hello",
        "max_tokens": 100,
    }
    return GenerateRequest(**{**values, **changes})


def _body(seen: list[urllib.request.Request]) -> dict[str, Any]:
    data = seen[0].data
    assert isinstance(data, bytes)
    body: dict[str, Any] = json.loads(data)
    return body


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://example.test", code, "x", None, None)  # type: ignore[arg-type]


def test_claude_api_sends_the_prompt_and_counts_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _serve(
        monkeypatch,
        {
            "content": [{"type": "text", "text": "{"}, {"type": "text", "text": "}"}],
            "usage": {"input_tokens": 12, "output_tokens": 3},
        },
    )
    result = clients.generate(_request("claude_api", temperature=0.5))
    assert result == Generation("{}", 12, 3)
    assert seen[0].full_url == "https://example.test/v1/messages"
    assert seen[0].get_header("X-api-key") == "k"
    body = _body(seen)
    assert body["system"] == "Answer in JSON."
    assert body["messages"] == [{"role": "user", "content": "Hello"}]
    assert (body["max_tokens"], body["temperature"]) == (100, 0.5)


def test_a_temperature_left_out_is_not_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _serve(monkeypatch, {"content": [], "usage": {}})
    clients.generate(_request("claude_api"))
    assert "temperature" not in _body(seen)


def test_chatgpt_api(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _serve(
        monkeypatch,
        {
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 2},
        },
    )
    assert clients.generate(_request("chatgpt_api")) == Generation("{}", 7, 2)
    assert seen[0].full_url == "https://example.test/v1/chat/completions"
    assert seen[0].get_header("Authorization") == "Bearer k"
    body = _body(seen)
    assert body["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in body["messages"]] == ["system", "user"]


def test_gemini_api(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _serve(
        monkeypatch,
        {
            "candidates": [{"content": {"parts": [{"text": "{"}, {"text": "}"}]}}],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 1},
        },
    )
    assert clients.generate(_request("gemini_api", temperature=0)) == Generation("{}", 5, 1)
    assert seen[0].full_url == "https://example.test/v1beta/models/m:generateContent"
    assert seen[0].get_header("X-goog-api-key") == "k"
    assert _body(seen)["generationConfig"]["temperature"] == 0


@pytest.mark.parametrize(
    ("provider", "answer"),
    [("chatgpt_api", {"choices": []}), ("gemini_api", {"candidates": []})],
)
def test_an_answer_without_text_is_unreadable(
    monkeypatch: pytest.MonkeyPatch, provider: str, answer: dict[str, Any]
) -> None:
    _serve(monkeypatch, answer)
    with pytest.raises(AiConnectionError, match="could not read"):
        clients.generate(_request(provider))


def test_missing_token_counts_are_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, {"content": [{"type": "text", "text": "x"}]})
    assert clients.generate(_request("claude_api")) == Generation("x", 0, 0)


def test_a_rejected_key_a_server_error_and_an_unreachable_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fail(monkeypatch, _http_error(401))
    with pytest.raises(AiConnectionError, match="rejected the API key"):
        clients.generate(_request("claude_api"))
    _fail(monkeypatch, _http_error(500))
    with pytest.raises(AiConnectionError, match="HTTP 500"):
        clients.generate(_request("claude_api"))
    _fail(monkeypatch, urllib.error.URLError("down"))
    with pytest.raises(AiConnectionError, match="Could not reach"):
        clients.generate(_request("claude_api"))


def test_an_unknown_provider_is_refused() -> None:
    with pytest.raises(AiConnectionError, match="Unknown provider: other"):
        clients.generate(_request("other"))
