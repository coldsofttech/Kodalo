"""AI connections: Claude API, Claude Code, ChatGPT API and Gemini API, and their models."""

from kodalo.core.ai.clients import GenerateRequest, Generation, Generator, Probe, Prober
from kodalo.core.ai.defaults import APP_DEFAULTS, ModelDefaults, defaults_for
from kodalo.core.ai.errors import (
    AiConnectionError,
    AiInvalidError,
    AiNotFoundError,
    AiSecretError,
)
from kodalo.core.ai.providers import PROVIDER_IDS, PROVIDERS, Provider
from kodalo.core.ai.secrets import KeychainSecrets, SecretStore
from kodalo.core.ai.service import AiConnection, AiConnections, AiModel, AiTarget, ConnectionCheck

__all__ = [
    "APP_DEFAULTS",
    "PROVIDERS",
    "PROVIDER_IDS",
    "AiConnection",
    "AiConnectionError",
    "AiConnections",
    "AiInvalidError",
    "AiModel",
    "AiNotFoundError",
    "AiSecretError",
    "AiTarget",
    "ConnectionCheck",
    "GenerateRequest",
    "Generation",
    "Generator",
    "KeychainSecrets",
    "ModelDefaults",
    "Probe",
    "Prober",
    "Provider",
    "SecretStore",
    "defaults_for",
]
