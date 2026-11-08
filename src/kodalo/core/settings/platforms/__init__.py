"""Platforms: how many hashtags a post gets and which ones every post carries, and the Instagram
connection."""

from kodalo.core.settings.platforms.errors import (
    PlatformConnectionError,
    PlatformInvalidError,
    PlatformSecretError,
)
from kodalo.core.settings.platforms.instagram import (
    InstagramAccount,
    InstagramConnection,
    PublishedPost,
)
from kodalo.core.settings.platforms.service import (
    DEFAULT_HASHTAG_COUNT,
    MAX_HASHTAGS,
    PLATFORMS,
    VISUALS,
    Platforms,
    PlatformSettings,
    clean_hashtags,
)

__all__ = [
    "DEFAULT_HASHTAG_COUNT",
    "MAX_HASHTAGS",
    "PLATFORMS",
    "VISUALS",
    "InstagramAccount",
    "InstagramConnection",
    "PlatformConnectionError",
    "PlatformInvalidError",
    "PlatformSecretError",
    "PlatformSettings",
    "Platforms",
    "PublishedPost",
    "clean_hashtags",
]
