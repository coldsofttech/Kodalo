import json
from pathlib import Path

from typer.testing import CliRunner

from kodalo.cli.cli import app

runner = CliRunner()


def invoke(data_dir: Path, *args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["--data-dir", str(data_dir), "repositories", *args])
    return result.exit_code, result.output


def test_add_local_folder_list_and_show(tmp_path: Path) -> None:
    data = tmp_path / "data"
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "a.py").write_text("print(1)")
    (folder / "tests").mkdir()
    (folder / "pyproject.toml").write_text("[project]")
    (folder / "turbo.json").write_text("{}")
    (folder / "README.md").write_text("# proj")
    (folder / "docs").mkdir()
    runner.invoke(
        app, ["--data-dir", str(data), "settings", "github", "set", "local_folder", "--folder", "."]
    )

    assert invoke(data, "add", str(folder))[0] == 1  # details are required the first time
    code, out = invoke(
        data, "add", str(folder), "--owner", "me", "--repo", "proj", "--license", "MIT",
        "--branch", "main", "--json",
    )  # fmt: skip
    assert code == 0
    info = json.loads(out)
    assert info["languages"][0]["name"] == "Python"
    assert sorted(d["path"] for d in info["notable_dirs"]) == ["docs", "tests"]
    assert [m["path"] for m in info["manifests"]] == ["pyproject.toml"]
    assert info["is_monorepo"] is True
    assert info["monorepo_signals"] == ["turbo.json"]
    assert "paths" not in info
    assert info["documentation"]["readmes"] == ["README.md"]
    assert info["documentation"]["docs_dir"] == "docs"
    assert info["skipped"] == []

    assert invoke(data, "add", str(folder))[0] == 0  # stored, no details needed
    assert "me/proj" in invoke(data, "list")[1]
    shown = invoke(data, "show", info["id"])[1]
    assert "Notable folders" in shown
    assert "turbo.json" in shown
    assert "Documentation" in shown
    assert "README.md" in shown
    assert "Not read" in shown
    assert json.loads(invoke(data, "show", info["id"], "--json")[1])["name"] == "proj"
    assert invoke(data, "show", "nope")[0] == 1


def test_list_empty(tmp_path: Path) -> None:
    assert "No repositories yet" in invoke(tmp_path, "list")[1]
