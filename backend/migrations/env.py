"""Alembic's entry point: which database, and which tables the migrations should match.
The URL comes from ITI_DATABASE_URL in the backend .env file, the same place the server reads it,
so there is one source of truth and no password in alembic.ini."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.main  # noqa: F401  loads every table class (chat, auth, documents, request_logs, chunks)
from app.core.a_config.get_settings import get_settings
from app.core.c_database.base import Base
from app.rag.d_vectorstore.rag_base import RagBase

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

DATABASE_URL = get_settings().database_url
target_metadata = [Base.metadata, RagBase.metadata]  # the app's tables + rag's chunks table


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: print the SQL instead of running it."""
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """The normal case: connect and apply the migrations."""
    engine = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
