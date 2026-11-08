"""Errors raised by the repository package. Messages are fit to show the user."""


class RepoError(Exception):
    """Base class for repository failures."""


class RepoReadError(RepoError):
    """The repository could not be read (GitHub, the GitHub CLI or git failed)."""


class RepoNotFoundError(RepoReadError):
    """GitHub has no such repository, or it is private and cannot be seen this way."""


class RepoDetailsError(RepoError):
    """Details a local folder cannot supply are missing or not valid."""
