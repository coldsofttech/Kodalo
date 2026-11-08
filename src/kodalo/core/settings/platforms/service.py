"""What each social platform's posts get: how many hashtags, the ones every post carries and which
visuals the designer may use.

Kept in the ``settings`` table, one group for each platform. The post copywriter reads the hashtag
settings: the default hashtags come first and count toward the total, and the AI writes the rest.
The designer will read the visual ones (all off until chosen).
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.settings.platforms.errors import PlatformInvalidError
from kodalo.core.storage import Database
from kodalo.core.storage.models import Setting

PLATFORMS: tuple[str, ...] = ("instagram", "custom")
MAX_HASHTAGS = 30  # Instagram allows up to 30 hashtags on a post
DEFAULT_HASHTAG_COUNT = 5
_COUNT_KEY = "hashtag_count"
_TAGS_KEY = "default_hashtags"
VISUALS = (
    "use_social_preview",
    "use_repo_icon",
    "use_icons",
    "build_custom_images",
    "use_ai_templates",
)


@dataclass(frozen=True)
class PlatformSettings:
    """The settings of one platform."""

    platform: str
    hashtag_count: int = DEFAULT_HASHTAG_COUNT
    default_hashtags: tuple[str, ...] = ()
    use_social_preview: bool = False
    use_repo_icon: bool = False
    use_icons: bool = False
    build_custom_images: bool = False
    use_ai_templates: bool = False


def clean_hashtags(value: object, limit: int = MAX_HASHTAGS) -> tuple[str, ...]:
    """Lowercase tags with one leading ``#`` and no spaces or punctuation, without duplicates and
    at most ``limit``. Anything that is not a list of text, or a text of tags, gives none."""
    items = value.replace(",", " ").split() if isinstance(value, str) else value
    found: dict[str, None] = {}
    for item in items if isinstance(items, list | tuple) else []:
        tag = re.sub(r"\W", "", str(item)[:60]).lower() if isinstance(item, str) else ""
        if tag:
            found[f"#{tag}"] = None
    return tuple(found)[:limit]


class Platforms:
    """Reads and saves the settings of each platform."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, platform: str) -> PlatformSettings:
        """The saved settings of ``platform``; the defaults for what was never saved."""
        _check(platform)
        with self._database.session() as session:
            count = self._row(session, platform, _COUNT_KEY)
            tags = self._row(session, platform, _TAGS_KEY)
            number = (
                int(count.value)
                if count is not None and count.value.isdigit()
                else DEFAULT_HASHTAG_COUNT
            )
            flags = {name: self._flag(session, platform, name) for name in VISUALS}
            return PlatformSettings(
                platform,
                min(number, MAX_HASHTAGS),
                clean_hashtags(tags.value if tags is not None else ""),
                **flags,
            )

    def save(
        self,
        platform: str,
        hashtag_count: int,
        default_hashtags: object,
        *,
        use_social_preview: bool = False,
        use_repo_icon: bool = False,
        use_icons: bool = False,
        build_custom_images: bool = False,
        use_ai_templates: bool = False,
    ) -> PlatformSettings:
        """Keep ``hashtag_count`` (0 to 30), the default hashtags and the visuals the designer may
        use for ``platform``. Raises ``PlatformInvalidError`` when the platform is unknown, the
        count is out of range or the default hashtags are more than the count."""
        _check(platform)
        if not 0 <= hashtag_count <= MAX_HASHTAGS:
            raise PlatformInvalidError(f"Use 0 to {MAX_HASHTAGS} hashtags.")
        tags = clean_hashtags(default_hashtags)
        if len(tags) > hashtag_count:
            raise PlatformInvalidError(
                f"There are {len(tags)} default hashtags but only {hashtag_count} hashtags in "
                "total. Raise the number of hashtags or remove some default ones."
            )
        with self._database.session() as session:
            self._set(session, platform, _COUNT_KEY, str(hashtag_count), "integer")
            self._set(session, platform, _TAGS_KEY, " ".join(tags), "string")
            flags = {
                "use_social_preview": use_social_preview,
                "use_repo_icon": use_repo_icon,
                "use_icons": use_icons,
                "build_custom_images": build_custom_images,
                "use_ai_templates": use_ai_templates,
            }
            for name, on in flags.items():
                self._set(session, platform, name, "true" if on else "false", "boolean")
        return PlatformSettings(platform, hashtag_count, tags, **flags)

    @staticmethod
    def _row(session: Session, platform: str, key: str) -> Setting | None:
        return session.scalars(
            select(Setting).where(
                Setting.scope == "global",
                Setting.owner_id == "",
                Setting.group_name == f"platform_{platform}",
                Setting.key == key,
            )
        ).first()

    def _flag(self, session: Session, platform: str, key: str) -> bool:
        row = self._row(session, platform, key)
        return row is not None and row.value == "true"

    def _set(self, session: Session, platform: str, key: str, value: str, kind: str) -> None:
        row = self._row(session, platform, key)
        if row is None:
            row = Setting(
                scope="global",
                owner_id="",
                group_name=f"platform_{platform}",
                key=key,
                mode="own",
            )
            session.add(row)
        row.value = value
        row.data_type = kind


def _check(platform: str) -> None:
    if platform not in PLATFORMS:
        raise PlatformInvalidError(
            f"Unknown platform: {platform}. Use one of: {', '.join(PLATFORMS)}."
        )
