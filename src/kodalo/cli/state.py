"""Global options shared with every command through the Typer context."""

from dataclasses import dataclass
from pathlib import Path

import typer


@dataclass
class State:
    """Global options, set once by the Typer callback."""

    verbose: bool = False
    quiet: bool = False
    data_dir: Path | None = None


def get_state(ctx: typer.Context) -> State:
    state = ctx.obj
    # Set by the callback in cli.py, so this only narrows the type.
    assert isinstance(state, State)  # noqa: S101
    return state
