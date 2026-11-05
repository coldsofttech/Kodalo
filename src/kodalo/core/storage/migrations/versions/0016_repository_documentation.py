"""Documentation files, skipped files and manifest evidence.

Adds ``documentation_json`` and ``skipped_json`` to ``repositories`` and ``evidence`` to
``repository_manifests``. Like the migrations before it, this one skips what already exists.

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    repositories = _columns("repositories")
    if "documentation_json" not in repositories:
        op.add_column(
            "repositories",
            sa.Column("documentation_json", sa.Text(), nullable=False, server_default="{}"),
        )
    if "skipped_json" not in repositories:
        op.add_column(
            "repositories",
            sa.Column("skipped_json", sa.Text(), nullable=False, server_default="[]"),
        )
    if "evidence" not in _columns("repository_manifests"):
        op.add_column(
            "repository_manifests",
            sa.Column("evidence", sa.String(128), nullable=False, server_default=""),
        )


def downgrade() -> None:
    with op.batch_alter_table("repository_manifests") as batch:
        batch.drop_column("evidence")
    with op.batch_alter_table("repositories") as batch:
        batch.drop_column("skipped_json")
        batch.drop_column("documentation_json")
