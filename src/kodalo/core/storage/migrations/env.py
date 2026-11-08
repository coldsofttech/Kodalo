"""Alembic environment. Migrations run on the connection that ``database.migrate`` passes in."""

from alembic import context

from kodalo.core.storage.models import VERSION_TABLE, Base

connection = context.config.attributes["connection"]
context.configure(
    connection=connection,
    target_metadata=Base.metadata,
    version_table=VERSION_TABLE,
    render_as_batch=True,
)
with context.begin_transaction():
    context.run_migrations()
