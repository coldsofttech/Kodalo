"""Appearance: the theme the window uses."""

from kodalo.core.appearance.errors import AppearanceInvalidError
from kodalo.core.appearance.service import DEFAULT_THEME, THEMES, Appearance, Theme

__all__ = ["DEFAULT_THEME", "THEMES", "Appearance", "AppearanceInvalidError", "Theme"]
