"""Reading the README and docs of a repository, and asking the AI for use cases."""

import base64
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from kodalo.core.ai import AiTarget, Generation
from kodalo.core.repositories import (
    ReadmeAssistant,
    ReadmeService,
    RepoNotFoundError,
    RepoService,
)
from kodalo.core.repositories import readme as rd
from kodalo.core.repositories.ai.readme import build_prompt, redact, system_prompt
from kodalo.core.settings.ai import AiInvalidError
from kodalo.core.settings.github import GitHubConnectivity, GitHubInvalidError, GitHubSettings
from kodalo.core.storage import Database, database_path
from kodalo.core.studio import validate_source

README = """# Sweepito

[![CI](https://img.shields.io/x.svg)](https://ci)

Sweepito cleans up caches and build folders. It is fast.

## Features

- **Clean caches**: remove package manager caches
- Dry run - show what would be removed
- **Scheduled cleaning**: coming soon

## Installation

```bash
$ pip install sweepito
uv tool install sweepito
# a comment
brew install sweepito
```

Download the installer from the releases page.

### From source

```
git clone https://github.com/o/r
```

See [the CLI guide](docs/cli.md#clean), [security](SECURITY.md), [site](https://x.dev/a.md)
and [changelog](CHANGELOG.md) and [reference](docs/cli-reference.md).

## Roadmap

- Windows service
"""
CLI = (
    "# CLI\n\n## Commands\n\n- `sweepito clean` - clean now\n\n"
    "## Install\n\n```\npip install sweepito\n```\n"
)


def _file(text: str) -> dict[str, Any]:
    return {
        "size": len(text),
        "encoding": "base64",
        "content": base64.b64encode(text.encode()).decode(),
    }


def _api(files: dict[str, str]) -> dict[str, Any]:
    tree = [{"path": "docs", "type": "tree"}] + [{"path": path, "type": "blob"} for path in files]
    data: dict[str, Any] = {
        "repos/o/r": {
            "name": "r",
            "owner": {"login": "o"},
            "description": "From GitHub",
            "default_branch": "main",
        },
        "repos/o/r/languages": {},
        "repos/o/r/git/trees/main?recursive=1": {"tree": tree},
    }
    data |= {f"repos/o/r/contents/{p}": _file(t) for p, t in files.items()}
    return data


class FakeApi:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.calls: list[str] = []

    def __call__(self, path: str) -> Any:
        self.calls.append(path)
        if path not in self.data:
            raise RepoNotFoundError("missing")
        return self.data[path]


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    db = Database.open(database_path(tmp_path / "data"))
    yield db
    db.close()


def _stored(database: Database, files: dict[str, str]) -> tuple[FakeApi, RepoService, str]:
    api = FakeApi(_api(files))
    repos = RepoService(database, gh=api)
    info = repos.read(GitHubSettings("gh_cli"), validate_source(GitHubSettings("gh_cli"), "o/r"))
    return api, repos, info.id


def test_purpose_skips_badges_and_takes_first_sentence() -> None:
    tagline, summary = rd.purpose(README)

    assert tagline == "Sweepito cleans up caches and build folders."
    assert summary == "Sweepito cleans up caches and build folders. It is fast."


def test_purpose_is_empty_without_prose() -> None:
    assert rd.purpose("# Title\n\n- only a list\n") == ("", "")


def test_installation_reads_install_sections_only() -> None:
    found = rd.installation("README.md", README + "\n## Other\n\n```\nnpm install nope\n```\n")

    assert [(i.method, i.command) for i in found] == [
        ("pip", "pip install sweepito"),
        ("uv", "uv tool install sweepito"),
        ("Homebrew", "brew install sweepito"),
        ("Installer", ""),
        ("From source", "git clone https://github.com/o/r"),
    ]
    assert found[0].evidence == rd.Evidence("README.md", "pip install sweepito", "documented")


def test_capabilities_name_description_and_planned_notes() -> None:
    found = rd.capabilities("README.md", README)

    assert [(c.name, c.description, c.note) for c in found] == [
        ("Clean caches", "remove package manager caches", ""),
        ("Dry run", "show what would be removed", ""),
        ("Scheduled cleaning", "coming soon", "Planned or experimental"),
        ("Windows service", "", "Planned or experimental"),
    ]
    assert found[0].evidence.quote == "- **Clean caches**: remove package manager caches"


def test_long_bullets_without_a_separator_are_cut_to_the_first_words() -> None:
    found = rd.capabilities(
        "a.md", "## Features\n\n- one two three four five six seven eight nine\n"
    )

    assert found[0].name == "one two three four five six seven eight"
    assert found[0].description == "nine"


