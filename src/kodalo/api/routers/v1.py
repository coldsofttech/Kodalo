"""Version 1 of the API, served under ``/api/v1``."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path as FsPath
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool

from kodalo.api.deps import (
    data_dir,
    get_ai_connections,
    get_appearance,
    get_brand_service,
    get_github_connectivity,
    get_readme_assistant,
    get_readme_service,
    get_repo_analyzer,
    get_repo_service,
)
from kodalo.api.schemas import (
    AiCallDetailResponse,
    AiCheckResponse,
    AiConnectionResponse,
    AiConnectionUpdate,
    AiDefaultConnection,
    AiDefaultModel,
    AiHistoryPageResponse,
    AiHistorySettingsResponse,
    AiHistorySettingsUpdate,
    AiModelResponse,
    AiModelUpdate,
    AiPeriod,
    AiProvider,
    AiPurgeResponse,
    AiUsageResponse,
    AnalysisPlanResponse,
    AnalysisResultResponse,
    BrandCreate,
    BrandDuplicate,
    BrandExport,
    BrandResponse,
    BrandUpdate,
    CanvasCreate,
    CanvasDuplicate,
    CanvasExport,
    CanvasResponse,
    CanvasUpdate,
    ContrastItem,
    ContrastRequest,
    DoctorCheck,
    DoctorResponse,
    FontResponse,
    GitHubCheckResponse,
    GitHubSettingsResponse,
    GitHubSettingsUpdate,
    LayoutCreate,
    LayoutDuplicate,
    LayoutExport,
    LayoutResponse,
    LayoutUpdate,
    PaletteCreate,
    PaletteDuplicate,
    PaletteExport,
    PaletteResponse,
    PaletteSuggestion,
    PaletteUpdate,
    ReadmePlanResponse,
    ReadmeReadRequest,
    ReadmeResponse,
    ReadmeResultResponse,
    RepoReadRequest,
    RepoResponse,
    StudioSourceRequest,
    StudioSourceResponse,
    ThemeResponse,
    ThemeUpdate,
)
from kodalo.core.ai import (
    AiConnectionError,
    AiConnections,
    AiInvalidError,
    AiNotFoundError,
    AiSecretError,
    Period,
    resolve_period,
)
from kodalo.core.appearance import Appearance, AppearanceInvalidError
from kodalo.core.brand import (
    BrandError,
    BrandInvalidError,
    BrandNameTakenError,
    BrandNotFoundError,
    BrandService,
    check_colors,
)
from kodalo.core.brand.logos import MAX_LOGO_BYTES
from kodalo.core.canvas import (
    CanvasError,
    CanvasInUseError,
    CanvasNameTakenError,
    CanvasNotFoundError,
    CanvasReadOnlyError,
)
from kodalo.core.doctor import passed, run_checks
from kodalo.core.github import (
    GitHubConnectivity,
    GitHubInvalidError,
    check_connection,
)
from kodalo.core.layout import (
    LayoutError,
    LayoutInUseError,
    LayoutNameTakenError,
    LayoutNotFoundError,
    LayoutReadOnlyError,
    LayoutSettings,
)
from kodalo.core.palette import (
    Palette,
    PaletteError,
    PaletteInvalidError,
    PaletteNameTakenError,
    PaletteNotFoundError,
    PaletteReadOnlyError,
)
from kodalo.core.palette.suggest import PaletteSuggester
from kodalo.core.repo import (
    ReadmeAssistant,
    ReadmeService,
    RepoAnalyzer,
    RepoDetailsError,
    RepoNotFoundError,
    RepoReadError,
    RepoService,
    suggest,
)
from kodalo.core.studio import StudioInvalidError, validate_source

# Cornea has already authenticated the caller by the time a request reaches these routes.
router = APIRouter(tags=["v1"])

Service = Annotated[BrandService, Depends(get_brand_service)]
GitHub = Annotated[GitHubConnectivity, Depends(get_github_connectivity)]
ThemeSetting = Annotated[Appearance, Depends(get_appearance)]
AiSetting = Annotated[AiConnections, Depends(get_ai_connections)]
AiProviderPath = Annotated[AiProvider, Path(description="The AI provider.")]
AiModelName = Annotated[str, Path(min_length=1, max_length=128, description="The model name.")]
Repos = Annotated[RepoService, Depends(get_repo_service)]
Analyzer = Annotated[RepoAnalyzer, Depends(get_repo_analyzer)]
Readme = Annotated[ReadmeService, Depends(get_readme_service)]
ReadmeAi = Annotated[ReadmeAssistant, Depends(get_readme_assistant)]
BrandPath = Annotated[str, Path(max_length=64, description="Brand profile id.")]
Variant = Annotated[
    Literal["light", "dark"],
    Query(description="Which logo: the main one, or the one used in dark mode."),
]

RepoPath = Annotated[str, Path(max_length=64, description="Stored repository id.")]

LOGO_TYPES = {"image/png": "png", "image/svg+xml": "svg"}
# A logo is only ever shown, never run: no scripts, no outside requests, even if opened directly.
LOGO_CSP = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
LOGO_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "description": "The logo file, a PNG or an SVG of at most 2 MB.",
        "content": {
            "image/png": {"schema": {"type": "string", "format": "binary"}},
            "image/svg+xml": {"schema": {"type": "string", "format": "binary"}},
        },
    }
}

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


@contextmanager
def _mapped() -> Iterator[None]:
    """Turn the library's brand errors into HTTP errors."""
    try:
        yield
    except BrandNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except BrandNameTakenError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except BrandInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    except BrandError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


