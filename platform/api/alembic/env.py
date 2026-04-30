"""Alembic environment.

The runtime app uses an asyncpg URL; alembic's online migrations work
synchronously, so we strip ``+asyncpg`` and let SQLAlchemy fall back to
the default psycopg2 driver.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import models so their tables register on Base.metadata.
from app.db import Base
from app import models_maintenance  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _sync_url() -> str:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://iot_user:iot_password@postgres:5432/iot_database",
    )
    return url.replace("+asyncpg", "")


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = _sync_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
