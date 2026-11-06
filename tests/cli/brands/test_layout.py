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


def test_list_show_add_set_settings(data_dir: Path) -> None:
    listed = json.loads(invoke(data_dir, "layout", "list", "--json").output)
    assert [(lay["name"], lay["slides_count"]) for lay in listed] == [
        ("Compact", 6),
        ("Default", 6),
        ("Spacious", 6),
    ]
    assert invoke(data_dir, "layout", "list").exit_code == 0

    assert invoke(data_dir, "layout", "add", "Mine").exit_code == 0
    copied = invoke(data_dir, "layout", "add", "Compact copy", "--from-layout", "Compact")
    assert copied.exit_code == 0
    assert invoke(data_dir, "layout", "set", "Mine", "slides_count", "9").exit_code == 0
    assert invoke(data_dir, "layout", "set", "Mine", "canvas_id", "X landscape").exit_code == 0
    shown = json.loads(invoke(data_dir, "layout", "show", "mine", "--json").output)
    assert (shown["slides_count"], shown["canvas_id"]) == (9, "system-x_landscape")
    assert "Mine" in invoke(data_dir, "layout", "show", "Mine").output
    settings = json.loads(invoke(data_dir, "layout", "settings", "Mine", "--json").output)
    assert settings["slides_count"] == 9
    assert "slides_count" in invoke(data_dir, "layout", "settings", "Mine").output
    bad = invoke(data_dir, "layout", "set", "Mine", "slides_count", "0")
    assert bad.exit_code == 1
    assert "slides_count" in bad.output
    assert invoke(data_dir, "layout", "set", "Default", "align", "center").exit_code == 1


def test_rename_duplicate_delete_and_use(data_dir: Path) -> None:
    invoke(data_dir, "layout", "add", "Mine")
    assert invoke(data_dir, "layout", "rename", "Mine", "Mine").exit_code == 1
    assert invoke(data_dir, "layout", "rename", "Mine", "Renamed").exit_code == 0
    assert invoke(data_dir, "layout", "duplicate", "Renamed", "Copy").exit_code == 0
    invoke(data_dir, "create", "Main")
    assert invoke(data_dir, "settings", "set", "Main", "layout_id", "Renamed").exit_code == 0
    blocked = invoke(data_dir, "layout", "delete", "Renamed", "--yes")
    assert blocked.exit_code == 1
    assert "Main" in blocked.output
    assert invoke(data_dir, "layout", "delete", "Copy", input_text="n\n").exit_code == 1
    assert invoke(data_dir, "layout", "delete", "Copy", "--yes").exit_code == 0
    assert invoke(data_dir, "layout", "show", "nope").exit_code == 1


def test_export_and_import(data_dir: Path, tmp_path: Path) -> None:
    invoke(data_dir, "layout", "add", "Mine")
    invoke(data_dir, "layout", "set", "Mine", "slides_count", "8")
    exported = json.loads(invoke(data_dir, "layout", "export", "Mine").output)
    assert (exported["format"], exported["slides_count"]) == ("kodalo-layout", 8)
    file = tmp_path / "mine.json"
    assert invoke(data_dir, "layout", "export", "Mine", "-o", str(file)).exit_code == 0
    assert invoke(data_dir, "layout", "import", str(file)).exit_code == 0
    assert invoke(data_dir, "layout", "import", str(file), "--name", "Other").exit_code == 0
    listed = json.loads(invoke(data_dir, "layout", "list", "--json").output)
    assert {"Mine (2)", "Other"} <= {lay["name"] for lay in listed}
    file.write_text(json.dumps({**exported, "slides_count": 0}), encoding="utf-8")
    assert invoke(data_dir, "layout", "import", str(file)).exit_code == 1
