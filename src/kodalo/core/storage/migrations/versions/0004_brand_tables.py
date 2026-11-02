"""Brand profiles: split ``data_json`` into canvases and one table each for colors, fonts, layouts
and logos, copying the data of existing profiles.

Revision ID: 0004
Revises: 0003

SQLite commits each schema change at once, so a run that was cut short can leave new tables in
place while ``data_json`` still exists. A rerun therefore starts over from those tables, and does
nothing once ``data_json`` is gone.
"""

import json
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SYSTEM_CANVASES: dict[str, tuple[int, int]] = {
    "instagram_portrait": (1080, 1350),
    "instagram_square": (1080, 1080),
    "instagram_story": (1080, 1920),
    "linkedin_landscape": (1200, 627),
    "x_landscape": (1600, 900),
}
COLORS = (
    "background",
    "background_alt",
    "primary",
    "primary_alt",
    "secondary",
    "secondary_alt",
    "text",
    "text_alt",
)
FONTS = ("body", "body_alt", "heading", "heading_alt", "mono", "mono_alt")
FALLBACK_LIGHT, FALLBACK_DARK, FALLBACK_FONT = "#ffffff", "#000000", "Inter"
SOURCES = "IN ('bundled', 'system')"
POSITIONS = (
    "IN ('top_left', 'top_center', 'top_right', 'bottom_left', 'bottom_center', 'bottom_right')"
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _part() -> list[sa.Column[Any]]:
    return [
        sa.Column("profile_id", sa.String(36), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
    ]


def _create_tables() -> None:
    op.create_table(
        "canvases",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("preset", sa.String(32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(8), nullable=False),
        sa.CheckConstraint("type IN ('system', 'user')", name="type"),
        sa.PrimaryKeyConstraint("id"),
    )
    color_columns = [
        sa.Column(f"{name}_{tone}", sa.String(7), nullable=False)
        for name in COLORS
        for tone in ("light", "dark")
    ]
    op.create_table(
        "brand_colors",
        *_part(),
        *color_columns,
        sa.ForeignKeyConstraint(["profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )
    font_columns: list[sa.Column[Any]] = []
    for name in FONTS:
        font_columns.append(sa.Column(name, sa.String(100), nullable=False))
        font_columns.append(sa.Column(f"{name}_source", sa.String(8), nullable=False))
    op.create_table(
        "brand_fonts",
        *_part(),
        *font_columns,
        sa.CheckConstraint(" AND ".join(f"{n}_source {SOURCES}" for n in FONTS), name="source"),
        sa.ForeignKeyConstraint(["profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )
    op.create_table(
        "brand_layouts",
        *_part(),
        sa.Column("canvas_id", sa.String(36), nullable=False),
        sa.Column("align", sa.String(8), nullable=False),
        sa.Column("corner_radius", sa.Integer(), nullable=False),
        sa.Column("density", sa.String(8), nullable=False),
        sa.Column("footer_text", sa.String(120), nullable=False),
        sa.Column("margin_bottom", sa.Integer(), nullable=False),
        sa.Column("margin_side", sa.Integer(), nullable=False),
        sa.Column("margin_top", sa.Integer(), nullable=False),
        sa.Column("slide_numbers", sa.Boolean(), nullable=False),
        sa.CheckConstraint("align IN ('left', 'center')", name="align"),
        sa.CheckConstraint("density IN ('compact', 'regular', 'spacious')", name="density"),
        sa.ForeignKeyConstraint(["canvas_id"], ["canvases.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )
    op.create_table(
        "brand_logos",
        *_part(),
        sa.Column("file", sa.String(64), nullable=True),
        sa.Column("dark_file", sa.String(64), nullable=True),
        sa.Column("padding", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(16), nullable=False),
        sa.Column("show_on", sa.String(8), nullable=False),
        sa.Column("size_percent", sa.Integer(), nullable=False),
        sa.CheckConstraint(f"position {POSITIONS}", name="position"),
        sa.CheckConstraint("show_on IN ('all', 'first', 'last')", name="show_on"),
        sa.ForeignKeyConstraint(["profile_id"], ["brand_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
    )


def _table(name: str, connection: sa.Connection) -> sa.Table:
    return sa.Table(name, sa.MetaData(), autoload_with=connection)


def _canvas_id(connection: sa.Connection, canvases: sa.Table, canvas: dict[str, Any]) -> str:
    preset = str(canvas.get("preset", "instagram_portrait"))
    width, height = int(canvas.get("width", 1080)), int(canvas.get("height", 1350))
    if preset in SYSTEM_CANVASES:
        return f"system-{preset}"
    found = connection.execute(
        sa.select(canvases.c.id).where(
            canvases.c.type == "user", canvases.c.width == width, canvases.c.height == height
        )
    ).scalar()
    if found:
        return str(found)
    new_id = f"user-{width}x{height}"
    now = _now()
    connection.execute(
        canvases.insert().values(
            id=new_id,
            created_at=now,
            updated_at=now,
            preset="custom",
            width=width,
            height=height,
            type="user",
        )
    )
    return new_id


def _copy_profiles(connection: sa.Connection) -> None:
    profiles = _table("brand_profiles", connection)
    canvases, colors = _table("canvases", connection), _table("brand_colors", connection)
    fonts, layouts = _table("brand_fonts", connection), _table("brand_layouts", connection)
    logos = _table("brand_logos", connection)
    now = _now()
    for profile_id, raw in connection.execute(sa.select(profiles.c.id, profiles.c.data_json)):
        try:
            data = json.loads(raw)
        except ValueError:
            data = {}
        data = data if isinstance(data, dict) else {}
        base = {"profile_id": profile_id, "created_at": now, "updated_at": now}
        color_values: dict[str, Any] = {}
        for name in COLORS:
            pair = data.get("colors", {}).get(name, {})
            color_values[f"{name}_light"] = pair.get("light", FALLBACK_LIGHT)
            color_values[f"{name}_dark"] = pair.get("dark", FALLBACK_DARK)
        connection.execute(colors.insert().values(**base, **color_values))
        font_values: dict[str, Any] = {}
        for name in FONTS:
            ref = data.get("fonts", {}).get(name, {})
            font_values[name] = ref.get("family", FALLBACK_FONT)
            font_values[f"{name}_source"] = ref.get("source", "bundled")
        connection.execute(fonts.insert().values(**base, **font_values))
        layout = data.get("layout", {})
        connection.execute(
            layouts.insert().values(
                **base,
                canvas_id=_canvas_id(connection, canvases, layout.get("canvas", {})),
                align=layout.get("align", "left"),
                corner_radius=layout.get("corner_radius", 24),
                density=layout.get("density", "regular"),
                footer_text=layout.get("footer_text", ""),
                margin_bottom=layout.get("margin_bottom", 96),
                margin_side=layout.get("margin_side", 80),
                margin_top=layout.get("margin_top", 96),
                slide_numbers=layout.get("slide_numbers", True),
            )
        )
        logo = data.get("logo", {})
        connection.execute(
            logos.insert().values(
                **base,
                file=logo.get("file"),
                dark_file=logo.get("dark_file"),
                padding=logo.get("padding", 48),
                position=logo.get("position", "top_left"),
                show_on=logo.get("show_on", "all"),
                size_percent=logo.get("size_percent", 14),
            )
        )


NEW_TABLES = ("brand_logos", "brand_layouts", "brand_fonts", "brand_colors", "canvases")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "data_json" not in {c["name"] for c in inspector.get_columns("brand_profiles")}:
        return
    for table in NEW_TABLES:
        if inspector.has_table(table):
            op.drop_table(table)
    _create_tables()
    canvases = _table("canvases", connection)
    now = _now()
    connection.execute(
        canvases.insert(),
        [
            {
                "id": f"system-{preset}",
                "created_at": now,
                "updated_at": now,
                "schema_version": 1,
                "preset": preset,
                "width": width,
                "height": height,
                "type": "system",
            }
            for preset, (width, height) in SYSTEM_CANVASES.items()
        ],
    )
    _copy_profiles(connection)
    # Not a batch change: rebuilding brand_profiles would cascade-delete the rows just copied.
    op.execute("ALTER TABLE brand_profiles DROP COLUMN data_json")