LayoutPath = Annotated[str, Path(max_length=64, description="Layout id.")]
LAYOUT_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No layout has that id."},
    status.HTTP_409_CONFLICT: {"description": "The name is taken, or brands still use the layout."},
}
LAYOUT_CHANGE_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"description": "The layout is built in and cannot be changed."},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The name or settings are not valid."},
}
PalettePath = Annotated[str, Path(max_length=64, description="Palette id.")]
PALETTE_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No palette has that id."},
    status.HTTP_409_CONFLICT: {"description": "Another palette uses that name."},
}
PALETTE_CHANGE_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"description": "The palette is built in and cannot be changed."},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The name or colors are not valid."},
}
IMPORT_NAME = Annotated[
    str | None,
    Query(min_length=1, max_length=64, description="Name to use. Default: the file's."),
]
CanvasPath = Annotated[str, Path(max_length=64, description="Canvas id.")]
CANVAS_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No canvas has that id."},
    status.HTTP_409_CONFLICT: {"description": "The name is taken, or brands still use the canvas."},
}
CANVAS_CHANGE_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"description": "The canvas is built in and cannot be changed."},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The name or size is not valid."},
}


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
def _ai_errors() -> Iterator[None]:
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


@contextmanager
def _layout_mapped() -> Iterator[None]:
    """Turn the library's layout errors into HTTP errors."""
    try:
        yield
    except LayoutNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except (LayoutNameTakenError, LayoutInUseError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except LayoutReadOnlyError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except LayoutError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@contextmanager
def _palette_mapped() -> Iterator[None]:
    """Turn the library's palette errors into HTTP errors."""
    try:
        yield
    except PaletteNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except PaletteNameTakenError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except PaletteReadOnlyError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except (PaletteInvalidError, PaletteError, BrandInvalidError) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@contextmanager
def _canvas_mapped() -> Iterator[None]:
    """Turn the library's canvas errors into HTTP errors."""
    try:
        yield
    except CanvasNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except (CanvasNameTakenError, CanvasInUseError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    except CanvasReadOnlyError as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    except CanvasError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


STUDIO_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "GitHub has no such repository."},
    status.HTTP_502_BAD_GATEWAY: {"description": "GitHub or the GitHub CLI could not be reached."},
}


@contextmanager
def _studio_errors() -> Iterator[None]:
    """Turn studio and repository errors into HTTP errors."""
    try:
        yield
    except RepoNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    except RepoReadError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    except (RepoDetailsError, StudioInvalidError) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.get("/doctor", summary="Diagnose the installation", responses=COMMON)
def doctor() -> DoctorResponse:
    """Run the same checks as `kodalo doctor`: versions, libraries, data folder and database."""
    checks = run_checks(data_dir())
    return DoctorResponse(healthy=passed(checks), checks=[DoctorCheck.from_core(c) for c in checks])


# Settings -----------------------------------------------------------------------------------


@router.get("/settings/github", summary="Get GitHub connectivity", responses=COMMON)
def get_github_settings(github: GitHub) -> GitHubSettingsResponse:
    """Return how Kodalo reaches GitHub. The default is the gh CLI."""
    return GitHubSettingsResponse.from_core(github.get())


@router.put("/settings/github", summary="Set GitHub connectivity", responses=COMMON | INVALID)
def set_github_settings(body: GitHubSettingsUpdate, github: GitHub) -> GitHubSettingsResponse:
    """Choose the way to reach GitHub: a local folder, the gh CLI or the web."""
    try:
        return GitHubSettingsResponse.from_core(
            github.save(
                body.mode,
                body.local_folder,
                body.manifest_limit,
                body.document_limit,
                body.document_max_kb,
            )
        )
    except GitHubInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


AI = "/settings/ai/connections"


@router.get(AI, summary="List AI connections", responses=COMMON)
def list_ai_connections(ai: AiSetting) -> list[AiConnectionResponse]:
    """Return every AI provider with its connection, saved or not. Keys are never returned."""
    return [AiConnectionResponse.from_core(c) for c in ai.list_all()]


@router.put(f"{AI}/default", summary="Set the default AI connection", responses=COMMON | AI_INVALID)
def set_default_ai_connection(body: AiDefaultConnection, ai: AiSetting) -> AiConnectionResponse:
    """Make a saved, enabled connection the default."""
    with _ai_errors():
        return AiConnectionResponse.from_core(ai.set_default(body.provider))


