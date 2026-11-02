"""The font catalogue: the fonts brands can use, kept in the database.

Bundled fonts are seeded by a migration. Installed fonts are added the first time they are listed
or chosen, so a brand can always point to a catalogue row.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kodalo.core.brand.fonts import FontInfo, available_fonts, bundled_fonts
from kodalo.core.brand.models import FontRef
from kodalo.core.storage import Database
from kodalo.core.storage.models import FontRow


class FontCatalogue:
    """Fonts kept in the local database."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def list_fonts(self, *, system: bool = True) -> list[FontInfo]:
        """Return bundled fonts first, then installed ones (unless ``system`` is false).

        Installed fonts that are not in the catalogue yet are added to it.
        """
        with self._database.session() as session:
            if system:
                for info in available_fonts():
                    self._ensure(session, info.family, info.source, info.category)
            else:
                for info in bundled_fonts():
                    self._ensure(session, info.family, info.source, info.category)
            rows = session.scalars(select(FontRow)).all()
            wanted = {i.family.lower() for i in (available_fonts() if system else bundled_fonts())}
            fonts = [
                FontInfo(r.family, r.category, r.source)  # type: ignore[arg-type]
                for r in rows
                if r.family.lower() in wanted
            ]
        order = {b.family.lower(): n for n, b in enumerate(bundled_fonts())}
        return sorted(
            fonts,
            key=lambda f: (f.source != "bundled", order.get(f.family.lower(), 0), f.family.lower()),
        )

    @staticmethod
    def find_row(session: Session, family: str) -> FontRow | None:
        return session.scalars(
            select(FontRow).where(func.lower(FontRow.family) == family.lower())
        ).first()

    def row_for(self, session: Session, ref: FontRef) -> FontRow:
        """Return the catalogue row for a font reference, adding it when it is new."""
        row = self.find_row(session, ref.family)
        if row is not None:
            return row
        category = next(
            (i.category for i in available_fonts() if i.family.lower() == ref.family.lower()),
            "sans",
        )
        return self._ensure(session, ref.family, ref.source, category)

    def _ensure(self, session: Session, family: str, source: str, category: str) -> FontRow:
        row = self.find_row(session, family)
        if row is None:
            row = FontRow(family=family, source=source, category=category)
            session.add(row)
            session.flush()
        return row
