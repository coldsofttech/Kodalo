"""Shared layouts and a font catalogue.

Brands now point to a row of ``layouts`` (with a slide count) instead of owning a layout row, and
their fonts point to rows of ``fonts``. Existing data is carried over: each brand's layout becomes
a layout named "<Brand> layout", and each font family becomes a catalogue entry.

Revision ID: 0007
Revises: 0006

SQLite commits each schema change at once, so every step here skips what already exists, which
lets a second run finish a run that was cut short. ``brand_profiles`` is never rebuilt, because
that would cascade-delete the brand rows that refer to it.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

BUNDLED = (
    ("Inter", "sans"),
    ("Poppins", "sans"),
    ("Montserrat", "sans"),
    ("Source Sans 3", "sans"),
    ("Space Grotesk", "display"),
    ("Playfair Display", "serif"),
    ("Lora", "serif"),
    ("JetBrains Mono", "mono"),
    ("Fira Code", "mono"),
    ("IBM Plex Mono", "mono"),
)
FONT_SLOTS = ("body", "body_alt", "heading", "heading_alt", "mono", "mono_alt")
CANVAS = "system-instagram_portrait"
# name -> (align, density)
SYSTEM_LAYOUTS = {
    "Default": ("left", "regular"),
    "Compact": ("center", "compact"),
    "Spacious": ("left", "spacious"),
}
LAYOUT_FIELDS = (
    "canvas_id",
    "align",
    "corner_radius",
    "density",
    "footer_text",
    "margin_bottom",
    "margin_side",
    "margin_top",
    "slide_numbers",
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _table(name: str, connection: sa.Connection) -> sa.Table:
    return sa.Table(name, sa.MetaData(), autoload_with=connection)


def _create_fonts(connection: sa.Connection) -> None:
    if not sa.inspect(connection).has_table("fonts"):
        op.create_table(
            "fonts",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.Column("updated_at", sa.String(32), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("family", sa.String(100), nullable=False),
            sa.Column("category", sa.String(8), nullable=False),
            sa.Column("source", sa.String(8), nullable=False),
            sa.CheckConstraint("category IN ('sans', 'serif', 'display', 'mono')", name="category"),
            sa.CheckConstraint("source IN ('bundled', 'system')", name="source"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("uq_fonts_family", "fonts", ["family"], unique=True)
    fonts = _table("fonts", connection)
    have = {row[0] for row in connection.execute(sa.select(fonts.c.id))}
    now = _now()
    for family, category in BUNDLED:
        font_id = f"bundled-{family.lower().replace(' ', '_')}"
        if font_id not in have:
            connection.execute(
                fonts.insert().values(
                    id=font_id,
                    created_at=now,
                    updated_at=now,
                    family=family,
                    category=category,
                    source="bundled",
                )
            )


def _create_layouts(connection: sa.Connection) -> None:
    if not sa.inspect(connection).has_table("layouts"):
        op.create_table(
            "layouts",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.Column("updated_at", sa.String(32), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("type", sa.String(8), nullable=False),
            sa.Column("canvas_id", sa.String(36), nullable=False),
            sa.Column("align", sa.String(8), nullable=False),
            sa.Column("corner_radius", sa.Integer(), nullable=False),
            sa.Column("density", sa.String(8), nullable=False),
            sa.Column("footer_text", sa.String(120), nullable=False),
            sa.Column("margin_bottom", sa.Integer(), nullable=False),
            sa.Column("margin_side", sa.Integer(), nullable=False),
            sa.Column("margin_top", sa.Integer(), nullable=False),
            sa.Column("slide_numbers", sa.Boolean(), nullable=False),
            sa.Column("slides_count", sa.Integer(), nullable=False, server_default="6"),
            sa.CheckConstraint("type IN ('system', 'user')", name="type"),
            sa.CheckConstraint("align IN ('left', 'center')", name="align"),
            sa.CheckConstraint("density IN ('compact', 'regular', 'spacious')", name="density"),
            sa.ForeignKeyConstraint(["canvas_id"], ["canvases.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("uq_layouts_name", "layouts", ["name"], unique=True)
    layouts = _table("layouts", connection)
    have = {row[0] for row in connection.execute(sa.select(layouts.c.id))}
    now = _now()
    for name, (align, density) in SYSTEM_LAYOUTS.items():
        layout_id = f"system-{name.lower()}"
        if layout_id not in have:
            connection.execute(
                layouts.insert().values(
                    id=layout_id,
                    created_at=now,
                    updated_at=now,
                    name=name,
                    type="system",
                    canvas_id=CANVAS,
                    align=align,
                    corner_radius=24,
                    density=density,
                    footer_text="",
                    margin_bottom=96,
                    margin_side=80,
                    margin_top=96,
                    slide_numbers=True,
                    slides_count=6,
                )
            )


def _layout_name(brand: str, taken: set[str]) -> str:
    base = f"{brand} layout"[:64]
    candidate, number = base, 1
    while candidate.lower() in taken:
        number += 1
        suffix = f" ({number})"
        candidate = base[: 64 - len(suffix)] + suffix
    taken.add(candidate.lower())
    return candidate


def _move_layouts(connection: sa.Connection) -> None:
    inspector = sa.inspect(connection)
    if "layout_id" not in {c["name"] for c in inspector.get_columns("brand_profiles")}:
        op.execute(
            "ALTER TABLE brand_profiles ADD COLUMN layout_id VARCHAR(36) REFERENCES layouts (id)"
        )
    if not inspector.has_table("brand_layouts"):
        return
    layouts = _table("layouts", connection)
    old = _table("brand_layouts", connection)
    profiles = _table("brand_profiles", connection)
    taken = {row[0].lower() for row in connection.execute(sa.select(layouts.c.name))}
    now = _now()
    rows = connection.execute(
        sa.select(profiles.c.id, profiles.c.name, profiles.c.layout_id, old).select_from(
            profiles.join(old, old.c.profile_id == profiles.c.id)
        )
    ).mappings()
    for row in list(rows):
        if row["layout_id"]:
            continue
        layout_id = str(uuid.uuid4())
        values: dict[str, Any] = {field: row[field] for field in LAYOUT_FIELDS}
        connection.execute(
            layouts.insert().values(
                id=layout_id,
                created_at=now,
                updated_at=now,
                name=_layout_name(row["name"], taken),
                type="user",
                slides_count=6,
                **values,
            )
        )
        connection.execute(
            profiles.update().where(profiles.c.id == row["id"]).values(layout_id=layout_id)
        )
    connection.execute(
        profiles.update().where(profiles.c.layout_id.is_(None)).values(layout_id="system-default")
    )
    op.drop_table("brand_layouts")


def _font_id(connection: sa.Connection, fonts: sa.Table, family: str, source: str) -> str:
    found = connection.execute(
        sa.select(fonts.c.id).where(sa.func.lower(fonts.c.family) == family.lower())
    ).scalar()
    if found:
        return str(found)
    font_id, now = str(uuid.uuid4()), _now()
    connection.execute(
        fonts.insert().values(
            id=font_id,
            created_at=now,
            updated_at=now,
            family=family,
            category="sans",
            source="system" if source == "system" else "bundled",
        )
    )
    return font_id


def _move_fonts(connection: sa.Connection) -> None:
    inspector = sa.inspect(connection)
    if "body" not in {c["name"] for c in inspector.get_columns("brand_fonts")}:
        return
    fonts = _table("fonts", connection)
    old = _table("brand_fonts", connection)
    kept: list[dict[str, Any]] = []
    for row in list(connection.execute(sa.select(old)).mappings()):
        entry: dict[str, Any] = {
            key: row[key] for key in ("profile_id", "schema_version", "created_at", "updated_at")
        }
        for slot in FONT_SLOTS:
            entry[f"{slot}_id"] = _font_id(connection, fonts, row[slot], row[f"{slot}_source"])
        kept.append(entry)
    op.drop_table("brand_fonts")
    op.create_table(
        "brand_fonts",
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        *[sa.Column(f"{slot}_id", sa.String(36), nullable=False) for slot in FONT_SLOTS],
        *[sa.ForeignKeyConstraint([f"{slot}_id"], ["fonts.id"]) for slot in FONT_SLOTS],
        sa.ForeignKeyConstraint(["profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )
    if kept:
        connection.execute(_table("brand_fonts", connection).insert(), kept)


def upgrade() -> None:
    connection = op.get_bind()
    _create_fonts(connection)
    _create_layouts(connection)
    _move_layouts(connection)
    _move_fonts(connection)
