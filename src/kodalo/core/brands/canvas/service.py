"""Create, change, copy and delete canvases, the slide sizes brand layouts can use."""

from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.brands.canvas.errors import (
    CanvasInUseError,
    CanvasInvalidError,
    CanvasNameTakenError,
    CanvasNotFoundError,
    CanvasReadOnlyError,
)
from kodalo.core.brands.canvas.models import (
    CUSTOM_PLATFORM_ID,
    MAX_SIZE,
    MIN_SIZE,
    Canvas,
    CanvasName,
    PlatformSize,
    SocialPlatform,
)
from kodalo.core.storage import Database
from kodalo.core.storage.models import Canvas as CanvasRow
from kodalo.core.storage.models import LayoutRow, SocialPlatformSize
from kodalo.core.storage.models import SocialPlatform as PlatformRow

EXPORT_FORMAT = "kodalo-canvas"
EXPORT_VERSION = 1
_NAME = TypeAdapter(CanvasName)


def _clean_name(name: str) -> str:
    try:
        return _NAME.validate_python(name)
    except ValidationError:
        raise CanvasInvalidError("A canvas name must be 1 to 64 characters.") from None


def _check_size(width: int, height: int) -> None:
    if not (MIN_SIZE <= width <= MAX_SIZE and MIN_SIZE <= height <= MAX_SIZE):
        raise CanvasInvalidError(
            f"The width and height must each be between {MIN_SIZE} and {MAX_SIZE} pixels."
        )


def size_concern(platform: SocialPlatform, width: int, height: int) -> str | None:
    """Say so when a size is not one the platform recommends. Platforms without sizes never do."""
    if not platform.sizes or any((s.width, s.height) == (width, height) for s in platform.sizes):
        return None
    options = ", ".join(f"{s.width} x {s.height}" for s in platform.sizes)
    return f"{platform.name} recommends {options}. {width} x {height} may be cropped or resized."