def test_linked_documents_are_relative_markdown_only() -> None:
    assert rd.linked_documents("README.md", README) == [
        "docs/cli.md",
        "SECURITY.md",
        "CHANGELOG.md",
        "docs/cli-reference.md",
    ]
    assert rd.linked_documents("docs/a.md", "[x](b.md) [y](../c.md) [z](../../d.md)") == [
        "docs/b.md",
        "c.md",
    ]


def test_quote_is_one_short_line() -> None:
    assert rd.quote("a\n  b") == "a b"
    assert len(rd.quote("x" * 300)) == rd.MAX_QUOTE


def test_read_follows_links_one_level_and_skips_the_rest(database: Database) -> None:
    api, repos, repo_id = _stored(
        database,
        {"README.md": README, "docs/cli.md": CLI, "SECURITY.md": "x", "CHANGELOG.md": "x"},
    )
    service = ReadmeService(database, repos)
    before = len(api.calls)

    result = service.read(GitHubSettings("gh_cli"), repo_id)

    assert [(d.path, d.status, d.reason) for d in result.documents] == [
        ("README.md", "read", ""),
        ("docs/cli.md", "read", ""),
        ("docs/cli-reference.md", "skipped", rd.SKIP_GENERATED),
        ("SECURITY.md", "skipped", rd.SKIP_NOT_USEFUL),
        ("CHANGELOG.md", "skipped", rd.SKIP_NOT_USEFUL),
    ]
    assert result.tagline == "Sweepito cleans up caches and build folders."
    assert result.purpose_file == "README.md"
    assert "sweepito clean" in [c.name for c in result.capabilities]
    assert [i.method for i in result.installation].count("pip") == 1  # the same command, once
    assert api.calls[before:] == [
        "repos/o/r/contents/README.md",
        "repos/o/r/contents/docs/cli.md",
    ]  # nothing the first analysis already fetched is fetched again


def test_saved_analysis_is_reused_until_refresh(database: Database) -> None:
    api, repos, repo_id = _stored(database, {"README.md": README})
    service = ReadmeService(database, repos)
    settings = GitHubSettings("gh_cli")

    first = service.read(settings, repo_id)
    calls = len(api.calls)
    again = service.read(settings, repo_id)

    assert again == first
    assert len(api.calls) == calls
    assert service.get(repo_id) == first
    service.read(settings, repo_id, refresh=True)
    assert len(api.calls) > calls


def test_document_limit_and_size_are_settings(database: Database) -> None:
    _, repos, repo_id = _stored(
        database, {"README.md": README, "docs/cli.md": CLI, "docs/more.md": "x"}
    )
    service = ReadmeService(database, repos)
    settings = GitHubSettings("gh_cli", document_limit=1, document_max_kb=1)

    result = service.read(settings, repo_id)

    assert [d.path for d in result.documents if d.status == "read"] == ["README.md"]
    assert next(d for d in result.documents if d.path == "docs/cli.md").reason == rd.SKIP_OVER_LIMIT

    big = _stored_big(database)
    assert any("larger than 1 KB" in w for w in big.warnings)


def _stored_big(database: Database) -> rd.ReadmeAnalysis:
    text = "# T\n\nIntro.\n\n" + "- filler item here\n" * 200
    api = FakeApi(_api({"README.md": text}))
    repos = RepoService(database, gh=api)
    info = repos.read(GitHubSettings(), validate_source(GitHubSettings(), "o/r"), refresh=True)
    return ReadmeService(database, repos).read(
        GitHubSettings(document_max_kb=1), info.id, refresh=True
    )


def test_missing_readme_falls_back_to_the_description(database: Database) -> None:
    _, repos, repo_id = _stored(database, {"main.py": "x"})

    result = ReadmeService(database, repos).read(GitHubSettings("gh_cli"), repo_id)

    assert (result.tagline, result.summary) == ("From GitHub", "From GitHub")
    assert "No README or document could be read." in result.warnings


def test_unknown_repository_is_not_found(database: Database) -> None:
    service = ReadmeService(database, RepoService(database))

    with pytest.raises(RepoNotFoundError):
        service.read(GitHubSettings(), "missing")


def test_document_settings_are_saved_and_checked(database: Database) -> None:
    connectivity = GitHubConnectivity(database)

    assert connectivity.get().document_limit == 10
    assert connectivity.get().document_max_kb == 200
    saved = connectivity.save("gh_cli", document_limit=20, document_max_kb=50)
    assert (saved.document_limit, saved.document_max_kb) == (20, 50)
    assert connectivity.save("gh_cli").document_limit == 20  # left out keeps the saved value
    with pytest.raises(GitHubInvalidError):
        connectivity.save("gh_cli", document_limit=0)
    with pytest.raises(GitHubInvalidError):
        connectivity.save("gh_cli", document_max_kb=2001)
    assert connectivity.save("gh_cli", document_max_kb=2000).document_max_kb == 2000


