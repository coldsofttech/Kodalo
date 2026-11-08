"""The framework part of the AI analysis: what is sent and checking entries."""

import pytest

from kodalo.core.repositories import Entry, RepoInfo
from kodalo.core.repositories.ai.frameworks import (
    _check,
    _Sample,
    build_prompt,
    top_level_names,
    unknown_dependencies,
    unknown_tool_files,
)
from kodalo.core.repositories.configs.framework import (
    FrameworkConfigError,
    load_framework_configs,
    load_tooling_configs,
)
from kodalo.core.repositories.models import Manifest

HTMX = {"id": "htmx", "name": "htmx", "category": "ui", "dependencies": ["htmx.org"]}
INFO = RepoInfo(
    url="u",
    owner="o",
    name="n",
    top_level=(
        Entry("README.md", "file"),
        Entry(".env", "file"),
        Entry("src", "dir"),
        Entry("Earthfile", "file"),
        Entry("Makefile", "file"),
        Entry(".github", "dir"),
        Entry(".weird", "dir"),
    ),
    manifests=(
        Manifest(
            "package.json",
            "js",
            dependencies=("react", "htmx.org"),
            dev_dependencies=("left-pad",),
        ),
    ),
)


def test_only_unknown_names_and_safe_files_are_sent() -> None:
    rules = load_framework_configs(None).rules
    assert unknown_dependencies(INFO, rules) == [("js", "htmx.org"), ("js", "left-pad")]
    assert top_level_names(INFO)[:2] == ["src", "Earthfile"]
    prompt = build_prompt(_Sample((("js", "htmx.org"),), ("src",), ("Earthfile",)))
    assert prompt == "dependencies (js): htmx.org\nfiles: src\ntool files: Earthfile"


def test_only_names_no_tooling_config_covers_are_sent_as_tool_files() -> None:
    rules = load_tooling_configs(None).rules
    assert unknown_tool_files(INFO, rules) == ["Earthfile", ".weird"]


def test_check_requires_a_match_with_what_was_sent() -> None:
    sample = _Sample((("js", "htmx.org"),), ("src",))
    assert _check(HTMX, sample, set()).id == "htmx"
    with pytest.raises(FrameworkConfigError, match="already exists"):
        _check(HTMX, sample, {"htmx"})
    invented = {**HTMX, "id": "other", "dependencies": ["not-sent"]}
    with pytest.raises(FrameworkConfigError, match="does not match"):
        _check(invented, sample, set())


def test_files_that_are_not_tooling_are_not_asked_about() -> None:
    info = RepoInfo(
        url="u",
        owner="o",
        name="n",
        top_level=tuple(
            Entry(name, "file")
            for name in (
                ".gitignore",
                ".gitattributes",
                ".python-version",
                ".pre-commit-hooks.yaml",
            )
        ),
    )
    assert unknown_tool_files(info, load_tooling_configs(None).rules) == []
