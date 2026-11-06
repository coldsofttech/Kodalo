"""Describe how to recognise a framework (FastAPI, React, Django ...) or a tool (ruff, Docker ...).

A config file holds a list of frameworks (or tools, which use the same shape and their own
categories). Each one says which dependency names, file names or paths mean "this is used". The
bundled files live in ``core/configs/frameworks/`` and ``core/configs/toolings/``; a folder of
the user's own files adds to them, and an entry with the same ``id`` replaces the bundled one.
Configs hold only data, never code. See ``docs/framework-detection.md``.
"""

import fnmatch
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from kodalo.core.repositories.models import Entry, Framework, Manifest

SCHEMA_VERSION = 1
CATEGORIES = ("web", "ui", "cli", "data", "testing", "build", "mobile", "desktop", "ml", "other")
TOOL_CATEGORIES = ("build", "test", "lint_format", "ci", "containers", "package_distribution")
MAX_CONFIG_BYTES = 64 * 1024
MAX_CONFIGS = 200
MAX_FRAMEWORKS = 200
MAX_ITEMS = 30
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_PATTERN = re.compile(r"^[A-Za-z0-9@_.*?\[\]/-][A-Za-z0-9@_.*?\[\]/ -]{0,127}$")


@dataclass(frozen=True)
class ConfigKind:
    """Where one kind of config lives and what it may hold."""

    folder: str
    key: str
    label: str
    categories: tuple[str, ...]


FRAMEWORKS = ConfigKind("frameworks", "frameworks", "Framework", CATEGORIES)
TOOLING = ConfigKind("toolings", "tools", "Tooling", TOOL_CATEGORIES)


class FrameworkConfigError(ValueError):
    """A framework config is not valid. The message says what is wrong, in plain words."""


@dataclass(frozen=True)
class FrameworkRule:
    """One framework and what shows it is in use. Any one match is enough."""

    id: str
    name: str
    category: str
    dependencies: tuple[str, ...] = ()
    ecosystems: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    source: str = "bundled"


@dataclass(frozen=True)
class FrameworkConfigSet:
    """The frameworks in use, and a plain sentence for each file that could not be loaded."""

    rules: tuple[FrameworkRule, ...] = ()
    problems: tuple[str, ...] = field(default=())


def load_tooling_configs(user_dir: Path | None = None) -> FrameworkConfigSet:
    """Load the bundled tooling configs, then the user's."""
    return load_framework_configs(user_dir, TOOLING)


def load_framework_configs(
    user_dir: Path | None = None, kind: ConfigKind = FRAMEWORKS
) -> FrameworkConfigSet:
    """Load the bundled configs, then the user's. Invalid ones are skipped with a problem."""
    found: dict[str, FrameworkRule] = {}
    problems: list[str] = []
    bundled = resources.files("kodalo.core.configs") / kind.folder
    for entry in sorted(bundled.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".json"):
            _add(found, problems, entry.name, entry.read_text(encoding="utf-8"), "bundled", kind)
    if user_dir is not None and user_dir.is_dir():
        for path in sorted(user_dir.glob("*.json"))[:MAX_CONFIGS]:
            try:
                if path.stat().st_size > MAX_CONFIG_BYTES:
                    raise FrameworkConfigError("The file is too large.")
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError, FrameworkConfigError) as error:
                problems.append(
                    f"{kind.label} config {path.name} was skipped: {error or 'unreadable'}."
                )
                continue
            _add(found, problems, path.name, text, "user", kind)
    ordered = sorted(found.values(), key=lambda r: r.id)
    return FrameworkConfigSet(tuple(ordered), tuple(problems))


def _add(
    found: dict[str, FrameworkRule],
    problems: list[str],
    name: str,
    text: str,
    source: str,
    kind: ConfigKind,
) -> None:
    try:
        rules = parse_framework_config(json.loads(text), source, kind)
    except (FrameworkConfigError, ValueError) as error:
        problems.append(f"{kind.label} config {name} was skipped: {error}")
        return
    for rule in rules:
        found[rule.id] = rule


def parse_framework_config(
    data: Any, source: str = "user", kind: ConfigKind = FRAMEWORKS
) -> list[FrameworkRule]:
    """Check ``data`` (a decoded JSON document with a ``frameworks`` or ``tools`` list)."""
    if not isinstance(data, dict):
        raise FrameworkConfigError("The file must hold one JSON object.")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise FrameworkConfigError(f"schema_version must be {SCHEMA_VERSION}.")
    items = data.get(kind.key)
    if not isinstance(items, list) or not items or len(items) > MAX_FRAMEWORKS:
        raise FrameworkConfigError(f"{kind.key} must be a list of 1 to {MAX_FRAMEWORKS} entries.")
    return [parse_framework(item, source, kind) for item in items]


