"""``settings`` commands: change how Kodalo is set up. Each topic lives in its own module."""

import typer

from kodalo.cli.settings import ai, github

app = typer.Typer(
    help="Change Kodalo's settings.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
app.add_typer(ai.app, name="ai")
app.add_typer(github.app, name="github")
