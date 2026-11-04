import io
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any

import pytest

from kodalo.core.ai import AiConnectionError, clients
from kodalo.core.ai.providers import CLAUDE_CODE_MODELS


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def _serve(monkeypatch: pytest.MonkeyPatch, body: Any) -> list[urllib.request.Request]:
    seen: list[urllib.request.Request] = []

    def urlopen(request: urllib.request.Request, timeout: int) -> _Response:
        seen.append(request)
        return _Response(json.dumps(body).encode())

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    return seen


def _fail(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    def urlopen(request: urllib.request.Request, timeout: int) -> _Response:
        raise error

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)


def test_claude_api(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _serve(monkeypatch, {"data": [{"id": "claude-b"}, {"id": "claude-a"}]})
    result = clients.probe("claude_api", "https://api.anthropic.com", "k")
    assert result.models == ["claude-a", "claude-b"]
    assert seen[0].get_header("X-api-key") == "k"
    assert seen[0].full_url.startswith("https://api.anthropic.com/v1/models")


def test_chatgpt_api(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _serve(monkeypatch, {"data": [{"id": "gpt-x"}]})
    assert clients.probe("chatgpt_api", "https://api.openai.com", "k").models == ["gpt-x"]
    assert seen[0].get_header("Authorization") == "Bearer k"


def test_gemini_api_strips_prefix_and_skips_non_chat_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _serve(
        monkeypatch,
        {
            "models": [
                {"name": "models/gemini-a", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/embed", "supportedGenerationMethods": ["embedContent"]},
            ]
        },
    )
    result = clients.probe("gemini_api", "https://generativelanguage.googleapis.com", "k")
    assert result.models == ["gemini-a"]
    assert seen[0].get_header("X-goog-api-key") == "k"


@pytest.mark.parametrize(("code", "text"), [(401, "rejected"), (500, "HTTP 500")])
def test_http_errors_are_summarised(monkeypatch: pytest.MonkeyPatch, code: int, text: str) -> None:
    _fail(monkeypatch, urllib.error.HTTPError("u", code, "m", None, io.BytesIO(b"secret-body")))  # type: ignore[arg-type]
    with pytest.raises(AiConnectionError, match=text) as info:
        clients.probe("claude_api", "https://x", "the-key")
    assert "the-key" not in str(info.value)
    assert "secret-body" not in str(info.value)


def test_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _fail(monkeypatch, urllib.error.URLError("down"))
    with pytest.raises(AiConnectionError, match="Could not reach"):
        clients.probe("chatgpt_api", "https://x", "k")


def test_unreadable_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, ["not", "an", "object"])
    with pytest.raises(AiConnectionError, match="could not read"):
        clients.probe("chatgpt_api", "https://x", "k")


def test_claude_code_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(AiConnectionError, match="not installed"):
        clients.probe("claude_code", "", "")


def test_claude_code_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    class Done:
        returncode = 0
        stdout = "2.1.0 (Claude Code)\n"

    monkeypatch.setattr(shutil, "which", lambda _name: "claude")
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: Done())
    result = clients.probe("claude_code", "", "")
    assert result.models == list(CLAUDE_CODE_MODELS)
    assert "2.1.0" in result.detail
