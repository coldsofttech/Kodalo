"""Parser configs: validation and the user's own folder."""

import json
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.repositories.configs.manifest import ConfigError, load_configs, parse_config
from kodalo.core.repositories.parsers.manifest import parse_manifest

VALID: dict[str, Any] = {
    "schema_version": 1,
    "id": "my-stack",
    "ecosystem": "mystack",
    "files": ["stack.json"],
    "format": "json",
    "name": ["name"],
    "dependencies": [{"path": "deps", "shape": "keys"}],
}


def test_user_config_adds_a_stack(tmp_path: Path) -> None:
    (tmp_path / "stack.json").write_text(json.dumps(VALID), encoding="utf-8")

    result = load_configs(tmp_path)
    mine = next(c for c in result.configs if c.id == "my-stack")

    assert result.problems == ()
    assert mine.source == "user"
    assert parse_manifest('{"name": "x", "deps": {"a": 1}}', mine).dependencies == ("a",)


def test_user_config_with_same_id_replaces_the_bundled_one(tmp_path: Path) -> None:
    replacement = {**VALID, "id": "js-package", "files": ["package.json"], "ecosystem": "js"}
    (tmp_path / "js.json").write_text(json.dumps(replacement), encoding="utf-8")

    configs = [c for c in load_configs(tmp_path).configs if c.id == "js-package"]

    assert len(configs) == 1
    assert configs[0].source == "user"


def test_broken_user_configs_are_skipped_with_a_problem(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{ nope", encoding="utf-8")
    (tmp_path / "also.json").write_text(json.dumps({**VALID, "format": "yaml"}), encoding="utf-8")

    result = load_configs(tmp_path)

    assert len(result.problems) == 2
    assert all(c.id != "my-stack" for c in result.configs)
    assert len(result.configs) == 17  # the bundled ones still work


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": 2},
        {"id": "Bad Id"},
        {"files": []},
        {"files": ["sub/package.json"]},
        {"files": [".env"]},
        {"files": ["my-secret.json"]},
        {"format": "lines", "dependencies": [{"regex": "(unclosed"}]},
        {"format": "lines", "dependencies": [{"regex": "no-group"}]},
        {"dependencies": [{"path": "deps", "shape": "bogus"}]},
        {"priority": -1},
        {"format": "none"},
    ],
)
def test_invalid_configs_are_refused(change: dict[str, Any]) -> None:
    with pytest.raises(ConfigError):
        parse_config({**VALID, **change})
