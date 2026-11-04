"""Ask a provider which models it offers, which also shows that the connection works.

Error messages never carry the key or anything the provider sent back.
"""

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from kodalo.core.ai.errors import AiConnectionError
from kodalo.core.ai.providers import CLAUDE_CODE_MODELS

_TIMEOUT = 15
_MAX_BYTES = 4_000_000
_ANTHROPIC_VERSION = "2023-06-01"


@dataclass(frozen=True)
class Probe:
    """What a provider answered: the names of its models and a short note for the user."""

    models: list[str]
    detail: str


Prober = Callable[[str, str, str], Probe]
"""Takes the provider id, the base URL and the API key, and returns a :class:`Probe`."""


def probe(provider: str, base_url: str, api_key: str) -> Probe:
    """Check the connection to ``provider`` and list its models. Raises ``AiConnectionError``."""
    if provider == "claude_code":
        return _probe_claude_code()
    if provider == "claude_api":
        data = _get_json(
            f"{base_url}/v1/models?limit=1000",
            {"x-api-key": api_key, "anthropic-version": _ANTHROPIC_VERSION},
        )
        names = [str(item["id"]) for item in _items(data, "data") if "id" in item]
    elif provider == "chatgpt_api":
        data = _get_json(f"{base_url}/v1/models", {"Authorization": f"Bearer {api_key}"})
        names = [str(item["id"]) for item in _items(data, "data") if "id" in item]
    elif provider == "gemini_api":
        data = _get_json(f"{base_url}/v1beta/models?pageSize=1000", {"x-goog-api-key": api_key})
        names = [
            str(item["name"]).removeprefix("models/")
            for item in _items(data, "models")
            if "name" in item
            and "generateContent" in item.get("supportedGenerationMethods", ["generateContent"])
        ]
    else:
        raise AiConnectionError(f"Unknown provider: {provider}.")
    return Probe(sorted(set(names)), f"Connected. {len(names)} models available.")