class _Ai:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def default_target(self) -> AiTarget:
        return AiTarget("claude_api", "Claude API", "m", 5000, None, None)

    def generate(self, system: str, prompt: str, max_tokens: int, **_: str) -> Generation:
        self.prompts.append(prompt)
        return Generation(self.reply, 10, 20)


def _assistant(
    database: Database, reply: dict[str, Any] | str, files: dict[str, str] | None = None
) -> tuple[ReadmeAssistant, ReadmeService, _Ai, str]:
    _, repos, repo_id = _stored(database, files or {"README.md": README, "docs/cli.md": CLI})
    service = ReadmeService(database, repos)
    service.read(GitHubSettings("gh_cli"), repo_id)
    ai = _Ai(reply if isinstance(reply, str) else json.dumps(reply))
    return ReadmeAssistant(service, ai), service, ai, repo_id  # type: ignore[arg-type]


REPLY = {
    "purpose": {
        "tagline": "Sweepito tidies caches.",
        "summary": "Sweepito cleans up caches and build folders.",
        "file": "README.md",
    },
    "installation": [
        {"method": "pip", "command": "pip install sweepito", "file": "README.md",
         "quote": "pip install sweepito"},
        {"method": "npm", "command": "npm i x", "file": "README.md", "quote": "npm i x"},
    ],
    "capabilities": [
        {"name": "Clean caches", "description": "Removes caches.", "file": "README.md",
         "quote": "**Clean caches**: remove package manager caches"},
        {"name": "Invented", "description": "x", "file": "README.md", "quote": "not in the file"},
        {"name": "Planned thing", "description": "", "note": "Planned or experimental",
         "file": "docs/cli.md", "quote": "sweepito clean` - clean now"},
    ],
    "use_cases": [
        {"title": "Free disk space", "description": "Clean caches.",
         "capabilities": ["clean caches"]},
        {"title": "Made up", "description": "x", "capabilities": ["Invented"]},
        {"title": "No capability", "description": "x", "capabilities": []},
    ],
}  # fmt: skip


def test_the_ai_reads_the_documents_and_only_evidence_is_kept(database: Database) -> None:
    assistant, service, ai, repo_id = _assistant(database, REPLY)

    plan = assistant.plan(repo_id)
    result = assistant.apply(GitHubSettings("gh_cli"), repo_id)

    assert plan.documents == ("README.md", "docs/cli.md")
    assert plan.input_tokens > 0
    assert "### README.md" in ai.prompts[0]
    assert "# Sweepito" in ai.prompts[0]
    assert "### docs/cli.md" in ai.prompts[0]
    assert (result.installation, result.capabilities, result.use_cases) == (1, 2, 1)
    assert len(result.skipped) == 4  # npm, Invented, Made up, No capability
    saved = service.get(repo_id)
    assert saved is not None
    assert saved.tagline == "Sweepito tidies caches."
    assert [(i.method, i.evidence.quote) for i in saved.installation] == [
        ("pip", "pip install sweepito")
    ]
    assert [c.name for c in saved.capabilities] == ["Clean caches", "Planned thing"]
    assert saved.capabilities[1].note == "Planned or experimental"
    assert saved.use_cases[0].evidence == rd.Evidence(
        "README.md", "**Clean caches**: remove package manager caches", "inferred"
    )
    assert saved.use_cases_at


def test_features_keep_only_checked_details(database: Database) -> None:
    reply = {
        **REPLY,
        "features": [
            {"name": "Cache cleanup", "description": "Removes caches.", "importance": "headline",
             "maturity": "stable", "capabilities": ["Clean caches"],
             "use_cases": ["free disk space", "Made up"],
             "claims": [
                 {"type": "performance", "text": "remove package manager caches", "reason": "x"},
                 {"type": "number", "text": "97 rules", "reason": "not in the documents"},
                 {"type": "bogus", "text": "remove package manager caches", "reason": "x"},
             ]},
            {"name": "Odd values", "importance": "huge", "maturity": "soon",
             "capabilities": ["Planned thing"]},
            {"name": "Unbacked", "capabilities": ["Invented"]},
        ],
    }  # fmt: skip
    assistant, service, _, repo_id = _assistant(database, reply)

    result = assistant.apply(GitHubSettings("gh_cli"), repo_id)

    saved = service.get(repo_id)
    assert saved is not None
    assert result.features == 2
    first, second = saved.features
    assert (first.importance, first.maturity) == ("headline", "stable")
    assert first.use_cases == ("Free disk space",)
    assert [(c.type, c.text) for c in first.claims] == [
        ("performance", "remove package manager caches")
    ]
    assert (second.importance, second.maturity) == ("supporting", "unspecified")


