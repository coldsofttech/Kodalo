"""README analysis: a feature's importance, maturity, risky claims and linked use cases.

Adds four columns to ``repository_features``. Like the migrations before it, this one skips what
already exists.

Revision ID: 0019
Revises: 0018
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("importance", sa.String(16), "supporting"),
    ("maturity", sa.String(16), "unspecified"),
    ("claims_json", sa.Text(), "[]"),
    ("use_cases_json", sa.Text(), "[]"),
)


def upgrade() -> None:
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("repository_features")}
    for name, kind, default in _COLUMNS:
        if name not in existing:
            op.add_column(
                "repository_features",
                sa.Column(name, kind, nullable=False, server_default=default),
            )


def downgrade() -> None:
    with op.batch_alter_table("repository_features") as batch:
        for name, _, _ in _COLUMNS:
            batch.drop_column(name)
