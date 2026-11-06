"""Errors raised by the layout package. Messages are fit to show the user."""


class LayoutError(Exception):
    """Base class for layout failures."""


class LayoutNotFoundError(LayoutError):
    """No layout has the given id or name."""


class LayoutNameTakenError(LayoutError):
    """Another layout already uses the name."""


class LayoutInvalidError(LayoutError):
    """The name or settings of a layout, or a layout file, are not valid."""


class LayoutReadOnlyError(LayoutError):
    """A built-in layout cannot be changed or deleted."""


class LayoutInUseError(LayoutError):
    """Brands still use the layout. ``brands`` holds their names."""

    def __init__(self, message: str, brands: list[str]) -> None:
        super().__init__(message)
        self.brands = brands
