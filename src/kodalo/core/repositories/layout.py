"""Find the notable folders, the project files and the monorepo signs in a list of paths.

Everything here is plain rules over names. The rules come from seed tables in the database and
arrive as :class:`LayoutRules`, so this module never touches the database.
"""

import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass
from posixpath import dirname

from kodalo.core.repositories.models import Entry, Layout, Manifest, NotableDir

MAX_NOTABLE = 200
MAX_MANIFESTS = 200
_UNCOUNTED_PURPOSES = frozenset({"docs", "examples", "tests"})


@dataclass(frozen=True)
class DirectoryRule:
    """A folder name and what it is for. Rules are given in the order they are tried."""

    id: str
    name: str
    purpose: str
    match_kind: str
    max_depth: int


@dataclass(frozen=True)
class SignalRule:
    ecosystem: str
    kind: str
    file_name: str
    min_count: int


@dataclass(frozen=True)
class ManifestRule:
    pattern: str
    ecosystem: str
    is_lockfile: bool


@dataclass(frozen=True)
class LayoutRules:
    directories: tuple[DirectoryRule, ...] = ()
    signals: tuple[SignalRule, ...] = ()
    manifests: tuple[ManifestRule, ...] = ()
    ignored: frozenset[str] = frozenset()


def analyze(entries: Iterable[Entry], rules: LayoutRules) -> Layout:
    """Return the notable folders, project files and monorepo verdict for ``entries``."""
    kept = without_ignored(entries, rules.ignored)
    notable = _notable_dirs(kept, rules.directories)
    manifests = _manifests(kept, rules.manifests)
    uncounted = tuple(n.path for n in notable if n.purpose in _UNCOUNTED_PURPOSES)
    signals = _signals(kept, manifests, uncounted, rules.signals)
    return Layout(
        notable_dirs=tuple(notable[:MAX_NOTABLE]),
        manifests=tuple(manifests[:MAX_MANIFESTS]),
        is_monorepo=bool(signals),
        monorepo_signals=tuple(signals),
    )


def without_ignored(entries: Iterable[Entry], ignored: frozenset[str]) -> list[Entry]:
    """Leave out everything inside a folder named in ``ignored`` (``node_modules`` and so on)."""
    return [e for e in entries if not _ignored(e.path, ignored)]


def _ignored(path: str, ignored: frozenset[str]) -> bool:
    return any(part.lower() in ignored for part in path.split("/"))


def _notable_dirs(entries: list[Entry], rules: tuple[DirectoryRule, ...]) -> list[NotableDir]:
    found: dict[str, NotableDir] = {}
    for entry in entries:
        if entry.type != "dir":
            continue
        lowered = entry.path.lower()
        depth = lowered.count("/") + 1
        for rule in rules:
            if depth > rule.max_depth:
                continue
            name = rule.name.lower()
            if rule.match_kind == "exact":
                hit = lowered.rsplit("/", 1)[-1] == name
            else:
                hit = lowered == name or lowered.endswith("/" + name)
            if hit:
                found[entry.path] = NotableDir(entry.path, rule.purpose, rule.id)
                break
    return sorted(found.values(), key=lambda n: n.path.lower())


def _manifests(entries: list[Entry], rules: tuple[ManifestRule, ...]) -> list[Manifest]:
    found: list[Manifest] = []
    for entry in entries:
        if entry.type != "file":
            continue
        file_name = entry.path.rsplit("/", 1)[-1]
        for rule in rules:
            if fnmatch.fnmatchcase(file_name, rule.pattern):
                found.append(Manifest(entry.path, rule.ecosystem, rule.is_lockfile))
                break
    return sorted(found, key=lambda m: m.path.lower())


def _signals(
    entries: list[Entry],
    manifests: list[Manifest],
    uncounted: tuple[str, ...],
    rules: tuple[SignalRule, ...],
) -> list[str]:
    top_files = {e.path for e in entries if e.type == "file" and "/" not in e.path}
    folders: dict[str, set[str]] = {}
    for manifest in manifests:
        if manifest.is_lockfile or any(manifest.path.startswith(u + "/") for u in uncounted):
            continue
        folders.setdefault(manifest.ecosystem, set()).add(dirname(manifest.path))
    found: list[str] = []
    for rule in rules:
        if rule.kind == "file_exists":
            if rule.file_name in top_files:
                found.append(rule.file_name)
        elif len(folders.get(rule.ecosystem, ())) >= rule.min_count:
            found.append(f"{rule.ecosystem} projects in {len(folders[rule.ecosystem])} folders")
    return found
