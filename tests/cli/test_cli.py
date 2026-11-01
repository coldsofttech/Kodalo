import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import kodalo.core
from kodalo.cli.cli import app, run

runner = CliRunner()

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def plain(text: str) -> str:
    """Remove color codes. Typer's help always colors output on GitHub Actions."""
    return ANSI.sub("", text)


def test_help_lists_commands_and_options() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for text in ("brand", "doctor", "--version", "--verbose", "--quiet", "--no-color"):
        assert text in plain(result.output)


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert kodalo.core.__version__ in result.output


def test_verbose_and_quiet_conflict() -> None:
    result = runner.invoke(app, ["--verbose", "--quiet", "doctor"])

    assert result.exit_code == 2


def test_doctor_shows_version(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "doctor"])

    assert result.exit_code == 0
    assert kodalo.core.__version__ in result.output
    assert "Python" in result.output


def test_no_color_flag_is_accepted() -> None:
    result = runner.invoke(app, ["--no-color", "doctor"])

    assert result.exit_code == 0
    assert kodalo.core.__version__ in result.output


def test_doctor_json(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--data-dir", str(tmp_path), "doctor", "--json"])

    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload["healthy"] is True
    versions = {c["name"]: c["detail"] for c in payload["checks"]}
    assert versions["Kodalo"] == kodalo.core.__version__


def test_doctor_reports_brand_profiles(tmp_path: Path) -> None:
    runner.invoke(app, ["--data-dir", str(tmp_path), "brand", "create", "Main"])

    result = runner.invoke(app, ["--data-dir", str(tmp_path), "doctor", "--json"])

    details = {c["name"]: c["detail"] for c in json.loads(result.output)["checks"]}
    assert details["Brand profiles"] == "1 (default: Main)"
    assert "up to date" in details["Database"]


def test_doctor_fails_for_a_database_from_a_newer_version(tmp_path: Path) -> None:
    runner.invoke(app, ["--data-dir", str(tmp_path), "brand", "create", "Main"])
    with sqlite3.connect(tmp_path / "kodalo.db") as connection:
        connection.execute("UPDATE schema_migrations SET version_num = '9999'")

    result = runner.invoke(app, ["--data-dir", str(tmp_path), "doctor"])

    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_doctor_fails_for_a_file_that_is_not_a_database(tmp_path: Path) -> None:
    (tmp_path / "kodalo.db").write_text("not a database", encoding="utf-8")

    result = runner.invoke(app, ["--data-dir", str(tmp_path), "doctor"])

    assert result.exit_code == 1


def _boom(*_: object) -> list[object]:
    raise RuntimeError("boom")


def test_unexpected_error_is_short_by_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["kodalo", "doctor"])
    monkeypatch.setattr("kodalo.cli.cli.run_checks", _boom)

    with pytest.raises(SystemExit) as exit_info:
        run()

    stderr = capsys.readouterr().err
    assert exit_info.value.code == 1
    assert "RuntimeError: boom" in stderr
    assert "--verbose" in stderr
    assert "Traceback" not in stderr


def test_unexpected_error_shows_traceback_with_verbose(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["kodalo", "--verbose", "doctor"])
    monkeypatch.setattr("kodalo.cli.cli.run_checks", _boom)

    with pytest.raises(SystemExit):
        run()

    assert "Traceback" in capsys.readouterr().err
