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
