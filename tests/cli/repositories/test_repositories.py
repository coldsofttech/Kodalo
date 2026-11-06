import json
from pathlib import Path

from typer.testing import CliRunner

from kodalo.cli.cli import app

runner = CliRunner()


def invoke(data_dir: Path, *args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["--data-dir", str(data_dir), "repositories", *args])
    return result.exit_code, result.output


def test_add_list_show_and_remove(tmp_path: Path) -> None:
    data = tmp_path / "data"
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("print(1)")
    runner.invoke(
        app, ["--data-dir", str(data), "settings", "github", "set", "local_folder", "--folder", "."]
    )

    assert invoke(data, "add", str(folder))[0] == 1  # details are required the first time
    code, out = invoke(
        data, "add", str(folder), "--owner", "me", "--repo", "proj", "--license", "MIT",
        "--branch", "main", "--json",
    )  # fmt: skip
    assert code == 0
    repo_id = json.loads(out)["id"]

    assert "me/proj" in invoke(data, "list")[1]
    assert json.loads(invoke(data, "list", "--json")[1])[0]["id"] == repo_id
    assert json.loads(invoke(data, "show", repo_id, "--json")[1])["name"] == "proj"

    assert invoke(data, "remove", repo_id)[0] == 1  # asks first; no input means no
    assert invoke(data, "remove", repo_id, "--yes")[0] == 0
    assert "No repositories yet" in invoke(data, "list")[1]
    assert invoke(data, "show", repo_id)[0] == 1
    assert invoke(data, "remove", repo_id, "--yes")[0] == 1


def test_list_empty(tmp_path: Path) -> None:
    assert "No repositories yet" in invoke(tmp_path, "list")[1]
