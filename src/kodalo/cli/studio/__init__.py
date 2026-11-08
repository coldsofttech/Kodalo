"""``studio`` commands: make a post from a repository, step by step. They parse input and show
output only.

Choosing, reading and analyzing a repository is done with ``repositories``; the steps here follow:
``ideas``, ``copy`` and ``design``.
"""

import typer

from kodalo.cli.studio import copy, design, ideas

app = typer.Typer(
    help="Make a post from a repository: ideas, then copy, then design.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)

app.add_typer(ideas.app, name="ideas")
app.add_typer(copy.app, name="copy")
app.add_typer(design.app, name="design")
