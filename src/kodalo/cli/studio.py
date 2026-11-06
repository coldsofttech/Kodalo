"""``studio`` commands: start a post from a repository. They parse input and show output only.

Choosing, reading and analyzing a repository moved to ``repositories``; the post steps will follow.
"""

import typer

app = typer.Typer(
    help="Start a post from a repository.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
