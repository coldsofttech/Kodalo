"""The AI parser step: finding gaps, checking replies and saving only valid configs."""

import json
from pathlib import Path

import pytest

from kodalo.core.ai import AiInvalidError
from kodalo.core.repo import Entry, RepoInfo
from kodalo.core.repo.ai_parsers import (
    FileSample,
    ParserAssistant,
    _check,
    _reply_json,
    candidates,
    redact,
    system_prompt,
)
from kodalo.core.repo.manifest_config import ConfigError, load_configs

CARTFILE = 'github "Alamofire/Alamofire" ~> 5.0\ngithub "SnapKit/SnapKit"\n'
CONFIG = {
    "schema_version": 1,
    "id": "swift-carthage",
    "ecosystem": "swift",
    "files": ["Cartfile"],
    "format": "lines",
    "dependencies": [{"regex": '^github "(?P<value>[^"]+)"'}],
}


def _info(*names: str) -> RepoInfo:
    return RepoInfo(url="u", owner="o", name="n", top_level=tuple(Entry(n, "file") for n in names))


def test_prompt_has_no_front_matter() -> None:
    assert not system_prompt().startswith("---")
    assert "schema_version" in system_prompt()


def test_candidates_skip_known_docs_secrets_and_dotfiles() -> None:
    configs = load_configs(None).configs
    info = _info("pyproject.toml", "README.md", ".env", "Cartfile", "Gemfile", "notes.png")
    assert candidates(info, configs) == ["Cartfile"]


def test_redact_drops_secret_lines_and_caps_size() -> None:
    text = "name = 'x'\napi_key = 'abc'\n" + "a = 1\n" * 1000
    out = redact(text)
    assert "api_key" not in out
    assert len(out.encode()) <= 1500


def test_reply_json_accepts_fenced_answers() -> None:
    assert _reply_json('```json\n{"configs": []}\n```') == {"configs": []}
    assert _reply_json("no json here") is None


def test_check_runs_the_config_on_the_file() -> None:
    sample = FileSample("Cartfile", CARTFILE, CARTFILE)
    config, path = _check(CONFIG, [sample], set())
    assert (config.id, path) == ("swift-carthage", "Cartfile")
    with pytest.raises(ConfigError, match="already exists"):
        _check(CONFIG, [sample], {"swift-carthage"})
    with pytest.raises(ConfigError, match="read nothing"):
        _check(CONFIG, [FileSample("Cartfile", "# empty", "# empty")], set())


class _Repos:
    def __init__(self, parsers: Path) -> None:
        self._parsers = parsers

    def get(self, repo_id: str) -> RepoInfo:
        return _info("Cartfile")

    def configs(self):  # type: ignore[no-untyped-def]
        return load_configs(self._parsers)

    def read_text(self, settings: object, info: RepoInfo, path: str) -> str:
        return CARTFILE


class _Ai:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls = 0

    def default_target(self):  # type: ignore[no-untyped-def]
        from kodalo.core.ai import AiTarget

        return AiTarget("claude_api", "Claude API", "m", 500, None, None)

    def generate(self, system: str, prompt: str, max_tokens: int):  # type: ignore[no-untyped-def]
        from kodalo.core.ai import Generation

        self.calls += 1
        assert max_tokens == 500
        return Generation(self.reply, 10, 20)


def _assistant(tmp_path: Path, reply: str) -> tuple[ParserAssistant, _Ai]:
    ai = _Ai(reply)
    return ParserAssistant(_Repos(tmp_path), ai, tmp_path), ai  # type: ignore[arg-type]


def test_plan_caps_output_and_sends_nothing(tmp_path: Path) -> None:
    assistant, ai = _assistant(tmp_path, "")
    plan = assistant.plan(None, "id")  # type: ignore[arg-type]
    assert plan.files == ("Cartfile",)
    assert plan.max_output_tokens == 500
    assert plan.input_tokens > 0
    assert ai.calls == 0


def test_apply_saves_valid_configs(tmp_path: Path) -> None:
    assistant, _ = _assistant(tmp_path, json.dumps({"configs": [CONFIG]}))
    result = assistant.apply(None, "id")  # type: ignore[arg-type]
    assert result.added == ("swift-carthage",)
    assert (tmp_path / "swift-carthage.json").is_file()
    assert (result.input_tokens, result.output_tokens) == (10, 20)


def test_apply_skips_invalid_configs_and_rejects_bad_answers(tmp_path: Path) -> None:
    assistant, _ = _assistant(tmp_path, json.dumps({"configs": [{"id": "x"}]}))
    result = assistant.apply(None, "id")  # type: ignore[arg-type]
    assert result.added == ()
    assert any("Cartfile was left alone" in line for line in result.skipped)
    bad, _ = _assistant(tmp_path, "sorry")
    with pytest.raises(AiInvalidError):
        bad.apply(None, "id")  # type: ignore[arg-type]
