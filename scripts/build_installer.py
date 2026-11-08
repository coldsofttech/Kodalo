#!/usr/bin/env python3
"""Build the installers: PyInstaller folders, then NSIS setups (Windows only).

Everything comes from the project's own metadata (installer/projectinfo.py), so renaming the
project needs no edit here: names from [project.scripts] and [tool.installer], version from
``__version__``, title from ``TITLE`` in the window's app module, description, author, homepage and
license from [project] in pyproject.toml, icon from the window's ui/public/icon.png. Tool versions
are pinned in installer/tools.toml.

Signing is off by default. Set SIGN_COMMAND to a command that signs one file, with {file} where
its path goes (for example a signtool or SignPath call); the executables and then each setup.exe
are signed. Nothing in this script is tied to one provider.

Products:  cli  the command line (Windows setup and portable zip)
           ui   the window together with the command line (Windows setup only)

Usage:  uv sync --group installer
        uv run python scripts/build_installer.py [cli] [ui] [--build-frontend] [--smoke]
The installers are written to dist/installer/. See docs/packaging.md for the details.
"""

import argparse
import functools
import os
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "installer"))
import projectinfo  # noqa: E402

INFO = projectinfo.load()
UI_DIR = INFO.ui_dir
BUILD = ROOT / "build" / "installer"
WORK = ROOT / "build" / "installer-work"
OUT = ROOT / "dist" / "installer"
SPECS = ROOT / "installer" / "pyinstaller"
NSIS_DIR = ROOT / "installer" / "windows" / "nsis"
WINDOWS = sys.platform == "win32"
T = TypeVar("T")


@dataclass(frozen=True)
class Meta:
    """What the installers are built from."""

    project: dict[str, object]
    cli: str  # command line executable and package name
    ui: str  # window executable name
    version: str
    title: str  # product name of the window

    @property
    def cli_title(self) -> str:
        return f"{self.title} CLI"


def load_meta() -> Meta:
    return Meta(INFO.project, INFO.cli_script, INFO.ui_script, INFO.version, INFO.title)


def run(command: list[str], *, env: dict[str, str] | None = None, cwd: Path = ROOT) -> None:
    print("+", " ".join(shlex.quote(part) for part in command), flush=True)
    subprocess.run(command, check=True, cwd=cwd, env=env)


def run_parallel(tasks: list[Callable[[], T]], jobs: int) -> list[T]:
    """Run independent ``tasks`` on up to ``jobs`` threads; results keep the order of ``tasks``.

    The work is in subprocesses (PyInstaller, makensis), so threads are enough. The first
    failure is raised once the others have finished.
    """
    with ThreadPoolExecutor(max_workers=max(1, min(jobs, len(tasks) or 1))) as pool:
        futures = [pool.submit(task) for task in tasks]
        return [future.result() for future in futures]


def author(meta: Meta) -> dict[str, str]:
    authors = meta.project.get("authors") or [{}]
    return dict(authors[0])  # type: ignore[index, call-overload]


# ---- PyInstaller -------------------------------------------------------------------------------
def build_frontend() -> None:
    npm = "npm.cmd" if WINDOWS else "npm"
    run([npm, "ci"], cwd=UI_DIR)
    run([npm, "run", "build"], cwd=UI_DIR)


def freeze(product: str) -> Path:
    """Run PyInstaller for one product and return its output folder."""
    spec = "cli.spec" if product == "cli" else "ui.spec"
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(SPECS / spec),
            "--noconfirm",
            "--distpath",
            str(BUILD),
            "--workpath",
            str(WORK / product),
        ]
    )
    return BUILD / (META.cli if product == "cli" else META.ui)


