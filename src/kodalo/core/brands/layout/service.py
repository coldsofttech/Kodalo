"""Create, change, copy, delete, export and import layouts shared by brands."""

from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.brands.canvas import CanvasError, CanvasService
from kodalo.core.brands.layout.errors import (
    LayoutInUseError,
    LayoutInvalidError,
    LayoutNameTakenError,
    LayoutNotFoundError,
    LayoutReadOnlyError,
)
from kodalo.core.brands.layout.models import Layout, LayoutName, LayoutSettings
from kodalo.core.storage import Database
from kodalo.core.storage.models import BrandProfile, LayoutRow
from kodalo.core.storage.models import Canvas as CanvasRow

EXPORT_FORMAT = "kodalo-layout"
EXPORT_VERSION = 1
_NAME = TypeAdapter(LayoutName)
SETTING_NAMES = tuple(name for name in LayoutSettings.model_fields if name != "canvas_id")


def _clean_name(name: str) -> str:
    try:
        return _NAME.validate_python(name)
    except ValidationError:
        raise LayoutInvalidError("A layout name must be 1 to 64 characters.") from None


def _convert(raw: str, current: object, path: str) -> object:
    if isinstance(current, bool):
        lowered = raw.strip().lower()
        if lowered in {"true", "yes", "on", "1"}:
            return True
        if lowered in {"false", "no", "off", "0"}:
            return False
        raise LayoutInvalidError(f"{path} must be true or false.")
    if isinstance(current, int):
        try:
            return int(raw)
        except ValueError:
            raise LayoutInvalidError(f"{path} must be a whole number.") from None
    return raw


