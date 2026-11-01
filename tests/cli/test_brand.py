import json
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from kodalo.cli.cli import app

runner = CliRunner()
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


def invoke(data_dir: Path, *args: str, input_text: str | None = None) -> Result:
    return runner.invoke(app, ["--data-dir", str(data_dir), "brand", *args], input=input_text)


def names(data_dir: Path) -> dict[str, bool]:
    listed = json.loads(invoke(data_dir, "list", "--json").output)
    return {b["name"]: b["is_default"] for b in listed}


def test_empty_list(data_dir: Path) -> None:
    result = invoke(data_dir, "list")
    assert result.exit_code == 0
    assert "No brands yet" in result.output
    assert json.loads(invoke(data_dir, "list", "--json").output) == []


def test_create_list_show(data_dir: Path) -> None:
    assert invoke(data_dir, "create", "Main", "--palette", "paper").exit_code == 0
    assert names(data_dir) == {"Main": True}
    shown = json.loads(invoke(data_dir, "show", "main", "--json").output)
    assert shown["data"]["colors"]["background"]["light"] == "#faf7f2"
    table = invoke(data_dir, "show", shown["id"])
    assert "colors.primary" in table.output
    assert "(default)" in table.output
    assert "Main" in invoke(data_dir, "list").output


def test_create_errors(data_dir: Path) -> None:
    assert invoke(data_dir, "create", "Main").exit_code == 0
    duplicate = invoke(data_dir, "create", "main")
    assert duplicate.exit_code == 1
    assert "already exists" in duplicate.output
    unknown = invoke(data_dir, "create", "Other", "--palette", "neon")
    assert unknown.exit_code == 1
    assert "Unknown palette" in unknown.output
    missing = invoke(data_dir, "show", "nope")
    assert missing.exit_code == 1
    assert "No brand named" in missing.output


def test_rename_default_duplicate_delete(data_dir: Path) -> None:
    invoke(data_dir, "create", "A")
    invoke(data_dir, "create", "B", "--default")
    assert invoke(data_dir, "rename", "A", "Alpha").exit_code == 0
    assert invoke(data_dir, "duplicate", "Alpha", "Alpha copy").exit_code == 0
    assert invoke(data_dir, "default", "alpha").exit_code == 0
    assert names(data_dir) == {"Alpha": True, "Alpha copy": False, "B": False}
    refused = invoke(data_dir, "delete", "B", input_text="n\n")
    assert refused.exit_code == 1
    assert invoke(data_dir, "delete", "B", input_text="y\n").exit_code == 0
    assert invoke(data_dir, "delete", "Alpha copy", "--yes").exit_code == 0
    assert names(data_dir) == {"Alpha": True}


def test_set_and_settings(data_dir: Path) -> None:
    invoke(data_dir, "create", "Main")
    assert invoke(data_dir, "set", "Main", "colors.primary.light", "#112233").exit_code == 0
    shown = json.loads(invoke(data_dir, "show", "Main", "--json").output)
    assert shown["data"]["colors"]["primary"]["light"] == "#112233"
    bad = invoke(data_dir, "set", "Main", "colors.primary.light", "blue")
    assert bad.exit_code == 1
    assert "colors.primary.light" in bad.output
    assert "layout.align" in invoke(data_dir, "settings", "Main").output


def test_check_and_strict(data_dir: Path) -> None:
    invoke(data_dir, "create", "Main")
    assert invoke(data_dir, "check", "Main", "--strict").exit_code == 0
    invoke(data_dir, "set", "Main", "colors.text.light", "#eeeeee")
    assert invoke(data_dir, "check", "Main").exit_code == 0
    failing = invoke(data_dir, "check", "Main", "--strict", "--json")
    assert failing.exit_code == 1
    assert any(not r["passes"] for r in json.loads(failing.output))


def test_palettes_and_fonts(data_dir: Path) -> None:
    keys = [p["key"] for p in json.loads(invoke(data_dir, "palettes", "--json").output)]
    assert keys == ["midnight", "paper", "graphite"]
    assert "Midnight" in invoke(data_dir, "palettes").output
    bundled = json.loads(invoke(data_dir, "fonts", "--bundled", "--json").output)
    assert {f["source"] for f in bundled} == {"bundled"}
    assert "Inter" in invoke(data_dir, "fonts", "--bundled").output


def test_logo_export_import(data_dir: Path, tmp_path: Path) -> None:
    invoke(data_dir, "create", "Main")
    logo = tmp_path / "logo.png"
    logo.write_bytes(PNG)
    assert invoke(data_dir, "logo", "set", "Main", str(logo)).exit_code == 0
    assert invoke(data_dir, "logo", "set", "Main", str(logo), "--dark").exit_code == 0
    exported = tmp_path / "main.json"
    assert invoke(data_dir, "export", "Main", "--output", str(exported)).exit_code == 0
    assert json.loads(exported.read_text(encoding="utf-8"))["format"] == "kodalo-brand"
    assert invoke(data_dir, "import", str(exported), "--name", "Copy").exit_code == 0
    shown = json.loads(invoke(data_dir, "show", "Copy", "--json").output)
    assert shown["data"]["logo"]["file"]
    assert json.loads(invoke(data_dir, "export", "Main").output)["name"] == "Main"
    assert invoke(data_dir, "logo", "remove", "Main", "--dark").exit_code == 0


def test_bad_logo_and_bad_import(data_dir: Path, tmp_path: Path) -> None:
    invoke(data_dir, "create", "Main")
    bad = tmp_path / "bad.svg"
    bad.write_bytes(b"<svg><script/></svg>")
    result = invoke(data_dir, "logo", "set", "Main", str(bad))
    assert result.exit_code == 1
    assert "not allowed" in result.output
    for text in ("not json", "[]", '{"format": "x"}'):
        broken = tmp_path / "broken.json"
        broken.write_text(text, encoding="utf-8")
        assert invoke(data_dir, "import", str(broken)).exit_code == 1


def test_data_dir_is_where_the_database_goes(tmp_path: Path) -> None:
    target = tmp_path / "chosen"
    assert runner.invoke(app, ["--data-dir", str(target), "brand", "create", "Main"]).exit_code == 0
    assert (target / "kodalo.db").exists()


def test_quiet_hides_messages(data_dir: Path) -> None:
    result = runner.invoke(app, ["--data-dir", str(data_dir), "-q", "brand", "create", "Main"])
    assert result.exit_code == 0
    assert "Created" not in result.output
