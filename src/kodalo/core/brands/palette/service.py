"""Create, change, copy, delete, export and import palettes of brand colors."""

from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from kodalo.core.brands.brand.models import BrandColors, ColorPair
from kodalo.core.brands.palette.errors import (
    PaletteInvalidError,
    PaletteNameTakenError,
    PaletteNotFoundError,
    PaletteReadOnlyError,
)
from kodalo.core.brands.palette.models import Palette, PaletteName
from kodalo.core.storage import Database
from kodalo.core.storage.models import PaletteRow

EXPORT_FORMAT = "kodalo-palette"
EXPORT_VERSION = 1
_NAME = TypeAdapter(PaletteName)
_COLOR_NAMES = tuple(BrandColors.model_fields)
_TONES = ("light", "dark")


def _clean_name(name: str) -> str:
    try:
        return _NAME.validate_python(name)
    except ValidationError:
        raise PaletteInvalidError("A palette name must be 1 to 64 characters.") from None


def _values(colors: BrandColors) -> dict[str, str]:
    return {
        f"{name}_{tone}": getattr(getattr(colors, name), tone)
        for name in _COLOR_NAMES
        for tone in _TONES
    }


class PaletteService:
    """Palettes kept in the local database. Built-in (``system``) palettes are read-only."""

    def __init__(self, database: Database) -> None:
        self._database = database

    # Reading

    def list_palettes(self) -> list[Palette]:
        """Return every palette: built-in ones first, then the user's, each sorted by name."""
        with self._database.session() as session:
            palettes = [self._palette(row) for row in session.scalars(select(PaletteRow))]
        return sorted(palettes, key=lambda p: (p.type != "system", p.name.lower()))

    def get(self, palette_id: str) -> Palette:
        with self._database.session() as session:
            return self._palette(self._row(session, palette_id))

    def find(self, reference: str) -> Palette:
        """Return the palette whose id or name (ignoring case) matches ``reference``.

        A built-in palette's old short key, such as ``midnight``, matches too.
        """
        wanted = reference.strip().lower()
        for palette in self.list_palettes():
            short = palette.id.removeprefix("system-") if palette.type == "system" else None
            if wanted in (palette.id.lower(), palette.name.lower(), short):
                return palette
        raise PaletteNotFoundError(f'No palette named "{reference}".')

    # Changing

    def create(self, name: str, colors: BrandColors) -> Palette:
        name = _clean_name(name)
        with self._database.session() as session:
            self._check_name(session, name)
            row = PaletteRow(name=name, type="user", **_values(colors))
            session.add(row)
            session.flush()
            return self._palette(row)

    def update(
        self, palette_id: str, *, name: str | None = None, colors: BrandColors | None = None
    ) -> Palette:
        """Rename a user palette and/or replace its colors."""
        with self._database.session() as session:
            row = self._row(session, palette_id)
            self._check_editable(row)
            if name is not None:
                name = _clean_name(name)
                self._check_name(session, name, ignore=palette_id)
                row.name = name
            if colors is not None:
                for key, value in _values(colors).items():
                    setattr(row, key, value)
            session.flush()
            return self._palette(row)

    def set_color(self, palette_id: str, path: str, value: str) -> Palette:
        """Change one color of a user palette; ``path`` is ``NAME.light`` or ``NAME.dark``."""
        tree = self.get(palette_id).colors.model_dump()
        name, _, tone = path.partition(".")
        if name not in tree or tone not in _TONES:
            raise PaletteInvalidError(
                f"Unknown color: {path}. Use NAME.light or NAME.dark, such as primary.light."
            )
        tree[name][tone] = value
        try:
            colors = BrandColors.model_validate(tree)
        except ValidationError:
            raise PaletteInvalidError(f"{path} must be a color like #2563eb.") from None
        return self.update(palette_id, colors=colors)

    def duplicate(self, palette_id: str, name: str) -> Palette:
        """Copy any palette, built in or not, as a new user palette."""
        return self.create(name, self.get(palette_id).colors)

    def delete(self, palette_id: str) -> None:
        """Remove a user palette. Brands made from it keep their colors."""
        with self._database.session() as session:
            row = self._row(session, palette_id)
            self._check_editable(row)
            session.delete(row)

    # Export and import

    def export_palette(self, palette_id: str) -> dict[str, Any]:
        """Return a self-contained, JSON-ready description of a palette."""
        palette = self.get(palette_id)
        return {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "name": palette.name,
            "colors": palette.colors.model_dump(mode="json"),
        }

    def import_palette(self, payload: dict[str, Any], *, name: str | None = None) -> Palette:
        """Add a palette from :meth:`export_palette` output. A taken name gets a number added."""
        if payload.get("format") != EXPORT_FORMAT:
            raise PaletteInvalidError("This is not a Kodalo palette file.")
        if payload.get("version") != EXPORT_VERSION:
            raise PaletteInvalidError(
                "This palette file was made by a different version of Kodalo."
            )
        try:
            colors = BrandColors.model_validate(payload.get("colors"))
        except ValidationError:
            raise PaletteInvalidError("The colors in the palette file are not valid.") from None
        return self.create(self._free_name(name or str(payload.get("name") or "Imported")), colors)

    # Helpers

    def _free_name(self, wanted: str) -> str:
        base = _clean_name(wanted)
        taken = {p.name.lower() for p in self.list_palettes()}
        candidate, number = base, 1
        while candidate.lower() in taken:
            number += 1
            suffix = f" ({number})"
            candidate = base[: 64 - len(suffix)] + suffix
        return candidate

    @staticmethod
    def _check_editable(row: PaletteRow) -> None:
        if row.type == "system":
            raise PaletteReadOnlyError(
                f'"{row.name}" is built in and cannot be changed. Duplicate it to make your own.'
            )

    @staticmethod
    def _check_name(session: Session, name: str, ignore: str | None = None) -> None:
        rows = session.execute(select(PaletteRow.id, PaletteRow.name)).all()
        if any(r.name.lower() == name.lower() and r.id != ignore for r in rows):
            raise PaletteNameTakenError(f'A palette named "{name}" already exists.')

    @staticmethod
    def _row(session: Session, palette_id: str) -> PaletteRow:
        row = session.get(PaletteRow, palette_id)
        if row is None:
            raise PaletteNotFoundError("That palette does not exist.")
        return row

    @staticmethod
    def _palette(row: PaletteRow) -> Palette:
        colors = BrandColors(
            **{
                name: ColorPair(
                    light=getattr(row, f"{name}_light"), dark=getattr(row, f"{name}_dark")
                )
                for name in _COLOR_NAMES
            }
        )
        return Palette(
            id=row.id,
            name=row.name,
            type=row.type,  # type: ignore[arg-type]
            colors=colors,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