def _probe_claude_code() -> Probe:
    program = shutil.which("claude")
    if program is None:
        raise AiConnectionError("Claude Code is not installed, or is not on your PATH.")
    try:
        result = subprocess.run(  # noqa: S603
            [program, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AiConnectionError("Claude Code did not answer.") from exc
    if result.returncode != 0:
        raise AiConnectionError("Claude Code did not answer.")
    version = result.stdout.strip().splitlines()[0][:80] if result.stdout.strip() else ""
    detail = f"Claude Code is installed ({version})." if version else "Claude Code is installed."
    return Probe(list(CLAUDE_CODE_MODELS), detail)


@dataclass(frozen=True)
class GenerateRequest:
    """One prompt for one model. ``temperature`` and ``timeout_s`` of ``None`` use the defaults."""

    provider: str
    base_url: str
    api_key: str
    model: str
    system: str
    prompt: str
    max_tokens: int
    temperature: float | None = None
    timeout_s: int | None = None


@dataclass(frozen=True)
class Generation:
    """What a model answered, and how many tokens the provider counted for it."""

    text: str
    input_tokens: int
    output_tokens: int


Generator = Callable[[GenerateRequest], Generation]
"""Sends a :class:`GenerateRequest` and returns the answer."""

_GENERATE_TIMEOUT = 120


def generate(request: GenerateRequest) -> Generation:
    """Ask the model for JSON text. Raises ``AiConnectionError``."""
    timeout = request.timeout_s or _GENERATE_TIMEOUT
    if request.provider == "claude_code":
        return _generate_claude_code(request, timeout)
    if request.provider == "claude_api":
        body: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        data = _post_json(
            f"{request.base_url}/v1/messages",
            {"x-api-key": request.api_key, "anthropic-version": _ANTHROPIC_VERSION},
            body,
            timeout,
        )
        parts = data.get("content") if isinstance(data, dict) else None
        text = "".join(str(p.get("text", "")) for p in parts or [] if isinstance(p, dict))
        usage = _usage(data)
        return Generation(text, _count(usage, "input_tokens"), _count(usage, "output_tokens"))
    if request.provider == "chatgpt_api":
        body = {
            "model": request.model,
            "max_completion_tokens": request.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
        }
        if request.temperature is not None:
            body["temperature"] = request.temperature
        data = _post_json(
            f"{request.base_url}/v1/chat/completions",
            {"Authorization": f"Bearer {request.api_key}"},
            body,
            timeout,
        )
        try:
            text = str(data["choices"][0]["message"]["content"] or "")
        except (KeyError, IndexError, TypeError) as exc:
            raise AiConnectionError(_UNREADABLE) from exc
        usage = _usage(data)
        return Generation(text, _count(usage, "prompt_tokens"), _count(usage, "completion_tokens"))
    if request.provider == "gemini_api":
        config: dict[str, Any] = {
            "maxOutputTokens": request.max_tokens,
            "responseMimeType": "application/json",
        }
        if request.temperature is not None:
            config["temperature"] = request.temperature
        data = _post_json(
            f"{request.base_url}/v1beta/models/{request.model}:generateContent",
            {"x-goog-api-key": request.api_key},
            {
                "systemInstruction": {"parts": [{"text": request.system}]},
                "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
                "generationConfig": config,
            },
            timeout,
        )
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(str(p.get("text", "")) for p in parts)
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise AiConnectionError(_UNREADABLE) from exc
        usage = data.get("usageMetadata") if isinstance(data, dict) else None
        return Generation(
            text, _count(usage, "promptTokenCount"), _count(usage, "candidatesTokenCount")
        )
    raise AiConnectionError(f"Unknown provider: {request.provider}.")


def _generate_claude_code(request: GenerateRequest, timeout: int) -> Generation:
    program = shutil.which("claude")
    if program is None:
        raise AiConnectionError("Claude Code is not installed, or is not on your PATH.")
    command = [program, "-p", "--output-format", "json", "--max-turns", "1"]
    if request.model:
        command += ["--model", request.model]
    try:
        result = subprocess.run(  # noqa: S603
            command,
            input=f"{request.system}\n\n{request.prompt}",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )
        data = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        raise AiConnectionError("Claude Code did not answer.") from exc
    if result.returncode != 0 or not isinstance(data, dict) or data.get("is_error"):
        raise AiConnectionError("Claude Code did not answer.")
    usage = _usage(data)
    received = sum(
        _count(usage, key)
        for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )
    return Generation(str(data.get("result", "")), received, _count(usage, "output_tokens"))


def _usage(data: Any) -> Any:
    return data.get("usage") if isinstance(data, dict) else None


def _count(usage: Any, key: str) -> int:
    value = usage.get(key) if isinstance(usage, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


_UNREADABLE = "The provider sent an answer Kodalo could not read."


def _post_json(url: str, headers: dict[str, str], body: dict[str, Any], timeout: int) -> Any:
    request = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    return _open_json(request, timeout)


def _get_json(url: str, headers: dict[str, str]) -> Any:
    request = urllib.request.Request(  # noqa: S310
        url, headers={**headers, "Accept": "application/json"}
    )
    return _open_json(request, _TIMEOUT)


def _open_json(request: urllib.request.Request, timeout: int) -> Any:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read(_MAX_BYTES))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise AiConnectionError("The provider rejected the API key.") from exc
        raise AiConnectionError(f"The provider returned an error (HTTP {exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise AiConnectionError("Could not reach the provider.") from exc
    except ValueError as exc:
        raise AiConnectionError("The provider sent an answer Kodalo could not read.") from exc


def _items(data: Any, key: str) -> list[dict[str, Any]]:
    items = data.get(key) if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise AiConnectionError("The provider sent an answer Kodalo could not read.")
    return [item for item in items if isinstance(item, dict)]
