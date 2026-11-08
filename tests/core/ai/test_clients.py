import io
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.ai import GenerateRequest, clients
from kodalo.core.settings.ai import AiConnectionError
from kodalo.core.settings.ai.providers import CLAUDE_CODE_MODELS


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


def test_claude_code_runs_lean_from_an_empty_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    class Done:
        returncode = 0
        stdout = json.dumps(
            {"result": "ok", "usage": {"input_tokens": 2, "cache_creation_input_tokens": 650}}
        )

    def run(command: list[str], **kwargs: object) -> Done:
        seen["command"] = command
        seen["kwargs"] = kwargs
        seen["instructions"] = Path(command[command.index("--system-prompt-file") + 1]).read_text(
            encoding="utf-8"
        )
        return Done()

    monkeypatch.setattr(shutil, "which", lambda _name: "claude")
    monkeypatch.setattr(subprocess, "run", run)
    request = GenerateRequest("claude_code", "", "", "haiku", "SYSTEM", "PROMPT", 100, None, None)
    reply = clients.generate(request)
    command = seen["command"]
    assert isinstance(command, list)
    assert command[command.index("--tools") + 1] == ""
    assert command[command.index("--setting-sources") + 1] == ""
    for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
        assert flag in command
    assert "SYSTEM" not in " ".join(command)
    assert seen["instructions"] == "SYSTEM"
    kwargs = seen["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["input"] == "PROMPT"
    assert kwargs["cwd"] != str(Path.cwd())
    assert (reply.text, reply.input_tokens, reply.output_tokens) == ("ok", 652, 0)


def _claude_code(monkeypatch: pytest.MonkeyPatch, run: object) -> GenerateRequest:
    monkeypatch.setattr(shutil, "which", lambda _name: "claude")
    monkeypatch.setattr(subprocess, "run", run)
    return GenerateRequest("claude_code", "", "", "haiku", "SYSTEM", "PROMPT", 100, None, 30)


def test_claude_code_timeout_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(command: list[str], **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(command, 30)

    request = _claude_code(monkeypatch, run)

    with pytest.raises(AiConnectionError, match="took longer than 30 seconds"):
        clients.generate(request)


def test_claude_code_failure_gives_its_own_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    class Failed:
        returncode = 1
        stdout = ""
        stderr = "Error: not signed in\n"

    class Errored:
        returncode = 0
        stdout = json.dumps({"is_error": True, "result": "Prompt is too long"})
        stderr = ""

    request = _claude_code(monkeypatch, lambda command, **kwargs: Failed())
    with pytest.raises(AiConnectionError, match="did not answer: Error: not signed in"):
        clients.generate(request)

    request = _claude_code(monkeypatch, lambda command, **kwargs: Errored())
    with pytest.raises(AiConnectionError, match="did not answer: Prompt is too long"):
        clients.generate(request)


IMAGES = (("image/png", b"\x89PNG\r\n\x1a\n"),)


@pytest.mark.parametrize(
    ("provider", "answer"),
    [
        ("claude_api", {"content": [{"text": "ok"}], "usage": {}}),
        ("chatgpt_api", {"choices": [{"message": {"content": "ok"}}], "usage": {}}),
        ("gemini_api", {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}),
    ],
)
def test_an_image_is_sent_to_each_api_provider(
    monkeypatch: pytest.MonkeyPatch, provider: str, answer: dict[str, Any]
) -> None:
    seen = _serve(monkeypatch, answer)
    request = GenerateRequest(provider, "https://x", "k", "m", "S", "P", 10, images=IMAGES)

    assert clients.generate(request).text == "ok"

    body = json.loads(seen[0].data)  # type: ignore[arg-type]
    assert "iVBORw0KGgo" in json.dumps(body)  # the PNG header, base64
    assert body.get("messages") or body.get("contents")


def test_claude_code_gets_only_a_file_reader_for_an_image(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    class Done:
        returncode = 0
        stdout = json.dumps({"result": "ok", "usage": {}})

    def run(command: list[str], **kwargs: Any) -> Done:
        seen["command"] = command
        seen["input"] = kwargs["input"]
        seen["files"] = sorted(p.name for p in Path(kwargs["cwd"]).iterdir())
        return Done()

    request = _claude_code(monkeypatch, run)
    request = GenerateRequest(
        "claude_code", "", "", "haiku", "SYSTEM", "PROMPT", 100, None, 30, images=IMAGES
    )

    clients.generate(request)

    command = seen["command"]
    assert command[command.index("--tools") + 1] == "Read"
    assert command[command.index("--allowedTools") + 1] == "Read"
    assert command[command.index("--max-turns") + 1] != "1"
    assert "image-1.png" in seen["input"]
    assert "image-1.png" in seen["files"]
