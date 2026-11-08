import json
from pathlib import Path

from typer.testing import CliRunner, Result

from kodalo.cli.cli import app

runner = CliRunner()


def invoke(data_dir: Path, *args: str) -> Result:
    return runner.invoke(app, ["--data-dir", str(data_dir), "settings", "github", *args])


def test_show_defaults_then_set(tmp_path: Path) -> None:
    assert json.loads(invoke(tmp_path, "show", "--json").output)["mode"] == "gh_cli"
    result = invoke(tmp_path, "set", "local_folder", "--folder", str(tmp_path), "--json")
    assert result.exit_code == 0
    assert json.loads(invoke(tmp_path, "show", "--json").output)["mode"] == "local_folder"


def test_set_invalid_exits_1(tmp_path: Path) -> None:
    assert invoke(tmp_path, "set", "ftp").exit_code == 1
    assert invoke(tmp_path, "set", "local_folder").exit_code == 1


def test_check_exit_code(tmp_path: Path) -> None:
    invoke(tmp_path, "set", "local_folder", "--folder", str(tmp_path))
    assert invoke(tmp_path, "check").exit_code == 0
    invoke(tmp_path, "set", "local_folder", "--folder", str(tmp_path / "missing"))
    assert invoke(tmp_path, "check").exit_code == 1


def test_show_as_a_table_lists_every_setting(tmp_path: Path) -> None:
    result = invoke(tmp_path, "show")
    assert result.exit_code == 0
    for label in ("Mode", "Local folder", "Project files to read", "Documents to read"):
        assert label in result.output
    assert "gh_cli" in result.output
    assert "200 KB" in result.output


def test_set_saves_the_limits_and_keeps_them_when_left_out(tmp_path: Path) -> None:
    result = invoke(
        tmp_path,
        "set",
        "web_fetch",
        "--manifest-limit",
        "25",
        "--document-limit",
        "5",
        "--document-max-kb",
        "1500",
        "--json",
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "mode": "web_fetch",
        "local_folder": "",
        "manifest_limit": 25,
        "document_limit": 5,
        "document_max_kb": 1500,
    }
    kept = json.loads(invoke(tmp_path, "set", "gh_cli", "--json").output)
    assert (kept["manifest_limit"], kept["document_limit"], kept["document_max_kb"]) == (
        25,
        5,
        1500,
    )


def test_set_keeps_the_folder_when_it_is_left_out(tmp_path: Path) -> None:
    invoke(tmp_path, "set", "local_folder", "--folder", str(tmp_path))
    result = json.loads(invoke(tmp_path, "set", "web_fetch", "--json").output)
    assert result["local_folder"] == str(tmp_path)


def test_set_rejects_limits_out_of_range(tmp_path: Path) -> None:
    for option, bad in [
        ("--manifest-limit", "0"),
        ("--manifest-limit", "101"),
        ("--document-limit", "0"),
        ("--document-limit", "51"),
        ("--document-max-kb", "0"),
        ("--document-max-kb", "2001"),
    ]:
        assert invoke(tmp_path, "set", "gh_cli", option, bad).exit_code == 1


def test_a_rejected_set_keeps_the_saved_setting(tmp_path: Path) -> None:
    invoke(tmp_path, "set", "web_fetch")
    assert invoke(tmp_path, "set", "ftp").exit_code == 1
    assert json.loads(invoke(tmp_path, "show", "--json").output)["mode"] == "web_fetch"


def test_check_as_json_reports_the_result(tmp_path: Path) -> None:
    invoke(tmp_path, "set", "local_folder", "--folder", str(tmp_path))
    result = invoke(tmp_path, "check", "--json")
    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "mode": "local_folder",
        "ok": True,
        "detail": f"Using {tmp_path}.",
    }
    invoke(tmp_path, "set", "local_folder", "--folder", str(tmp_path / "missing"))
    failed = invoke(tmp_path, "check", "--json")
    assert failed.exit_code == 1
    assert json.loads(failed.output)["ok"] is False
