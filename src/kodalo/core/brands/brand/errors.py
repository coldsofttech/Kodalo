"""Errors raised by the brand package. Messages are fit to show the user."""


class BrandError(Exception):
    """Base class for brand failures."""


class BrandNotFoundError(BrandError):
    """No brand profile has the given id."""


class BrandNameTakenError(BrandError):
    """Another brand profile already uses the name."""


class BrandInvalidError(BrandError):
    """The brand data or a profile file is not valid. ``problems`` lists each one."""

    def __init__(self, message: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems = problems or [message]


class LogoError(BrandError):
    """A logo file was rejected."""
