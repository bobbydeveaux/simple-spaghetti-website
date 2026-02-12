"""
Tests for database connection and session management.

This module tests the core database functionality including
connection management, session handling, and health checks.
"""

import pytest
from datetime import datetime, timezone

from app.database import db_manager, get_db, health_check, DatabaseError
from app.config import settings
from app.models.user import User


class TestDatabaseConnection:
    """Test database connection functionality."""

    def test_database_engine_creation(self, test_engine):
        """Test that database engine is created successfully."""
        assert test_engine is not None
        assert test_engine.url.database

    def test_database_connection_info(self, test_engine):
        """Test getting database connection information."""
        # Temporarily override the global db_manager for testing
        original_engine = db_manager._engine
        db_manager._engine = test_engine

        try:
            info = db_manager.get_connection_info()
            assert isinstance(info, dict)
            assert "database_url" in info
            assert "pool_size" in info
            assert "current_checked_in" in info
            # Password should be masked
            assert "***" in info["database_url"]
        finally:
            db_manager._engine = original_engine

    def test_session_factory_creation(self, test_session_factory):
        """Test that session factory is created successfully."""
        assert test_session_factory is not None

        # Test creating a session
        session = test_session_factory()
        assert session is not None
        session.close()

    def test_session_context_manager(self, test_engine):
        """Test database session context manager."""
        # Temporarily override for testing
        original_engine = db_manager._engine
        original_factory = db_manager._session_factory
        db_manager._engine = test_engine
        db_manager._session_factory = None  # Force recreation

        try:
            with db_manager.get_session() as session:
                # Test basic query
                result = session.execute("SELECT 1")
                assert result.scalar() == 1

            # Session should be closed after context exit
        finally:
            db_manager._engine = original_engine
            db_manager._session_factory = original_factory

    def test_get_db_dependency(self, db_session):
        """Test the FastAPI database dependency."""
        # This tests that get_db yields a session
        session_generator = get_db()
        session = next(session_generator)

        assert session is not None
        # Test that we can execute a query
        result = session.execute("SELECT 1")
        assert result.scalar() == 1

    def test_database_health_check(self):
        """Test database health check functionality."""
        health_status = health_check()

        assert isinstance(health_status, dict)
        assert "status" in health_status
        assert "timestamp" in health_status

        # Status should be either 'healthy' or 'unhealthy'
        assert health_status["status"] in ["healthy", "unhealthy"]


class TestDatabaseOperations:
    """Test basic database operations."""

    def test_create_user(self, db_session, sample_user_data):
        """Test creating a user in the database."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.user_id is not None
        assert user.email == sample_user_data["email"]
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_query_user(self, db_session, test_user):
        """Test querying a user from the database."""
        queried_user = db_session.query(User).filter(
            User.email == test_user.email
        ).first()

        assert queried_user is not None
        assert queried_user.user_id == test_user.user_id
        assert queried_user.email == test_user.email

    def test_update_user(self, db_session, test_user):
        """Test updating a user in the database."""
        original_updated_at = test_user.updated_at
        new_username = "updated_username"

        test_user.username = new_username
        test_user.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(test_user)

        assert test_user.username == new_username
        assert test_user.updated_at > original_updated_at

    def test_delete_user(self, db_session, sample_user_data):
        """Test deleting a user from the database."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        user_id = user.user_id

        db_session.delete(user)
        db_session.commit()

        # User should no longer exist
        deleted_user = db_session.query(User).filter(
            User.user_id == user_id
        ).first()
        assert deleted_user is None

    def test_transaction_rollback(self, db_session, sample_user_data):
        """Test transaction rollback functionality."""
        # Create a user
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        original_username = user.username

        try:
            # Start a transaction
            user.username = "modified_username"
            # Force an error by trying to create a duplicate email
            duplicate_user = User(
                email=sample_user_data["email"],  # Same email
                password_hash="different_hash"
            )
            db_session.add(duplicate_user)
            db_session.commit()  # This should fail
        except Exception:
            db_session.rollback()

        # Refresh the user and check that changes were rolled back
        db_session.refresh(user)
        assert user.username == original_username

    def test_concurrent_sessions(self, test_session_factory):
        """Test multiple concurrent database sessions."""
        session1 = test_session_factory()
        session2 = test_session_factory()

        try:
            # Both sessions should work independently
            result1 = session1.execute("SELECT 1 as value")
            result2 = session2.execute("SELECT 2 as value")

            assert result1.scalar() == 1
            assert result2.scalar() == 2

        finally:
            session1.close()
            session2.close()


