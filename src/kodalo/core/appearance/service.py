"""The window's theme, kept in the ``settings`` table."""

from typing import Literal, get_args

from sqlalchemy import Select, select

from kodalo.core.appearance.errors import AppearanceInvalidError
from kodalo.core.storage import Database
from kodalo.core.storage.models import Setting

Theme = Literal["system", "light", "dark"]
THEMES: tuple[str, ...] = get_args(Theme)
DEFAULT_THEME: Theme = "system"

GROUP = "appearance"
THEME_KEY = "theme"


class Appearance:
    """The theme the window uses. Only the window reads it; the command line ignores it."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self) -> Theme:
        """Return the saved theme, or ``system`` (follow the OS) when none is saved."""
        with self._database.session() as session:
            row = session.scalars(self._query()).first()
            if row is None or row.data_type != "string" or row.value not in THEMES:
                return DEFAULT_THEME
            return row.value  # type: ignore[return-value]

    def save(self, theme: str) -> Theme:
        """Choose ``theme``: ``system``, ``light`` or ``dark``."""
        if theme not in THEMES:
            raise AppearanceInvalidError(
                f"Unknown theme: {theme}. Use one of: {', '.join(THEMES)}."
            )
        with self._database.session() as session:
            row = session.scalars(self._query()).first()
            if row is None:
                row = Setting(
                    scope="global", owner_id="", group_name=GROUP, key=THEME_KEY, mode="own"
                )
                session.add(row)
            row.value = theme
            row.data_type = "string"
        return theme  # type: ignore[return-value]

    @staticmethod
    def _query() -> Select[Setting]:
        return select(Setting).where(
            Setting.scope == "global",
            Setting.owner_id == "",
            Setting.group_name == GROUP,
            Setting.key == THEME_KEY,
        )
