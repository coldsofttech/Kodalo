"""Wire Cornea Shell to ``kodalo.api`` and ``kodalo.core``. It holds no business logic.

Cornea serves the built frontend, gates every mounted router behind its session cookie and
registers the native actions. It never prints or exits; the CLI shows errors and picks exit codes.
"""

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

from kodalo.api.routers import v1
from kodalo.core import __version__

if TYPE_CHECKING:
    from cornea import Shell

UI_DIR = Path(__file__).parent / "ui"
DEV_URL = "http://localhost:5173"
DEV_COMMAND = "npm run dev"
APP_ID = "com.kodalo.app"
TITLE = "Kodalo"
VERSION = __version__
# Window and taskbar icon: public/icon.png is copied into dist by the build. Replace it with yours.
ICON = UI_DIR / "dist" / "icon.png"
MAX_EXPORT_BYTES = 5_000_000


class UiUnavailableError(RuntimeError):
    """Raised when the window cannot be used on this system."""


def api_router() -> APIRouter:
    """Return the ``kodalo.api`` routes as Cornea mounts them: ``/api/v1/...``.

    Cornea adds the ``/api`` prefix itself, and its session gate has already authenticated the
    request before it reaches a route.
    """
    router = APIRouter(prefix="/v1")
    router.include_router(v1.router)
    return router


def app_info() -> dict[str, str]:
    """Native action ``app_info``: what the page may ask the app about itself."""
    return {"name": TITLE, "version": VERSION}


def write_json_file(path: str, text: str) -> None:
    """Native action ``write_json_file``: save an export where the user chose in the save dialog.

    Raises:
        ValueError: If the path is not a local ``.json`` file in an existing folder, or the text
            is too large.
    """
    if not path or "\0" in path or path.startswith(("\\\\", "//")):
        raise ValueError("Choose a file on this computer.")
    target = Path(path)
    if target.suffix.lower() != ".json" or not target.parent.is_dir():
        raise ValueError("Exports are saved as .json files in an existing folder.")
    data = text.encode("utf-8")
    if len(data) > MAX_EXPORT_BYTES:
        raise ValueError("That export is too large to save.")
    target.write_bytes(data)


def build_shell(*, dev: bool = False, window: bool = True) -> "Shell":
    """Build the Cornea shell.

    Args:
        dev: Start Vite (``npm run dev``) and show it through Cornea for hot reload.
        window: Open a native window. ``False`` only serves, so a browser can be used.

    Raises:
        UiUnavailableError: If the UI needs Windows, or Cornea is not installed.
    """
    if sys.platform != "win32":
        raise UiUnavailableError("The UI needs Windows. The CLI and API work on every system.")
    try:
        from cornea import DEV_CSP, App, Process, Security, Shell, Static, Window
    except ImportError as exc:
        raise UiUnavailableError("The UI needs the 'cornea-shell' package.") from exc

    source: Any
    security = Security()
    if dev:
        source = Process(DEV_COMMAND, url=DEV_URL, cwd=UI_DIR, mode="proxy")
        security = Security(csp=DEV_CSP)
    else:
        source = Static(package="kodalo.ui", package_path="ui/dist")

    shell = Shell(
        source,
        routers=[api_router()],
        security=security,
        window=(
            Window(title=TITLE, size=(1024, 768), icon=ICON if ICON.is_file() else None)
            if window
            else None
        ),
        identity=App(id=APP_ID),
    )
    shell.action("app_info")(app_info)
    shell.action("write_json_file")(write_json_file)
    return shell


def run_ui(
    *, dev: bool = False, window: bool = True, on_ready: Callable[[str], None] | None = None
) -> None:
    """Build the shell and run it until the window closes (or, without a window, until stopped).

    Args:
        dev: See ``build_shell``.
        window: See ``build_shell``.
        on_ready: Called once with a JSON line holding the address, which carries the one-time
            start-up token. Use it to show the address when there is no window.

    Raises:
        UiUnavailableError: If the UI needs Windows, or Cornea is not installed.
    """
    shell = build_shell(dev=dev, window=window)
    if on_ready is None:
        shell.run()
        return
    from cornea import ready_line

    shell.run(on_ready=lambda ready: on_ready(ready_line(ready)))
