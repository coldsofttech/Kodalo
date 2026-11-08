"""Appearance: the theme the window uses."""

from kodalo.core.settings.appearance.errors import AppearanceInvalidError
from kodalo.core.settings.appearance.service import DEFAULT_THEME, THEMES, Appearance, Theme

__all__ = ["DEFAULT_THEME", "THEMES", "Appearance", "AppearanceInvalidError", "Theme"]
