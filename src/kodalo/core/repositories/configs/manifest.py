"""Describe how to read a project file (``package.json``, ``go.mod`` ...) in a JSON config.

Each config covers one kind of file. The bundled ones live in ``core/configs/parsers/``; a folder
of the user's own configs adds to them, and a config with the same ``id`` replaces the bundled
one. A config holds only data (file names, a format and where the values are), never code, so
a config written by hand or by a tool cannot run anything. See ``docs/repository-analysis.md``.
"""

import fnmatch
import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from kodalo.core.repositories.layout import ManifestRule

SCHEMA_VERSION = 1
FORMATS = ("json", "toml", "xml", "lines", "none")
SHAPES = {"json": ("keys", "requirements"), "toml": ("keys", "requirements"), "xml": ("values",)}
MAX_CONFIG_BYTES = 64 * 1024
MAX_CONFIGS = 200
MAX_ITEMS = 20
MAX_REGEX = 300
DEFAULT_PRIORITY = 100
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_SECRET_NAMES = (".env*", "*.pem", "*.key", "id_rsa*", "*secret*", "*credential*")


class ConfigError(ValueError):
    """A config file is not valid. The message says what is wrong, in plain words."""


@dataclass(frozen=True)
class Selector:
    """Where to find one value: a ``path`` in structured data, or a ``regex`` for text lines."""

    path: str = ""
    shape: str = ""
    regex: re.Pattern[str] | None = None
    section: re.Pattern[str] | None = None


@dataclass(frozen=True)
class ManifestConfig:
    id: str
    ecosystem: str
    format: str
    files: tuple[str, ...]
    lockfiles: tuple[str, ...] = ()
    priority: int = DEFAULT_PRIORITY
    name: tuple[Selector, ...] = ()
    version: tuple[Selector, ...] = ()
    dependencies: tuple[Selector, ...] = ()
    dev_dependencies: tuple[Selector, ...] = ()
    exclude_dependencies: tuple[str, ...] = ()
    dev_wins: bool = False
    source: str = "bundled"


@dataclass(frozen=True)
class ConfigSet:
    """The configs in use, and a plain sentence for each config that could not be loaded."""

    configs: tuple[ManifestConfig, ...] = ()
    problems: tuple[str, ...] = field(default=())


def load_configs(user_dir: Path | None = None) -> ConfigSet:
    """Load the bundled configs, then the user's. Invalid ones are skipped with a problem."""
    found: dict[str, ManifestConfig] = {}
    problems: list[str] = []
    bundled = resources.files("kodalo.core.configs") / "parsers"
    for entry in sorted(bundled.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".json"):
            _add(found, problems, entry.name, entry.read_text(encoding="utf-8"), "bundled")
    if user_dir is not None and user_dir.is_dir():
        for path in sorted(user_dir.glob("*.json"))[:MAX_CONFIGS]:
            try:
                if path.stat().st_size > MAX_CONFIG_BYTES:
                    raise ConfigError("The file is too large.")
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError, ConfigError) as error:
                problems.append(f"Parser config {path.name} was skipped: {error or 'unreadable'}.")
                continue
            _add(found, problems, path.name, text, "user")
    ordered = sorted(found.values(), key=lambda c: (c.priority, c.id))
    return ConfigSet(tuple(ordered), tuple(problems))


def _add(
    found: dict[str, ManifestConfig], problems: list[str], name: str, text: str, source: str
) -> None:
    try:
        config = parse_config(json.loads(text), source)
    except (ConfigError, ValueError) as error:
        problems.append(f"Parser config {name} was skipped: {error}")
        return
    found[config.id] = config


def match_config(
    path: str, configs: tuple[ManifestConfig, ...]
) -> tuple[ManifestConfig, bool] | None:
    """Return the config for the file at ``path`` and whether it is a lockfile, or ``None``."""
    file_name = path.rsplit("/", 1)[-1]
    for config in configs:
        if any(fnmatch.fnmatchcase(file_name, pattern) for pattern in config.files):
            return config, False
        if any(fnmatch.fnmatchcase(file_name, pattern) for pattern in config.lockfiles):
            return config, True
    return None


def manifest_rules(configs: tuple[ManifestConfig, ...]) -> tuple[ManifestRule, ...]:
    """The file-name rules the layout step uses to find project files."""
    rules: list[ManifestRule] = []
    for config in configs:
        rules += [ManifestRule(p, config.ecosystem, False) for p in config.files]
        rules += [ManifestRule(p, config.ecosystem, True) for p in config.lockfiles]
    return tuple(rules)


