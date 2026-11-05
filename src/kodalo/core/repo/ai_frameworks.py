"""The framework and tooling part of the AI repository analysis.

Only dependency names that no framework config covers, and the names of a few top-level files, are
sent: never file contents. The entries in the answer must be in the framework config format; every
one is checked and must match something that was sent before it is saved to the user's frameworks
or tooling folder. The AI call itself is in ``ai_analyzer``. See ``docs/framework-detection.md``.
"""

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kodalo.core.repo.framework_config import (
    FRAMEWORKS,
    TOOLING,
    ConfigKind,
    FrameworkConfigError,
    FrameworkRule,
    detect_frameworks,
    known_dependencies,
    parse_framework,
)
from kodalo.core.repo.models import Entry, Manifest, RepoInfo
from kodalo.core.repo.service import RepoService

MAX_DEPENDENCIES = 80
MAX_NAMES = 40
MAX_FRAMEWORKS = 20
_SKIP = ("readme*", "license*", "licence*", "changelog*", "contributing*", "security*", "notice*")
_SECRET_FILE = (".env*", "*.pem", "*.key", "id_rsa*", "*secret*", "*credential*")
_NOT_TOOLING = (
    ".gitignore",
    ".gitattributes",
    ".gitmodules",
    ".mailmap",
    ".python-version",
    ".node-version",
    ".nvmrc",
    ".ruby-version",
    ".tool-versions",
    ".npmignore",
    ".env.example",
    ".env.sample",
    "codeowners",
    "authors",
    "code_of_conduct*",
    "copying*",
    "py.typed",
)
_CONFIG_SUFFIX = (".json", ".jsonc", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".xml", ".lock")


@dataclass(frozen=True)
class _Sample:
    """What is sent: package names per ecosystem, and top-level file names."""

    dependencies: tuple[tuple[str, str], ...]  # (ecosystem, name)
    files: tuple[str, ...]
    tool_files: tuple[str, ...] = ()
    already: tuple[str, ...] = ()  # ids Kodalo already recognised in this repository


def unknown_dependencies(info: RepoInfo, rules: tuple[FrameworkRule, ...]) -> list[tuple[str, str]]:
    """Dependency names (with their ecosystem) no framework or tooling config covers."""
    known = known_dependencies(rules, info.manifests)
    projects = [m for m in info.manifests if not m.is_lockfile]
    found: dict[tuple[str, str], None] = {}
    for manifest in projects:
        for name in manifest.dependencies:
            if name not in known:
                found[(manifest.ecosystem, name)] = None
    for manifest in projects:
        for name in manifest.dev_dependencies:
            if name not in known:
                found[(manifest.ecosystem, name)] = None
    return list(found)[:MAX_DEPENDENCIES]


def top_level_names(info: RepoInfo) -> list[str]:
    """The top-level file and folder names that are safe to send, at most 40."""
    return [
        e.path
        for e in info.top_level
        if not any(fnmatch.fnmatchcase(e.path.lower(), p) for p in (*_SKIP, *_SECRET_FILE))
    ][:MAX_NAMES]


def unknown_tool_files(info: RepoInfo, rules: tuple[FrameworkRule, ...]) -> list[str]:
    """Top-level config-like names no tooling config covers and no project file explains."""
    manifests = {m.path for m in info.manifests}
    prefixes = {p.split("/", 1)[0] for r in rules for p in r.paths}
    found: list[str] = []
    for entry in info.top_level:
        name = entry.path
        lowered = name.lower()
        if name in manifests or any(
            fnmatch.fnmatchcase(lowered, p) for p in _SKIP + _SECRET_FILE + _NOT_TOOLING
        ):
            continue
        if entry.type == "dir":
            likely = name.startswith(".") and name not in prefixes
        else:
            likely = (
                name.startswith(".") or "." not in name or lowered.endswith(_CONFIG_SUFFIX)
            ) and not any(fnmatch.fnmatchcase(name, p) for r in rules for p in r.files)
        if likely:
            found.append(name)
    return found[:MAX_NAMES]


