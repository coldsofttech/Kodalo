"""Canvases: give each a unique name and drop the preset column.

Revision ID: 0005
Revises: 0004

No batch change here: rebuilding ``canvases`` while ``brand_layouts`` refers to it would fail, so
the column is added and dropped in place. A run that was cut short is finished by the next one.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SYSTEM_NAMES = {
    "instagram_portrait": "Instagram portrait",
    "instagram_square": "Instagram square",
    "instagram_story": "Instagram story",
    "linkedin_landscape": "LinkedIn landscape",
    "x_landscape": "X landscape",
}


def _name(row: sa.Row[tuple[str, str, int, int, str]], taken: set[str]) -> str:
    base = SYSTEM_NAMES.get(row.preset) if row.type == "system" else None
    base = base or f"Custom {row.width}x{row.height}"
    candidate, number = base, 1
    while candidate.lower() in taken:
        number += 1
        candidate = f"{base} ({number})"
    taken.add(candidate.lower())
    return candidate


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {c["name"] for c in inspector.get_columns("canvases")}
    if "name" not in columns:
        op.add_column(
            "canvases", sa.Column("name", sa.String(64), nullable=False, server_default="")
        )
    if "preset" in columns:
        taken: set[str] = set()
        rows = connection.execute(
            sa.text("SELECT id, preset, width, height, type FROM canvases ORDER BY type, id")
        ).all()
        for row in rows:
            connection.execute(
                sa.text("UPDATE canvases SET name = :name WHERE id = :id"),
                {"name": _name(row, taken), "id": row.id},
            )
    if "uq_canvases_name" not in {i["name"] for i in inspector.get_indexes("canvases")}:
        op.create_index("uq_canvases_name", "canvases", ["name"], unique=True)
    if "preset" in columns:
        op.execute("ALTER TABLE canvases DROP COLUMN preset")
