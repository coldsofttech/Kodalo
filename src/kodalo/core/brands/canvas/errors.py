"""Errors raised by the canvas package. Messages are fit to show the user."""


class CanvasError(Exception):
    """Base class for canvas failures."""


class CanvasNotFoundError(CanvasError):
    """No canvas has the given id or name."""


class CanvasNameTakenError(CanvasError):
    """Another canvas already uses the name."""


class CanvasInvalidError(CanvasError):
    """The name or size of a canvas is not valid."""


class CanvasReadOnlyError(CanvasError):
    """A built-in canvas cannot be changed or deleted."""


class CanvasInUseError(CanvasError):
    """Brands still use the canvas. ``brands`` holds their names."""

    def __init__(self, message: str, brands: list[str]) -> None:
        super().__init__(message)
        self.brands = brands