class CanvasService:
    """Canvases kept in the local database. Built-in (``system``) canvases are read-only."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # Reading

    def list_canvases(self) -> list[Canvas]:
        """Return every canvas: built-in ones first, then the user's, each sorted by name."""
        with self._database.session() as session:
            rows = session.scalars(select(CanvasRow)).all()
            canvases = [self._canvas(session, row) for row in rows]
        return sorted(canvases, key=lambda c: (c.type != "system", c.name.lower()))

    def list_platforms(self) -> list[SocialPlatform]:
        """Return the social platforms with their recommended sizes, Custom last."""
        with self._database.session() as session:
            return self._platforms(session)

    def get(self, canvas_id: str) -> Canvas:
        with self._database.session() as session:
            return self._canvas(session, self._row(session, canvas_id))

    def find(self, reference: str) -> Canvas:
        """Return the canvas whose id or name (ignoring case) matches ``reference``."""
        wanted = reference.strip().lower()
        for canvas in self.list_canvases():
            if canvas.id.lower() == wanted or canvas.name.lower() == wanted:
                return canvas
        raise CanvasNotFoundError(f'No canvas named "{reference}".')

    # Changing

    def create(
        self, name: str, width: int, height: int, platform_id: str = CUSTOM_PLATFORM_ID
    ) -> Canvas:
        name = _clean_name(name)
        _check_size(width, height)
        with self._database.session() as session:
            self._check_name(session, name)
            self._check_platform(session, platform_id)
            row = CanvasRow(
                name=name, width=width, height=height, type="user", platform_id=platform_id
            )
            session.add(row)
            session.flush()
            return self._canvas(session, row)

    def update(
        self,
        canvas_id: str,
        *,
        name: str | None = None,
        width: int | None = None,
        height: int | None = None,
        platform_id: str | None = None,
    ) -> Canvas:
        """Change a user canvas. Every brand that uses it follows the change."""
        with self._database.session() as session:
            row = self._row(session, canvas_id)
            self._check_editable(row)
            if name is not None:
                name = _clean_name(name)
                self._check_name(session, name, ignore=canvas_id)
                row.name = name
            new_width = row.width if width is None else width
            new_height = row.height if height is None else height
            _check_size(new_width, new_height)
            row.width, row.height = new_width, new_height
            if platform_id is not None:
                self._check_platform(session, platform_id)
                row.platform_id = platform_id
            session.flush()
            return self._canvas(session, row)

    def duplicate(self, canvas_id: str, name: str) -> Canvas:
        """Copy any canvas, built-in or not, as a new user canvas."""
        source = self.get(canvas_id)
        return self.create(name, source.width, source.height, source.platform_id)

    def delete(self, canvas_id: str) -> None:
        """Remove a user canvas that no brand uses."""
        with self._database.session() as session:
            row = self._row(session, canvas_id)
            self._check_editable(row)
            brands = self._users(session, canvas_id)
            if brands:
                raise CanvasInUseError(
                    f'"{row.name}" is used by the layouts: {", ".join(brands)}. Choose another '
                    "canvas for those layouts first.",
                    brands,
                )
            session.delete(row)

    # Export and import

    def export_canvas(self, canvas_id: str) -> dict[str, Any]:
        """Return a self-contained, JSON-ready description of a canvas."""
        canvas = self.get(canvas_id)
        return {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "name": canvas.name,
            "width": canvas.width,
            "height": canvas.height,
        }

    def import_canvas(self, payload: dict[str, Any], *, name: str | None = None) -> Canvas:
        """Add a canvas from :meth:`export_canvas` output. A taken name gets a number added."""
        if payload.get("format") != EXPORT_FORMAT:
            raise CanvasInvalidError("This is not a Kodalo canvas file.")
        if payload.get("version") != EXPORT_VERSION:
            raise CanvasInvalidError("This canvas file was made by a different version of Kodalo.")
        width, height = payload.get("width"), payload.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            raise CanvasInvalidError("The size in the canvas file is not valid.")
        return self.create(
            self.free_name(name or str(payload.get("name") or "Imported")), width, height
        )

    def ensure(self, entry: object) -> str:
        """Return the id of the canvas a file describes (``name``, ``width``, ``height``).

        A canvas with the same size (and the same name, when the file gives one) is reused;
        otherwise a user canvas is created.
        """
        if not isinstance(entry, dict):
            raise CanvasInvalidError("The canvas in the file is not valid.")
        width, height = entry.get("width"), entry.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            raise CanvasInvalidError("The canvas in the file is not valid.")
        name = entry.get("name")
        named = isinstance(name, str) and bool(name.strip())
        wanted = str(name).strip() if named else f"Custom {width}x{height}"
        for canvas in self.list_canvases():
            same_size = (canvas.width, canvas.height) == (width, height)
            if same_size and (not named or canvas.name.lower() == wanted.lower()):
                return canvas.id
        return self.create(self.free_name(wanted), width, height).id

    def free_name(self, wanted: str) -> str:
        """Return ``wanted``, or the first "wanted (2)", "wanted (3)"... that no canvas uses."""
        base = _clean_name(wanted)
        taken = {c.name.lower() for c in self.list_canvases()}
        candidate, number = base, 1
        while candidate.lower() in taken:
            number += 1
            suffix = f" ({number})"
            candidate = base[: 64 - len(suffix)] + suffix
        return candidate

    # Helpers

    @staticmethod
    def _check_editable(row: CanvasRow) -> None:
        if row.type == "system":
            raise CanvasReadOnlyError(
                f'"{row.name}" is built in and cannot be changed. Duplicate it to make your own.'
            )

    @staticmethod
    def _check_name(session: Session, name: str, ignore: str | None = None) -> None:
        rows = session.execute(select(CanvasRow.id, CanvasRow.name)).all()
        if any(r.name.lower() == name.lower() and r.id != ignore for r in rows):
            raise CanvasNameTakenError(f'A canvas named "{name}" already exists.')

    @staticmethod
    def _check_platform(session: Session, platform_id: str) -> None:
        if session.get(PlatformRow, platform_id) is None:
            raise CanvasInvalidError("Choose a social platform from the list.")

    @staticmethod
    def _platforms(session: Session) -> list[SocialPlatform]:
        sizes = session.scalars(select(SocialPlatformSize)).all()
        platforms = [
            SocialPlatform(
                id=row.id,
                name=row.name,
                sizes=[
                    PlatformSize(name=s.name, width=s.width, height=s.height)
                    for s in sorted(sizes, key=lambda s: s.name)
                    if s.platform_id == row.id
                ],
            )
            for row in session.scalars(select(PlatformRow)).all()
        ]
        return sorted(platforms, key=lambda p: (p.id == CUSTOM_PLATFORM_ID, p.name.lower()))

    @staticmethod
    def _row(session: Session, canvas_id: str) -> CanvasRow:
        row = session.get(CanvasRow, canvas_id)
        if row is None:
            raise CanvasNotFoundError("That canvas does not exist.")
        return row

    @staticmethod
    def _users(session: Session, canvas_id: str) -> list[str]:
        names = session.scalars(
            select(LayoutRow.name).where(LayoutRow.canvas_id == canvas_id)
        ).all()
        return sorted(names, key=str.lower)

    @classmethod
    def _canvas(cls, session: Session, row: CanvasRow) -> Canvas:
        platforms = {p.id: p for p in cls._platforms(session)}
        platform = platforms.get(row.platform_id or CUSTOM_PLATFORM_ID) or platforms.get(
            CUSTOM_PLATFORM_ID
        )
        return Canvas(
            platform_id=platform.id if platform else CUSTOM_PLATFORM_ID,
            platform=platform.name if platform else "Custom",
            size_concern=size_concern(platform, row.width, row.height) if platform else None,
            id=row.id,
            name=row.name,
            width=row.width,
            height=row.height,
            type=row.type,  # type: ignore[arg-type]
            used_by=cls._users(session, row.id),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
