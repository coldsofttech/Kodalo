"""A brand's logo can be hidden on every slide: ``show_on`` also accepts ``none``.

Revision ID: 0020
Revises: 0019
"""

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

_NAME = "show_on"
_BEFORE = "show_on IN ('all', 'first', 'last')"
_AFTER = "show_on IN ('all', 'first', 'last', 'none')"


def _replace(check: str) -> None:
    with op.batch_alter_table("brand_logos") as batch:
        batch.drop_constraint(_NAME, type_="check")
        batch.create_check_constraint(_NAME, check)


def upgrade() -> None:
    _replace(_AFTER)


def downgrade() -> None:
    op.execute("UPDATE brand_logos SET show_on = 'all' WHERE show_on = 'none'")
    _replace(_BEFORE)
