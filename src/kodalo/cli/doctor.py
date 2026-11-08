"""The ``doctor`` command: diagnose the installation and the local data."""

from typing import Annotated

import typer
from rich.table import Table
from rich.text import Text

from kodalo.cli import output
from kodalo.cli.state import get_state
from kodalo.core.doctor import passed, run_checks

JsonOption = Annotated[bool, typer.Option("--json", help="Output as JSON.")]


def doctor(ctx: typer.Context, json_output: JsonOption = False) -> None:
    """Diagnose the installation and the local data. Exits with 1 if a required check fails."""
    checks = run_checks(get_state(ctx).data_dir)
    healthy = passed(checks)
    if json_output:
        output.console.print_json(
            data={"healthy": healthy, "checks": [c.to_dict() for c in checks]}
        )
    else:
        table = Table(title="kodalo doctor")
        for column in ("Check", "Status", "Detail"):
            table.add_column(column)
        for check in checks:
            if check.ok:
                status = Text("ok", style="green")
            elif check.required:
                status = Text("FAIL", style="bold red")
            else:
                status = Text("warn", style="yellow")
            table.add_row(check.name, status, check.detail)
        output.console.print(table)
        if not healthy:
            output.error("One or more required checks failed.")
    if not healthy:
        raise typer.Exit(code=1)
