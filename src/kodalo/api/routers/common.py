"""Aliases, error maps and error mapping shared by the API routers."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Path, Query, status

from kodalo.api.deps import (
    get_ai_connections,
    get_appearance,
    get_github_connectivity,
    get_ideas_assistant,
    get_readme_assistant,
    get_readme_service,
    get_repo_analyzer,
    get_repo_service,
)
from kodalo.api.schemas import (
    AiProvider,
)
from kodalo.core.ai import AiConnections
from kodalo.core.repo import (
    IdeasAssistant,
    ReadmeAssistant,
    ReadmeService,
    RepoAnalyzer,
    RepoDetailsError,
    RepoNotFoundError,
    RepoReadError,
    RepoService,
)
from kodalo.core.settings.ai import (
    AiConnectionError,
    AiInvalidError,
    AiNotFoundError,
    AiSecretError,
)
from kodalo.core.settings.appearance import Appearance
from kodalo.core.settings.github import (
    GitHubConnectivity,
)
from kodalo.core.studio import StudioInvalidError

GitHub = Annotated[GitHubConnectivity, Depends(get_github_connectivity)]
ThemeSetting = Annotated[Appearance, Depends(get_appearance)]
AiSetting = Annotated[AiConnections, Depends(get_ai_connections)]
AiProviderPath = Annotated[AiProvider, Path(description="The AI provider.")]
AiModelName = Annotated[str, Path(min_length=1, max_length=128, description="The model name.")]
Repos = Annotated[RepoService, Depends(get_repo_service)]
Analyzer = Annotated[RepoAnalyzer, Depends(get_repo_analyzer)]
Readme = Annotated[ReadmeService, Depends(get_readme_service)]
ReadmeAi = Annotated[ReadmeAssistant, Depends(get_readme_assistant)]
IdeasAi = Annotated[IdeasAssistant, Depends(get_ideas_assistant)]

RepoPath = Annotated[str, Path(max_length=64, description="Stored repository id.")]

NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No brand profile has that id."}
}
INVALID: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The brand data or file is not valid."}
}
NAME_TAKEN: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {"description": "Another brand profile uses that name."}
}
UNAVAILABLE: dict[int | str, dict[str, Any]] = {
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "The local data cannot be opened."}
}
COMMON = UNAVAILABLE

IMPORT_NAME = Annotated[
    str | None,
    Query(min_length=1, max_length=64, description="Name to use. Default: the file's."),
]

AI_INVALID: dict[int | str, dict[str, Any]] = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The AI connection value is not valid."}
}
AI_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "The connection has no such model."}
}
AI_UNREACHABLE: dict[int | str, dict[str, Any]] = {
    status.HTTP_502_BAD_GATEWAY: {"description": "The provider could not be reached."}
}


@contextmanager
def ai_errors() -> Generator[None]:
    """Turn the AI library's errors into HTTP errors."""
    try:
        yield
    except AiNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except AiInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except AiConnectionError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except AiSecretError as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error


STUDIO_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "GitHub has no such repository."},
    status.HTTP_502_BAD_GATEWAY: {"description": "GitHub or the GitHub CLI could not be reached."},
}


@contextmanager
def studio_errors() -> Generator[None]:
    """Turn studio and repository errors into HTTP errors."""
    try:
        yield
    except RepoNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except RepoReadError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except (RepoDetailsError, StudioInvalidError) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
