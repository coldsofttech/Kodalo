"""Ask the default AI model to write parser configs for project files Kodalo does not know yet.

Only the top-level files that no config covers are looked at, and only the first few lines of each
(with secret-looking lines removed) are sent. The answer must be JSON in the parser config format;
every config is checked and tried on the real file before it is saved to the user's parsers folder.
See ``docs/manifest-parsers.md``.
"""

import fnmatch
import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from kodalo.core.ai import AiConnections, AiInvalidError
from kodalo.core.github import GitHubSettings
from kodalo.core.repo.manifest_config import (
    ConfigError,
    ManifestConfig,
    match_config,
    parse_config,
)
from kodalo.core.repo.manifest_parser import parse_manifest
from kodalo.core.repo.models import RepoInfo
from kodalo.core.repo.service import RepoService

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
_SECRET_FILE = (".env*", "*.pem", "*.key", "id_rsa*", "*secret*", "*credential*")


@dataclass(frozen=True)
class FileSample:
    """A project file nobody covers: its path, its whole text, and the part that gets sent."""

    path: str
    text: str
    sent: str


@dataclass(frozen=True)
class ParserPlan:
    """What a run would do and cost, for the user to approve before anything is sent."""

    provider: str
    label: str
    model: str
    files: tuple[str, ...]
    input_tokens: int
    max_output_tokens: int


@dataclass(frozen=True)
class ParserResult:
    """What a run did: the configs saved, the files skipped (with why) and the tokens used."""

    added: tuple[str, ...]
    skipped: tuple[str, ...]
    input_tokens: int
    output_tokens: int


def system_prompt() -> str:
    """The instructions sent to every provider: the bundled skill file without its front matter."""
    prompt = resources.files("kodalo.core.ai") / "prompts" / "repo" / "parser-config.SKILL.md"
    text = prompt.read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


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
    """Plans and runs the AI step for one stored repository."""

    def __init__(self, repos: RepoService, ai: AiConnections, parsers_dir: Path) -> None:
        self._repos = repos
        self._ai = ai
        self._parsers_dir = parsers_dir

    def _samples(self, settings: GitHubSettings, info: RepoInfo) -> list[FileSample]:
        samples: list[FileSample] = []
        for path in candidates(info, self._repos.configs().configs):
            text = self._repos.read_text(settings, info, path)
            if text:
                samples.append(FileSample(path, text, redact(text)))
        return samples

    def plan(self, settings: GitHubSettings, repo_id: str) -> ParserPlan:
        """Work out which files need a config and what asking would cost. Nothing is sent."""
        return self._plan(self._samples(settings, self._repos.get(repo_id)))

    def _plan(self, samples: list[FileSample]) -> ParserPlan:
        if not samples:
            return ParserPlan("", "", "", (), 0, 0)
        target = self._ai.default_target()
        output = OUTPUT_TOKENS_PER_FILE * len(samples)
        return ParserPlan(
            provider=target.provider,
            label=target.label,
            model=target.model,
            files=tuple(s.path for s in samples),
            input_tokens=estimate_tokens(system_prompt(), build_prompt(samples)),
            max_output_tokens=min(output, target.max_tokens or output),
        )

    def apply(self, settings: GitHubSettings, repo_id: str) -> ParserResult:
        """Ask the model once for all files, and save every config that passes the checks."""
        samples = self._samples(settings, self._repos.get(repo_id))
        if not samples:
            return ParserResult((), (), 0, 0)
        reply = self._ai.generate(
            system_prompt(), build_prompt(samples), self._plan(samples).max_output_tokens
        )
        data = _reply_json(reply.text)
        items = data.get("configs") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise AiInvalidError(
                "The AI did not answer in the expected format, so nothing was changed."
            )
        known = {c.id for c in self._repos.configs().configs}
        added: list[str] = []
        covered: set[str] = set()
        skipped: list[str] = []
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
        skipped += [f"{s.path} was left alone." for s in samples if s.path not in covered]
        return ParserResult(tuple(added), tuple(skipped), reply.input_tokens, reply.output_tokens)
