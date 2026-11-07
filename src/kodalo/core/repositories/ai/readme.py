"""Ask the default AI model once to read a repository's documents and describe its product.

The documents are the ones the README analysis already chose (the README and the docs it links to),
read again with the same limits, with the lines that look like secrets removed. The model returns
the purpose, the ways to install, the capabilities, the features and the use cases. Nothing without
evidence is kept: an installation method or capability is saved only when its quote is found in the
file it names, and a feature or use case only when it rests on a saved capability. A part the
model left empty, or whose items all failed the check, keeps what was found before. See
``docs/readme-analysis.md``.
"""

import re
from dataclasses import dataclass
from importlib import resources
from typing import Any

from kodalo.core.ai import AiConnections
from kodalo.core.repositories.ai.parsers import _SECRET_LINE, _reply_json, estimate_tokens
from kodalo.core.repositories.errors import RepoNotFoundError
from kodalo.core.repositories.readme import (
    CLAIM_TYPES,
    DOCUMENTED,
    IMPORTANCE,
    INFERRED,
    MATURITY,
    MAX_CAPABILITIES,
    Capability,
    ClaimFlag,
    Evidence,
    Feature,
    Installation,
    ReadmeAnalysis,
    ReadmeService,
    UseCase,
    quote,
)
from kodalo.core.settings.ai import AiInvalidError
from kodalo.core.settings.github import GitHubSettings

MAX_USE_CASES = 6
MAX_FEATURES = 12
MAX_CLAIMS = 5
MAX_OUTPUT_TOKENS = 6000
_KEYS = ("purpose", "installation", "capabilities", "features", "use_cases")


@dataclass(frozen=True)
class ReadmePlan:
    """What a run would send and cost, for the user to approve before anything is sent."""

    provider: str
    label: str
    model: str
    documents: tuple[str, ...]
    input_tokens: int
    max_output_tokens: int


@dataclass(frozen=True)
class ReadmeResult:
    """What a run saved, what was left out (with why) and the tokens used."""

    installation: int
    capabilities: int
    use_cases: int
    skipped: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    features: int = 0
    icon: str = ""  # the path of the icon that was kept; empty when none was found


def system_prompt() -> str:
    """The instructions sent to every provider: the bundled skill file without its front matter."""
    prompt = resources.files("kodalo.core.ai") / "prompts" / "repo" / "readme-analyzer.SKILL.md"
    text = prompt.read_text(encoding="utf-8")
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def redact(text: str) -> str:
    """Take out the lines that look like secrets."""
    return "\n".join(line for line in text.splitlines() if not _SECRET_LINE.search(line))


def build_prompt(texts: dict[str, str], icons: tuple[str, ...] = ()) -> str:
    """The user message: every document after its path, then the icon candidates."""
    parts = [f"### {path}\n{text}" for path, text in texts.items()]
    if icons:
        parts.append("### Icon candidates\n" + "\n".join(icons))
    return "\n\n".join(parts)


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


class ReadmeAssistant:
    """Plans and runs the single AI request that describes one stored repository's product."""

    def __init__(self, readme: ReadmeService, ai: AiConnections) -> None:
        self._readme = readme
        self._ai = ai

    def _analysis(self, repo_id: str) -> ReadmeAnalysis:
        analysis = self._readme.get(repo_id)
        if analysis is None:
            raise RepoNotFoundError("The README analysis has not been read yet.")
        return analysis

    def plan(self, repo_id: str) -> ReadmePlan:
        """Work out what would be sent and what asking would cost. Nothing is sent and no
        document is read again; the sizes recorded by the README analysis are used."""
        read = [d for d in self._analysis(repo_id).documents if d.status == "read"]
        if not read:
            return ReadmePlan("", "", "", (), 0, 0)
        target = self._ai.default_target("repo_features")
        tokens = estimate_tokens(system_prompt()) + sum(d.size for d in read) // 3 + len(read)
        return ReadmePlan(
            provider=target.provider,
            label=target.label,
            model=target.model,
            documents=tuple(d.path for d in read),
            input_tokens=tokens,
            max_output_tokens=min(MAX_OUTPUT_TOKENS, target.max_tokens or MAX_OUTPUT_TOKENS),
        )

    def apply(self, settings: GitHubSettings, repo_id: str) -> ReadmeResult:
        """Read the documents again, ask the model once and save what passes the checks."""
        plan = self.plan(repo_id)
        if not plan.documents:
            return ReadmeResult(0, 0, 0, (), 0, 0)
        texts = {path: redact(text) for path, text in self._readme.texts(settings, repo_id).items()}
        if not texts:
            return ReadmeResult(0, 0, 0, ("No document could be read again.",), 0, 0)
        icons = self._readme.icon_candidates(repo_id)
        reply = self._ai.generate(
            system_prompt(),
            build_prompt(texts, icons),
            plan.max_output_tokens,
            purpose="studio",
            title=f"README analysis of {repo_id}",
            task="repo_features",
        )
        data = _reply_json(reply.text)
        if not isinstance(data, dict) or not any(key in data for key in _KEYS):
            raise AiInvalidError(
                "The AI did not answer in the expected format, so nothing was changed."
            )
        skipped: list[str] = []
        installs = _installs(data.get("installation"), texts, skipped)
        capable = _capabilities(data.get("capabilities"), texts, skipped)
        cases = _use_cases(data.get("use_cases"), capable, skipped)
        featured = _features(data.get("features"), capable, cases, texts, skipped)
        purpose = data.get("purpose")
        tagline = summary = file = ""
        if isinstance(purpose, dict):
            tagline = _text(purpose.get("tagline"), 256)
            summary = _text(purpose.get("summary"), 1000)
            file = _text(purpose.get("file"), 1024)
            if file not in texts:
                file = ""
        picked = data.get("icon")
        icon = _text(picked.get("path"), 1024) if isinstance(picked, dict) else ""
        kept = self._readme.keep_icon(settings, repo_id, icon)
        self._readme.save_ai(
            repo_id,
            (tagline, summary, file) if summary else None,
            installs or None,
            capable or None,
            cases or None,
            featured or None,
        )
        return ReadmeResult(
            len(installs),
            len(capable),
            len(cases),
            tuple(skipped),
            reply.input_tokens,
            reply.output_tokens,
            len(featured),
            icon if kept else "",
        )


