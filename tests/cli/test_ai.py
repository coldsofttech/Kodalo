import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kodalo.cli.cli import app
from kodalo.core.ai import AiConnectionError, Probe
from tests.conftest import MemorySecrets

runner = CliRunner()
KEY = "sk-test-1234567890abcdef"


def invoke(data_dir: Path, *args: str, input: str | None = None) -> tuple[int, str]:
    result = runner.invoke(app, ["--data-dir", str(data_dir), "settings", "ai", *args], input=input)
    return result.exit_code, result.output


@pytest.fixture
def probe_result(monkeypatch: pytest.MonkeyPatch) -> dict[str, str | None]:
    state: dict[str, str | None] = {"error": None}

    def fake(provider: str, base_url: str, api_key: str) -> Probe:
        if state["error"]:
            raise AiConnectionError(state["error"])
        return Probe(["m-b", "m-a"], "Connected. 2 models available.")

    monkeypatch.setattr("kodalo.core.ai.service.probe", fake)
    return state


def test_list_shows_every_provider(tmp_path: Path) -> None:
    code, out = invoke(tmp_path, "list", "--json")
    assert code == 0
    assert [c["provider"] for c in json.loads(out)] == [
        "claude_api",
        "claude_code",
        "chatgpt_api",
        "gemini_api",
    ]
    assert invoke(tmp_path, "list")[0] == 0


def test_set_reads_the_key_from_a_hidden_prompt(tmp_path: Path) -> None:
    code, out = invoke(tmp_path, "set", "claude_api", "--key", "--json", input=KEY + "\n")
    assert code == 0
    data = json.loads(out[out.index("{") :])
    assert data["has_key"] is True
    assert data["key_hint"] == KEY[-4:]
    assert KEY not in out
    assert MemorySecrets.values == {"ai/claude_api": KEY}
    assert invoke(tmp_path, "show", "claude_api")[0] == 0


def test_set_rejects_bad_values(tmp_path: Path) -> None:
    assert invoke(tmp_path, "set", "nope")[0] == 1
    assert invoke(tmp_path, "set", "claude_code", "--key", input=KEY + "\n")[0] == 1
    assert invoke(tmp_path, "set", "claude_api", "--base-url", "ftp://x")[0] == 1


def test_test_exit_codes(tmp_path: Path, probe_result: dict[str, str | None]) -> None:
    invoke(tmp_path, "set", "claude_api", "--key", input=KEY + "\n")
    code, out = invoke(tmp_path, "test", "claude_api")
    assert code == 0
    assert "ok" in out

    probe_result["error"] = "The provider rejected the API key."
    code, out = invoke(tmp_path, "test", "claude_api", "--json")
    assert code == 1
    assert json.loads(out)["ok"] is False

    assert invoke(tmp_path, "test", "gemini_api")[0] == 1  # no key saved


def test_default_and_remove(tmp_path: Path) -> None:
    assert invoke(tmp_path, "default", "claude_api")[0] == 1  # not saved
    invoke(tmp_path, "set", "claude_api", "--key", input=KEY + "\n")
    assert invoke(tmp_path, "default", "claude_api")[0] == 0
    invoke(tmp_path, "set", "claude_api", "--disable")
    assert invoke(tmp_path, "default", "claude_api")[0] == 1

    code, out = invoke(tmp_path, "remove", "claude_api")
    assert code == 0
    assert "Removed" in out
    assert MemorySecrets.values == {}
    assert "was not saved" in invoke(tmp_path, "remove", "claude_api")[1]


def test_models(tmp_path: Path, probe_result: dict[str, str | None]) -> None:
    invoke(tmp_path, "set", "claude_api", "--key", input=KEY + "\n")
    code, out = invoke(tmp_path, "models", "refresh", "claude_api", "--json")
    assert code == 0
    assert [m["name"] for m in json.loads(out)] == ["m-a", "m-b"]

    code, out = invoke(
        tmp_path, "models", "set", "claude_api", "mine",
        "--max-tokens", "500", "--temperature", "0.5", "--timeout", "30", "--json",
    )  # fmt: skip
    assert code == 0
    assert json.loads(out)[0]["max_tokens"] == 500

    assert invoke(tmp_path, "models", "default", "claude_api", "mine")[0] == 0
    code, out = invoke(tmp_path, "models", "list", "claude_api", "--json")
    assert [m["name"] for m in json.loads(out) if m["is_default"]] == ["mine"]
    assert invoke(tmp_path, "models", "list", "claude_api")[0] == 0

    assert invoke(tmp_path, "models", "remove", "claude_api", "mine")[0] == 0
    assert invoke(tmp_path, "models", "remove", "claude_api", "mine")[0] == 1
    assert invoke(tmp_path, "models", "set", "claude_api", "x", "--temperature", "9")[0] == 1


def test_refresh_failure_exits_with_1(tmp_path: Path, probe_result: dict[str, str | None]) -> None:
    invoke(tmp_path, "set", "claude_api", "--key", input=KEY + "\n")
    probe_result["error"] = "Could not reach the provider."
    assert invoke(tmp_path, "models", "refresh", "claude_api")[0] == 1
