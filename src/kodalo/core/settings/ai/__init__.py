"""AI settings: the providers, their defaults, API key storage and the history of calls."""

from kodalo.core.settings.ai.defaults import APP_DEFAULTS, ModelDefaults, defaults_for
from kodalo.core.settings.ai.errors import (
    AiConnectionError,
    AiInvalidError,
    AiNotFoundError,
    AiSecretError,
)
from kodalo.core.settings.ai.history import (
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
from kodalo.core.settings.ai.providers import PROVIDER_IDS, PROVIDERS, Provider
from kodalo.core.settings.ai.secrets import KeychainSecrets, SecretStore

__all__ = [
    "APP_DEFAULTS",
    "PERIODS",
    "PROVIDERS",
    "PROVIDER_IDS",
    "PURPOSES",
    "AiCallDetail",
    "AiCallRecord",
    "AiConnectionError",
    "AiHistory",
    "AiHistorySettings",
    "AiInvalidError",
    "AiNotFoundError",
    "AiSecretError",
    "DayUsage",
    "HistoryPage",
    "KeychainSecrets",
    "ModelDefaults",
    "Period",
    "Provider",
    "SecretStore",
    "Usage",
    "UsageRow",
    "defaults_for",
    "purge_expired_history",
    "resolve_period",
]
