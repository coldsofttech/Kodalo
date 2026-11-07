import pytest

from kodalo.core.ai.models.defaults import ModelDefaults, _load, model_defaults
from kodalo.core.ai.service import starting_settings
from kodalo.core.settings.ai.defaults import defaults_for
from kodalo.core.settings.ai.providers import PROVIDER_IDS


def test_known_model_has_defaults() -> None:
    found = model_defaults("claude_api", "claude-sonnet-5-5")
    assert found is not None
    assert found.max_tokens == 128000
    assert found.temperature_range[0] <= found.temperature <= found.temperature_range[1]
    assert found.timeout_s > 0


def test_unknown_model_or_provider_returns_none() -> None:
    assert model_defaults("claude_api", "nope") is None
    assert model_defaults("nope", "claude-sonnet-5-5") is None


def test_provider_and_model_are_case_sensitive() -> None:
    assert model_defaults("Claude_API", "claude-sonnet-5-5") is None
    assert model_defaults("claude_api", "Claude-Sonnet-5-5") is None


def test_providers_are_real_provider_ids() -> None:
    table = _load()
    assert set(table.models) <= set(PROVIDER_IDS)
    assert set(table.aliases) <= set(PROVIDER_IDS)


@pytest.mark.parametrize(
    ("alias", "full"),
    [
        ("opus", "claude-opus-5-5"),
        ("sonnet", "claude-sonnet-5-5"),
        ("haiku", "claude-haiku-5-5"),
    ],
)
def test_claude_code_alias_resolves_to_full_model(alias: str, full: str) -> None:
    assert model_defaults("claude_code", alias) is model_defaults("claude_api", full)
    assert model_defaults("claude_code", alias) is not None


def test_alias_does_not_apply_to_other_providers() -> None:
    assert model_defaults("claude_api", "opus") is None


def test_loaded_values_are_cached() -> None:
    assert _load() is _load()
    assert model_defaults("chatgpt_api", "gpt-6-astra") is model_defaults(
        "chatgpt_api", "gpt-6-astra"
    )


def test_defaults_are_immutable() -> None:
    found = model_defaults("gemini_api", "gemini-4-argon")
    assert found is not None
    with pytest.raises(AttributeError):
        found.max_tokens = 1  # type: ignore[misc]


def test_starting_settings_use_shipped_defaults_for_known_model() -> None:
    start = starting_settings("claude_code", "haiku")
    assert (start.max_tokens, start.temperature, start.timeout_s) == (128000, 1.0, 120)


def test_starting_settings_fall_back_to_family_standard() -> None:
    assert starting_settings("chatgpt_api", "gpt-4o-mini") == defaults_for("gpt-4o-mini")


@pytest.mark.parametrize(
    ("provider", "model"),
    [(p, m) for p, models in _load().models.items() for m in models],
)
def test_every_entry_is_consistent(provider: str, model: str) -> None:
    found = model_defaults(provider, model)
    assert isinstance(found, ModelDefaults)
    low, high = found.temperature_range
    assert low <= found.temperature <= high
    assert found.max_tokens > 0
    assert found.timeout_s > 0
