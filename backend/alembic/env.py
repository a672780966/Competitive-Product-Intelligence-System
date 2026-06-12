"""
CPIS V1 — 竞品公开信息自动采集与分析系统

Alembic environment configuration (async).

环境 Python 3.12+ / FastAPI / PostgreSQL 16 / asyncpg
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core import get_settings
from app.models import Base  # noqa: F401 — ensure all models are loaded

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    logging.basicConfig(level=logging.WARN)

# Override sqlalchemy.url from settings
config.set_main_option("sqlalchemy.url", str(settings.DATABASE_URL))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL script without DB connection.

    This is useful for review before applying to production.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Helper: run migrations with a given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode — applies directly to the database."""

    connectable: AsyncEngine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.DATABASE_ECHO,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
