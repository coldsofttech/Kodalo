"""Notable folders and monorepo detection."""

from kodalo.core.repositories.layout import (
    DirectoryRule,
    LayoutRules,
    ManifestRule,
    SignalRule,
    analyze,
)
from kodalo.core.repositories.models import Entry

RULES = LayoutRules(
    directories=(
        DirectoryRule("p1", "src/test", "tests", "path_suffix", 3),
        DirectoryRule("p2", "src", "source", "exact", 2),
        DirectoryRule("p3", "tests", "tests", "exact", 2),
        DirectoryRule("p4", "docs", "docs", "exact", 2),
    ),
    signals=(
        SignalRule("js", "file_exists", "turbo.json", 1),
        SignalRule("js", "multi_manifest", "", 2),
        SignalRule("python", "multi_manifest", "", 2),
    ),
    manifests=(
        ManifestRule("package.json", "js", False),
        ManifestRule("package-lock.json", "js", True),
        ManifestRule("pyproject.toml", "python", False),
    ),
    ignored=frozenset({"node_modules"}),
)


def _entries(*paths: str) -> list[Entry]:
    return [Entry(p, "file" if "." in p.rsplit("/", 1)[-1] else "dir") for p in paths]


def test_notable_dirs_get_a_purpose_and_the_matching_rule() -> None:
    layout = analyze(_entries("src", "tests", "other", "app/src/test", "a/b/c/src"), RULES)

    found = {d.path: (d.purpose, d.pattern_id) for d in layout.notable_dirs}
    assert found == {
        "src": ("source", "p2"),
        "tests": ("tests", "p3"),
        "app/src/test": ("tests", "p1"),
    }


def test_ignored_folders_are_skipped() -> None:
    layout = analyze(_entries("node_modules/src", "node_modules/x/package.json"), RULES)

    assert layout.notable_dirs == ()
    assert layout.manifests == ()


def test_workspace_file_at_the_top_marks_a_monorepo() -> None:
    layout = analyze(_entries("turbo.json", "package.json"), RULES)

    assert layout.is_monorepo
    assert layout.monorepo_signals == ("turbo.json",)


def test_several_projects_of_one_ecosystem_mark_a_monorepo() -> None:
    layout = analyze(_entries("pyproject.toml", "api/pyproject.toml", "web/package.json"), RULES)

    assert layout.is_monorepo
    assert layout.monorepo_signals == ("python projects in 2 folders",)


def test_different_ecosystems_are_not_a_monorepo() -> None:
    layout = analyze(_entries("pyproject.toml", "ui/package.json"), RULES)

    assert not layout.is_monorepo
    assert layout.monorepo_signals == ()


def test_lockfiles_and_docs_site_do_not_count() -> None:
    layout = analyze(
        _entries("package.json", "package-lock.json", "docs", "docs/package.json"), RULES
    )

    assert not layout.is_monorepo
    assert [m.path for m in layout.manifests] == [
        "docs/package.json",
        "package-lock.json",
        "package.json",
    ]
