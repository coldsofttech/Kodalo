"""Ask the default AI model once to analyze a repository: parsers, frameworks and tools together.

One request holds the start of the project files no parser config covers, and the package and file
names no framework or tooling config covers. The one answer is split into the three kinds of config;
each is checked by its own part (``parsers``, ``frameworks``) before it is saved. Frameworks
may also match the packages that a newly saved parser reads from its file, so one run is enough.
See ``docs/repository-analysis.md``.
"""

from dataclasses import dataclass, replace
from importlib import resources
from pathlib import Path

from kodalo.core.ai import AiConnections
from kodalo.core.repositories.ai import frameworks, parsers
from kodalo.core.repositories.configs.framework import FRAMEWORKS, TOOLING
from kodalo.core.repositories.parsers.manifest import parse_manifest
from kodalo.core.repositories.service import RepoService
from kodalo.core.settings.ai import AiInvalidError
from kodalo.core.settings.github import GitHubSettings

OUTPUT_TOKENS_PER_FRAMEWORK = 120


@dataclass(frozen=True)
class AnalyzerPlan:
    """What a run would send and cost, for the user to approve before anything is sent."""

    provider: str
    label: str
    model: str
    files: tuple[str, ...]
    dependencies: tuple[str, ...]
    names: tuple[str, ...]
    tool_files: tuple[str, ...]
    input_tokens: int
    max_output_tokens: int


@dataclass(frozen=True)
class AnalyzerResult:
    """What a run did: the configs saved, what was left out (with why) and the tokens used."""

    parsers: tuple[str, ...]
    frameworks: tuple[str, ...]
    tools: tuple[str, ...]
    skipped: tuple[str, ...]
    input_tokens: int
    output_tokens: int


def system_prompt() -> str:
    """The instructions sent to every provider: the bundled skill file without its front matter."""
    prompt = resources.files("kodalo.core.ai") / "prompts" / "repo" / "repo-analyzer.SKILL.md"
    text = prompt.read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def build_prompt(samples: list[parsers.FileSample], sample: frameworks._Sample, asked: bool) -> str:
    """The user message: the project files, then the names (only when there are names to ask)."""
    parts = []
    if samples:
        parts.append("project files:\n" + parsers.build_prompt(samples))
    if asked:
        parts.append(frameworks.build_prompt(sample))
    return "\n\n".join(parts)


def _asked(sample: frameworks._Sample) -> bool:
    return bool(sample.dependencies or sample.tool_files)


class RepoAnalyzer:
    """Plans and runs the single AI analysis for one stored repository."""

    def __init__(
        self,
        repos: RepoService,
        ai: AiConnections,
        parsers_dir: Path,
        frameworks_dir: Path,
        tooling_dir: Path,
    ) -> None:
        self._repos = repos
        self._ai = ai
        self._parsers = parsers.ParserAssistant(repos, parsers_dir)
        self._frameworks = frameworks.FrameworkAssistant(repos, frameworks_dir, tooling_dir)

    def plan(self, settings: GitHubSettings, repo_id: str) -> AnalyzerPlan:
        """Work out what would be sent and what asking would cost. Nothing is sent."""
        info = self._repos.get(repo_id)
        return self._plan(self._parsers.samples(settings, info), self._frameworks.sample(info))

    def _plan(self, samples: list[parsers.FileSample], sample: frameworks._Sample) -> AnalyzerPlan:
        asked = _asked(sample)
        if not samples and not asked:
            return AnalyzerPlan("", "", "", (), (), (), (), 0, 0)
        target = self._ai.default_target("repo_metadata")
        output = parsers.OUTPUT_TOKENS_PER_FILE * len(samples)
        if asked:
            output += OUTPUT_TOKENS_PER_FRAMEWORK * frameworks.MAX_FRAMEWORKS
        return AnalyzerPlan(
            provider=target.provider,
            label=target.label,
            model=target.model,
            files=tuple(s.path for s in samples),
            dependencies=tuple(name for _, name in sample.dependencies) if asked else (),
            names=sample.files if asked else (),
            tool_files=sample.tool_files,
            input_tokens=parsers.estimate_tokens(
                system_prompt(), build_prompt(samples, sample, asked)
            ),
            max_output_tokens=min(output, target.max_tokens or output),
        )

    def apply(self, settings: GitHubSettings, repo_id: str) -> AnalyzerResult:
        """Ask the model once, and save every parser, framework and tool that passes the checks."""
        info = self._repos.get(repo_id)
        samples = self._parsers.samples(settings, info)
        sample = self._frameworks.sample(info)
        asked = _asked(sample)
        if not samples and not asked:
            return AnalyzerResult((), (), (), (), 0, 0)
        reply = self._ai.generate(
            system_prompt(),
            build_prompt(samples, sample, asked),
            self._plan(samples, sample).max_output_tokens,
            purpose="studio",
            title=f"Repository analysis for {info.owner}/{info.name}",
            task="repo_metadata",
        )
        data = parsers._reply_json(reply.text)
        kinds = ("configs", FRAMEWORKS.key, TOOLING.key)
        if not isinstance(data, dict) or not any(isinstance(data.get(k), list) for k in kinds):
            raise AiInvalidError(
                "The AI did not answer in the expected format, so nothing was changed."
            )
        skipped: list[str] = []
        added_parsers: tuple[str, ...] = ()
        if samples:
            items = data.get("configs")
            saved = self._parsers.save(items if isinstance(items, list) else [], samples)
            added_parsers = saved.added
            skipped += saved.skipped
            sample = _with_parsed(sample, samples, saved)
        found = frameworks.FrameworkSaved((), (), ())
        if _asked(sample):
            found = self._frameworks.save(data, sample)
            skipped += found.skipped
        return AnalyzerResult(
            added_parsers,
            found.added,
            found.tools,
            tuple(skipped),
            reply.input_tokens,
            reply.output_tokens,
        )


def _with_parsed(
    sample: frameworks._Sample, samples: list[parsers.FileSample], saved: parsers.ParserSaved
) -> frameworks._Sample:
    """Add the packages a newly saved parser reads from its file to what frameworks may match."""
    text = {s.path: s.text for s in samples}
    found: dict[tuple[str, str], None] = dict.fromkeys(sample.dependencies)
    for config, path in saved.configs:
        details = parse_manifest(text[path], config)
        for name in (*details.dependencies, *details.dev_dependencies):
            found[(config.ecosystem, name)] = None
    return replace(sample, dependencies=tuple(found))
