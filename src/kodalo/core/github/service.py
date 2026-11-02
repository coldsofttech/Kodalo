"""Store the GitHub connectivity setting and check that the chosen way works."""

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from kodalo.core.github.errors import GitHubInvalidError
from kodalo.core.storage import Database
from kodalo.core.storage.models import Setting

Mode = Literal["local_folder", "gh_cli", "web_fetch"]
MODES: tuple[str, ...] = get_args(Mode)
DEFAULT_MODE: Mode = "gh_cli"

GROUP = "github"
MODE_KEY = "mode"
FOLDER_KEY = "local_folder"
MAX_PATH = 1024
_TIMEOUT = 10
_RATE_LIMIT_URL = "https://api.github.com/rate_limit"


@dataclass(frozen=True)
class GitHubSettings:
    """How Kodalo reaches GitHub. ``local_folder`` is only used by the ``local_folder`` mode."""

    mode: Mode = DEFAULT_MODE
    local_folder: str = ""


@dataclass(frozen=True)
class ConnectionCheck:
    """The outcome of trying one way of reaching GitHub."""

    mode: Mode
    ok: bool
    detail: str


class GitHubConnectivity:
    """The GitHub connectivity setting, kept in the ``settings`` table."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self) -> GitHubSettings:
        """Return the saved setting, or the defaults (``gh_cli``) when none is saved."""
        with self._database.session() as session:
            mode = self._load(session, MODE_KEY, DEFAULT_MODE)
            folder = self._load(session, FOLDER_KEY, "")
        return GitHubSettings(mode=_valid_mode(mode), local_folder=folder)

    def save(self, mode: str, local_folder: str | None = None) -> GitHubSettings:
        """Choose ``mode``. ``local_folder`` is kept as given; ``None`` leaves it unchanged."""
        mode = _valid_mode(mode)
        if local_folder is not None:
            local_folder = local_folder.strip()
            if len(local_folder) > MAX_PATH:
                raise GitHubInvalidError(f"The folder path must be at most {MAX_PATH} characters.")
        current = self.get()
        folder = current.local_folder if local_folder is None else local_folder
        if mode == "local_folder" and not folder:
            raise GitHubInvalidError("Local folder mode needs a folder.")
        with self._database.session() as session:
            self._store(session, MODE_KEY, mode)
            self._store(session, FOLDER_KEY, folder)
        return GitHubSettings(mode=mode, local_folder=folder)

    @staticmethod
    def _query(key: str) -> Select[Setting]:
        return select(Setting).where(
            Setting.scope == "global",
            Setting.owner_id == "",
            Setting.group_name == GROUP,
            Setting.key == key,
        )

    def _load(self, session: Session, key: str, default: str) -> str:
        row = session.scalars(self._query(key)).first()
        if row is None:
            return default
        value = json.loads(row.value_json)
        return value if isinstance(value, str) else default

    def _store(self, session: Session, key: str, value: str) -> None:
        row = session.scalars(self._query(key)).first()
        if row is None:
            row = Setting(
                scope="global",
                owner_id="",
                group_name=GROUP,
                key=key,
                mode="own",
                value_json="null",
            )
            session.add(row)
        row.value_json = json.dumps(value)


def _valid_mode(mode: str) -> Mode:
    if mode not in MODES:
        raise GitHubInvalidError(f"Unknown mode: {mode}. Use one of: {', '.join(MODES)}.")
    return mode  # type: ignore[return-value]


def check_connection(settings: GitHubSettings) -> ConnectionCheck:
    """Try the chosen way once. Never raises; the outcome says what is wrong."""
    mode = settings.mode
    if mode == "local_folder":
        return _check_folder(settings.local_folder)
    if mode == "gh_cli":
        return _check_gh()
    return _check_web()


def _check_folder(folder: str) -> ConnectionCheck:
    if not folder:
        return ConnectionCheck("local_folder", False, "No folder is set.")
    path = Path(folder).expanduser()
    if not path.is_dir():
        return ConnectionCheck("local_folder", False, "The folder does not exist.")
    return ConnectionCheck("local_folder", True, f"Using {path}.")


def _check_gh() -> ConnectionCheck:
    gh = shutil.which("gh")
    if gh is None:
        return ConnectionCheck("gh_cli", False, "The GitHub CLI (gh) is not installed.")
    try:
        result = subprocess.run(  # noqa: S603
            [gh, "auth", "status"], capture_output=True, text=True, timeout=_TIMEOUT, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return ConnectionCheck("gh_cli", False, "The GitHub CLI did not respond.")
    if result.returncode != 0:
        return ConnectionCheck(
            "gh_cli", False, "The GitHub CLI is not signed in. Run: gh auth login"
        )
    return ConnectionCheck("gh_cli", True, "The GitHub CLI is installed and signed in.")


def _check_web() -> ConnectionCheck:
    request = urllib.request.Request(_RATE_LIMIT_URL, headers={"User-Agent": "kodalo"})
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT):  # noqa: S310
            pass
    except urllib.error.HTTPError as error:
        return ConnectionCheck("web_fetch", False, f"GitHub answered with status {error.code}.")
    except (urllib.error.URLError, OSError, TimeoutError):
        return ConnectionCheck("web_fetch", False, "GitHub could not be reached.")
    return ConnectionCheck("web_fetch", True, "GitHub is reachable (public repositories only).")
