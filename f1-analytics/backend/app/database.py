"""
Database configuration and session management for F1 Prediction Analytics.

This module sets up SQLAlchemy engine, session management, and database
connection handling with connection pooling for optimal performance.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import settings

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before use
    echo=settings.DEBUG,  # Log SQL queries in debug mode
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for model definitions
Base = declarative_base()


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