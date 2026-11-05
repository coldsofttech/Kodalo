"""Framework configs: loading, checking and detecting."""

import json
from pathlib import Path

import pytest

from kodalo.core.repo.framework_config import (
    TOOL_CATEGORIES,
    TOOLING,
    FrameworkConfigError,
    detect_frameworks,
    detect_tooling,
    known_dependencies,
    load_framework_configs,
    load_tooling_configs,
    parse_framework,
    parse_framework_config,
)
from kodalo.core.repo.models import Entry, Manifest

RULES = load_framework_configs(None).rules


def _ids(manifests: list[Manifest], entries: list[Entry] | None = None) -> set[str]:
    return {f.id for f in detect_frameworks(RULES, manifests, entries or [])}


def test_bundled_configs_all_load() -> None:
    configs = load_framework_configs(None)
    assert configs.problems == ()
    assert {"fastapi", "react", "vite"} <= {r.id for r in configs.rules}


def test_dependency_match_is_per_ecosystem_and_ignores_case_and_underscores() -> None:
    python = Manifest("pyproject.toml", "python", dependencies=("FastAPI", "scikit_learn"))
    js = Manifest("package.json", "js", dev_dependencies=("fastapi", "react"))
    assert _ids([python]) == {"fastapi", "scikit-learn"}
    assert _ids([js]) == {"react"}


def test_evidence_names_the_file_and_the_dependency() -> None:
    found = detect_frameworks(
        RULES,
        [
            Manifest("web/package.json", "js", dependencies=("react",)),
            Manifest("package.json", "js", dependencies=("react",)),
        ],
        [],
    )
    assert [(f.id, f.evidence, f.path) for f in found] == [
        ("react", 'package.json: "react"', "package.json")
    ]


def test_lockfiles_are_not_read_for_evidence() -> None:
    lock = Manifest("uv.lock", "python", is_lockfile=True, dependencies=("fastapi",))
    assert _ids([lock]) == set()


def test_file_and_path_markers() -> None:
    entries = [
        Entry("web/vite.config.ts", "file"),
        Entry("manage.py", "file"),
        Entry("app.xcodeproj", "dir"),
        Entry("blog/wp-content/themes/a.php", "file"),
    ]
    assert _ids([], entries) == {"vite", "django", "xcode", "wordpress"}


def test_known_dependencies_lists_only_covered_names() -> None:
    manifest = Manifest("pyproject.toml", "python", dependencies=("fastapi", "pathspec"))
    assert known_dependencies(RULES, [manifest]) == {"fastapi"}


@pytest.mark.parametrize(
    ("item", "message"),
    [
        ({"id": "Bad Id", "name": "x", "category": "web", "files": ["a"]}, "id must be"),
        ({"id": "x", "name": "x", "category": "nope", "files": ["a"]}, "category must be"),
        ({"id": "x", "name": "x", "category": "web"}, "needs dependencies"),
        ({"id": "x", "name": "x", "category": "web", "paths": ["../a"]}, "relative"),
        ({"id": "x", "name": "x", "category": "web", "files": ["a;b"]}, "plain names"),
        ({"id": "x", "name": "x", "category": "web", "files": ["a"] * 31}, "at most"),
    ],
)
def test_invalid_entries_are_refused(item: dict[str, object], message: str) -> None:
    with pytest.raises(FrameworkConfigError, match=message):
        parse_framework(item)


def test_file_must_be_an_object_with_the_right_version() -> None:
    with pytest.raises(FrameworkConfigError, match="schema_version"):
        parse_framework_config({"frameworks": []})
    with pytest.raises(FrameworkConfigError, match="frameworks must"):
        parse_framework_config({"schema_version": 1, "frameworks": []})


def test_user_configs_add_replace_and_report_problems(tmp_path: Path) -> None:
    mine = {
        "schema_version": 1,
        "frameworks": [
            {"id": "react", "name": "My React", "category": "ui", "dependencies": ["react"]},
            {"id": "htmx", "name": "htmx", "category": "ui", "dependencies": ["htmx.org"]},
        ],
    }
    (tmp_path / "mine.json").write_text(json.dumps(mine), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    configs = load_framework_configs(tmp_path)
    by_id = {r.id: r for r in configs.rules}
    assert by_id["react"].name == "My React"
    assert by_id["react"].source == "user"
    assert "htmx" in by_id
    assert len(configs.problems) == 1
    assert "broken.json" in configs.problems[0]


def test_bundled_tooling_configs_load_and_cover_every_category() -> None:
    configs = load_tooling_configs(None)
    assert configs.problems == ()
    assert {r.category for r in configs.rules} == set(TOOL_CATEGORIES)


def test_tooling_is_found_by_file_folder_and_dependency() -> None:
    rules = load_tooling_configs(None).rules
    pyproject = Manifest("pyproject.toml", "python", dev_dependencies=("ruff", "pytest"))
    entries = [
        Entry(".github/workflows/ci.yml", "file"),
        Entry("Dockerfile", "file"),
        Entry("uv.lock", "file"),
        Entry("src/ui/vite.config.js", "file"),
    ]
    found = {t.id: t for t in detect_tooling(rules, [pyproject], entries)}
    assert {"github-actions", "docker", "uv", "vite", "ruff", "pytest"} <= set(found)
    assert found["github-actions"].category == "ci"
    assert found["ruff"].evidence == 'pyproject.toml: "ruff"'


def test_tooling_uses_its_own_categories() -> None:
    item = {"id": "x", "name": "X", "category": "web", "files": ["x.cfg"]}
    with pytest.raises(FrameworkConfigError, match="category must be one of: build"):
        parse_framework(item, "user", TOOLING)
    with pytest.raises(FrameworkConfigError, match="tools must be a list"):
        parse_framework_config({"schema_version": 1, "frameworks": [item]}, "user", TOOLING)


def test_user_tooling_config_adds_to_and_replaces_bundled(tmp_path: Path) -> None:
    mine = {"id": "make", "name": "My Make", "category": "build", "files": ["Makefile"]}
    (tmp_path / "make.json").write_text(
        json.dumps({"schema_version": 1, "tools": [mine]}), encoding="utf-8"
    )
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    configs = load_tooling_configs(tmp_path)
    assert {r.id: r for r in configs.rules}["make"].name == "My Make"
    assert len(configs.problems) == 1
    assert configs.problems[0].startswith("Tooling config broken.json was skipped")