def parse_config(data: Any, source: str = "user") -> ManifestConfig:
    """Check ``data`` (a decoded JSON document) and turn it into a config."""
    if not isinstance(data, dict):
        raise ConfigError("The file must hold one JSON object.")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ConfigError(f"schema_version must be {SCHEMA_VERSION}.")
    config_id = _text(data, "id")
    if not _ID.match(config_id):
        raise ConfigError("id must be lowercase letters, digits and dashes.")
    ecosystem = _text(data, "ecosystem")
    if not _ID.match(ecosystem):
        raise ConfigError("ecosystem must be lowercase letters, digits and dashes.")
    fmt = _text(data, "format")
    if fmt not in FORMATS:
        raise ConfigError(f"format must be one of: {', '.join(FORMATS)}.")
    files = _names(data, "files", required=True)
    lockfiles = _names(data, "lockfiles")
    for pattern in (*files, *lockfiles):
        if any(fnmatch.fnmatchcase(pattern.lower(), secret) for secret in _SECRET_NAMES):
            raise ConfigError(f"{pattern} looks like a secrets file and is never read.")
    priority = data.get("priority", DEFAULT_PRIORITY)
    if not isinstance(priority, int) or isinstance(priority, bool) or not 0 <= priority <= 1000:
        raise ConfigError("priority must be a whole number from 0 to 1000.")
    return ManifestConfig(
        id=config_id,
        ecosystem=ecosystem,
        format=fmt,
        files=files,
        lockfiles=lockfiles,
        priority=priority,
        name=_selectors(data, "name", fmt, plain=True),
        version=_selectors(data, "version", fmt, plain=True),
        dependencies=_selectors(data, "dependencies", fmt, plain=False),
        dev_dependencies=_selectors(data, "dev_dependencies", fmt, plain=False),
        exclude_dependencies=_names(data, "exclude_dependencies"),
        dev_wins=data.get("dev_wins") is True,
        source=source,
    )


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key} is required and must be text.")
    return value.strip()


def _names(data: dict[str, Any], key: str, *, required: bool = False) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise ConfigError(f"{key} must be a list of at most {MAX_ITEMS} names.")
    if required and not value:
        raise ConfigError(f"{key} needs at least one name.")
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 128 or "/" in item:
            raise ConfigError(f"{key} must hold plain file names, without folders.")
    return tuple(value)


def _regex(value: Any, what: str) -> re.Pattern[str]:
    if not isinstance(value, str) or not value or len(value) > MAX_REGEX:
        raise ConfigError(f"{what} must be a pattern of at most {MAX_REGEX} characters.")
    try:
        pattern = re.compile(value)
    except re.error:
        raise ConfigError(f"{what} is not a valid pattern.") from None
    if "value" not in pattern.groupindex:
        raise ConfigError(f"{what} needs a group named value, like (?P<value>...).")
    return pattern


def _section(value: Any) -> re.Pattern[str] | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > MAX_REGEX:
        raise ConfigError("A section must be a pattern.")
    try:
        return re.compile(value)
    except re.error:
        raise ConfigError("A section is not a valid pattern.") from None


def _selectors(data: dict[str, Any], key: str, fmt: str, *, plain: bool) -> tuple[Selector, ...]:
    items = data.get(key, [])
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ConfigError(f"{key} must be a list of at most {MAX_ITEMS} entries.")
    if items and fmt == "none":
        raise ConfigError(f"{key} cannot be used with format none.")
    selectors: list[Selector] = []
    for item in items:
        what = f"An entry of {key}"
        if fmt == "lines":
            spec = item if isinstance(item, dict) else {"regex": item}
            section = spec.get("section")
            selectors.append(
                Selector(
                    regex=_regex(spec.get("regex"), what),
                    section=_section(section),
                )
            )
        elif plain:
            if not isinstance(item, str) or not item or len(item) > 200:
                raise ConfigError(f"{what} must be a path.")
            selectors.append(Selector(path=item))
        else:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise ConfigError(f"{what} must have a path and a shape.")
            shape = item.get("shape")
            if shape not in SHAPES[fmt]:
                raise ConfigError(f"{what} needs a shape: {', '.join(SHAPES[fmt])}.")
            selectors.append(Selector(path=item["path"], shape=shape))
    return tuple(selectors)
