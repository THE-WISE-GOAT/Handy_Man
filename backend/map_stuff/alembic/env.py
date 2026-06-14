import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# 1. CRITICAL: Import GeoAlchemy2 so Alembic recognizes the Geography column type
import geoalchemy2

# 2. Import your central database Base layout
from backend.map_stuff.src.database import Base

# 3. CRITICAL: Import ALL model source files so Alembic's autogenerate detects your complete schema
import backend.map_stuff.src.models  # Imports your Map/Worker models
# If your User/Role tables live in a separate file (e.g., core app models), import them here too:
# from src.auth import models as auth_models 

# This is the Alembic Config object, which provides access to the values within the .ini file.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic directly to your mapped model metadata structure
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() here emit the given string to the script output.
    """
    url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/handyman_db")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    configuration = config.get_section(config.config_ini_section) or {}
    
    # Injects your environment variable database connection URL dynamically
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/handyman_db")
    configuration["sqlalchemy.url"] = db_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def do_run_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_all_migrations)
        await connectable.dispose()

    def do_run_all_migrations(connection):
        # include_object can be passed here if you ever need to filter system tables
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

    # Safely executes the async event block inside Alembic's wrapper
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Handles nested event loops cleanly if called inside an active execution space
        loop.create_task(do_run_migrations())
    else:
        asyncio.run(do_run_migrations())