def test_a_part_the_ai_leaves_out_keeps_what_was_found(database: Database) -> None:
    assistant, service, _, repo_id = _assistant(database, {"capabilities": []})
    before = service.get(repo_id)

    result = assistant.apply(GitHubSettings("gh_cli"), repo_id)

    after = service.get(repo_id)
    assert before is not None
    assert after is not None
    assert (result.installation, result.capabilities, result.use_cases) == (0, 0, 0)
    assert after.capabilities == before.capabilities
    assert after.installation == before.installation
    assert after.tagline == before.tagline


def test_a_refresh_after_the_ai_keeps_the_use_cases(database: Database) -> None:
    assistant, service, _, repo_id = _assistant(database, REPLY)
    assistant.apply(GitHubSettings("gh_cli"), repo_id)

    again = service.read(GitHubSettings("gh_cli"), repo_id, refresh=True)

    assert [u.title for u in again.use_cases] == ["Free disk space"]


def test_a_refresh_after_the_ai_keeps_its_text_and_only_adds_installation(
    database: Database,
) -> None:
    _, repos, repo_id = _stored(database, {"README.md": README})
    service = ReadmeService(database, repos)
    settings = GitHubSettings("gh_cli")
    found = service.read(settings, repo_id)
    service.save_ai(
        repo_id,
        ("AI tagline", "AI summary", "README.md"),
        [rd.Installation("brew", "brew install r")],
        [rd.Capability("AI capability")],
        [],
    )

    again = service.read(settings, repo_id, refresh=True)

    assert (again.tagline, again.summary) == ("AI tagline", "AI summary")
    assert next(i.method for i in again.installation) == "brew"
    assert {i.command for i in found.installation} <= {i.command for i in again.installation}
    assert [c.name for c in again.capabilities] == ["AI capability"]  # none added from the README
    assert found.capabilities  # the plain read does find capabilities of its own
    assert service.read(settings, repo_id, refresh=True) == again  # nothing new, nothing changes


def test_a_refresh_before_the_ai_replaces_what_was_found(database: Database) -> None:
    _, repos, repo_id = _stored(database, {"README.md": README})
    service = ReadmeService(database, repos)
    settings = GitHubSettings("gh_cli")

    first = service.read(settings, repo_id)

    again = service.read(settings, repo_id, refresh=True)
    assert (again.installation, again.capabilities) == (first.installation, first.capabilities)


def test_the_ai_needs_a_reply_in_the_expected_format(database: Database) -> None:
    assistant, service, _, repo_id = _assistant(database, "not json")

    with pytest.raises(AiInvalidError):
        assistant.apply(GitHubSettings("gh_cli"), repo_id)
    saved = service.get(repo_id)
    assert saved is not None
    assert saved.use_cases == ()


def test_nothing_is_sent_without_documents(database: Database) -> None:
    _, repos, repo_id = _stored(database, {"main.py": "x"})
    service = ReadmeService(database, repos)
    service.read(GitHubSettings("gh_cli"), repo_id)
    ai = _Ai("{}")
    assistant = ReadmeAssistant(service, ai)  # type: ignore[arg-type]

    assert assistant.plan(repo_id).documents == ()
    assert assistant.apply(GitHubSettings("gh_cli"), repo_id).installation == 0
    assert ai.prompts == []


def test_the_ai_needs_the_readme_to_be_read_first(database: Database) -> None:
    _, repos, repo_id = _stored(database, {"README.md": README})
    assistant = ReadmeAssistant(ReadmeService(database, repos), _Ai("{}"))  # type: ignore[arg-type]

    with pytest.raises(RepoNotFoundError):
        assistant.plan(repo_id)


def test_secret_looking_lines_are_not_sent() -> None:
    text = "Install it.NLapi_key = abcNLPASSWORD: xNLDone."

    assert redact(text.replace("NL", chr(10))) == "Install it." + chr(10) + "Done."
    assert build_prompt({"a.md": "hi", "b.md": "yo"}) == (
        "### a.md" + chr(10) + "hi" + chr(10) + chr(10) + "### b.md" + chr(10) + "yo"
    )
    assert "capabilities" in system_prompt()