def _text(value: object, limit: int) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _evidence(item: dict[str, Any], texts: dict[str, str]) -> Evidence | None:
    """The item's file and quote, when the quote really is in that file."""
    file, text = _text(item.get("file"), 1024), _text(item.get("quote"), 400)
    if file in texts and text and _squash(text) in _squash(texts[file]):
        return Evidence(file, quote(text), DOCUMENTED)
    return None


def _items(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _installs(value: object, texts: dict[str, str], skipped: list[str]) -> list[Installation]:
    found: dict[tuple[str, str], Installation] = {}
    for item in _items(value):
        method, command = _text(item.get("method"), 32), _text(item.get("command"), 512)
        evidence = _evidence(item, texts)
        if not method or evidence is None:
            skipped.append(f"{method or 'An installation method'}: no matching quote in the file")
            continue
        found.setdefault(
            (method, command), Installation(method, command, _text(item.get("note"), 256), evidence)
        )
    return list(found.values())


def _capabilities(value: object, texts: dict[str, str], skipped: list[str]) -> list[Capability]:
    found: dict[str, Capability] = {}
    for item in _items(value):
        name = _text(item.get("name"), 128)
        evidence = _evidence(item, texts)
        if not name or evidence is None:
            skipped.append(f"{name or 'A capability'}: no matching quote in the file")
            continue
        description, note = _text(item.get("description"), 512), _text(item.get("note"), 256)
        found.setdefault(name.casefold(), Capability(name, description, note, evidence))
    return list(found.values())[:MAX_CAPABILITIES]


def _claims(value: object, texts: dict[str, str]) -> tuple[ClaimFlag, ...]:
    """The flagged statements whose text really is in one of the documents."""
    found: dict[str, ClaimFlag] = {}
    for item in _items(value):
        kind, text = _text(item.get("type"), 16), _text(item.get("text"), 120)
        if (
            kind in CLAIM_TYPES
            and text
            and any(_squash(text) in _squash(t) for t in texts.values())
        ):
            found.setdefault(text.casefold(), ClaimFlag(kind, text, _text(item.get("reason"), 200)))
    return tuple(found.values())[:MAX_CLAIMS]


def _features(
    value: object,
    capable: list[Capability],
    cases: list[UseCase],
    texts: dict[str, str],
    skipped: list[str],
) -> list[Feature]:
    by_name = {c.name.casefold(): c for c in capable}
    titles = {u.title.casefold(): u.title for u in cases}
    found: dict[str, Feature] = {}
    for item in _items(value):
        name = _text(item.get("name"), 128)
        names = item.get("capabilities")
        asked = [n for n in names if isinstance(n, str)] if isinstance(names, list) else []
        cited = [by_name[n.casefold()] for n in asked if n.casefold() in by_name]
        if not name or not cited or len(cited) != len(asked):
            skipped.append(f"{name or 'A feature'}: it does not rest on a saved capability")
            continue
        evidence = cited[0].evidence
        importance, maturity = _text(item.get("importance"), 16), _text(item.get("maturity"), 16)
        linked = item.get("use_cases")
        found.setdefault(
            name.casefold(),
            Feature(
                name,
                _text(item.get("description"), 300),
                Evidence(evidence.file, evidence.quote, INFERRED),
                importance if importance in IMPORTANCE else "supporting",
                maturity if maturity in MATURITY else "unspecified",
                _claims(item.get("claims"), texts),
                tuple(
                    titles[t.casefold()]
                    for t in (linked if isinstance(linked, list) else [])
                    if isinstance(t, str) and t.casefold() in titles
                ),
            ),
        )
    return list(found.values())[:MAX_FEATURES]


def _use_cases(value: object, capable: list[Capability], skipped: list[str]) -> list[UseCase]:
    by_name = {c.name.casefold(): c for c in capable}
    found: list[UseCase] = []
    for item in _items(value)[:MAX_USE_CASES]:
        title = _text(item.get("title"), 128)
        names = item.get("capabilities")
        asked = [n for n in names if isinstance(n, str)] if isinstance(names, list) else []
        cited = [by_name[n.casefold()] for n in asked if n.casefold() in by_name]
        if not title or not cited or len(cited) != len(asked):
            skipped.append(f"{title or 'A use case'}: it does not rest on a saved capability")
            continue
        evidence = cited[0].evidence
        found.append(
            UseCase(
                title,
                _text(item.get("description"), 300),
                Evidence(evidence.file, evidence.quote, INFERRED),
            )
        )
    return found
