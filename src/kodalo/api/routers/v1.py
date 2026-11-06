"""Version 1 of the API, served under ``/api/v1``."""

from pathlib import Path as FsPath
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from kodalo.api.deps import (
    data_dir,
)
from kodalo.api.routers import brands
from kodalo.api.routers.common import (
    AI_INVALID,
    AI_NOT_FOUND,
    AI_UNREACHABLE,
    COMMON,
    INVALID,
    NOT_FOUND,
    STUDIO_ERRORS,
    AiModelName,
    AiProviderPath,
    AiSetting,
    Analyzer,
    GitHub,
    IdeasAi,
    Readme,
    ReadmeAi,
    RepoPath,
    Repos,
    ThemeSetting,
    ai_errors,
    studio_errors,
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
    AiPurgeResponse,
    AiUsageResponse,
    AnalysisPlanResponse,
    AnalysisResultResponse,
    DoctorCheck,
    DoctorResponse,
    GitHubCheckResponse,
    GitHubSettingsResponse,
    GitHubSettingsUpdate,
    IdeasPlanResponse,
    IdeasRequest,
    IdeasResponse,
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
    Period,
    resolve_period,
)
from kodalo.core.appearance import AppearanceInvalidError
from kodalo.core.doctor import passed, run_checks
from kodalo.core.github import (
    GitHubInvalidError,
    check_connection,
)
from kodalo.core.repo import (
    RepoNotFoundError,
    suggest,
)
from kodalo.core.studio import validate_source

# Cornea has already authenticated the caller by the time a request reaches these routes.
router = APIRouter(tags=["v1"])


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
    with ai_errors():
        return AiConnectionResponse.from_core(ai.set_default(body.provider))


@router.put(f"{AI}/{{provider}}", summary="Save an AI connection", responses=COMMON | AI_INVALID)
def save_ai_connection(
    provider: AiProviderPath, body: AiConnectionUpdate, ai: AiSetting
) -> AiConnectionResponse:
    """Save a connection. The API key goes to the system keychain and is never returned."""
    with ai_errors():
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
    with ai_errors():
        ai.remove(provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    f"{AI}/{{provider}}/test", summary="Test an AI connection", responses=COMMON | AI_INVALID
)
def test_ai_connection(provider: AiProviderPath, ai: AiSetting) -> AiCheckResponse:
    """Try the connection once. A failure is reported in the body."""
    with ai_errors():
        return AiCheckResponse.from_core(ai.test(provider))


@router.get(f"{AI}/{{provider}}/models", summary="List the models", responses=COMMON)
def list_ai_models(provider: AiProviderPath, ai: AiSetting) -> list[AiModelResponse]:
    """Return the saved models of a connection."""
    with ai_errors():
        return [AiModelResponse.from_core(m) for m in ai.models(provider)]


@router.post(
    f"{AI}/{{provider}}/models/refresh",
    summary="Refresh the models",
    responses=COMMON | AI_INVALID | AI_UNREACHABLE,
)
def refresh_ai_models(provider: AiProviderPath, ai: AiSetting) -> list[AiModelResponse]:
    """Ask the provider for its models and save them. Models typed in by hand are kept."""
    with ai_errors():
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
    with ai_errors():
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
    with ai_errors():
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
    with ai_errors():
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
    with ai_errors():
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
    with ai_errors():
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
    with ai_errors():
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
    with ai_errors():
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
    with ai_errors():
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
    with studio_errors():
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
    with studio_errors():
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
    with studio_errors():
        return RepoResponse.from_core(repos.get(repo_id))


@router.post(
    "/studio/repositories/{repo_id}/analysis/plan",
    summary="Plan the AI analysis",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_analysis(repo_id: RepoPath, github: GitHub, analyzer: Analyzer) -> AnalysisPlanResponse:
    """List the project files, package names and file names the AI would be asked about and
    estimate the tokens. Nothing is sent."""
    with studio_errors(), ai_errors():
        return AnalysisPlanResponse.from_core(analyzer.plan(github.get(), repo_id))


@router.post(
    "/studio/repositories/{repo_id}/analysis",
    summary="Analyze a repository with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def run_analysis(repo_id: RepoPath, github: GitHub, analyzer: Analyzer) -> AnalysisResultResponse:
    """Ask the default AI model once for parser, framework and tooling configs, check each one,
    and save the valid ones. Read the repository again to use them."""
    with studio_errors(), ai_errors():
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
    with studio_errors():
        return ReadmeResponse.from_core(readme.read(github.get(), repo_id, refresh=body.refresh))


@router.get(
    "/studio/repositories/{repo_id}/readme",
    summary="Get the saved README analysis",
    responses=COMMON | NOT_FOUND,
)
def get_readme(repo_id: RepoPath, readme: Readme) -> ReadmeResponse:
    """Return the saved README analysis; 404 when the documents were not read yet."""
    with studio_errors():
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
    with studio_errors(), ai_errors():
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
    with studio_errors(), ai_errors():
        return ReadmeResultResponse.from_core(assistant.apply(github.get(), repo_id))


@router.post(
    "/studio/repositories/{repo_id}/ideas/plan",
    summary="Plan the AI post ideas request",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def plan_ideas(repo_id: RepoPath, body: IdeasRequest, assistant: IdeasAi) -> IdeasPlanResponse:
    """Say what the AI would be sent for the chosen post and estimate the tokens. Nothing is
    sent."""
    with studio_errors(), ai_errors():
        return IdeasPlanResponse.from_core(
            assistant.plan(repo_id, body.post_type, body.kind, body.name)
        )


@router.post(
    "/studio/repositories/{repo_id}/ideas",
    summary="Plan post ideas with the AI",
    responses=COMMON | NOT_FOUND | INVALID | AI_UNREACHABLE,
)
def make_ideas(repo_id: RepoPath, body: IdeasRequest, assistant: IdeasAi) -> IdeasResponse:
    """Send the saved README analysis for the chosen tool, feature, use case or capability once
    to the default AI model and return a strategy, three angles with hooks and five post ideas.
    Claims are kept only when their quote was in what was sent. Nothing is saved."""
    with studio_errors(), ai_errors():
        return IdeasResponse.from_core(
            assistant.generate(repo_id, body.post_type, body.kind, body.name)
        )


router.include_router(brands.router)
