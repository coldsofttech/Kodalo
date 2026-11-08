"""``repositories`` commands: the repositories that posts are made from. They parse input and
show output only."""

import typer

from kodalo.cli.repositories import add, commands

app = typer.Typer(
    help="Add, check, list, show and remove the repositories that posts are made from.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

app.command("check")(commands.check_command)
app.command("add")(add.add_command)
app.command("list")(commands.list_command)
app.command("show")(commands.show_command)
app.command("remove")(commands.remove_command)
