"""Errors raised by the storage layer. They carry a message fit to show the user."""


class StorageError(Exception):
    """Base class for storage failures."""


class MigrationError(StorageError):
    """A migration failed; the database was put back as it was before the attempt."""


class DatabaseTooNewError(StorageError):
    """The database was written by a newer version of the application."""
