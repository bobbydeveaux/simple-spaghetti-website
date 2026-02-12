"""
Database connection and session management.
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
    pool_pre_ping=True,  # Validate connections before use
    echo=db_config.DB_ECHO,  # Log SQL queries if enabled
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for ORM models
Base = declarative_base()

# Define metadata for Alembic migration
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)


def get_database():
    """
    Database dependency for FastAPI.

    Returns:
        Database session that automatically closes after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)