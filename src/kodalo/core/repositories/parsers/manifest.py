"""Read the name, version and dependencies out of a project file, as its config says.

Only the standard library is used. A file that cannot be read gives empty details and a warning,
never an error, and each list of dependencies is capped.
"""

import fnmatch
import json
import re
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from kodalo.core.repositories.configs.manifest import ManifestConfig, Selector

MAX_NAMES = 50
MAX_LINES = 5000
MAX_LINE = 2000
_REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


@dataclass(frozen=True)
class ManifestDetails:
    package_name: str | None = None
    version: str | None = None
    dependencies: tuple[str, ...] = ()
    dev_dependencies: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def parse_manifest(text: str, config: ManifestConfig) -> ManifestDetails:
    """Return what ``text`` says about the package, following ``config``."""
    if config.format == "none":
        return ManifestDetails()
    try:
        if config.format == "lines":
            return _finish(config, *_from_lines(text, config))
        if config.format == "xml":
            return _finish(config, *_from_xml(text, config))
        data = json.loads(text) if config.format == "json" else tomllib.loads(text)
        return _finish(config, *_from_data(data, config))
    except (ValueError, ET.ParseError, RecursionError):
        return ManifestDetails(warnings=("could not be read, so its details are missing.",))


def _finish(
    config: ManifestConfig,
    name: str | None,
    version: str | None,
    deps: list[str],
    dev: list[str],
) -> ManifestDetails:
    warnings: list[str] = []
    dev_names = _unique(n for n in dev if not _excluded(n, config))
    dep_names = _unique(n for n in deps if not _excluded(n, config))
    if config.dev_wins:
        dep_names = [n for n in dep_names if n not in set(dev_names)]
    for label, names in (("dependencies", dep_names), ("dev dependencies", dev_names)):
        if len(names) > MAX_NAMES:
            warnings.append(
                f"has more than {MAX_NAMES} {label}; only the first {MAX_NAMES} are kept."
            )
    return ManifestDetails(
        package_name=name,
        version=version,
        dependencies=tuple(dep_names[:MAX_NAMES]),
        dev_dependencies=tuple(dev_names[:MAX_NAMES]),
        warnings=tuple(warnings),
    )


def _excluded(name: str, config: ManifestConfig) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in config.exclude_dependencies)


def _unique(names: Iterator[str] | list[str]) -> list[str]:
    return list(dict.fromkeys(n for n in names if n))


# JSON and TOML


def _from_data(
    data: Any, config: ManifestConfig
) -> tuple[str | None, str | None, list[str], list[str]]:
    return (
        _scalar(data, config.name),
        _scalar(data, config.version),
        _data_names(data, config.dependencies),
        _data_names(data, config.dev_dependencies),
    )


def _walk(data: Any, path: str) -> Iterator[Any]:
    nodes = [data]
    for key in path.split("."):
        following: list[Any] = []
        for node in nodes:
            if key == "*":
                if isinstance(node, dict):
                    following += list(node.values())
                elif isinstance(node, list):
                    following += node
            elif isinstance(node, dict) and key in node:
                following.append(node[key])
        nodes = following
    return iter(nodes)


def _scalar(data: Any, selectors: tuple[Selector, ...]) -> str | None:
    for selector in selectors:
        for value in _walk(data, selector.path):
            if isinstance(value, str | int | float) and not isinstance(value, bool):
                text = str(value).strip()
                if text:
                    return text[:256]
    return None


def _data_names(data: Any, selectors: tuple[Selector, ...]) -> list[str]:
    names: list[str] = []
    for selector in selectors:
        for value in _walk(data, selector.path):
            if isinstance(value, dict):
                names += [str(key) for key in value]
            elif isinstance(value, list) and selector.shape == "requirements":
                for item in value:
                    match = _REQUIREMENT.match(item) if isinstance(item, str) else None
                    if match:
                        names.append(match.group(1))
    return names


# XML


def _from_xml(
    text: str, config: ManifestConfig
) -> tuple[str | None, str | None, list[str], list[str]]:
    root = ET.fromstring(text)  # noqa: S314
    for element in root.iter():
        if isinstance(element.tag, str):
            element.tag = element.tag.rsplit("}", 1)[-1]
    return (
        _xml_first(root, config.name),
        _xml_first(root, config.version),
        _xml_all(root, config.dependencies),
        _xml_all(root, config.dev_dependencies),
    )


def _xml_values(root: ET.Element, path: str) -> list[str]:
    attribute = None
    if "/@" in path:
        path, attribute = path.rsplit("/@", 1)
    found: list[str] = []
    for element in root.findall(path):
        value = element.get(attribute) if attribute else element.text
        if value and value.strip():
            found.append(value.strip())
    return found


def _xml_first(root: ET.Element, selectors: tuple[Selector, ...]) -> str | None:
    for selector in selectors:
        values = _xml_values(root, selector.path)
        if values:
            return values[0][:256]
    return None


def _xml_all(root: ET.Element, selectors: tuple[Selector, ...]) -> list[str]:
    return [value for selector in selectors for value in _xml_values(root, selector.path)]


# Text lines


def _from_lines(
    text: str, config: ManifestConfig
) -> tuple[str | None, str | None, list[str], list[str]]:
    lines = [line[:MAX_LINE] for line in text.splitlines()[:MAX_LINES]]
    return (
        _line_first(lines, config.name),
        _line_first(lines, config.version),
        _line_all(lines, config.dependencies),
        _line_all(lines, config.dev_dependencies),
    )


def _line_first(lines: list[str], selectors: tuple[Selector, ...]) -> str | None:
    for selector in selectors:
        if selector.regex is None:
            continue
        for line in lines:
            match = selector.regex.search(line)
            if match:
                return match.group("value")[:256]
    return None


def _in_section(lines: list[str], header: re.Pattern[str]) -> Iterator[str]:
    inside = False
    for line in lines:
        if inside:
            if not line.strip() or line[0] in " \t":
                yield line
                continue
            inside = False
        if header.search(line):
            inside = True


def _line_all(lines: list[str], selectors: tuple[Selector, ...]) -> list[str]:
    names: list[str] = []
    for selector in selectors:
        if selector.regex is None:
            continue
        scope = _in_section(lines, selector.section) if selector.section else iter(lines)
        for line in scope:
            names += [match.group("value") for match in selector.regex.finditer(line)]
    return names