@router.put(f"{AI}/{{provider}}", summary="Save an AI connection", responses=COMMON | AI_INVALID)
def save_ai_connection(
    provider: AiProviderPath, body: AiConnectionUpdate, ai: AiSetting
) -> AiConnectionResponse:
    """Save a connection. The API key goes to the system keychain and is never returned."""
    with _ai_errors():
        return AiConnectionResponse.from_core(
            ai.save(provider, enabled=body.enabled, api_key=body.api_key, base_url=body.base_url)
        )


@router.delete(
    f"{AI}/{{provider}}",
    summary="Remove an AI connection",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COMMON,
)
def remove_ai_connection(provider: AiProviderPath, ai: AiSetting) -> Response:
    """Forget a connection: its settings, models and API key."""
    with _ai_errors():
        ai.remove(provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    f"{AI}/{{provider}}/test", summary="Test an AI connection", responses=COMMON | AI_INVALID
)
def test_ai_connection(provider: AiProviderPath, ai: AiSetting) -> AiCheckResponse:
    """Try the connection once. A failure is reported in the body."""
    with _ai_errors():
        return AiCheckResponse.from_core(ai.test(provider))


@router.get(f"{AI}/{{provider}}/models", summary="List the models", responses=COMMON)
def list_ai_models(provider: AiProviderPath, ai: AiSetting) -> list[AiModelResponse]:
    """Return the saved models of a connection."""
    with _ai_errors():
        return [AiModelResponse.from_core(m) for m in ai.models(provider)]


@router.post(
    f"{AI}/{{provider}}/models/refresh",
    summary="Refresh the models",
    responses=COMMON | AI_INVALID | AI_UNREACHABLE,
)
def refresh_ai_models(provider: AiProviderPath, ai: AiSetting) -> list[AiModelResponse]:
    """Ask the provider for its models and save them. Models typed in by hand are kept."""
    with _ai_errors():
        return [AiModelResponse.from_core(m) for m in ai.refresh_models(provider)]


@router.put(
    f"{AI}/{{provider}}/default-model",
    summary="Set the default model",
    responses=COMMON | AI_INVALID | AI_NOT_FOUND,
)
def set_default_ai_model(
    provider: AiProviderPath, body: AiDefaultModel, ai: AiSetting
) -> AiModelResponse:
    """Make a model the one the connection uses by default."""
    with _ai_errors():
        return AiModelResponse.from_core(ai.set_default_model(provider, body.name))


@router.put(
    f"{AI}/{{provider}}/models/{{name:path}}",
    summary="Save a model",
    responses=COMMON | AI_INVALID,
)
def save_ai_model(
    provider: AiProviderPath, name: AiModelName, body: AiModelUpdate, ai: AiSetting
) -> AiModelResponse:
    """Add a model or change its settings. A setting left out goes back to the provider's own."""
    with _ai_errors():
        return AiModelResponse.from_core(
            ai.save_model(
                provider,
                name,
                max_tokens=body.max_tokens,
                temperature=body.temperature,
                timeout_s=body.timeout_s,
            )
        )