def parse_framework(
    item: Any, source: str = "user", kind: ConfigKind = FRAMEWORKS
) -> FrameworkRule:
    """Check one framework entry."""
    if not isinstance(item, dict):
        raise FrameworkConfigError("A framework must be a JSON object.")
    framework_id = _text(item, "id")
    if not _ID.match(framework_id):
        raise FrameworkConfigError("id must be lowercase letters, digits and dashes.")
    name = _text(item, "name")
    if len(name) > 64:
        raise FrameworkConfigError("name must be at most 64 characters.")
    category = _text(item, "category")
    if category not in kind.categories:
        raise FrameworkConfigError(f"category must be one of: {', '.join(kind.categories)}.")
    rule = FrameworkRule(
        id=framework_id,
        name=name,
        category=category,
        dependencies=_patterns(item, "dependencies"),
        ecosystems=_patterns(item, "ecosystems"),
        files=_patterns(item, "files"),
        paths=_patterns(item, "paths"),
        source=source,
    )
    if not (rule.dependencies or rule.files or rule.paths):
        raise FrameworkConfigError(f"{framework_id} needs dependencies, files or paths to match.")
    return rule


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise FrameworkConfigError(f"{key} is required and must be text.")
    return value.strip()


def _patterns(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise FrameworkConfigError(f"{key} must be a list of at most {MAX_ITEMS} entries.")
    for item in value:
        if not isinstance(item, str) or not _PATTERN.match(item):
            raise FrameworkConfigError(f"{key} must hold plain names, without odd characters.")
        if ".." in item or item.startswith("/"):
            raise FrameworkConfigError(f"{key} must hold relative names.")
    return tuple(value)


def _normal(name: str) -> str:
    return name.lower().replace("_", "-")


def _matches_dependency(rule: FrameworkRule, manifest: Manifest, name: str) -> bool:
    if rule.ecosystems and manifest.ecosystem not in rule.ecosystems:
        return False
    return any(fnmatch.fnmatchcase(_normal(name), _normal(p)) for p in rule.dependencies)


def known_dependencies(rules: Iterable[FrameworkRule], manifests: Iterable[Manifest]) -> set[str]:
    """The dependency names (as written in the project files) that some rule already covers."""
    rule_list = list(rules)
    return {
        name
        for manifest in manifests
        if not manifest.is_lockfile
        for name in (*manifest.dependencies, *manifest.dev_dependencies)
        if any(_matches_dependency(rule, manifest, name) for rule in rule_list)
    }


def detect_tooling(
    rules: Iterable[FrameworkRule], manifests: Iterable[Manifest], entries: Iterable[Entry]
) -> tuple[Framework, ...]:
    """Return the tools in use. Tools are found the same way frameworks are."""
    return detect_frameworks(rules, manifests, entries)


def detect_frameworks(
    rules: Iterable[FrameworkRule], manifests: Iterable[Manifest], entries: Iterable[Entry]
) -> tuple[Framework, ...]:
    """Return the frameworks in use, each with the first evidence found (top folders first)."""
    projects = sorted(
        (m for m in manifests if not m.is_lockfile),
        key=lambda m: (m.path.count("/"), m.path.lower()),
    )
    files = sorted((e.path for e in entries), key=lambda p: (p.count("/"), p.lower()))
    found: list[Framework] = []
    for rule in rules:
        hit = _evidence(rule, projects, files)
        if hit is not None:
            found.append(Framework(rule.id, rule.name, rule.category, hit[0], hit[1]))
    return tuple(sorted(found, key=lambda f: (f.name.lower(), f.id)))


def _evidence(
    rule: FrameworkRule, projects: list[Manifest], files: list[str]
) -> tuple[str, str] | None:
    for manifest in projects:
        for name in (*manifest.dependencies, *manifest.dev_dependencies):
            if _matches_dependency(rule, manifest, name):
                return f'{manifest.path}: "{name}"'[:120], manifest.path
    for path in files:
        base = path.rsplit("/", 1)[-1]
        if any(fnmatch.fnmatchcase(base, p) for p in rule.files):
            return path[:120], path
        if any(f"/{p}/" in f"/{path}/" for p in rule.paths):
            return path[:120], path
    return None
