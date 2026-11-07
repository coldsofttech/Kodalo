from collections.abc import Iterator
from pathlib import Path

import pytest

from kodalo.core.ai import AiConnections, Probe
from kodalo.core.settings.ai import (
    APP_DEFAULTS,
    PROVIDER_IDS,
    AiConnectionError,
    AiInvalidError,
    AiNotFoundError,
    defaults_for,
)
from kodalo.core.storage import Database, database_path

KEY = "sk-test-1234567890abcdef"


class MemorySecrets:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, ref: str) -> str | None:
        return self.values.get(ref)

    def set(self, ref: str, value: str) -> None:
        self.values[ref] = value

    def delete(self, ref: str) -> None:
        self.values.pop(ref, None)


class FakeProber:
    def __init__(self) -> None:
        self.models = ["model-b", "model-a"]
        self.error: str | None = None
        self.calls: list[tuple[str, str, str]] = []

    def __call__(self, provider: str, base_url: str, api_key: str) -> Probe:
        self.calls.append((provider, base_url, api_key))
        if self.error is not None:
            raise AiConnectionError(self.error)
        return Probe(list(self.models), "Connected.")


@pytest.fixture
def secrets() -> MemorySecrets:
    return MemorySecrets()


@pytest.fixture
def prober() -> FakeProber:
    return FakeProber()


@pytest.fixture
def ai(tmp_path: Path, secrets: MemorySecrets, prober: FakeProber) -> Iterator[AiConnections]:
    database = Database.open(database_path(tmp_path))
    yield AiConnections(database, secrets, prober)
    database.close()


def test_lists_every_provider_unsaved(ai: AiConnections) -> None:
    connections = ai.list_all()
    assert [c.provider for c in connections] == list(PROVIDER_IDS)
    assert not any(c.saved or c.enabled or c.has_key for c in connections)


def test_save_keeps_the_key_out_of_the_database(ai: AiConnections, secrets: MemorySecrets) -> None:
    connection = ai.save("claude_api", api_key=f"  {KEY}  ")
    assert connection.saved
    assert connection.enabled
    assert connection.has_key
    assert connection.key_hint == KEY[-4:]
    assert secrets.values == {"ai/claude_api": KEY}
    assert KEY not in repr(connection)


def test_save_none_keeps_saved_values(ai: AiConnections) -> None:
    ai.save("chatgpt_api", api_key=KEY, base_url="https://proxy.example.com/")
    connection = ai.save("chatgpt_api", enabled=False)
    assert not connection.enabled
    assert connection.has_key
    assert connection.base_url == "https://proxy.example.com"


def test_empty_base_url_goes_back_to_default(ai: AiConnections) -> None:
    ai.save("gemini_api", api_key=KEY, base_url="https://proxy.example.com")
    assert ai.save("gemini_api", base_url="").base_url == ""


@pytest.mark.parametrize(
    ("provider", "kwargs"),
    [
        ("nope", {}),
        ("claude_api", {"api_key": "  "}),
        ("claude_api", {"base_url": "ftp://example.com"}),
        ("claude_api", {"base_url": "https://" + "a" * 600}),
        ("claude_code", {"api_key": KEY}),
        ("claude_code", {"base_url": "https://example.com"}),
    ],
)
def test_save_rejects_bad_values(ai: AiConnections, provider: str, kwargs: dict[str, str]) -> None:
    with pytest.raises(AiInvalidError):
        ai.save(provider, **kwargs)  # type: ignore[arg-type]


def test_remove_forgets_everything(ai: AiConnections, secrets: MemorySecrets) -> None:
    ai.save("claude_api", api_key=KEY)
    ai.save_model("claude_api", "m1")
    assert ai.remove("claude_api") is True
    assert secrets.values == {}
    assert not ai.get("claude_api").saved
    assert ai.remove("claude_api") is False


def test_only_one_default_connection(ai: AiConnections) -> None:
    ai.save("claude_api", api_key=KEY)
    ai.save("chatgpt_api", api_key=KEY)
    ai.set_default("claude_api")
    ai.set_default("chatgpt_api")
    assert [c.provider for c in ai.list_all() if c.is_default] == ["chatgpt_api"]


def test_default_needs_a_saved_enabled_connection(ai: AiConnections) -> None:
    with pytest.raises(AiInvalidError):
        ai.set_default("claude_api")
    ai.save("claude_api", api_key=KEY)
    ai.set_default("claude_api")
    assert not ai.save("claude_api", enabled=False).is_default
    with pytest.raises(AiInvalidError):
        ai.set_default("claude_api")


