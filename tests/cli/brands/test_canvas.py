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


def test_list_add_edit_show_duplicate_delete(data_dir: Path) -> None:
    listed = json.loads(invoke(data_dir, "canvas", "list", "--json").output)
    assert len(listed) == 5
    assert invoke(data_dir, "canvas", "list").exit_code == 0

    assert invoke(data_dir, "canvas", "add", "Feed", "1080", "1350").exit_code == 0
    assert invoke(data_dir, "canvas", "edit", "Feed", "--width", "1000").exit_code == 0
    shown = json.loads(invoke(data_dir, "canvas", "show", "feed", "--json").output)
    assert (shown["width"], shown["type"]) == (1000, "user")
    assert "Feed" in invoke(data_dir, "canvas", "show", "Feed").output
    assert invoke(data_dir, "canvas", "duplicate", "Feed", "Feed 2").exit_code == 0
    assert invoke(data_dir, "canvas", "delete", "Feed 2", "--yes").exit_code == 0
    assert invoke(data_dir, "canvas", "delete", "Feed", input_text="n\n").exit_code == 1


def test_errors_and_layout_use(data_dir: Path) -> None:
    assert invoke(data_dir, "canvas", "edit", "Feed").exit_code == 1
    assert invoke(data_dir, "canvas", "show", "nope").exit_code == 1
    assert invoke(data_dir, "canvas", "edit", "Instagram story", "--width", "500").exit_code == 1
    invoke(data_dir, "canvas", "add", "Feed", "1080", "1350")
    invoke(data_dir, "layout", "add", "Feed layout")
    assert invoke(data_dir, "layout", "set", "Feed layout", "canvas_id", "Feed").exit_code == 0
    invoke(data_dir, "create", "Main")
    result = invoke(data_dir, "settings", "set", "Main", "layout_id", "Feed layout")
    assert result.exit_code == 0
    shown = json.loads(invoke(data_dir, "show", "Main", "--json").output)
    assert shown["canvas"]["name"] == "Feed"
    assert shown["layout"]["name"] == "Feed layout"
    assert invoke(data_dir, "show", "Main").exit_code == 0
    assert invoke(data_dir, "list").exit_code == 0
    blocked = invoke(data_dir, "canvas", "delete", "Feed", "--yes")
    assert blocked.exit_code == 1
    assert "Feed layout" in blocked.output


def test_export_and_import(data_dir: Path, tmp_path: Path) -> None:
    invoke(data_dir, "canvas", "add", "Feed", "1080", "1350")
    exported = json.loads(invoke(data_dir, "canvas", "export", "Feed").output)
    assert (exported["format"], exported["width"]) == ("kodalo-canvas", 1080)
    file = tmp_path / "feed.json"
    assert invoke(data_dir, "canvas", "export", "Feed", "-o", str(file)).exit_code == 0
    assert invoke(data_dir, "canvas", "import", str(file)).exit_code == 0
    assert invoke(data_dir, "canvas", "import", str(file), "--name", "Other").exit_code == 0
    listed = json.loads(invoke(data_dir, "canvas", "list", "--json").output)
    assert {"Feed (2)", "Other"} <= {c["name"] for c in listed}
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert invoke(data_dir, "canvas", "import", str(bad)).exit_code == 1
    bad.write_text("[]", encoding="utf-8")
    assert invoke(data_dir, "canvas", "import", str(bad)).exit_code == 1
    bad.write_text(json.dumps({**exported, "width": 5}), encoding="utf-8")
    assert invoke(data_dir, "canvas", "import", str(bad)).exit_code == 1
