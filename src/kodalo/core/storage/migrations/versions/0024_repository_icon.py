"""Repository icon: the files that may be it, the one picked and when it was looked for.

Adds four columns to ``repositories``. Like the migrations before it, this one skips what already
exists.

Revision ID: 0024
Revises: 0023
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("icon_candidates_json", sa.Text(), False, "[]"),
    ("icon_path", sa.String(1024), False, ""),
    ("icon_ext", sa.String(8), False, ""),
    ("icon_checked_at", sa.String(32), True, None),
)


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("repositories")}
    for name, kind, nullable, default in _COLUMNS:
        if name not in existing:
            op.add_column(
                "repositories",
                sa.Column(name, kind, nullable=nullable, server_default=default),
            )


def downgrade() -> None:
    with op.batch_alter_table("repositories") as batch:
        for name, *_ in _COLUMNS:
            batch.drop_column(name)