def test_test_records_the_outcome(ai: AiConnections, prober: FakeProber) -> None:
    ai.save("claude_api", api_key=KEY)
    check = ai.test("claude_api")
    assert (check.ok, check.detail) == (True, "Connected.")
    assert prober.calls == [("claude_api", "https://api.anthropic.com", KEY)]
    assert ai.get("claude_api").status == "ok"

    prober.error = "The provider rejected the API key."
    check = ai.test("claude_api")
    assert not check.ok
    connection = ai.get("claude_api")
    assert (connection.status, connection.status_detail) == ("failed", check.detail)


def test_test_needs_a_key(ai: AiConnections) -> None:
    with pytest.raises(AiInvalidError):
        ai.test("gemini_api")


def test_changing_the_key_clears_the_status(ai: AiConnections) -> None:
    ai.save("claude_api", api_key=KEY)
    ai.test("claude_api")
    assert ai.save("claude_api", api_key=KEY + "x").status == ""


def test_claude_code_needs_no_key(ai: AiConnections, prober: FakeProber) -> None:
    assert ai.test("claude_code").ok
    assert prober.calls == [("claude_code", "", "")]


def test_refresh_saves_models(ai: AiConnections) -> None:
    ai.save("claude_api", api_key=KEY)
    models = ai.refresh_models("claude_api")
    assert [(m.name, m.source) for m in models] == [("model-a", "fetched"), ("model-b", "fetched")]


def test_refresh_needs_a_saved_connection(ai: AiConnections) -> None:
    with pytest.raises(AiInvalidError):
        ai.refresh_models("claude_code")


def test_refresh_keeps_manual_models_and_settings(ai: AiConnections, prober: FakeProber) -> None:
    ai.save("claude_api", api_key=KEY)
    ai.refresh_models("claude_api")
    ai.save_model("claude_api", "model-a", max_tokens=500, temperature=0.5, timeout_s=30)
    ai.save_model("claude_api", "mine")
    ai.set_default_model("claude_api", "model-b")

    prober.models = ["model-a"]
    models = {m.name: m for m in ai.refresh_models("claude_api")}
    assert set(models) == {"model-a", "mine"}
    assert (models["model-a"].max_tokens, models["model-a"].temperature) == (500, 0.5)
    assert ai.get("claude_api").default_model is None


def test_refresh_failure_is_recorded_and_raised(ai: AiConnections, prober: FakeProber) -> None:
    ai.save("claude_api", api_key=KEY)
    prober.error = "Could not reach the provider."
    with pytest.raises(AiConnectionError):
        ai.refresh_models("claude_api")
    assert ai.get("claude_api").status == "failed"


def test_save_model_replaces_settings(ai: AiConnections) -> None:
    ai.save("gemini_api", api_key=KEY)
    ai.save_model("gemini_api", "g1", max_tokens=100, temperature=1.0, timeout_s=20)
    model = ai.save_model("gemini_api", "g1", max_tokens=200)
    assert (model.max_tokens, model.temperature, model.timeout_s) == (200, None, None)
    assert model.source == "manual"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_tokens": 0},
        {"max_tokens": 2_000_000},
        {"temperature": -0.1},
        {"temperature": 2.5},
        {"timeout_s": 0},
        {"timeout_s": 601},
    ],
)
def test_save_model_rejects_out_of_range(ai: AiConnections, kwargs: dict[str, float]) -> None:
    ai.save("gemini_api", api_key=KEY)
    with pytest.raises(AiInvalidError):
        ai.save_model("gemini_api", "g1", **kwargs)  # type: ignore[arg-type]


def test_save_model_rejects_bad_names(ai: AiConnections) -> None:
    ai.save("gemini_api", api_key=KEY)
    for name in ("", "  ", "x" * 129):
        with pytest.raises(AiInvalidError):
            ai.save_model("gemini_api", name)


def test_one_default_model_per_connection(ai: AiConnections) -> None:
    ai.save("claude_api", api_key=KEY)
    ai.save("chatgpt_api", api_key=KEY)
    for provider in ("claude_api", "chatgpt_api"):
        ai.save_model(provider, "a")
        ai.save_model(provider, "b")
        ai.set_default_model(provider, "a")
    ai.set_default_model("claude_api", "b")
    assert ai.get("claude_api").default_model == "b"
    assert ai.get("chatgpt_api").default_model == "a"