# ---- Windows: NSIS -----------------------------------------------------------------------------
@functools.cache
def make_icon() -> Path:
    """The installer icon: the same PNG the window uses, converted to .ico."""
    from PIL import Image

    icon = WORK / "icon.ico"
    icon.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(UI_DIR / "public" / "icon.png") as image:
        image.save(icon, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return icon


def sign(files: list[Path]) -> None:
    """Sign ``files`` with SIGN_COMMAND, if it is set; otherwise do nothing."""
    template = os.environ.get("SIGN_COMMAND", "").strip()
    if not template:
        return
    if "{file}" not in template:
        raise SystemExit("SIGN_COMMAND must contain {file}, where the file to sign goes.")
    for file in files:
        command = template.replace("{file}", f'"{file}"')
        print("+", command, flush=True)
        # Windows takes the command line as written; elsewhere it is split like a shell would.
        # SIGN_COMMAND is set by whoever runs the build (a CI variable), so it is trusted input.
        subprocess.run(command if WINDOWS else shlex.split(command), check=True, cwd=ROOT)


def find_makensis() -> str:
    found = shutil.which("makensis")
    if found:
        return found
    for variable in ("ProgramFiles(x86)", "ProgramFiles"):
        candidate = Path(os.environ.get(variable, "")) / "NSIS" / "makensis.exe"
        if candidate.is_file():
            return str(candidate)
    raise SystemExit("makensis not found. Install NSIS (version in installer/tools.toml).")


def numeric_version(version: str) -> str:
    numbers = re.findall(r"\d+", version)[:4]
    return ".".join(numbers + ["0"] * (4 - len(numbers)))


def package_exe(product: str, folder: Path) -> Path:
    """Build the NSIS setup for one product."""
    OUT.mkdir(parents=True, exist_ok=True)
    name = META.cli if product == "cli" else META.ui
    sign(sorted(folder.glob("*.exe")))
    setup = OUT / f"{name}-{META.version}-setup.exe"
    urls = META.project.get("urls") or {}
    flags = {
        "APP_NAME": META.cli_title if product == "cli" else META.title,
        "APP_VERSION": META.version,
        "APP_VERSION_NUMERIC": numeric_version(META.version),
        "SOURCE_DIR": str(folder),
        "OUT_FILE": str(setup),
        "ICON_FILE": str(make_icon()),
        "LICENSE_FILE": str(ROOT / "LICENSE"),
        "PUBLISHER": author(META).get("name", ""),
        "URL": str(urls.get("Homepage", "")),  # type: ignore[attr-defined]
    }
    command = [find_makensis(), "/V2"]
    command += [f"/D{key}={value}" for key, value in flags.items() if value]
    run([*command, str(NSIS_DIR / f"{product}.nsi")])
    sign([setup])
    return setup


def package_zip(folder: Path) -> Path:
    """The command line as a portable zip (what the Scoop manifest installs)."""
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"{META.cli}-{META.version}-windows-x64"
    return Path(shutil.make_archive(str(target), "zip", root_dir=folder))


# ---- smoke test --------------------------------------------------------------------------------
def smoke(products: list[str]) -> None:
    """Start each built executable and check it answers (the test_frozen_*.py integration tests)."""
    tests = ["tests/cli/integration/test_frozen_cli.py"]
    if "ui" in products:
        tests.append("tests/ui/integration/test_frozen_ui.py")
    run([sys.executable, "-m", "pytest", "-m", "integration", "--no-cov", "-p", "no:cacheprovider",
         *tests])  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("products", nargs="*", choices=["cli", "ui"], help="default: all")
    parser.add_argument("--build-frontend", action="store_true", help="run npm ci && npm run build")
    parser.add_argument("--smoke", action="store_true", help="run the smoke tests on the builds")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1,
                        help="builds to run at once (1 = one after the other)")  # fmt: skip
    args = parser.parse_args()

    if not WINDOWS:
        raise SystemExit("Installers are built on Windows only.")
    products = args.products or ["cli", "ui"]

    built: list[Path] = []
    if "ui" in products and args.build_frontend:
        build_frontend()
    folders = dict(
        zip(
            products,
            run_parallel([functools.partial(freeze, p) for p in products], args.jobs),
            strict=True,
        )
    )
    make_icon()  # once, before the setups are built side by side
    tasks: list[Callable[[], Path]] = [
        functools.partial(package_exe, p, folders[p]) for p in products
    ]
    if "cli" in products:
        tasks.append(functools.partial(package_zip, folders["cli"]))
    built.extend(run_parallel(tasks, args.jobs))
    if args.smoke:
        smoke(products)
    print("\nBuilt:")
    for path in built:
        print(f"  {path.relative_to(ROOT)}  ({path.stat().st_size / 1_048_576:.1f} MB)")


META = load_meta()

if __name__ == "__main__":
    main()
