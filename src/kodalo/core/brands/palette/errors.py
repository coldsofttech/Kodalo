"""Errors raised by the palette package. Messages are fit to show the user."""


class PaletteError(Exception):
    """Base class for palette failures."""


class PaletteNotFoundError(PaletteError):
    """No palette has the given id or name."""


class PaletteNameTakenError(PaletteError):
    """Another palette already uses the name."""


class PaletteInvalidError(PaletteError):
    """The name or colors of a palette, or a palette file, are not valid."""


class PaletteReadOnlyError(PaletteError):
    """A built-in palette cannot be changed or deleted."""