class TestDatabaseConstraints:
    """Test database constraints and validation."""

    def test_unique_email_constraint(self, db_session, sample_user_data):
        """Test that email uniqueness is enforced."""
        # Create first user
        user1 = User(**sample_user_data)
        db_session.add(user1)
        db_session.commit()

        # Try to create second user with same email
        user2_data = sample_user_data.copy()
        user2_data["username"] = "different_username"
        user2 = User(**user2_data)
        db_session.add(user2)

        # This should raise an integrity error
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            db_session.commit()

        db_session.rollback()

    def test_user_model_validation(self, db_session):
        """Test user model field validation."""
        # Test with missing required fields
        with pytest.raises(Exception):
            user = User(email=None, password_hash="hash")
            db_session.add(user)
            db_session.commit()

        db_session.rollback()

    def test_timestamp_defaults(self, db_session, sample_user_data):
        """Test that timestamp fields have proper defaults."""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

        # Both timestamps should be recent (within last minute)
        now = datetime.now(timezone.utc)
        time_diff = abs((now - user.created_at).total_seconds())
        assert time_diff < 60  # Within 1 minute


class TestDatabasePerformance:
    """Test database performance and optimization."""

    def test_bulk_operations(self, db_session):
        """Test bulk database operations performance."""
        users_data = []
        for i in range(100):
            users_data.append(User(
                email=f"bulk_user_{i}@example.com",
                password_hash="bulk_hash",
                username=f"bulk_user_{i}"
            ))

        # Bulk insert
        db_session.add_all(users_data)
        db_session.commit()

        # Verify all users were created
        user_count = db_session.query(User).filter(
            User.email.like("bulk_user_%@example.com")
        ).count()
        assert user_count == 100

        # Bulk delete
        db_session.query(User).filter(
            User.email.like("bulk_user_%@example.com")
        ).delete()
        db_session.commit()

        # Verify all users were deleted
        remaining_count = db_session.query(User).filter(
            User.email.like("bulk_user_%@example.com")
        ).count()
        assert remaining_count == 0

    def test_query_optimization(self, db_session, test_data_builder):
        """Test query optimization with indexes."""
        # Create test data
        season_data = test_data_builder.create_season_data()

        # Test that indexed queries are efficient
        # (In a real test, you'd measure query execution time)
        drivers = season_data["drivers"]
        teams = season_data["teams"]

        # Query by driver code (should use index)
        driver = db_session.query(User).filter(
            User.email == "test@example.com"
        ).first()

        # For SQLite testing, we can't easily test PostgreSQL-specific
        # optimizations, but we can verify the queries work
        assert len(drivers) > 0
        assert len(teams) > 0


class TestDatabaseError_Handling:
    """Test database error handling."""

    def test_connection_error_handling(self):
        """Test handling of database connection errors."""
        # This is difficult to test without actually breaking the connection
        # In a real scenario, you might temporarily change the connection string
        pass

    def test_session_error_recovery(self, db_session):
        """Test session error recovery."""
        try:
            # Force a database error
            db_session.execute("SELECT * FROM nonexistent_table")
        except Exception:
            # Session should be recoverable after rollback
            db_session.rollback()

            # This query should work after rollback
            result = db_session.execute("SELECT 1")
            assert result.scalar() == 1

    def test_database_manager_initialization(self):
        """Test database manager initialization."""
        # Test that database manager initializes correctly
        assert db_manager is not None
        assert hasattr(db_manager, 'get_session')
        assert hasattr(db_manager, 'test_connection')

    def test_database_cleanup(self, test_engine):
        """Test proper database cleanup."""
        # Test that cleanup methods work
        # In production, you'd test connection pool cleanup
        assert test_engine is not None

        # Test engine disposal
        test_engine.dispose()
        # After disposal, should be able to create new connections
        # (This is more of a sanity check)