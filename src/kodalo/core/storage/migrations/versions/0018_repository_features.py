"""README analysis: the product features the AI groups from the capabilities.

Adds ``repository_features``. Like the migrations before it, this one skips what already exists.

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def _text(name: str, size: int, default: str = "") -> sa.Column[str]:
    return sa.Column(name, sa.String(size), nullable=False, server_default=default)


def upgrade() -> None:
    if "repository_features" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "repository_features",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column(
            "repository_id",
            sa.String(36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(128), nullable=False),
        _text("description", 512),
        _text("file", 1024),
        _text("quote", 128),
        _text("status", 16, "inferred"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id", name="pk_repository_features"),
    )


def downgrade() -> None:
    op.drop_table("repository_features")
