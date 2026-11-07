"""Studio ideas: the post ideas the AI made, kept for each repository and focus.

Revision ID: 0022
Revises: 0021
"""

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "studio_ideas" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "studio_ideas",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.String(32), nullable=False),
        sa.Column("updated_at", sa.String(32), nullable=False),
        sa.Column(
            "repository_id",
            sa.String(36),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("focus_key", sa.String(600), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_studio_ideas"),
        sa.UniqueConstraint("repository_id", "focus_key", name="uq_studio_ideas_repository_id"),
    )


def downgrade() -> None:
    op.drop_table("studio_ideas")
