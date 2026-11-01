"""Brand profiles: record the data version and allow only one default profile.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "brand_profiles",
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "uq_brand_profiles_default",
        "brand_profiles",
        ["is_default"],
        unique=True,
        sqlite_where=sa.text("is_default = 1"),
    )
