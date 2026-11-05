import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from kodalo.cli.cli import app
from kodalo.core.ai import AiHistory, Probe
from kodalo.core.storage import Database, database_path

runner = CliRunner()


def invoke(data_dir: Path, *args: str, input: str | None = None) -> tuple[int, str]:
    result = runner.invoke(app, ["--data-dir", str(data_dir), "settings", "ai", *args], input=input)
    return result.exit_code, result.output


@pytest.fixture(autouse=True)
def _probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "kodalo.core.ai.service.probe", lambda provider, url, key: Probe(["m"], "Connected.")
    )


def _make_call(data_dir: Path) -> None:
    invoke(data_dir, "set", "claude_api", "--key", input="sk-test-1234567890abcdef\n")
    invoke(data_dir, "test", "claude_api")


def test_history_and_usage_show_a_connection_test(tmp_path: Path) -> None:
    _make_call(tmp_path)
    code, out = invoke(tmp_path, "history", "--json")
    assert code == 0
    data = json.loads(out)
    assert data["total"] == 1
    assert data["items"][0]["purpose"] == "connection_test"
    code, out = invoke(tmp_path, "usage", "--json")
    assert code == 0
    assert json.loads(out)["calls"] == 1
    code, out = invoke(tmp_path, "history", "--show", data["items"][0]["id"], "--json")
    assert code == 0
    assert json.loads(out)["prompt"] is None


def test_tables_and_periods(tmp_path: Path) -> None:
    _make_call(tmp_path)
    assert invoke(tmp_path, "history", "--period", "week")[0] == 0
    assert invoke(tmp_path, "usage")[0] == 0
    custom = ("--period", "custom", "--from", "2000-01-01", "--to", "2000-01-02", "--json")
    assert json.loads(invoke(tmp_path, "history", *custom)[1])["total"] == 0
    assert invoke(tmp_path, "usage", "--period", "decade")[0] == 1
    assert invoke(tmp_path, "history", "--show", "nope")[0] == 1


def test_settings_and_purge(tmp_path: Path) -> None:
    _code, out = invoke(tmp_path, "history-settings", "--json")
    assert json.loads(out) == {"store_text": False, "retention_days": 90}
    _code, out = invoke(
        tmp_path, "history-settings", "--store-text", "--retention-days", "30", "--json"
    )
    assert json.loads(out) == {"store_text": True, "retention_days": 30}
    assert invoke(tmp_path, "history-settings", "--retention-days=-5")[0] == 1
    _make_call(tmp_path)
    assert invoke(tmp_path, "purge-history", input="n\n")[0] == 1
    assert json.loads(invoke(tmp_path, "history", "--json")[1])["total"] == 1
    assert invoke(tmp_path, "purge-history", "--yes")[0] == 0
    assert json.loads(invoke(tmp_path, "history", "--json")[1])["total"] == 0


def test_any_command_removes_old_history_first(tmp_path: Path) -> None:
    database = Database.open(database_path(tmp_path))
    AiHistory(database).record(
        title="old",
        purpose="palette",
        provider="claude_api",
        model="m",
        status="ok",
        at="2020-01-01T00:00:00+00:00",
    )
    database.close()
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "doctor"])
    assert result.exit_code in (0, 1)
    assert json.loads(invoke(tmp_path, "history", "--json")[1])["total"] == 0
