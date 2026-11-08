"""Shared by cli.spec and ui.spec: where names, version, icon and dependencies come from.

Names, version and icon come from one place each (see installer/projectinfo.py), so renaming the
project needs no edit here:

- executable names: the ``[project.scripts]`` keys in ``pyproject.toml`` (the entry scripts are
  generated from their targets)
- version and title: ``__version__`` and ``TITLE`` in the code
- icon: the ``.ico`` in ``brand/light``
- description and author: ``[project]`` in ``pyproject.toml``
"""

import importlib.util
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.config import CONF
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import projectinfo

INFO = projectinfo.load()
REPO_ROOT = INFO.root
UI_DIR = INFO.ui_dir
ICON_SOURCE = next(iter(sorted((REPO_ROOT / "brand" / "light").glob("*.ico"))), None)

PROJECT = INFO.project
SCRIPTS: dict[str, str] = INFO.entry_points  # executable name -> "module:function"
CLI_SCRIPT, UI_SCRIPT = INFO.cli_script, INFO.ui_script
WINDOWS = sys.platform == "win32"

# Not part of any program. The dev tools only exist in the build environment; PyInstaller can
# reach them through the test helpers of libraries collected whole (alembic, pydantic).
EXCLUDES = [
    "tkinter",
    "pytest",
    "_pytest",
    "hypothesis",
    "mypy",
    "mypyc",
    "setuptools",
    "pkg_resources",
]
# The command line imports neither the API nor the window.
CLI_EXCLUDES = [
    *EXCLUDES,
    INFO.api_package,
    INFO.ui_package,
    "cornea",
    "webview",
    "fastapi",
    "uvicorn",
]


class Collected:
    """Data files, native libraries and hidden imports gathered for one executable."""

    def __init__(self) -> None:
        self.datas: list[Any] = []
        self.binaries: list[Any] = []
        self.hiddenimports: list[str] = []

    def package(self, name: str) -> None:
        """Collect a package whole: submodules, data files and native libraries (no source files).

        The ``.dist-info`` folder is left out: nothing reads these packages' metadata at run time.
        Ask for it with ``metadata()`` where something does (keyring finds its backends there).
        """
        if importlib.util.find_spec(name) is None:
            return
        # Not collect_all(): it also copies every .py file as data, a second copy of code that is
        # already frozen into the executable.
        self.datas.extend(
            item for item in collect_data_files(name) if not str(item[1]).endswith(".dist-info")
        )
        self.binaries.extend(collect_dynamic_libs(name))
        self.hiddenimports.extend(collect_submodules(name))

    def metadata(self, *distributions: str) -> None:
        """Keep the package metadata that ``importlib.metadata`` reads at run time."""
        for distribution in distributions:
            self.datas.extend(copy_metadata(distribution))


def cli_dependencies() -> Collected:
    """What the command line needs. The window's build includes these too."""
    collected = Collected()
    collected.hiddenimports.extend(collect_submodules(INFO.core_package))
    collected.hiddenimports.extend(collect_submodules(INFO.cli_package))
    # rich lazily imports a Unicode-version-specific submodule that static analysis cannot see.
    collected.package("rich")
    collected.package("typer")
    # Alembic ships its own templates. The migrations are modules of the core package, so they are
    # frozen into the executable with the rest of the code (kodalo.core.storage.bundled).
    collected.package("alembic")
    return collected


def ui_dependencies() -> Collected:
    """What the window needs, on top of the command line's. Windows only.

    Cornea serves the frontend and the API with uvicorn, FastAPI and Starlette, which load protocol
    and middleware modules by name; pywebview reaches WebView2 through pythonnet and clr_loader.
    """
    if not WINDOWS or importlib.util.find_spec("cornea") is None:
        raise SystemExit("The UI build needs Windows and cornea-shell (uv sync --group installer).")
    if not (UI_DIR / "dist" / "index.html").is_file():
        raise SystemExit(f"Build the frontend first: npm ci && npm run build in {UI_DIR}")
    collected = Collected()
    for package in (
        "cornea", "webview", "clr_loader", "pythonnet", "proxy_tools", "bottle", "uvicorn",
        "fastapi", "starlette", "pydantic", "pydantic_core", "anyio", "h11",
    ):  # fmt: skip
        collected.package(package)
    collected.hiddenimports.extend(collect_submodules(INFO.api_package))
    collected.hiddenimports.extend(collect_submodules(INFO.ui_package))
    # The window finds the bundle through its package (Static(package=<ui package>, ...)).
    bundle = "/".join([*INFO.ui_package.split("."), "ui", "dist"])
    collected.datas.append((str(UI_DIR / "dist"), bundle))
    return collected


