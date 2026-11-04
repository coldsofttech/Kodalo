"""``ai`` commands: connect Kodalo to Claude, ChatGPT or Gemini. They parse input and show output
only. API keys are asked for with a hidden prompt (or read from a pipe), never taken from an
argument, so they stay out of the shell history."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

import typer
from rich.table import Table

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.ai import (
    PROVIDER_IDS,
    AiConnection,
    AiConnectionError,
    AiConnections,
    AiInvalidError,
    AiModel,
    AiNotFoundError,
    AiSecretError,
)
from kodalo.core.storage import Database, StorageError, database_path, default_data_dir

app = typer.Typer(
    help="Connect Kodalo to Claude, ChatGPT or Gemini, and choose their models.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
models_app = typer.Typer(
    help="Manage the models of a connection.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
app.add_typer(models_app, name="models")

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]
ProviderArgument = Annotated[str, typer.Argument(help=f"One of: {', '.join(PROVIDER_IDS)}.")]
NameArgument = Annotated[str, typer.Argument(help="The model name.")]


@contextmanager
def _connections(ctx: typer.Context) -> Iterator[AiConnections]:
    """Open the database for one command, turning expected failures into exit code 1."""
    data_dir = get_state(ctx).data_dir or default_data_dir()
    database: Database | None = None
    try:
        database = Database.open(database_path(data_dir))
        yield AiConnections(database)
    except (AiInvalidError, AiNotFoundError, AiConnectionError, AiSecretError, StorageError) as e:
        output.error(str(e))
        raise typer.Exit(code=1) from e
    finally:
        if database is not None:
            database.close()


def _model_data(model: AiModel) -> dict[str, Any]:
    return {
        "name": model.name,
        "source": model.source,
        "is_default": model.is_default,
        "max_tokens": model.max_tokens,
        "temperature": model.temperature,
        "timeout_s": model.timeout_s,
    }


def _connection_data(connection: AiConnection) -> dict[str, Any]:
    return {
        "provider": connection.provider,
        "label": connection.label,
        "kind": connection.kind,
        "saved": connection.saved,
        "enabled": connection.enabled,
        "is_default": connection.is_default,
        "base_url": connection.base_url or connection.default_base_url,
        "has_key": connection.has_key,
        "key_hint": connection.key_hint,
        "status": connection.status,
        "status_detail": connection.status_detail,
        "checked_at": connection.checked_at,
        "default_model": connection.default_model,
        "models": [_model_data(model) for model in connection.models],
    }


def _key_text(connection: AiConnection) -> str:
    if connection.kind == "local_cli":
        return "not needed"
    if not connection.has_key:
        return "-"
    return f"saved (…{connection.key_hint})" if connection.key_hint else "saved"


def _show_connections(connections: list[AiConnection], as_json: bool) -> None:
    if as_json:
        output.console.print_json(data=[_connection_data(c) for c in connections])
        return
    table = Table()
    for column in ("Provider", "Saved", "Enabled", "Default", "Key", "Status", "Model", "Models"):
        table.add_column(column)
    for c in connections:
        table.add_row(
            f"{c.label} ({c.provider})",
            "yes" if c.saved else "no",
            "yes" if c.enabled else "no",
            "yes" if c.is_default else "",
            _key_text(c),
            c.status or "-",
            c.default_model or "-",
            str(len(c.models)),
        )
    output.console.print(table)


def _show_connection(connection: AiConnection, as_json: bool) -> None:
    if as_json:
        output.console.print_json(data=_connection_data(connection))
        return
    table = Table(show_header=False)
    table.add_row("Provider", f"{connection.label} ({connection.provider})")
    table.add_row("Enabled", "yes" if connection.enabled else "no")
    table.add_row("Default connection", "yes" if connection.is_default else "no")
    table.add_row("Key", _key_text(connection))
    if connection.kind == "api_key":
        table.add_row("Address", connection.base_url or connection.default_base_url)
    table.add_row("Status", connection.status or "not tested")
    if connection.status_detail:
        table.add_row("Last result", connection.status_detail)
    table.add_row("Default model", connection.default_model or "-")
    output.console.print(table)


def _show_models(models: list[AiModel], as_json: bool) -> None:
    if as_json:
        output.console.print_json(data=[_model_data(model) for model in models])
        return
    table = Table()
    for column in ("Model", "Source", "Default", "Max tokens", "Temperature", "Timeout (s)"):
        table.add_column(column)
    for m in models:
        table.add_row(
            m.name,
            m.source,
            "yes" if m.is_default else "",
            _optional(m.max_tokens),
            _optional(m.temperature),
            _optional(m.timeout_s),
        )
    output.console.print(table)


def _optional(value: float | None) -> str:
    return "-" if value is None else f"{value:g}"


@app.command("list")
def list_command(ctx: typer.Context, as_json: JsonOption = False) -> None:
    """List every provider with its connection, saved or not."""
    with _connections(ctx) as ai:
        _show_connections(ai.list_all(), as_json)


@app.command("show")
def show_command(
    ctx: typer.Context, provider: ProviderArgument, as_json: JsonOption = False
) -> None:
    """Show the connection to one provider."""
    with _connections(ctx) as ai:
        _show_connection(ai.get(provider), as_json)


@app.command("set")
def set_command(
    ctx: typer.Context,
    provider: ProviderArgument,
    key: Annotated[
        bool,
        typer.Option(
            "--key", help="Enter the API key at a hidden prompt, or pipe it in. Never an argument."
        ),
    ] = False,
    enabled: Annotated[
        bool | None,
        typer.Option("--enable/--disable", help="Turn the connection on or off."),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Another address for the API. Empty for the default."),
    ] = None,
    as_json: JsonOption = False,
) -> None:
    """Save the connection to a provider. Values you leave out are kept."""
    api_key = typer.prompt("API key", hide_input=True) if key else None
    with _connections(ctx) as ai:
        _show_connection(
            ai.save(provider, enabled=enabled, api_key=api_key, base_url=base_url), as_json
        )


@app.command("test")
def try_command(
    ctx: typer.Context, provider: ProviderArgument, as_json: JsonOption = False
) -> None:
    """Check that the connection works. Exits with 1 when it does not."""
    with _connections(ctx) as ai:
        check = ai.test(provider)
    if as_json:
        output.console.print_json(
            data={"provider": check.provider, "ok": check.ok, "detail": check.detail}
        )
    else:
        output.console.print(f"{check.provider}: {'ok' if check.ok else 'failed'}. {check.detail}")
    if not check.ok:
        raise typer.Exit(code=1)


@app.command("default")
def default_command(
    ctx: typer.Context, provider: ProviderArgument, as_json: JsonOption = False
) -> None:
    """Make a provider the default connection."""
    with _connections(ctx) as ai:
        _show_connection(ai.set_default(provider), as_json)


@app.command("remove")
def remove_command(ctx: typer.Context, provider: ProviderArgument) -> None:
    """Forget a connection: its settings, models and API key."""
    with _connections(ctx) as ai:
        removed = ai.remove(provider)
    output.console.print(f"Removed {provider}." if removed else f"{provider} was not saved.")


@models_app.command("list")
def models_list_command(
    ctx: typer.Context, provider: ProviderArgument, as_json: JsonOption = False
) -> None:
    """List the saved models of a connection."""
    with _connections(ctx) as ai:
        _show_models(ai.models(provider), as_json)


@models_app.command("refresh")
def models_refresh_command(
    ctx: typer.Context, provider: ProviderArgument, as_json: JsonOption = False
) -> None:
    """Ask the provider which models it offers and save them."""
    with _connections(ctx) as ai:
        _show_models(ai.refresh_models(provider), as_json)


@models_app.command("set")
def models_set_command(
    ctx: typer.Context,
    provider: ProviderArgument,
    name: NameArgument,
    max_tokens: Annotated[
        int | None, typer.Option("--max-tokens", help="Most tokens to generate, 1 to 1000000.")
    ] = None,
    temperature: Annotated[
        float | None, typer.Option("--temperature", help="Randomness, 0 to 2.")
    ] = None,
    timeout: Annotated[
        int | None, typer.Option("--timeout", help="Seconds to wait for an answer, 1 to 600.")
    ] = None,
    as_json: JsonOption = False,
) -> None:
    """Add a model or change its settings. Options you leave out go back to the provider's own."""
    with _connections(ctx) as ai:
        model = ai.save_model(
            provider, name, max_tokens=max_tokens, temperature=temperature, timeout_s=timeout
        )
    _show_models([model], as_json)


@models_app.command("default")
def models_default_command(
    ctx: typer.Context, provider: ProviderArgument, name: NameArgument, as_json: JsonOption = False
) -> None:
    """Make a model the one the connection uses by default."""
    with _connections(ctx) as ai:
        model = ai.set_default_model(provider, name)
    _show_models([model], as_json)


@models_app.command("remove")
def models_remove_command(
    ctx: typer.Context, provider: ProviderArgument, name: NameArgument
) -> None:
    """Forget a model. A model the provider offers comes back on the next refresh."""
    with _connections(ctx) as ai:
        ai.remove_model(provider, name)
    output.console.print(f"Removed {name}.")