def build_prompt(sample: _Sample) -> str:
    """The user message: one ``dependencies`` line per ecosystem, then the ``files`` line."""
    by_ecosystem: dict[str, list[str]] = {}
    for ecosystem, name in sample.dependencies:
        by_ecosystem.setdefault(ecosystem, []).append(name)
    lines = [f"dependencies ({eco}): {', '.join(names)}" for eco, names in by_ecosystem.items()]
    lines.append(f"files: {', '.join(sample.files)}")
    if sample.tool_files:
        lines.append(f"tool files: {', '.join(sample.tool_files)}")
    if sample.already:
        lines.append(f"already known: {', '.join(sample.already)}")
    return "\n".join(lines)


def _check(
    item: Any, sample: _Sample, known: set[str], kind: ConfigKind = FRAMEWORKS
) -> FrameworkRule:
    """Validate one entry and make sure it matches something that was sent."""
    rule = parse_framework(item, "user", kind)
    if rule.id in known:
        raise _Duplicate(f"{rule.id} already exists.")
    manifests = [
        Manifest("sent", eco, dependencies=tuple(n for e, n in sample.dependencies if e == eco))
        for eco in dict.fromkeys(e for e, _ in sample.dependencies)
    ]
    entries = [Entry(name, "file") for name in (*sample.files, *sample.tool_files)]
    if not detect_frameworks([rule], manifests, entries):
        raise FrameworkConfigError(f"{rule.id} does not match anything that was sent.")
    return rule


def _config_data(rule: FrameworkRule, kind: ConfigKind) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": rule.id, "name": rule.name, "category": rule.category}
    for key, value in (
        ("ecosystems", rule.ecosystems),
        ("dependencies", rule.dependencies),
        ("files", rule.files),
        ("paths", rule.paths),
    ):
        if value:
            entry[key] = list(value)
    return {"schema_version": 1, kind.key: [entry]}


@dataclass(frozen=True)
class FrameworkSaved:
    """The frameworks and tools saved, and what was left out (with why)."""

    added: tuple[str, ...]
    tools: tuple[str, ...]
    skipped: tuple[str, ...]


class _Duplicate(FrameworkConfigError):
    """The model answered with an id Kodalo already has. This is dropped without a message."""


class FrameworkAssistant:
    """Works out which names to ask about and saves the frameworks and tools the AI found."""

    def __init__(self, repos: RepoService, frameworks_dir: Path, tooling_dir: Path) -> None:
        self._repos = repos
        self._dirs = {FRAMEWORKS.key: frameworks_dir, TOOLING.key: tooling_dir}

    def sample(self, info: RepoInfo) -> _Sample:
        """The names that would be sent: package names, top-level names and known ids."""
        tools = self._repos.tooling_configs().rules
        rules = (*self._repos.framework_configs().rules, *tools)
        return _Sample(
            tuple(unknown_dependencies(info, rules)),
            tuple(top_level_names(info)),
            tuple(unknown_tool_files(info, tools)),
            tuple(f.id for f in (*info.frameworks, *info.tooling)),
        )

    def save(self, data: dict[str, Any], sample: _Sample) -> FrameworkSaved:
        """Check every framework and tool in the answer and save the valid ones."""
        skipped: list[str] = []
        saved: dict[str, list[str]] = {FRAMEWORKS.key: [], TOOLING.key: []}
        known = {
            FRAMEWORKS.key: {r.id for r in self._repos.framework_configs().rules},
            TOOLING.key: {r.id for r in self._repos.tooling_configs().rules},
        }
        for kind in (FRAMEWORKS, TOOLING):
            items = data.get(kind.key)
            for item in (items if isinstance(items, list) else [])[:MAX_FRAMEWORKS]:
                try:
                    rule = _check(item, sample, known[kind.key], kind)
                except _Duplicate:
                    continue
                except FrameworkConfigError as error:
                    noun = "tool" if kind is TOOLING else "framework"
                    skipped.append(f"A {noun} was not saved: {error}")
                    continue
                folder = self._dirs[kind.key]
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / f"{rule.id}.json"
                target.write_text(
                    json.dumps(_config_data(rule, kind), indent=2) + "\n", encoding="utf-8"
                )
                known[kind.key].add(rule.id)
                saved[kind.key].append(rule.id)
        return FrameworkSaved(
            tuple(saved[FRAMEWORKS.key]), tuple(saved[TOOLING.key]), tuple(skipped)
        )
