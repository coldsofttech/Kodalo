"""Errors raised by the platforms package. Messages are fit to show the user."""


class PlatformInvalidError(Exception):
    """A platform setting is not valid."""


class PlatformConnectionError(Exception):
    """A platform could not be reached, refused the token or is not connected."""


class PlatformSecretError(Exception):
    """The system keychain could not store, read or remove a platform token."""