def test_unknown_model_is_not_found(ai: AiConnections) -> None:
    ai.save("claude_api", api_key=KEY)
    with pytest.raises(AiNotFoundError):
        ai.set_default_model("claude_api", "missing")
    with pytest.raises(AiNotFoundError):
        ai.remove_model("claude_api", "missing")


def test_remove_model(ai: AiConnections) -> None:
    ai.save("claude_api", api_key=KEY)
    ai.save_model("claude_api", "a")
    ai.remove_model("claude_api", "a")
    assert ai.models("claude_api") == []


def test_models_of_an_unsaved_provider_is_empty(ai: AiConnections) -> None:
    assert ai.models("claude_api") == []


def test_new_models_start_with_the_standard_settings(ai: AiConnections) -> None:
    ai.save("claude_api", api_key=KEY)
    models = {m.name: m for m in ai.refresh_models("claude_api")}
    standard = defaults_for("model-a")
    assert standard == APP_DEFAULTS
    assert (models["model-a"].max_tokens, models["model-a"].temperature) == (
        APP_DEFAULTS.max_tokens,
        APP_DEFAULTS.temperature,
    )
    assert models["model-b"].timeout_s == APP_DEFAULTS.timeout_s


def test_family_rules_match_by_name(ai: AiConnections) -> None:
    assert defaults_for("Claude-OPUS-9") != APP_DEFAULTS
    assert defaults_for("claude-haiku-9").timeout_s < defaults_for("claude-opus-9").timeout_s
    assert defaults_for("gemini-pro") != APP_DEFAULTS
    assert defaults_for("mystery") == APP_DEFAULTS


def test_new_manual_model_fills_only_what_is_left_out(ai: AiConnections) -> None:
    ai.save("claude_api", api_key=KEY)
    model = ai.save_model("claude_api", "claude-sonnet-x", temperature=1.5)
    standard = defaults_for("claude-sonnet-x")
    assert (model.max_tokens, model.temperature, model.timeout_s) == (
        standard.max_tokens,
        1.5,
        standard.timeout_s,
    )


def test_refresh_keeps_edited_settings_of_a_known_model(
    ai: AiConnections, prober: FakeProber
) -> None:
    ai.save("claude_api", api_key=KEY)
    ai.refresh_models("claude_api")
    ai.save_model("claude_api", "model-a", max_tokens=111)
    models = {m.name: m for m in ai.refresh_models("claude_api")}
    assert models["model-a"].max_tokens == 111
    assert models["model-a"].temperature is None


def _default_connection_with_models(ai: AiConnections) -> None:
    ai.save("claude_api", api_key="sk-test-1234567890abcdef")
    ai.set_default("claude_api")
    ai.save_model("claude_api", "fast")
    ai.save_model("claude_api", "smart")
    ai.set_default_model("claude_api", "fast")


def test_a_task_uses_its_own_model_and_others_the_default(ai: AiConnections) -> None:
    _default_connection_with_models(ai)
    ai.set_task_model("studio_copy", "smart")
    assert ai.task_models() == {"studio_copy": "smart"}
    assert ai.default_target("studio_copy").model == "smart"
    assert ai.default_target("palette").model == "fast"
    assert ai.default_target().model == "fast"


def test_a_task_falls_back_when_its_model_is_gone(ai: AiConnections) -> None:
    _default_connection_with_models(ai)
    ai.set_task_model("studio_copy", "smart")
    ai.remove_model("claude_api", "smart")
    assert ai.default_target("studio_copy").model == "fast"


def test_a_task_goes_back_to_the_default_when_cleared(ai: AiConnections) -> None:
    _default_connection_with_models(ai)
    ai.set_task_model("palette", "smart")
    assert ai.set_task_model("palette", None) == {}


def test_set_task_model_rejects_bad_input(ai: AiConnections) -> None:
    with pytest.raises(AiInvalidError):
        ai.set_task_model("nope", "x")
    with pytest.raises(AiInvalidError):
        ai.set_task_model("palette", "x")
    _default_connection_with_models(ai)
    with pytest.raises(AiNotFoundError):
        ai.set_task_model("palette", "missing")


def test_idea_count_defaults_to_five_and_is_kept(ai: AiConnections) -> None:
    assert ai.idea_count() == 5
    assert ai.set_idea_count(12) == 12
    assert ai.idea_count() == 12


@pytest.mark.parametrize("count", [0, 21])
def test_idea_count_must_be_from_one_to_twenty(ai: AiConnections, count: int) -> None:
    with pytest.raises(AiInvalidError):
        ai.set_idea_count(count)
