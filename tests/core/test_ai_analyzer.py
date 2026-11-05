"""The AI repository analysis: one request, one answer, three kinds of config saved."""

import json
from pathlib import Path

import pytest

from kodalo.core.ai import AiInvalidError, AiTarget, Generation
from kodalo.core.repo import Entry, RepoAnalyzer, RepoInfo
from kodalo.core.repo.ai_analyzer import system_prompt
from kodalo.core.repo.framework_config import load_framework_configs, load_tooling_configs
from kodalo.core.repo.manifest_config import load_configs

CARTFILE = 'github "Alamofire/Alamofire" ~> 5.0\ngithub "SnapKit/SnapKit"\n'
PARSER = {
    "schema_version": 1,
    "id": "swift-carthage",
    "ecosystem": "swift",
    "files": ["Cartfile"],
    "format": "lines",
    "dependencies": [{"regex": '^github "(?P<value>[^"]+)"'}],
}
ALAMOFIRE = {
    "id": "alamofire",
    "name": "Alamofire",
    "category": "other",
    "ecosystems": ["swift"],
    "dependencies": ["Alamofire/Alamofire"],
}
EARTHLY = {"id": "earthly", "name": "Earthly", "category": "build", "files": ["Earthfile"]}
UNSENT = {"id": "unsent", "name": "Unsent", "category": "build", "files": ["Nothing"]}


def _info(*names: str) -> RepoInfo:
    return RepoInfo(url="u", owner="o", name="n", top_level=tuple(Entry(n, "file") for n in names))


class _Repos:
    def __init__(self, folder: Path, info: RepoInfo) -> None:
        self._folder = folder
        self._info = info

    def get(self, repo_id: str) -> RepoInfo:
        return self._info

    def configs(self):  # type: ignore[no-untyped-def]
        return load_configs(self._folder / "parsers")

    def framework_configs(self):  # type: ignore[no-untyped-def]
        return load_framework_configs(self._folder / "frameworks")

    def tooling_configs(self):  # type: ignore[no-untyped-def]
        return load_tooling_configs(self._folder / "tooling")

    def read_text(self, settings: object, info: RepoInfo, path: str) -> str:
        return CARTFILE


class _Ai:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def default_target(self) -> AiTarget:
        return AiTarget("claude_api", "Claude API", "m", 5000, None, None)

    def generate(self, system: str, prompt: str, max_tokens: int, **_: str) -> Generation:
        self.prompts.append(prompt)
        assert max_tokens == 3100  # one parser file and the framework and tool entries
        return Generation(self.reply, 10, 20)


def _analyzer(folder: Path, reply: str, *names: str) -> tuple[RepoAnalyzer, _Ai]:
    ai = _Ai(reply)
    repos = _Repos(folder, _info(*(names or ("Cartfile", "Earthfile"))))
    analyzer = RepoAnalyzer(
        repos,  # type: ignore[arg-type]
        ai,  # type: ignore[arg-type]
        folder / "parsers",
        folder / "frameworks",
        folder / "tooling",
    )
    return analyzer, ai


def test_one_skill_holds_all_three_kinds_of_config() -> None:
    prompt = system_prompt()
    assert not prompt.startswith("---")
    for word in ("schema_version", '"configs"', '"frameworks"', '"tools"'):
        assert word in prompt


def test_plan_sends_nothing_and_caps_output(tmp_path: Path) -> None:
    analyzer, ai = _analyzer(tmp_path, "")
    plan = analyzer.plan(None, "id")  # type: ignore[arg-type]
    assert plan.files == ("Cartfile",)
    assert plan.tool_files == ("Cartfile", "Earthfile")
    assert plan.max_output_tokens == 3100
    assert plan.input_tokens > 0
    assert ai.prompts == []


def test_apply_asks_once_and_saves_every_kind(tmp_path: Path) -> None:
    reply = json.dumps(
        {"configs": [PARSER], "frameworks": [ALAMOFIRE, {"id": "x"}], "tools": [EARTHLY, UNSENT]}
    )
    analyzer, ai = _analyzer(tmp_path, f"```json\n{reply}\n```")
    result = analyzer.apply(None, "id")  # type: ignore[arg-type]
    assert len(ai.prompts) == 1
    assert ai.prompts[0].startswith("project files:\n### Cartfile")
    assert (result.parsers, result.frameworks, result.tools) == (
        ("swift-carthage",),
        ("alamofire",),
        ("earthly",),
    )
    assert len(result.skipped) == 2  # the incomplete framework and the tool that matches nothing
    assert (tmp_path / "parsers" / "swift-carthage.json").is_file()
    assert (tmp_path / "frameworks" / "alamofire.json").is_file()
    assert (tmp_path / "tooling" / "earthly.json").is_file()
    assert (result.input_tokens, result.output_tokens) == (10, 20)


def test_a_framework_needs_a_parser_that_was_saved_to_match_its_packages(tmp_path: Path) -> None:
    reply = json.dumps({"configs": [{"id": "x"}], "frameworks": [ALAMOFIRE]})
    analyzer, _ = _analyzer(tmp_path, reply)
    result = analyzer.apply(None, "id")  # type: ignore[arg-type]
    assert result.parsers == ()  # the invalid parser means the package is never read
    assert result.frameworks == ()
    assert any("Cartfile was left alone" in line for line in result.skipped)


def test_apply_rejects_answers_in_the_wrong_format(tmp_path: Path) -> None:
    analyzer, _ = _analyzer(tmp_path, "sorry")
    with pytest.raises(AiInvalidError):
        analyzer.apply(None, "id")  # type: ignore[arg-type]
    assert not list(tmp_path.rglob("*.json"))


def test_nothing_is_asked_when_everything_is_understood(tmp_path: Path) -> None:
    analyzer, ai = _analyzer(tmp_path, "", "README.md")
    result = analyzer.apply(None, "id")  # type: ignore[arg-type]
    assert result.input_tokens == 0
    assert ai.prompts == []
