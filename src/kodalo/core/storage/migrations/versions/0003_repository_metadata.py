"""Repositories: full metadata, structure and warnings, and a table of languages.

Revision ID: 0003
Revises: 0002

SQLite commits each schema change at once, so a run that was cut short can leave some columns in
place while the version is still 0002. Every step here therefore skips what already exists, which
lets a second run finish the job.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_COLUMNS: list[sa.Column[Any]] = [
    sa.Column("homepage", sa.String(512), nullable=False, server_default=""),
    sa.Column("license", sa.String(128), nullable=True),
    sa.Column("topics_json", sa.Text(), nullable=False, server_default="[]"),
    sa.Column("is_fork", sa.Boolean(), nullable=False, server_default="0"),
    sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
    sa.Column("last_pushed_at", sa.String(40), nullable=True),
    sa.Column("access_method", sa.String(16), nullable=False, server_default=""),
    sa.Column("tree_truncated", sa.Boolean(), nullable=False, server_default="0"),
    sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("structure_json", sa.Text(), nullable=False, server_default="[]"),
    sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
    sa.Column("local_path", sa.String(1024), nullable=False, server_default=""),
]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    present = {column["name"] for column in inspector.get_columns("repositories")}
    for column in _COLUMNS:
        if column.name not in present:
            op.add_column("repositories", column)
    if not inspector.has_table("repository_languages"):
        op.create_table(
            "repository_languages",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.Column("updated_at", sa.String(32), nullable=False),
            sa.Column("repository_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("bytes", sa.Integer(), nullable=False),
            sa.Column("percent", sa.Double(), nullable=False),
            sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("repository_id", "name"),
        )
