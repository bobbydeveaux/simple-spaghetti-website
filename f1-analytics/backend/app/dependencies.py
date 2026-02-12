"""
FastAPI Dependencies

This module provides dependency injection functions for FastAPI route handlers,
including database session management and common utilities.
"""

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from .database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session.

    This function creates a new database session for each request and ensures
    it's properly closed after the request is completed.

    Yields:
        Session: SQLAlchemy database session

    Usage:
        @app.get("/races/")
        def get_races(db: Session = Depends(get_db)):
            return db.query(Race).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()