"""An Alembic script directory that reads the migrations as modules of this package.

Alembic normally loads ``env.py`` and the files in ``versions/`` by path. Importing them instead
lets the installed programs carry them inside the executable, like the rest of the code, with no
loose migration files. Alembic is slow to load, so ``database`` imports this module only when a
database is opened.
"""

import importlib
import os
import pkgutil
import sys
from collections.abc import Iterator
from typing import Any

from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import Script, ScriptDirectory

PACKAGE = f"{__package__}.migrations"


class BundledScripts(ScriptDirectory):
    """Reads ``<package>.versions.*`` and ``<package>.env`` through the import system."""

    def __init__(self) -> None:
        # Alembic insists on an existing folder, and the frozen programs have none for this
        # package (its code is inside the executable). Nothing is read from it.
        super().__init__(os.curdir)

    def _load_revisions(self) -> Iterator[Script]:
        versions = importlib.import_module(f"{PACKAGE}.versions")
        for info in sorted(pkgutil.iter_modules(versions.__path__), key=lambda i: i.name):
            module = importlib.import_module(f"{versions.__name__}.{info.name}")
            yield Script(module, module.revision, module.__name__)

    def run_env(self) -> None:
        name = f"{PACKAGE}.env"
        # env.py does its work when it is executed, so it must run again for every migration.
        if name in sys.modules:
            importlib.reload(sys.modules[name])
        else:
            importlib.import_module(name)


def upgrade_to_head(config: Config, script: ScriptDirectory) -> None:
    """What ``alembic upgrade head`` does, on the given script directory."""

    def upgrade(rev: Any, context: Any) -> Any:
        return script._upgrade_revs("head", rev)

    with EnvironmentContext(
        config,
        script,
        fn=upgrade,
        as_sql=False,
        starting_rev=None,
        destination_rev="head",
        tag=None,
    ):
        script.run_env()
