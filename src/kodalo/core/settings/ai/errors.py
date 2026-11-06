"""Errors raised by the AI package. Messages are fit to show the user."""


class AiInvalidError(Exception):
    """An AI connection or model value is not valid."""


class AiNotFoundError(Exception):
    """The AI model asked for is not saved."""


class AiConnectionError(Exception):
    """A provider could not be reached, or refused the connection."""


class AiSecretError(Exception):
    """The system keychain could not store, read or remove a key."""
