"""Create, change, copy, delete, export and import brand profiles."""

import base64
import binascii
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from kodalo.core.brand.contrast import ContrastResult, check_colors
from kodalo.core.brand.errors import (
    BrandInvalidError,
    BrandNameTakenError,
    BrandNotFoundError,
)
from kodalo.core.brand.logos import LogoStore
from kodalo.core.brand.models import Brand, BrandData, ProfileName
from kodalo.core.brand.palettes import starter_brand
from kodalo.core.storage import Database
from kodalo.core.storage.models import BrandProfile

EXPORT_FORMAT = "kodalo-brand"
EXPORT_VERSION = 1
_NAME = TypeAdapter(ProfileName)


def _problems(error: ValidationError) -> list[str]:
    return [
        f"{'.'.join(str(part) for part in item['loc']) or 'value'}: {item['msg']}"
        for item in error.errors()
    ]


def _clean_name(name: str) -> str:
    try:
        return _NAME.validate_python(name)
    except ValidationError:
        raise BrandInvalidError("A brand name must be 1 to 64 characters.") from None


def _logo_names(data: BrandData) -> set[str]:
    return {name for name in (data.logo.file, data.logo.dark_file) if name}


class BrandService:
    """Brand profiles kept in the local database, with their logo files in ``data_dir``."""

    def __init__(self, database: Database, data_dir: Path) -> None:
        self._database = database
        self.logos = LogoStore(data_dir)

    # Reading

    def list_brands(self) -> list[Brand]:
        """Return every profile, sorted by name."""
        with self._database.session() as session:
            rows = session.scalars(select(BrandProfile)).all()
            return sorted((self._brand(row) for row in rows), key=lambda b: b.name.lower())

    def get(self, brand_id: str) -> Brand:
        with self._database.session() as session:
            return self._brand(self._row(session, brand_id))

    def find(self, reference: str) -> Brand:
        """Return the profile whose id or name (ignoring case) matches ``reference``."""
        wanted = reference.strip().lower()
        for brand in self.list_brands():
            if brand.id.lower() == wanted or brand.name.lower() == wanted:
                return brand
        raise BrandNotFoundError(f'No brand named "{reference}".')

    def default(self) -> Brand | None:
        """Return the default profile, or ``None`` when there are no profiles."""
        with self._database.session() as session:
            row = session.scalars(select(BrandProfile).where(BrandProfile.is_default)).first()
            return self._brand(row) if row else None

    # Changing

    def create(self, name: str, data: BrandData | None = None) -> Brand:
        """Add a profile. The first profile becomes the default."""
        name = _clean_name(name)
        data = data or starter_brand()
        self._check_logos(data)
        with self._database.session() as session:
            self._check_name(session, name)
            first = session.scalars(select(BrandProfile.id)).first() is None
            row = BrandProfile(name=name, is_default=first, data_json=data.model_dump_json())
            session.add(row)
            session.flush()
            return self._brand(row)

    def update(
        self, brand_id: str, *, name: str | None = None, data: BrandData | None = None
    ) -> Brand:
        """Rename a profile and/or replace its data. Logo files no longer used are removed."""
        if data is not None:
            self._check_logos(data)
        with self._database.session() as session:
            row = self._row(session, brand_id)
            previous = _logo_names(self._data(row))
            if name is not None:
                name = _clean_name(name)
                self._check_name(session, name, ignore=brand_id)
                row.name = name
            if data is not None:
                row.data_json = data.model_dump_json()
            session.flush()
            current = _logo_names(self._data(row))
            brand = self._brand(row)
        for stale in previous - current:
            self.logos.delete(stale)
        return brand

    def set_default(self, brand_id: str) -> Brand:
        with self._database.session() as session:
            row = self._row(session, brand_id)
            session.execute(update(BrandProfile).values(is_default=False))
            row.is_default = True
            session.flush()
            session.refresh(row)
            return self._brand(row)

    def duplicate(self, brand_id: str, name: str) -> Brand:
        """Copy a profile, including its logo files, under a new name. The copy is not default."""
        name = _clean_name(name)
        source = self.get(brand_id)
        data = source.data.model_copy(deep=True)
        data.logo.file = self._copy_logo(data.logo.file)
        data.logo.dark_file = self._copy_logo(data.logo.dark_file)
        try:
            return self.create(name, data)
        except Exception:
            self.logos.delete(data.logo.file)
            self.logos.delete(data.logo.dark_file)
            raise

    def delete(self, brand_id: str) -> None:
        """Remove a profile and its logo files. If it was the default, another becomes default."""
        with self._database.session() as session:
            row = self._row(session, brand_id)
            files = _logo_names(self._data(row))
            was_default = row.is_default
            session.delete(row)
            session.flush()
            if was_default:
                successor = session.scalars(
                    select(BrandProfile).order_by(BrandProfile.created_at)
                ).first()
                if successor is not None:
                    successor.is_default = True
        for name in files:
            self.logos.delete(name)

    # Logos

    def set_logo(self, brand_id: str, content: bytes, *, dark: bool = False) -> Brand:
        """Store a logo file and attach it as the profile's light (or dark) logo."""
        brand = self.get(brand_id)
        name = self.logos.save(content)
        data = brand.data.model_copy(deep=True)
        if dark:
            data.logo.dark_file = name
        else:
            data.logo.file = name
        try:
            return self.update(brand_id, data=data)
        except Exception:
            self.logos.delete(name)
            raise

    def remove_logo(self, brand_id: str, *, dark: bool = False) -> Brand:
        data = self.get(brand_id).data.model_copy(deep=True)
        if dark:
            data.logo.dark_file = None
        else:
            data.logo.file = None
        return self.update(brand_id, data=data)

    # Checks

    @staticmethod
    def contrast(data: BrandData) -> list[ContrastResult]:
        """Check the colors of a brand; failing results have ``passes == False``."""
        return check_colors(data.colors)

    # Export and import

    def export_profile(self, brand_id: str) -> dict[str, Any]:
        """Return a self-contained, JSON-ready description of a profile, logos included."""
        brand = self.get(brand_id)
        logos: dict[str, dict[str, str]] = {}
        for name in _logo_names(brand.data):
            content = self.logos.read(name)
            logos[name] = {"content_base64": base64.b64encode(content).decode("ascii")}
        return {
            "format": EXPORT_FORMAT,
            "version": EXPORT_VERSION,
            "name": brand.name,
            "data": brand.data.model_dump(mode="json"),
            "logos": logos,
        }

    def import_profile(self, payload: dict[str, Any], *, name: str | None = None) -> Brand:
        """Add a profile from :meth:`export_profile` output. A taken name gets a number added."""
        if payload.get("format") != EXPORT_FORMAT:
            raise BrandInvalidError("This is not a Kodalo brand file.")
        if payload.get("version") != EXPORT_VERSION:
            raise BrandInvalidError("This brand file was made by a different version of Kodalo.")
        try:
            data = BrandData.model_validate(payload.get("data"))
        except ValidationError as error:
            raise BrandInvalidError("The brand file is not valid.", _problems(error)) from None
        raw_logos = payload.get("logos")
        files = raw_logos if isinstance(raw_logos, dict) else {}
        stored: dict[str, str] = {}
        try:
            for old in _logo_names(data):
                stored[old] = self._import_logo(files.get(old))
            data.logo.file = stored.get(data.logo.file or "")
            data.logo.dark_file = stored.get(data.logo.dark_file or "")
            return self.create(
                self._free_name(name or str(payload.get("name") or "Imported")), data
            )
        except Exception:
            for new in stored.values():
                self.logos.delete(new)
            raise

    # Helpers

    def _import_logo(self, entry: object) -> str:
        encoded = entry.get("content_base64") if isinstance(entry, dict) else None
        if not isinstance(encoded, str):
            raise BrandInvalidError("The brand file refers to a logo it does not contain.")
        try:
            content = base64.b64decode(encoded, validate=True)
        except binascii.Error:
            raise BrandInvalidError("A logo in the brand file is not valid.") from None
        return self.logos.save(content)

    def _copy_logo(self, name: str | None) -> str | None:
        return self.logos.save(self.logos.read(name)) if name else None

    def _check_logos(self, data: BrandData) -> None:
        for name in _logo_names(data):
            if not self.logos.exists(name):
                raise BrandInvalidError("The brand refers to a logo file that does not exist.")

    def _free_name(self, wanted: str) -> str:
        base = _clean_name(wanted)
        taken = {b.name.lower() for b in self.list_brands()}
        candidate, number = base, 1
        while candidate.lower() in taken:
            number += 1
            suffix = f" ({number})"
            candidate = base[: 64 - len(suffix)] + suffix
        return candidate

    @staticmethod
    def _check_name(session: Session, name: str, ignore: str | None = None) -> None:
        rows = session.execute(select(BrandProfile.id, BrandProfile.name)).all()
        if any(row.name.lower() == name.lower() and row.id != ignore for row in rows):
            raise BrandNameTakenError(f'A brand named "{name}" already exists.')

    @staticmethod
    def _row(session: Session, brand_id: str) -> BrandProfile:
        row = session.get(BrandProfile, brand_id)
        if row is None:
            raise BrandNotFoundError("That brand does not exist.")
        return row

    @staticmethod
    def _data(row: BrandProfile) -> BrandData:
        return BrandData.model_validate_json(row.data_json)

    def _brand(self, row: BrandProfile) -> Brand:
        return Brand(
            id=row.id,
            name=row.name,
            is_default=row.is_default,
            data=self._data(row),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
