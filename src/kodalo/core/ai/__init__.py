"""AI connections: Claude API, Claude Code, ChatGPT API and Gemini API, and their models."""

from kodalo.core.ai.clients import GenerateRequest, Generation, Generator, Probe, Prober
from kodalo.core.ai.defaults import APP_DEFAULTS, ModelDefaults, defaults_for
from kodalo.core.ai.errors import (
    AiConnectionError,
    AiInvalidError,
    AiNotFoundError,
    AiSecretError,
)
from kodalo.core.ai.history import (
    PERIODS,
    PURPOSES,
    AiCallDetail,
    AiCallRecord,
    AiHistory,
    AiHistorySettings,
    DayUsage,
    HistoryPage,
    Period,
    Usage,
    UsageRow,
    purge_expired_history,
    resolve_period,
)
from kodalo.core.ai.providers import PROVIDER_IDS, PROVIDERS, Provider
from kodalo.core.ai.secrets import KeychainSecrets, SecretStore
from kodalo.core.ai.service import AiConnection, AiConnections, AiModel, AiTarget, ConnectionCheck

__all__ = [
    "APP_DEFAULTS",
    "PERIODS",
    "PROVIDERS",
    "PROVIDER_IDS",
    "PURPOSES",
    "AiCallDetail",
    "AiCallRecord",
    "AiConnection",
    "AiConnectionError",
    "AiConnections",
    "AiHistory",
    "AiHistorySettings",
    "AiInvalidError",
    "AiModel",
    "AiNotFoundError",
    "AiSecretError",
    "AiTarget",
    "ConnectionCheck",
    "DayUsage",
    "GenerateRequest",
    "Generation",
    "Generator",
    "HistoryPage",
    "KeychainSecrets",
    "ModelDefaults",
    "Period",
    "Probe",
    "Prober",
    "Provider",
    "SecretStore",
    "Usage",
    "UsageRow",
    "defaults_for",
    "purge_expired_history",
    "resolve_period",
]