class LayoutService:
    """Layouts kept in the local database. Built-in (``system``) layouts are read-only."""

    def __init__(self, database: Database, canvases: CanvasService) -> None:
        self._database = database
        self._canvases = canvases

    # Reading

    def list_layouts(self) -> list[Layout]:
        """Return every layout: built-in ones first, then the user's, each sorted by name."""
        with self._database.session() as session:
            layouts = [self._layout(session, row) for row in session.scalars(select(LayoutRow))]
        return sorted(layouts, key=lambda lay: (lay.type != "system", lay.name.lower()))

    def get(self, layout_id: str) -> Layout:
        with self._database.session() as session:
            return self._layout(session, self._row(session, layout_id))

    def find(self, reference: str) -> Layout:
        """Return the layout whose id or name (ignoring case) matches ``reference``."""
        wanted = reference.strip().lower()
        for layout in self.list_layouts():
            if wanted in (layout.id.lower(), layout.name.lower()):
                return layout
        raise LayoutNotFoundError(f'No layout named "{reference}".')

    # Changing

    def create(self, name: str, settings: LayoutSettings | None = None) -> Layout:
        name = _clean_name(name)
        settings = self._resolved(settings or LayoutSettings())
        with self._database.session() as session:
            self._check_name(session, name)
            row = LayoutRow(name=name, type="user", **settings.model_dump())
            session.add(row)
            session.flush()
            return self._layout(session, row)

    def update(
        self, layout_id: str, *, name: str | None = None, settings: LayoutSettings | None = None
    ) -> Layout:
        """Rename a user layout and/or replace its settings. Every brand using it follows."""
        if settings is not None:
            settings = self._resolved(settings)
        with self._database.session() as session:
            row = self._row(session, layout_id)
            self._check_editable(row)
            if name is not None:
                name = _clean_name(name)
                self._check_name(session, name, ignore=layout_id)
                row.name = name
            if settings is not None:
                for key, value in settings.model_dump().items():
                    setattr(row, key, value)
                row.canvas = session.get_one(CanvasRow, settings.canvas_id)
            session.flush()
            return self._layout(session, row)

    def change(self, layout_id: str, path: str, raw: str) -> Layout:
        """Change one setting from text, such as ``margin_top`` to ``120``."""
        layout = self.get(layout_id)
        if path == "canvas_id":
            settings = LayoutSettings(**{**self._settings(layout), "canvas_id": raw})
            return self.update(layout_id, settings=settings)
        if path not in SETTING_NAMES:
            raise LayoutInvalidError(f"Unknown setting: {path}")
        values = self._settings(layout)
        values[path] = _convert(raw, values[path], path)
        try:
            settings = LayoutSettings.model_validate(values)
        except ValidationError as error:
            raise LayoutInvalidError(f"{path}: {error.errors()[0]['msg']}") from None
        return self.update(layout_id, settings=settings)

    def duplicate(self, layout_id: str, name: str) -> Layout:
        """Copy any layout, built in or not, as a new user layout."""
        return self.create(name, LayoutSettings(**self._settings(self.get(layout_id))))

    def delete(self, layout_id: str) -> None:
        """Remove a user layout that no brand uses."""
        with self._database.session() as session:
            row = self._row(session, layout_id)
            self._check_editable(row)
            brands = self._users(session, layout_id)
            if brands:
                raise LayoutInUseError(
                    f'"{row.name}" is used by: {", ".join(brands)}. Choose another layout for '
                    "those brands first.",
                    brands,
                )
            session.delete(row)

    # Export and import

    def export_layout(self, layout_id: str) -> dict[str, Any]:
        """Return a self-contained, JSON-ready description of a layout, canvas included."""
        layout = self.get(layout_id)
        canvas = self._canvases.get(layout.canvas_id)
        return {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "name": layout.name,
            "canvas": {"name": canvas.name, "width": canvas.width, "height": canvas.height},
            **{key: getattr(layout, key) for key in SETTING_NAMES},
        }

    def import_layout(self, payload: dict[str, Any], *, name: str | None = None) -> Layout:
        """Add a layout from :meth:`export_layout` output. A taken name gets a number added."""
        if payload.get("format") != EXPORT_FORMAT:
            raise LayoutInvalidError("This is not a Kodalo layout file.")
        if payload.get("version") != EXPORT_VERSION:
            raise LayoutInvalidError("This layout file was made by a different version of Kodalo.")
        settings = self._settings_from(payload)
        return self.create(self.free_name(name or str(payload.get("name") or "Imported")), settings)

    def ensure(self, entry: object, default_name: str) -> str:
        """Return the id of the layout a brand file describes, creating it when none matches."""
        if not isinstance(entry, dict):
            raise LayoutInvalidError("The layout in the brand file is not valid.")
        settings = self._settings_from(entry)
        wanted = str(entry.get("name") or default_name)
        for layout in self.list_layouts():
            if layout.name.lower() == wanted.lower() and self._settings(layout) == (
                settings.model_dump()
            ):
                return layout.id
        return self.create(self.free_name(wanted), settings).id

    def free_name(self, wanted: str) -> str:
        """Return ``wanted``, or the first "wanted (2)", "wanted (3)"... that no layout uses."""
        base = _clean_name(wanted)
        taken = {lay.name.lower() for lay in self.list_layouts()}
        candidate, number = base, 1
        while candidate.lower() in taken:
            number += 1
            suffix = f" ({number})"
            candidate = base[: 64 - len(suffix)] + suffix
        return candidate

    # Helpers

    def _settings_from(self, entry: dict[str, Any]) -> LayoutSettings:
        """Settings from a file's fields; its ``canvas`` is matched or created."""
        values = {key: entry[key] for key in SETTING_NAMES if key in entry}
        canvas = entry.get("canvas")
        try:
            canvas_id = self._canvases.ensure(canvas) if canvas else LayoutSettings().canvas_id
            return LayoutSettings.model_validate({**values, "canvas_id": canvas_id})
        except CanvasError as error:
            raise LayoutInvalidError(
                f"The canvas in the layout file is not valid: {error}"
            ) from None
        except ValidationError:
            raise LayoutInvalidError("The settings in the layout file are not valid.") from None

    def _resolved(self, settings: LayoutSettings) -> LayoutSettings:
        """Return ``settings`` with the canvas given as an id; a canvas name is accepted too."""
        try:
            canvas = self._canvases.find(settings.canvas_id)
        except CanvasError:
            raise LayoutInvalidError("The layout refers to a canvas that does not exist.") from None
        return settings.model_copy(update={"canvas_id": canvas.id})

    @staticmethod
    def _settings(layout: Layout) -> dict[str, Any]:
        return {key: getattr(layout, key) for key in LayoutSettings.model_fields}

    @staticmethod
    def _check_editable(row: LayoutRow) -> None:
        if row.type == "system":
            raise LayoutReadOnlyError(
                f'"{row.name}" is built in and cannot be changed. Duplicate it to make your own.'
            )

    @staticmethod
    def _check_name(session: Session, name: str, ignore: str | None = None) -> None:
        rows = session.execute(select(LayoutRow.id, LayoutRow.name)).all()
        if any(r.name.lower() == name.lower() and r.id != ignore for r in rows):
            raise LayoutNameTakenError(f'A layout named "{name}" already exists.')

    @staticmethod
    def _row(session: Session, layout_id: str) -> LayoutRow:
        row = session.get(LayoutRow, layout_id)
        if row is None:
            raise LayoutNotFoundError("That layout does not exist.")
        return row

    @staticmethod
    def _users(session: Session, layout_id: str) -> list[str]:
        names = session.scalars(
            select(BrandProfile.name).where(BrandProfile.layout_id == layout_id)
        )
        return sorted(names, key=str.lower)

    @classmethod
    def _layout(cls, session: Session, row: LayoutRow) -> Layout:
        return Layout(
            id=row.id,
            name=row.name,
            type=row.type,  # type: ignore[arg-type]
            used_by=cls._users(session, row.id),
            created_at=row.created_at,
            updated_at=row.updated_at,
            **{key: getattr(row, key) for key in LayoutSettings.model_fields},
        )
