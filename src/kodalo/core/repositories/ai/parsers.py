"""The parser part of the AI repository analysis: finding unknown project files and saving configs.

Only the top-level files that no config covers are looked at, and only the first few lines of each
(with secret-looking lines removed) are sent. The configs in the answer must be in the parser config
format; every one is checked and tried on the real file before it is saved to the user's parsers
folder. The AI call itself is in ``analyzer``. See ``docs/manifest-parsers.md``.
"""

import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kodalo.core.repositories.configs.manifest import (
    ConfigError,
    ManifestConfig,
    match_config,
    parse_config,
)
from kodalo.core.repositories.documentation import SECRET_FILES
from kodalo.core.repositories.models import RepoInfo
from kodalo.core.repositories.parsers.manifest import parse_manifest
from kodalo.core.repositories.service import RepoService
from kodalo.core.settings.github import GitHubSettings

MAX_FILES = 5
MAX_SAMPLE_BYTES = 1500
OUTPUT_TOKENS_PER_FILE = 700
_CHARS_PER_TOKEN = 3
_EXTENSIONS = frozenset(
    {".toml", ".json", ".yaml", ".yml", ".xml", ".lock", ".txt", ".cfg", ".ini", ".gradle"}
    | {".kts", ".mod", ".gemspec", ".csproj", ".fsproj", ".vbproj", ".props", ".sbt", ".cabal"}
    | {".opam", ".nimble", ".podspec", ".exs"}
)
_NAMES = frozenset({"gemfile", "pipfile", "podfile", "cartfile", "rakefile", "build", "workspace"})
_SKIP = ("readme*", "license*", "licence*", "changelog*", "contributing*", "security*", "notice*")
_SECRET_LINE = re.compile(r"token|secret|passw|api[_-]?key|authorization|credential", re.IGNORECASE)
_SECRET_FILE = SECRET_FILES


@dataclass(frozen=True)
class FileSample:
    """A project file nobody covers: its path, its whole text, and the part that gets sent."""

    path: str
    text: str
    sent: str


@dataclass(frozen=True)
class ParserSaved:
    """The configs saved (with the file each one was checked on) and what was left alone."""

    added: tuple[str, ...]
    skipped: tuple[str, ...]
    configs: tuple[tuple[ManifestConfig, str], ...]


def candidates(info: RepoInfo, configs: tuple[ManifestConfig, ...]) -> list[str]:
    """The top-level files that look like project files but no config covers, at most five."""
    found: list[str] = []
    for entry in info.top_level:
        name = entry.path.lower()
        if entry.type != "file" or name.startswith(".") or match_config(entry.path, configs):
            continue
        if any(fnmatch.fnmatchcase(name, p) for p in (*_SKIP, *_SECRET_FILE)):
            continue
        if name in _NAMES or Path(name).suffix in _EXTENSIONS:
            found.append(entry.path)
    return found[:MAX_FILES]


def redact(text: str) -> str:
    """Take out the lines that look like secrets and keep the start of the rest."""
    kept = [line for line in text.splitlines() if not _SECRET_LINE.search(line)]
    return "\n".join(kept).encode("utf-8")[:MAX_SAMPLE_BYTES].decode("utf-8", errors="ignore")


def build_prompt(samples: list[FileSample]) -> str:
    return "\n\n".join(f"### {s.path}\n{s.sent}" for s in samples)


def estimate_tokens(*texts: str) -> int:
    """A rough count (no provider is asked): over-estimates a little on purpose."""
    return sum(len(text) // _CHARS_PER_TOKEN + 1 for text in texts)


def _reply_json(text: str) -> Any:
    """The JSON in a model's answer, which may still be wrapped in a code fence or in prose."""
    try:
        return json.loads(text)
    except ValueError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except ValueError:
            return None


def _check(data: Any, samples: list[FileSample], known: set[str]) -> tuple[ManifestConfig, str]:
    """Validate one config and try it on its file. Returns the config and the file's path."""
    config = parse_config(data, "user")
    if config.id in known:
        raise ConfigError(f"{config.id} already exists.")
    for sample in samples:
        matched = match_config(sample.path, (config,))
        if matched is None or matched[1]:
            continue
        details = parse_manifest(sample.text, config)
        if config.format != "none" and not (
            details.package_name or details.dependencies or details.dev_dependencies
        ):
            raise ConfigError(f"it read nothing from {sample.path}.")
        return config, sample.path
    raise ConfigError("it does not match any of the files that were sent.")


class ParserAssistant:
    """Finds the project files that need a config and saves the configs the AI wrote."""

    def __init__(self, repos: RepoService, parsers_dir: Path) -> None:
        self._repos = repos
        self._parsers_dir = parsers_dir

    def samples(self, settings: GitHubSettings, info: RepoInfo) -> list[FileSample]:
        """The project files no config covers, with the part of each that would be sent."""
        samples: list[FileSample] = []
        for path in candidates(info, self._repos.configs().configs):
            text = self._repos.read_text(settings, info, path)
            if text:
                samples.append(FileSample(path, text, redact(text)))
        return samples

    def save(self, items: list[Any], samples: list[FileSample]) -> ParserSaved:
        """Check every config on its file and save the valid ones."""
        known = {c.id for c in self._repos.configs().configs}
        added: list[str] = []
        covered: set[str] = set()
        skipped: list[str] = []
        configs: list[tuple[ManifestConfig, str]] = []
        for item in items[:MAX_FILES]:
            try:
                config, path = _check(item, samples, known)
            except ConfigError as error:
                skipped.append(f"A config was not saved: {error}")
                continue
            self._parsers_dir.mkdir(parents=True, exist_ok=True)
            target = self._parsers_dir / f"{config.id}.json"
            target.write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")
            known.add(config.id)
            covered.add(path)
            added.append(config.id)
            configs.append((config, path))
        skipped += [f"{s.path} was left alone." for s in samples if s.path not in covered]
        return ParserSaved(tuple(added), tuple(skipped), tuple(configs))
