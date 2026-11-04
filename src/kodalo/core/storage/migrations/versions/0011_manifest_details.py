"""Package details and dependencies of project files.

Adds ``package_name`` and ``version`` to ``repository_manifests`` and a ``repository_dependencies``
table. The ``manifest_files`` seed table goes: which files are project files now comes from the
parser configs. Like the migrations before it, this one skips what already exists.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("repository_manifests")}
    for name in ("package_name", "version"):
        if name not in columns:
            op.add_column("repository_manifests", sa.Column(name, sa.String(256), nullable=True))
    if not inspector.has_table("repository_dependencies"):
        op.create_table(
            "repository_dependencies",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.String(32), nullable=False),
            sa.Column("updated_at", sa.String(32), nullable=False),
            sa.Column("manifest_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(256), nullable=False),
            sa.Column("is_dev", sa.Boolean(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["manifest_id"], ["repository_manifests.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("manifest_id", "name", "is_dev"),
        )
    if inspector.has_table("manifest_files"):
        op.drop_table("manifest_files")


def downgrade() -> None:
    op.drop_table("repository_dependencies")
    op.drop_column("repository_manifests", "version")
    op.drop_column("repository_manifests", "package_name")
    # Recreated empty: the project file names are not seeded again.
    op.create_table(
        "manifest_files",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column("file_name_pattern", sa.String(128), nullable=False),
        sa.Column("ecosystem", sa.String(32), nullable=False),
        sa.Column("is_lockfile", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_name_pattern"),
    )
