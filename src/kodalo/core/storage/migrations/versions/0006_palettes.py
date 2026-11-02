"""Palettes: a table of named color sets, with the three starter palettes built in.

Revision ID: 0006
Revises: 0005
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

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

# name -> (background, background_alt, primary, primary_alt, secondary, secondary_alt, text,
# text_alt), each as (light, dark).
SYSTEM = {
    "Midnight": (
        ("#ffffff", "#0b1020"),
        ("#f1f5f9", "#151b30"),
        ("#2563eb", "#60a5fa"),
        ("#1d4ed8", "#93c5fd"),
        ("#7c3aed", "#a78bfa"),
        ("#6d28d9", "#c4b5fd"),
        ("#111827", "#f3f4f6"),
        ("#0f172a", "#e5e7eb"),
    ),
    "Paper": (
        ("#faf7f2", "#1c1917"),
        ("#f0e9dd", "#292524"),
        ("#b45309", "#fbbf24"),
        ("#92400e", "#fcd34d"),
        ("#0f766e", "#5eead4"),
        ("#115e59", "#99f6e4"),
        ("#1c1917", "#f5f5f4"),
        ("#292524", "#e7e5e4"),
    ),
    "Graphite": (
        ("#ffffff", "#0a0a0a"),
        ("#f3f4f6", "#171717"),
        ("#111827", "#fafafa"),
        ("#374151", "#e5e5e5"),
        ("#6b7280", "#a3a3a3"),
        ("#4b5563", "#a3a3a3"),
        ("#111827", "#fafafa"),
        ("#111827", "#fafafa"),
    ),
}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("palettes"):
        op.create_table(
            "palettes",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.Column("updated_at", sa.String(32), nullable=False),
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("type", sa.String(8), nullable=False),
            *[
                sa.Column(f"{name}_{tone}", sa.String(7), nullable=False)
                for name in COLORS
                for tone in ("light", "dark")
            ],
            sa.CheckConstraint("type IN ('system', 'user')", name="type"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("uq_palettes_name", "palettes", ["name"], unique=True)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    table = sa.table(
        "palettes",
        sa.column("id", sa.String),
        sa.column("created_at", sa.String),
        sa.column("updated_at", sa.String),
        sa.column("name", sa.String),
        sa.column("type", sa.String),
        *[sa.column(f"{n}_{t}", sa.String) for n in COLORS for t in ("light", "dark")],
    )
    existing = {row[0] for row in op.get_bind().execute(sa.text("SELECT id FROM palettes"))}
    rows = []
    for name, pairs in SYSTEM.items():
        palette_id = f"system-{name.lower()}"
        if palette_id in existing:
            continue
        row = {
            "id": palette_id,
            "created_at": now,
            "updated_at": now,
            "name": name,
            "type": "system",
        }
        for color, (light, dark) in zip(COLORS, pairs, strict=True):
            row[f"{color}_light"], row[f"{color}_dark"] = light, dark
        rows.append(row)
    if rows:
        op.bulk_insert(table, rows)
