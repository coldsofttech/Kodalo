import json
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from kodalo.cli.cli import app

runner = CliRunner()


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


def invoke(data_dir: Path, *args: str, input_text: str | None = None) -> Result:
    return runner.invoke(app, ["--data-dir", str(data_dir), "brand", *args], input=input_text)


def test_list_and_show(data_dir: Path) -> None:
    listed = json.loads(invoke(data_dir, "palette", "list", "--json").output)
    assert [(p["name"], p["type"]) for p in listed] == [
        ("Graphite", "system"),
        ("Midnight", "system"),
        ("Paper", "system"),
    ]
    assert "Midnight" in invoke(data_dir, "palette", "list").output
    shown = json.loads(invoke(data_dir, "palette", "show", "paper", "--json").output)
    assert shown["colors"]["background"]["light"] == "#faf7f2"
    assert "primary" in invoke(data_dir, "palette", "show", "Paper").output
    assert invoke(data_dir, "palette", "show", "nope").exit_code == 1


def test_add_set_rename_duplicate_delete(data_dir: Path) -> None:
    assert invoke(data_dir, "palette", "add", "Ocean", "--from-palette", "paper").exit_code == 0
    assert invoke(data_dir, "palette", "add", "Plain").exit_code == 0
    both = invoke(data_dir, "palette", "add", "x", "--from-brand", "a", "--from-palette", "b")
    assert both.exit_code == 1
    assert invoke(data_dir, "palette", "set", "Ocean", "primary.light", "#112233").exit_code == 0
    shown = json.loads(invoke(data_dir, "palette", "show", "Ocean", "--json").output)
    assert shown["colors"]["primary"]["light"] == "#112233"
    bad = invoke(data_dir, "palette", "set", "Ocean", "primary.light", "blue")
    assert bad.exit_code == 1
    assert "primary.light" in bad.output
    assert invoke(data_dir, "palette", "set", "Paper", "primary.light", "#112233").exit_code == 1
    assert invoke(data_dir, "palette", "rename", "Ocean", "Ocean").exit_code == 1
    assert invoke(data_dir, "palette", "rename", "Ocean", "Sea").exit_code == 0
    assert invoke(data_dir, "palette", "duplicate", "Sea", "Sea 2").exit_code == 0
    assert invoke(data_dir, "palette", "delete", "Sea 2", input_text="n\n").exit_code == 1
    assert invoke(data_dir, "palette", "delete", "Sea 2", "--yes").exit_code == 0
    assert invoke(data_dir, "palette", "delete", "Paper", "--yes").exit_code == 1


def test_add_from_a_brand_and_create_a_brand_from_a_palette(data_dir: Path) -> None:
    invoke(data_dir, "create", "Main", "--palette", "paper")
    assert invoke(data_dir, "palette", "add", "Mine", "--from-brand", "Main").exit_code == 0
    assert invoke(data_dir, "create", "Other", "--palette", "Mine").exit_code == 0
    shown = json.loads(invoke(data_dir, "show", "Other", "--json").output)
    assert shown["data"]["colors"]["background"]["light"] == "#faf7f2"


def test_export_and_import(data_dir: Path, tmp_path: Path) -> None:
    exported = json.loads(invoke(data_dir, "palette", "export", "Paper").output)
    assert (exported["format"], exported["name"]) == ("kodalo-palette", "Paper")
    file = tmp_path / "paper.json"
    assert invoke(data_dir, "palette", "export", "Paper", "-o", str(file)).exit_code == 0
    assert invoke(data_dir, "palette", "import", str(file)).exit_code == 0
    assert invoke(data_dir, "palette", "import", str(file), "--name", "Other").exit_code == 0
    listed = json.loads(invoke(data_dir, "palette", "list", "--json").output)
    assert {"Paper (2)", "Other"} <= {p["name"] for p in listed}
    file.write_text(json.dumps({**exported, "colors": {}}), encoding="utf-8")
    assert invoke(data_dir, "palette", "import", str(file)).exit_code == 1
