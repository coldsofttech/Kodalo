import json
from pathlib import Path

from typer.testing import CliRunner

from kodalo.cli.cli import app

runner = CliRunner()


def invoke(data_dir: Path, *args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["--data-dir", str(data_dir), "studio", *args])
    return result.exit_code, result.output


def test_read_local_folder_list_and_show(tmp_path: Path) -> None:
    data = tmp_path / "data"
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("print(1)")
    runner.invoke(
        app, ["--data-dir", str(data), "settings", "github", "set", "local_folder", "--folder", "."]
    )

    assert invoke(data, "read", str(folder))[0] == 1  # details are required the first time
    code, out = invoke(
        data, "read", str(folder), "--owner", "me", "--repo", "proj", "--license", "MIT",
        "--branch", "main", "--json",
    )  # fmt: skip
    assert code == 0
    info = json.loads(out)
    assert info["languages"][0]["name"] == "Python"

    assert invoke(data, "read", str(folder))[0] == 0  # stored, no details needed
    assert "me/proj" in invoke(data, "list")[1]
    assert json.loads(invoke(data, "show", info["id"], "--json")[1])["name"] == "proj"
    assert invoke(data, "show", "nope")[0] == 1


def test_list_empty(tmp_path: Path) -> None:
    assert "No repositories yet" in invoke(tmp_path, "list")[1]
