"""Social platforms: the networks a canvas is made for, and the sizes each one recommends.

Revision ID: 0021
Revises: 0020

Seeds Instagram (with its three sizes) and Custom (no sizes). Canvases get a ``platform_id``: the
built-in Instagram canvases use Instagram, every other canvas uses Custom. The column is added in
place, as in 0005, because rebuilding ``canvases`` would fail while layouts refer to it; SQLite
only accepts a foreign key column that can be NULL, so it is, though Kodalo never writes NULL.
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

PLATFORMS = {"instagram": "Instagram", "custom": "Custom"}
SIZES = (
    ("instagram", "Portrait", 1080, 1350),
    ("instagram", "Square", 1080, 1080),
    ("instagram", "Story", 1080, 1920),
)
INSTAGRAM_CANVASES = (
    "system-instagram_portrait",
    "system-instagram_square",
    "system-instagram_story",
)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    if "social_platforms" not in tables:
        op.create_table(
            "social_platforms",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.Column("updated_at", sa.String(32), nullable=False),
            sa.Column("name", sa.String(64), nullable=False),
        )
        op.create_index("uq_social_platforms_name", "social_platforms", ["name"], unique=True)
        now = _now()
        for key, name in PLATFORMS.items():
            connection.execute(
                sa.text(
                    "INSERT INTO social_platforms (id, created_at, updated_at, name) "
                    "VALUES (:id, :now, :now, :name)"
                ),
                {"id": key, "now": now, "name": name},
            )
    if "social_platform_sizes" not in tables:
        op.create_table(
            "social_platform_sizes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.Column("updated_at", sa.String(32), nullable=False),
            sa.Column(
                "platform_id",
                sa.String(36),
                sa.ForeignKey("social_platforms.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("width", sa.Integer(), nullable=False),
            sa.Column("height", sa.Integer(), nullable=False),
            sa.UniqueConstraint("platform_id", "width", "height"),
        )
        now = _now()
        for platform, name, width, height in SIZES:
            connection.execute(
                sa.text(
                    "INSERT INTO social_platform_sizes "
                    "(id, created_at, updated_at, platform_id, name, width, height) "
                    "VALUES (:id, :now, :now, :platform, :name, :width, :height)"
                ),
                {
                    "id": f"{platform}-{name.lower()}",
                    "now": now,
                    "platform": platform,
                    "name": name,
                    "width": width,
                    "height": height,
                },
            )
    columns = {c["name"] for c in inspector.get_columns("canvases")}
    if "platform_id" not in columns:
        op.execute(
            "ALTER TABLE canvases ADD COLUMN platform_id VARCHAR(36) "
            "REFERENCES social_platforms (id)"
        )
    op.execute("UPDATE canvases SET platform_id = 'custom' WHERE platform_id IS NULL")
    for canvas in INSTAGRAM_CANVASES:
        connection.execute(
            sa.text("UPDATE canvases SET platform_id = 'instagram' WHERE id = :id"),
            {"id": canvas},
        )


def downgrade() -> None:
    with op.batch_alter_table("canvases") as batch:
        batch.drop_column("platform_id")
    op.drop_table("social_platform_sizes")
    op.drop_index("uq_social_platforms_name", table_name="social_platforms")
    op.drop_table("social_platforms")
