"""
Database configuration and session management for F1 Prediction Analytics.

This module sets up SQLAlchemy engine, session management, and database
connection handling with connection pooling for optimal performance.
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import db_config

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    db_config.database_url,
    poolclass=QueuePool,
    pool_size=db_config.DB_POOL_SIZE,
    max_overflow=db_config.DB_MAX_OVERFLOW,
    pool_timeout=db_config.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # Verify connections before use
    echo=db_config.DB_ECHO,  # Log SQL queries if enabled
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for model definitions
Base = declarative_base()

# Define metadata for Alembic migration with naming conventions
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)


def get_db():
    """
    Dependency function to get database session.

    This function creates a new SQLAlchemy SessionLocal that will be used
    in a single request, and then close it once the request is finished.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables.

    This function creates all tables defined by SQLAlchemy models.
    Should be called during application startup or in migrations.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables.

    Warning: This will delete all data! Use only in development/testing.
    """
    Base.metadata.drop_all(bind=engine)


# Alias for backward compatibility
get_database = get_db