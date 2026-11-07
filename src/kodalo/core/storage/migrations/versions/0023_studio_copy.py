"""Studio copy: the slides, caption and hashtags written for a post idea, kept and editable.

Revision ID: 0023
Revises: 0022
"""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "studio_copy" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "studio_copy",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column(
            "repository_id",
            sa.String(36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("copy_key", sa.String(600), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_studio_copy"),
        sa.UniqueConstraint("repository_id", "copy_key", name="uq_studio_copy_repository_id"),
    )


def downgrade() -> None:
    op.drop_table("studio_copy")
