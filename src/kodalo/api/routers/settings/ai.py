"""AI connection, model, history and usage routes."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from kodalo.api.routers.common import (
    AI_INVALID,
    AI_NOT_FOUND,
    AI_UNREACHABLE,
    COMMON,
    AiModelName,
    AiProviderPath,
    AiSetting,
    ai_errors,
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
)
from kodalo.core.settings.ai import (
    Period,
    resolve_period,
)

router = APIRouter()


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
