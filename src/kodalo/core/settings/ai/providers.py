"""The AI providers Kodalo can connect to."""

from dataclasses import dataclass
from typing import Literal

Kind = Literal["api_key", "local_cli"]


@dataclass(frozen=True)
class Provider:
    """One supported provider. ``kind`` says how it is reached: with an API key, or through a
    program installed on this computer (which needs no key)."""

    id: str
    label: str
    kind: Kind
    default_base_url: str = ""


PROVIDERS: tuple[Provider, ...] = (
    Provider("claude_api", "Claude API", "api_key", "https://api.anthropic.com"),
    Provider("claude_code", "Claude Code", "local_cli"),
    Provider("chatgpt_api", "ChatGPT API", "api_key", "https://api.openai.com"),
    Provider("gemini_api", "Gemini API", "api_key", "https://generativelanguage.googleapis.com"),
)
PROVIDER_IDS: tuple[str, ...] = tuple(provider.id for provider in PROVIDERS)

# What Claude Code accepts for its ``--model`` option; it has no list to ask for.
CLAUDE_CODE_MODELS: tuple[str, ...] = ("opus", "sonnet", "haiku")


def get_provider(provider_id: str) -> Provider | None:
    """Return the provider called ``provider_id``, or ``None`` when there is none."""
    return next((provider for provider in PROVIDERS if provider.id == provider_id), None)