@router.delete(
    f"{AI}/{{provider}}/models/{{name:path}}",
    summary="Remove a model",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COMMON | AI_INVALID | AI_NOT_FOUND,
)
def remove_ai_model(provider: AiProviderPath, name: AiModelName, ai: AiSetting) -> Response:
    """Forget a model. One the provider offers comes back on the next refresh."""
    with _ai_errors():
        ai.remove_model(provider, name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


AI_HISTORY = "/settings/ai/history"
MAX_OFFSET = 10_000_000
PeriodQuery = Annotated[AiPeriod, Query(description="The time window.")]
StartQuery = Annotated[
    str | None, Query(max_length=10, description="First day of a custom period, 2026-11-01.")
]
EndQuery = Annotated[
    str | None, Query(max_length=10, description="Last day of a custom period, 2026-11-30.")
]


def _period(period: str, start: str | None, end: str | None) -> Period:
    with _ai_errors():
        return resolve_period(period, start, end)


@router.get(f"{AI_HISTORY}/settings", summary="Get the AI history settings", responses=COMMON)
def get_ai_history_settings(ai: AiSetting) -> AiHistorySettingsResponse:
    """Return whether the text of calls is kept and after how many days entries are removed."""
    return AiHistorySettingsResponse.from_core(ai.history.settings())


@router.put(
    f"{AI_HISTORY}/settings", summary="Set the AI history settings", responses=COMMON | AI_INVALID
)
def set_ai_history_settings(
    body: AiHistorySettingsUpdate, ai: AiSetting
) -> AiHistorySettingsResponse:
    """Choose whether to keep the text of calls and how long entries are kept (0 forever)."""
    with _ai_errors():
        return AiHistorySettingsResponse.from_core(
            ai.history.save_settings(body.store_text, body.retention_days)
        )


@router.get(AI_HISTORY, summary="List the AI calls", responses=COMMON | AI_INVALID)
def list_ai_history(
    ai: AiSetting,
    period: PeriodQuery = "all",
    start: StartQuery = None,
    end: EndQuery = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> AiHistoryPageResponse:
    """Return the calls made to AI providers in the period, newest first, without their text."""
    window = _period(period, start, end)
    with _ai_errors():
        return AiHistoryPageResponse.from_core(ai.history.list(window, limit, offset))


@router.get(
    f"{AI_HISTORY}/{{call_id}}",
    summary="Get one AI call",
    responses=COMMON | AI_INVALID | AI_NOT_FOUND,
)
def get_ai_call(
    call_id: Annotated[str, Path(min_length=1, max_length=36, description="The entry id.")],
    ai: AiSetting,
) -> AiCallDetailResponse:
    """Return one call with what was sent and what came back, when the text was kept."""
    with _ai_errors():
        return AiCallDetailResponse.from_detail(ai.history.get(call_id))


@router.delete(AI_HISTORY, summary="Purge the AI history", responses=COMMON)
def purge_ai_history(ai: AiSetting) -> AiPurgeResponse:
    """Remove every entry of the history. Token totals start again from zero."""
    return AiPurgeResponse(deleted=ai.history.purge_all())


@router.get("/settings/ai/usage", summary="Get the AI token usage", responses=COMMON | AI_INVALID)
def get_ai_usage(
    ai: AiSetting,
    period: PeriodQuery = "all",
    start: StartQuery = None,
    end: EndQuery = None,
) -> AiUsageResponse:
    """Return the calls and tokens used in the period per connection and model and per day."""
    window = _period(period, start, end)
    with _ai_errors():
        return AiUsageResponse.from_core(ai.history.usage(window))


@router.get("/settings/theme", summary="Get the window theme", responses=COMMON)
def get_theme(appearance: ThemeSetting) -> ThemeResponse:
    """Return the theme the window uses. The default, system, follows the operating system."""
    return ThemeResponse(theme=appearance.get())


@router.put("/settings/theme", summary="Set the window theme", responses=COMMON | INVALID)
def set_theme(body: ThemeUpdate, appearance: ThemeSetting) -> ThemeResponse:
    """Choose light, dark, or system. Only the window uses it."""
    try:
        return ThemeResponse(theme=appearance.save(body.theme))
    except AppearanceInvalidError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error


@router.post("/settings/github/check", summary="Check GitHub connectivity", responses=COMMON)
def check_github_settings(github: GitHub) -> GitHubCheckResponse:
    """Try the saved way of reaching GitHub once. A failure is reported in the body."""
    return GitHubCheckResponse.from_core(check_connection(github.get()))


# Studio -------------------------------------------------------------------------------------


@router.post(
    "/studio/source",
    summary="Check a repository to start a post from",
    responses=COMMON | INVALID,
)
def check_studio_source(
    body: StudioSourceRequest, github: GitHub, repos: Repos
) -> StudioSourceResponse:
    """Check the repository against the saved GitHub mode. Nothing is stored.

    For a local folder the answer also carries values read from git to prefill the details form.
    """
    with _studio_errors():
        source = validate_source(github.get(), body.source)
        suggested = suggest(FsPath(source.value)) if source.kind == "local_folder" else None
        return StudioSourceResponse.from_core(source, repos.stored(source), suggested)


@router.post(
    "/studio/repositories",
    summary="Read a repository",
    responses=COMMON | INVALID | STUDIO_ERRORS,
)
def read_repository(body: RepoReadRequest, github: GitHub, repos: Repos) -> RepoResponse:
    """Read the metadata, languages and top-level structure, and store them.

    A repository that was read before is returned from the database unless ``refresh`` is set.
    """
    with _studio_errors():
        settings = github.get()
        source = validate_source(settings, body.source)
        details = body.details.to_core() if body.details else None
        info = repos.read(settings, source, details, refresh=body.refresh)
        return RepoResponse.from_core(info)


@router.get("/studio/repositories", summary="List stored repositories", responses=COMMON)
def list_repositories(repos: Repos) -> list[RepoResponse]:
    """Return every repository that was read, sorted by owner and name."""
    return [RepoResponse.from_core(i) for i in repos.list_repos()]


@router.get(
    "/studio/repositories/{repo_id}",
    summary="Get a stored repository",
    responses=COMMON | NOT_FOUND,
)
def get_repository(repo_id: RepoPath, repos: Repos) -> RepoResponse:
    """Return one stored repository."""
    with _studio_errors():
        return RepoResponse.from_core(repos.get(repo_id))


@router.post(
    "/studio/repositories/{repo_id}/analysis/plan",
    summary="Plan the AI analysis",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_analysis(repo_id: RepoPath, github: GitHub, analyzer: Analyzer) -> AnalysisPlanResponse:
    """List the project files, package names and file names the AI would be asked about and
    estimate the tokens. Nothing is sent."""
    with _studio_errors(), _ai_errors():
        return AnalysisPlanResponse.from_core(analyzer.plan(github.get(), repo_id))


@router.post(
    "/studio/repositories/{repo_id}/analysis",
    summary="Analyze a repository with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def run_analysis(repo_id: RepoPath, github: GitHub, analyzer: Analyzer) -> AnalysisResultResponse:
    """Ask the default AI model once for parser, framework and tooling configs, check each one,
    and save the valid ones. Read the repository again to use them."""
    with _studio_errors(), _ai_errors():
        return AnalysisResultResponse.from_core(analyzer.apply(github.get(), repo_id))


@router.post(
    "/studio/repositories/{repo_id}/readme",
    summary="Read the README and docs",
    responses=COMMON | NOT_FOUND | STUDIO_ERRORS,
)
def read_readme(
    repo_id: RepoPath, body: ReadmeReadRequest, github: GitHub, readme: Readme
) -> ReadmeResponse:
    """Read the README and the docs it links to (no AI) and keep what they say: purpose,
    installation methods and capabilities. A saved analysis is returned unless ``refresh`` is set.
    """
    with _studio_errors():
        return ReadmeResponse.from_core(readme.read(github.get(), repo_id, refresh=body.refresh))


@router.get(
    "/studio/repositories/{repo_id}/readme",
    summary="Get the saved README analysis",
    responses=COMMON | NOT_FOUND,
)
def get_readme(repo_id: RepoPath, readme: Readme) -> ReadmeResponse:
    """Return the saved README analysis; 404 when the documents were not read yet."""
    with _studio_errors():
        saved = readme.get(repo_id)
        if saved is None:
            raise RepoNotFoundError("The README analysis has not been read yet.")
        return ReadmeResponse.from_core(saved)


@router.post(
    "/studio/repositories/{repo_id}/readme/analysis/plan",
    summary="Plan the AI README analysis",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_readme_analysis(repo_id: RepoPath, assistant: ReadmeAi) -> ReadmePlanResponse:
    """List the documents the AI would be sent and estimate the tokens. Nothing is sent."""
    with _studio_errors(), _ai_errors():
        return ReadmePlanResponse.from_core(assistant.plan(repo_id))


@router.post(
    "/studio/repositories/{repo_id}/readme/analysis",
    summary="Read the documents with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def run_readme_analysis(
    repo_id: RepoPath, github: GitHub, assistant: ReadmeAi
) -> ReadmeResultResponse:
    """Send the documents once to the default AI model and save the purpose, installation
    methods, capabilities and use cases that have evidence in the documents."""
    with _studio_errors(), _ai_errors():
        return ReadmeResultResponse.from_core(assistant.apply(github.get(), repo_id))


# Reference data -----------------------------------------------------------------------------


@router.get("/brands/fonts", summary="List fonts", responses=COMMON)
def list_fonts(service: Service) -> list[FontResponse]:
    """Return the font catalogue: bundled fonts first, then fonts installed on this computer."""
    return [FontResponse.from_core(font) for font in service.fonts.list_fonts()]


# Layouts ------------------------------------------------------------------------------------


@router.get("/layouts", summary="List layouts", responses=COMMON)
def list_layouts(service: Service) -> list[LayoutResponse]:
    """Return the built-in layouts first, then the user's, each sorted by name."""
    return [LayoutResponse.from_core(lay) for lay in service.layouts.list_layouts()]


@router.post(
    "/layouts",
    status_code=status.HTTP_201_CREATED,
    summary="Create a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS | LAYOUT_ERRORS,
)
def create_layout(body: LayoutCreate, service: Service) -> LayoutResponse:
    """Add a layout that brands can share."""
    with _layout_mapped():
        return LayoutResponse.from_core(service.layouts.create(body.name, body.settings))


@router.post(
    "/layouts/import",
    status_code=status.HTTP_201_CREATED,
    summary="Import a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS,
)
def import_layout(body: LayoutExport, service: Service, name: IMPORT_NAME = None) -> LayoutResponse:
    """Add a layout from an exported file. Its canvas is matched or created."""
    with _layout_mapped():
        layout = service.layouts.import_layout(body.model_dump(mode="json"), name=name)
        return LayoutResponse.from_core(layout)


@router.get("/layouts/{layout_id}", summary="Get a layout", responses=COMMON | LAYOUT_ERRORS)
def get_layout(layout_id: LayoutPath, service: Service) -> LayoutResponse:
    with _layout_mapped():
        return LayoutResponse.from_core(service.layouts.get(layout_id))


@router.patch(
    "/layouts/{layout_id}",
    summary="Change a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS | LAYOUT_ERRORS,
)
def update_layout(layout_id: LayoutPath, body: LayoutUpdate, service: Service) -> LayoutResponse:
    """Rename a layout or change settings. Every brand that uses it follows the change."""
    changes = body.model_dump(exclude_unset=True, exclude={"name"})
    with _layout_mapped():
        current = service.layouts.get(layout_id)
        settings = None
        if changes:
            merged = {k: getattr(current, k) for k in LayoutSettings.model_fields} | changes
            settings = LayoutSettings.model_validate(merged)
        layout = service.layouts.update(layout_id, name=body.name, settings=settings)
        return LayoutResponse.from_core(layout)


@router.post(
    "/layouts/{layout_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    summary="Copy a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS | LAYOUT_ERRORS,
)
def duplicate_layout(
    layout_id: LayoutPath, body: LayoutDuplicate, service: Service
) -> LayoutResponse:
    """Copy any layout, built in or not, as a layout of your own."""
    with _layout_mapped():
        return LayoutResponse.from_core(service.layouts.duplicate(layout_id, body.name))


@router.get(
    "/layouts/{layout_id}/export",
    summary="Export a layout",
    responses=COMMON | LAYOUT_ERRORS,
)
def export_layout(layout_id: LayoutPath, service: Service) -> LayoutExport:
    """Return the layout, with its canvas, as a file that `import` accepts."""
    with _layout_mapped():
        return LayoutExport.model_validate(service.layouts.export_layout(layout_id))


@router.delete(
    "/layouts/{layout_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a layout",
    responses=COMMON | LAYOUT_CHANGE_ERRORS | LAYOUT_ERRORS,
)
def delete_layout(layout_id: LayoutPath, service: Service) -> Response:
    """Remove a layout that no brand uses."""
    with _layout_mapped():
        service.layouts.delete(layout_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Palettes -----------------------------------------------------------------------------------


def _palette_response(service: BrandService, palette: Palette) -> PaletteResponse:
    return PaletteResponse.from_core(palette, service.starter(palette.id))


@router.get("/palettes", summary="List palettes", responses=COMMON)
def list_palettes(service: Service) -> list[PaletteResponse]:
    """Return the built-in palettes first, then the user's, each with brand data to start from."""
    return [_palette_response(service, p) for p in service.palettes.list_palettes()]


@router.post(
    "/palettes/suggest",
    summary="Suggest a palette with AI",
    responses={**COMMON, **INVALID, **AI_UNREACHABLE},
)
def suggest_palette(service: Service, ai: AiSetting) -> PaletteSuggestion:
    """Ask the default AI model for a new palette that differs from the existing ones. Nothing is
    saved."""
    with _ai_errors():
        name, colors = PaletteSuggester(service.palettes, ai).suggest()
    return PaletteSuggestion.model_validate({"name": name, "colors": colors.model_dump()})


@router.post(
    "/palettes",
    status_code=status.HTTP_201_CREATED,
    summary="Create a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS | PALETTE_ERRORS,
)
def create_palette(body: PaletteCreate, service: Service) -> PaletteResponse:
    """Add a palette of your own, for example from the colors of a brand."""
    with _palette_mapped():
        return _palette_response(service, service.palettes.create(body.name, body.colors))


@router.post(
    "/palettes/import",
    status_code=status.HTTP_201_CREATED,
    summary="Import a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS,
)
def import_palette(
    body: PaletteExport, service: Service, name: IMPORT_NAME = None
) -> PaletteResponse:
    """Add a palette from an exported file. A name already in use gets a number added."""
    with _palette_mapped():
        palette = service.palettes.import_palette(body.model_dump(mode="json"), name=name)
        return _palette_response(service, palette)


@router.get("/palettes/{palette_id}", summary="Get a palette", responses=COMMON | PALETTE_ERRORS)
def get_palette_by_id(palette_id: PalettePath, service: Service) -> PaletteResponse:
    with _palette_mapped():
        return _palette_response(service, service.palettes.get(palette_id))


@router.patch(
    "/palettes/{palette_id}",
    summary="Change a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS | PALETTE_ERRORS,
)
def update_palette(
    palette_id: PalettePath, body: PaletteUpdate, service: Service
) -> PaletteResponse:
    """Rename a palette or replace its colors. Brands made from it keep their colors."""
    with _palette_mapped():
        palette = service.palettes.update(palette_id, name=body.name, colors=body.colors)
        return _palette_response(service, palette)


@router.post(
    "/palettes/{palette_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    summary="Copy a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS | PALETTE_ERRORS,
)
def duplicate_palette(
    palette_id: PalettePath, body: PaletteDuplicate, service: Service
) -> PaletteResponse:
    """Copy any palette, built in or not, as a palette of your own."""
    with _palette_mapped():
        palette = service.palettes.duplicate(palette_id, body.name)
        return _palette_response(service, palette)


@router.get(
    "/palettes/{palette_id}/export",
    summary="Export a palette",
    responses=COMMON | PALETTE_ERRORS,
)
def export_palette(palette_id: PalettePath, service: Service) -> PaletteExport:
    """Return the palette as a file that `import` accepts."""
    with _palette_mapped():
        return PaletteExport.model_validate(service.palettes.export_palette(palette_id))


@router.delete(
    "/palettes/{palette_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a palette",
    responses=COMMON | PALETTE_CHANGE_ERRORS | PALETTE_ERRORS,
)
def delete_palette(palette_id: PalettePath, service: Service) -> Response:
    """Remove a palette of your own. Brands made from it keep their colors."""
    with _palette_mapped():
        service.palettes.delete(palette_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Canvases -----------------------------------------------------------------------------------


@router.get("/canvases", summary="List canvases", responses=COMMON)
def list_canvases(service: Service) -> list[CanvasResponse]:
    """Return the built-in canvases first, then the user's, each sorted by name."""
    return [CanvasResponse.from_core(c) for c in service.canvases.list_canvases()]


@router.post(
    "/canvases",
    status_code=status.HTTP_201_CREATED,
    summary="Create a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS | CANVAS_ERRORS,
)
def create_canvas(body: CanvasCreate, service: Service) -> CanvasResponse:
    """Add a slide size that brand layouts can use."""
    with _canvas_mapped():
        return CanvasResponse.from_core(service.canvases.create(body.name, body.width, body.height))


@router.post(
    "/canvases/import",
    status_code=status.HTTP_201_CREATED,
    summary="Import a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS,
)
def import_canvas(body: CanvasExport, service: Service, name: IMPORT_NAME = None) -> CanvasResponse:
    """Add a canvas from an exported file. A name already in use gets a number added."""
    with _canvas_mapped():
        canvas = service.canvases.import_canvas(body.model_dump(mode="json"), name=name)
        return CanvasResponse.from_core(canvas)


@router.get(
    "/canvases/{canvas_id}/export",
    summary="Export a canvas",
    responses=COMMON | CANVAS_ERRORS,
)
def export_canvas(canvas_id: CanvasPath, service: Service) -> CanvasExport:
    """Return the canvas as a file that `import` accepts."""
    with _canvas_mapped():
        return CanvasExport.model_validate(service.canvases.export_canvas(canvas_id))


@router.get("/canvases/{canvas_id}", summary="Get a canvas", responses=COMMON | CANVAS_ERRORS)
def get_canvas(canvas_id: CanvasPath, service: Service) -> CanvasResponse:
    with _canvas_mapped():
        return CanvasResponse.from_core(service.canvases.get(canvas_id))


@router.patch(
    "/canvases/{canvas_id}",
    summary="Change a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS | CANVAS_ERRORS,
)
def update_canvas(canvas_id: CanvasPath, body: CanvasUpdate, service: Service) -> CanvasResponse:
    """Rename or resize a canvas. Every brand that uses it follows the change."""
    with _canvas_mapped():
        canvas = service.canvases.update(
            canvas_id, name=body.name, width=body.width, height=body.height
        )
        return CanvasResponse.from_core(canvas)


@router.post(
    "/canvases/{canvas_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    summary="Copy a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS | CANVAS_ERRORS,
)
def duplicate_canvas(
    canvas_id: CanvasPath, body: CanvasDuplicate, service: Service
) -> CanvasResponse:
    """Copy any canvas, built in or not, as a new canvas of your own."""
    with _canvas_mapped():
        return CanvasResponse.from_core(service.canvases.duplicate(canvas_id, body.name))


@router.delete(
    "/canvases/{canvas_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a canvas",
    responses=COMMON | CANVAS_CHANGE_ERRORS | CANVAS_ERRORS,
)
def delete_canvas(canvas_id: CanvasPath, service: Service) -> Response:
    """Remove a canvas that no brand uses."""
    with _canvas_mapped():
        service.canvases.delete(canvas_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/brands/contrast", summary="Check contrast of colors", responses=COMMON)
def check_contrast(body: ContrastRequest) -> list[ContrastItem]:
    """Check colors that may not be saved yet. Nothing is changed or stored."""
    return [ContrastItem.from_core(r) for r in check_colors(body.colors)]


# Profiles -----------------------------------------------------------------------------------


@router.get("/brands", summary="List brand profiles", responses=COMMON)
def list_brands(service: Service) -> list[BrandResponse]:
    """Return every profile, sorted by name."""
    return [BrandResponse.from_core(b) for b in service.list_brands()]


@router.post(
    "/brands",
    summary="Create a brand profile",
    status_code=status.HTTP_201_CREATED,
    responses=COMMON | NAME_TAKEN | INVALID,
)
def create_brand(body: BrandCreate, service: Service) -> BrandResponse:
    """Create a profile from a starter palette, or from full data. The first one is the default."""
    with _mapped():
        data = body.data if body.data is not None else service.starter(body.palette)
        return BrandResponse.from_core(service.create(body.name, data))


@router.post(
    "/brands/import",
    summary="Import a brand profile",
    status_code=status.HTTP_201_CREATED,
    responses=COMMON | INVALID,
)
def import_brand(
    body: BrandExport,
    service: Service,
    name: Annotated[
        str | None,
        Query(
            min_length=1, max_length=64, description="Name for the profile. Default: the file's."
        ),
    ] = None,
) -> BrandResponse:
    """Add a profile from an exported file. A name already in use gets a number added."""
    with _mapped():
        brand = service.import_profile(body.model_dump(mode="json"), name=name)
        return BrandResponse.from_core(brand)


@router.get("/brands/{brand_id}", summary="Get a brand profile", responses=COMMON | NOT_FOUND)
def get_brand(brand_id: BrandPath, service: Service) -> BrandResponse:
    with _mapped():
        return BrandResponse.from_core(service.get(brand_id))


@router.patch(
    "/brands/{brand_id}",
    summary="Update a brand profile",
    responses=COMMON | NOT_FOUND | NAME_TAKEN | INVALID,
)
def update_brand(brand_id: BrandPath, body: BrandUpdate, service: Service) -> BrandResponse:
    """Rename a profile and/or replace its brand data. Fields left out are not changed."""
    with _mapped():
        brand = service.update(brand_id, name=body.name, data=body.data)
        return BrandResponse.from_core(brand)


@router.delete(
    "/brands/{brand_id}",
    summary="Delete a brand profile",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COMMON | NOT_FOUND,
)
def delete_brand(brand_id: BrandPath, service: Service) -> Response:
    """Remove a profile and its logo files. If it was the default, another becomes the default."""
    with _mapped():
        service.delete(brand_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/brands/{brand_id}/default",
    summary="Make a brand profile the default",
    responses=COMMON | NOT_FOUND,
)
def set_default_brand(brand_id: BrandPath, service: Service) -> BrandResponse:
    with _mapped():
        return BrandResponse.from_core(service.set_default(brand_id))


@router.post(
    "/brands/{brand_id}/duplicate",
    summary="Duplicate a brand profile",
    status_code=status.HTTP_201_CREATED,
    responses=COMMON | NOT_FOUND | NAME_TAKEN | INVALID,
)
def duplicate_brand(brand_id: BrandPath, body: BrandDuplicate, service: Service) -> BrandResponse:
    """Copy a profile, including its logo files, under a new name."""
    with _mapped():
        return BrandResponse.from_core(service.duplicate(brand_id, body.name))


@router.get(
    "/brands/{brand_id}/export",
    summary="Export a brand profile",
    responses=COMMON | NOT_FOUND,
)
def export_brand(brand_id: BrandPath, service: Service) -> BrandExport:
    """Return the profile and its logos as one file that `import` accepts."""
    with _mapped():
        return BrandExport.model_validate(service.export_profile(brand_id))


# Logos --------------------------------------------------------------------------------------


@router.put(
    "/brands/{brand_id}/logo",
    summary="Set a logo",
    responses=COMMON
    | NOT_FOUND
    | INVALID
    | {
        status.HTTP_413_CONTENT_TOO_LARGE: {"description": "The file is larger than 2 MB."},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"description": "Send image/png or image/svg+xml."},
    },
    openapi_extra=LOGO_BODY,
)
async def set_logo(
    brand_id: BrandPath, request: Request, service: Service, variant: Variant = "light"
) -> BrandResponse:
    """Store the request body as the profile's logo. SVG files with scripts are refused."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in LOGO_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Send the logo as image/png or image/svg+xml."
        )
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_LOGO_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "The logo is larger than 2 MB.")

    def store() -> BrandResponse:
        with _mapped():
            return BrandResponse.from_core(
                service.set_logo(brand_id, bytes(body), dark=variant == "dark")
            )

    return await run_in_threadpool(store)


@router.get(
    "/brands/{brand_id}/logo",
    summary="Get a logo",
    response_class=Response,
    responses=COMMON
    | NOT_FOUND
    | {
        status.HTTP_200_OK: {
            "description": "The logo file.",
            "content": {"image/png": {}, "image/svg+xml": {}},
        }
    },
)
def get_logo(brand_id: BrandPath, service: Service, variant: Variant = "light") -> Response:
    """Return the logo file, safe to show in an image tag. 404 if the profile has none."""
    with _mapped():
        logo = service.get(brand_id).data.logo
        name = logo.dark_file if variant == "dark" else logo.file
        if name is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "This brand has no such logo.")
        content = service.logos.read(name)
    media_type = "image/png" if name.endswith(".png") else "image/svg+xml"
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Security-Policy": LOGO_CSP, "X-Content-Type-Options": "nosniff"},
    )


@router.delete(
    "/brands/{brand_id}/logo",
    summary="Remove a logo",
    responses=COMMON | NOT_FOUND,
)
def remove_logo(brand_id: BrandPath, service: Service, variant: Variant = "light") -> BrandResponse:
    with _mapped():
        return BrandResponse.from_core(service.remove_logo(brand_id, dark=variant == "dark"))
