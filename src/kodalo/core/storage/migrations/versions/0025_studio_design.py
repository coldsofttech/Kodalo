"""Studio design: the design plan of a post, and where the logo is in a social preview.

Adds ``studio_design`` and the column ``repositories.icon_box_json``. Like the migrations before
it, this one skips what already exists.

Revision ID: 0025
Revises: 0024
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("repositories")}
    if "icon_box_json" not in columns:
        op.add_column(
            "repositories",
            sa.Column("icon_box_json", sa.String(128), nullable=False, server_default=""),
        )
    if "studio_design" in set(inspector.get_table_names()):
        return
    op.create_table(
        "studio_design",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column(
            "repository_id",
            sa.String(36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("design_key", sa.String(600), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_studio_design"),
        sa.UniqueConstraint("repository_id", "design_key", name="uq_studio_design_repository_id"),
    )


def downgrade() -> None:
    op.drop_table("studio_design")
    with op.batch_alter_table("repositories") as batch:
        batch.drop_column("icon_box_json")