def _entry_script(script: str) -> str:
    """Write the small script PyInstaller freezes for one console script of pyproject.toml."""
    module, function = SCRIPTS[script].split(":")
    path = Path(CONF["workpath"]) / f"entry_{script}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "import multiprocessing\n"
        f"from {module} import {function}\n\n"
        'if __name__ == "__main__":\n'
        "    multiprocessing.freeze_support()\n"
        f"    raise SystemExit({function}())\n",
        encoding="utf-8",
    )
    return str(path)


def _version_info() -> Any:
    """Windows file properties (Explorer > Properties > Details) built from the project metadata."""
    from PyInstaller.utils.win32.versioninfo import (
        FixedFileInfo,
        StringFileInfo,
        StringStruct,
        StringTable,
        VarFileInfo,
        VarStruct,
        VSVersionInfo,
    )

    __version__, TITLE = INFO.version, INFO.title

    numbers = [int(n) for n in re.findall(r"\d+", __version__)[:4]]
    version = tuple(numbers + [0] * (4 - len(numbers)))
    author = INFO.publisher
    strings = {
        "CompanyName": author,
        "FileDescription": PROJECT.get("description", TITLE),
        "FileVersion": __version__,
        "ProductName": TITLE,
        "ProductVersion": __version__,
        "LegalCopyright": f"MIT License. {author}".strip(),
    }
    return VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=version,
            prodvers=version,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo(
                [StringTable("040904B0", [StringStruct(k, v) for k, v in strings.items()])]
            ),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    )


# The one ``.dist-info`` kept: keyring finds its Windows backend in its own entry points. Nothing
# else reads package metadata at run time (what does, such as websockets or Cornea's diagnostics,
# copes without it).
KEEP_METADATA = ("keyring-",)


def _unneeded_metadata(destination: str) -> bool:
    """True for a file inside a ``.dist-info`` folder other than those in ``KEEP_METADATA``."""
    top = destination.replace("\\", "/").split("/", 1)[0]
    return top.endswith(".dist-info") and not top.startswith(KEEP_METADATA)


def executable(
    script: str,
    collected: Collected,
    shared: Iterable[Collected] = (),
    excludes: Sequence[str] = (),
    *,
    console: bool = True,
) -> tuple[Analysis, EXE]:
    """Analyse one console script and describe its executable.

    ``shared`` are extra collections added to this executable only (the window's, for example);
    each executable carries its own pure-Python modules, and the build folder shares one ``lib/``.
    """
    parts = [collected, *shared]
    analysis = Analysis(
        [_entry_script(script)],
        pathex=[str(REPO_ROOT / "src")],
        binaries=[item for part in parts for item in part.binaries],
        datas=[item for part in parts for item in part.datas],
        hiddenimports=[item for part in parts for item in part.hiddenimports],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=list(excludes),
        noarchive=False,
    )
    analysis.datas[:] = [item for item in analysis.datas if not _unneeded_metadata(item[0])]
    exe = EXE(
        PYZ(analysis.pure),
        analysis.scripts,
        [],
        exclude_binaries=True,
        name=script,
        console=console,
        icon=str(ICON_SOURCE) if WINDOWS and ICON_SOURCE else None,
        version=_version_info() if WINDOWS else None,
        upx=False,
        # Everything but the executables goes in lib/ (COLLECT follows the EXE).
        contents_directory="lib",
    )
    return analysis, exe
