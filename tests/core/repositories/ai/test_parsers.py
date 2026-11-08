"""The parser part of the AI analysis: finding gaps and checking configs."""

import pytest

from kodalo.core.repositories import Entry, RepoInfo
from kodalo.core.repositories.ai.parsers import (
    FileSample,
    _check,
    _reply_json,
    candidates,
    redact,
)
from kodalo.core.repositories.configs.manifest import ConfigError, load_configs

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
