"""GitHub connectivity: which way Kodalo reaches GitHub, and a check that the way works."""

from kodalo.core.github.errors import GitHubInvalidError
from kodalo.core.github.service import (
    DEFAULT_DOCUMENT_LIMIT,
    DEFAULT_DOCUMENT_MAX_KB,
    DEFAULT_MANIFEST_LIMIT,
    DEFAULT_MODE,
    MAX_DOCUMENT_LIMIT,
    MAX_DOCUMENT_MAX_KB,
    MAX_MANIFEST_LIMIT,
    MODES,
    ConnectionCheck,
    GitHubConnectivity,
    GitHubSettings,
    check_connection,
)

__all__ = [
    "DEFAULT_DOCUMENT_LIMIT",
    "DEFAULT_DOCUMENT_MAX_KB",
    "DEFAULT_MANIFEST_LIMIT",
    "DEFAULT_MODE",
    "MAX_DOCUMENT_LIMIT",
    "MAX_DOCUMENT_MAX_KB",
    "MAX_MANIFEST_LIMIT",
    "MODES",
    "ConnectionCheck",
    "GitHubConnectivity",
    "GitHubInvalidError",
    "GitHubSettings",
    "check_connection",
]
