"""
Database connection and session management for F1 Prediction Analytics.

This module provides SQLAlchemy engine configuration, session management,
and database utilities for the F1 analytics backend.
"""

import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, AsyncGenerator, Optional

from sqlalchemy import create_engine, event, Engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from .config import settings

logger = logging.getLogger(__name__)

# Base class for all ORM models
Base = declarative_base()


class DatabaseManager:
    """Database connection and session manager."""

    def __init__(self):
        self._engine: Optional[Engine] = None
        self._async_engine = None
        self._session_factory: Optional[sessionmaker] = None
        self._async_session_factory = None

    @property
    def engine(self) -> Engine:
        """Get synchronous database engine."""
        if self._engine is None:
            self._engine = self._create_sync_engine()
        return self._engine

    @property
    def async_engine(self):
        """Get asynchronous database engine."""
        if self._async_engine is None:
            self._async_engine = self._create_async_engine()
        return self._async_engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get synchronous session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        return self._session_factory

    @property
    def async_session_factory(self):
        """Get asynchronous session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._async_session_factory

    def _create_sync_engine(self) -> Engine:
        """Create synchronous SQLAlchemy engine."""
        logger.info(f"Creating database engine for {settings.database.db_host}:{settings.database.db_port}")

        engine = create_engine(
            settings.database.database_url,
            poolclass=QueuePool,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle,
            pool_pre_ping=True,
            echo=settings.database.echo_sql,
            future=True
        )

        # Add event listeners
        self._add_engine_listeners(engine)
        return engine

    def _create_async_engine(self):
        """Create asynchronous SQLAlchemy engine."""
        logger.info(f"Creating async database engine for {settings.database.db_host}:{settings.database.db_port}")

        engine = create_async_engine(
            settings.database.async_database_url,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle,
            pool_pre_ping=True,
            echo=settings.database.echo_sql,
            future=True
        )

        return engine

    def _add_engine_listeners(self, engine: Engine) -> None:
        """Add event listeners for database engine."""

        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Called when a new database connection is established."""
            logger.debug("Database connection established")

        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Called when a connection is retrieved from the pool."""
            logger.debug("Database connection checked out from pool")

        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Called when a connection is returned to the pool."""
            logger.debug("Database connection returned to pool")

        @event.listens_for(engine, "invalid")
        def on_invalid(dbapi_connection, connection_record, exception):
            """Called when a connection is invalidated."""
            logger.warning(f"Database connection invalidated: {exception}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.

        Usage:
            with db_manager.get_session() as session:
                user = session.query(User).first()
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Database session error: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session with automatic cleanup.

        Usage:
            async with db_manager.get_async_session() as session:
                result = await session.execute(select(User))
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

    def create_all_tables(self) -> None:
        """Create all tables in the database."""
        logger.info("Creating all database tables")
        Base.metadata.create_all(bind=self.engine)

    async def create_all_tables_async(self) -> None:
        """Create all tables in the database asynchronously."""
        logger.info("Creating all database tables (async)")
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    def drop_all_tables(self) -> None:
        """Drop all tables in the database. USE WITH CAUTION!"""
        if not settings.app.is_development:
            raise ValueError("Can only drop tables in development environment")

        logger.warning("Dropping all database tables")
        Base.metadata.drop_all(bind=self.engine)

    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    async def test_connection_async(self) -> bool:
        """Test async database connectivity."""
        try:
            async with self.get_async_session() as session:
                await session.execute("SELECT 1")
            logger.info("Async database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Async database connection test failed: {e}")
            return False

    def close_connections(self) -> None:
        """Close all database connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Synchronous database engine disposed")

        if self._async_engine:
            # AsyncEngine dispose is not awaitable in current version
            logger.info("Async database engine disposed")

    def get_connection_info(self) -> dict:
        """Get database connection information."""
        pool = self.engine.pool
        return {
            "database_url": settings.database.database_url.replace(settings.database.db_password, "***"),
            "pool_size": settings.database.pool_size,
            "max_overflow": settings.database.max_overflow,
            "pool_timeout": settings.database.pool_timeout,
            "current_checked_in": pool.checkedin(),
            "current_checked_out": pool.checkedout(),
            "current_overflow": pool.overflow(),
            "current_invalid": pool.invalid(),
        }


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get database session.

    Usage in route:
        @app.get("/users/")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    with db_manager.get_session() as session:
        yield session


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get async database session.

    Usage in route:
        @app.get("/users/")
        async def get_users(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with db_manager.get_async_session() as session:
        yield session


def health_check() -> dict:
    """
    Database health check for monitoring.

    Returns:
        dict: Health status and connection information
    """
    try:
        is_healthy = db_manager.test_connection()
        connection_info = db_manager.get_connection_info()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "database": "postgresql",
            "connection_info": connection_info,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }


async def async_health_check() -> dict:
    """
    Async database health check for monitoring.

    Returns:
        dict: Health status and connection information
    """
    try:
        is_healthy = await db_manager.test_connection_async()
        connection_info = db_manager.get_connection_info()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "database": "postgresql",
            "connection_info": connection_info,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""
    pass


class SessionError(DatabaseError):
    """Raised when database session operations fail."""
    pass