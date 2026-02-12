"""
Alembic environment configuration for F1 Prediction Analytics.

This file configures Alembic to work with our SQLAlchemy models
and database connection settings.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the app directory to Python path so we can import our models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our models and database configuration
from app.database import Base
from app.config import settings

# Import all models to ensure they are registered with SQLAlchemy
from app.models import (
    driver,
    team,
    circuit,
    race,
    race_result,
    qualifying_result,
    weather_data,
    prediction,
    prediction_accuracy,
    user
)

# This is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the SQLAlchemy URL from our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    """
    Filter function to include/exclude tables from migrations.

    This function is called by Alembic for each database object
    to determine whether it should be included in the migration.
    """
    # Only include our F1 analytics tables
    f1_tables = {
        'users', 'drivers', 'teams', 'circuits', 'races',
        'race_results', 'qualifying_results', 'weather_data',
        'predictions', 'prediction_accuracy'
    }

    if type_ == 'table':
        return name in f1_tables

    # Include all other objects (indexes, constraints, etc.)
    return True

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    # Get database connection configuration
    configuration = config.get_section(config.config_ini_section, {})
    configuration['sqlalchemy.url'] = settings.DATABASE_URL

    # Create engine with connection pooling settings
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't use connection pooling for migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=False,  # We're using PostgreSQL, not SQLite
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations():
    """Run migrations based on the context."""
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


# Run the migrations
run_migrations()
