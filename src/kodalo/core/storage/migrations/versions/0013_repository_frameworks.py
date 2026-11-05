"""Frameworks found in a repository.

Adds the ``repository_frameworks`` table. Like the migrations before it, this one skips what
already exists.

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("repository_frameworks"):
        return
    op.create_table(
        "repository_frameworks",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column("repository_id", sa.String(36), nullable=False),
        sa.Column("framework_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("evidence", sa.String(128), nullable=False),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "framework_id"),
    )


def downgrade() -> None:
    op.drop_table("repository_frameworks")
