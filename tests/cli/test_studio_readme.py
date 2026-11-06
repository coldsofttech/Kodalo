import json
from pathlib import Path

from typer.testing import CliRunner

from kodalo.cli.cli import app

runner = CliRunner()
README = """# Proj

Proj tidies things up.

## Features

- **Tidy**: tidy things

## Install

```
pip install proj
```
"""


def invoke(data_dir: Path, *args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["--data-dir", str(data_dir), "studio", *args])
    return result.exit_code, result.output


def _folder(tmp_path: Path, readme: str = README) -> tuple[Path, Path]:
    data = tmp_path / "data"
    folder = tmp_path / "proj"
    folder.mkdir()
    (folder / "README.md").write_text(readme, encoding="utf-8")
    runner.invoke(
        app, ["--data-dir", str(data), "settings", "github", "set", "local_folder", "--folder", "."]
    )
    return data, folder


READ = ("--owner", "me", "--repo", "proj", "--branch", "main", "--license", "MIT")


def test_readme_is_shown_and_saved(tmp_path: Path) -> None:
    data, folder = _folder(tmp_path)

    code, out = invoke(data, "read", str(folder), *READ, "--readme")
    assert code == 0
    for text in ("Purpose", "Proj tidies things up.", "pip install proj", "Tidy", "README.md"):
        assert text in out

    code, out = invoke(data, "read", str(folder), "--readme", "--json")
    body = json.loads(out)
    assert body["repository"]["name"] == "proj"
    assert body["readme"]["capabilities"][0]["name"] == "Tidy"
    assert body["readme"]["documents"][0]["status"] == "read"
    assert "paths" not in body["repository"]


def test_the_ai_needs_a_connection_and_a_document(tmp_path: Path) -> None:
    data, folder = _folder(tmp_path)

    code, out = invoke(data, "read", str(folder), *READ, "--readme-with-ai", "--yes")
    assert code == 1  # capabilities exist, but no AI connection is set up

    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "main.py").write_text("print(1)", encoding="utf-8")  # no README
    code, out = invoke(
        data, "read", str(plain), "--owner", "me", "--repo", "plain", "--branch", "main",
        "--license", "MIT", "--readme-with-ai", "--yes",
    )  # fmt: skip
    assert code == 0
    assert "nothing to send" in out


def test_document_settings_are_shown_and_changed(tmp_path: Path) -> None:
    base = ["--data-dir", str(tmp_path), "settings", "github"]

    shown = json.loads(runner.invoke(app, [*base, "show", "--json"]).output)
    assert (shown["document_limit"], shown["document_max_kb"]) == (10, 200)

    result = runner.invoke(
        app, [*base, "set", "gh_cli", "--document-limit", "20", "--document-max-kb", "50"]
    )
    assert result.exit_code == 0
    assert "Documents to read" in result.output
    again = json.loads(runner.invoke(app, [*base, "show", "--json"]).output)
    assert (again["document_limit"], again["document_max_kb"]) == (20, 50)
    assert runner.invoke(app, [*base, "set", "gh_cli", "--document-limit", "0"]).exit_code == 1
