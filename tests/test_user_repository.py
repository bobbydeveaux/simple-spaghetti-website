"""
Comprehensive tests for UserRepository implementation.

These tests verify all the acceptance criteria for issue #86:
- Users can be stored and retrieved by email
- Duplicate email prevention works correctly
- Repository supports basic CRUD operations
- Thread safety for concurrent access
"""
import pytest
import threading
import time
from datetime import datetime

from api.models.user import User
from api.services.user_repository import UserRepository


class TestUserRepository:
    """Test suite for UserRepository class."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.repository = UserRepository()
        # Clear any existing users from previous tests
        self.repository.clear_all_users()

    def teardown_method(self):
        """Clean up after each test."""
        self.repository.clear_all_users()

    def test_add_user_success(self):
        """Test successfully adding a new user."""
        # Arrange
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            created_at=datetime.now()
        )

        # Act
        self.repository.add_user(user)

        # Assert
        assert self.repository.user_exists("test@example.com")
        assert self.repository.get_user_count() == 1

    def test_add_user_duplicate_email_raises_error(self):
        """Test that adding a user with existing email raises ValueError."""
        # Arrange
        user1 = User(
            email="test@example.com",
            password_hash="hash1",
            created_at=datetime.now()
        )
        user2 = User(
            email="test@example.com",
            password_hash="hash2",
            created_at=datetime.now()
        )

        # Act & Assert
        self.repository.add_user(user1)

        with pytest.raises(ValueError, match="User with email test@example.com already exists"):
            self.repository.add_user(user2)

        # Verify only one user exists
        assert self.repository.get_user_count() == 1

    def test_add_user_invalid_type_raises_error(self):
        """Test that adding non-User object raises TypeError."""
        # Act & Assert
        with pytest.raises(TypeError, match="user must be an instance of User"):
            self.repository.add_user("not_a_user")

        with pytest.raises(TypeError, match="user must be an instance of User"):
            self.repository.add_user({"email": "test@example.com"})

    def test_get_user_by_email_success(self):
        """Test successfully retrieving user by email."""
        # Arrange
        created_at = datetime.now()
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            created_at=created_at
        )
        self.repository.add_user(user)

        # Act
        retrieved_user = self.repository.get_user_by_email("test@example.com")

        # Assert
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.password_hash == "hashed_password"
        assert retrieved_user.created_at == created_at

    def test_get_user_by_email_not_found(self):
        """Test retrieving non-existent user returns None."""
        # Act
        result = self.repository.get_user_by_email("nonexistent@example.com")

        # Assert
        assert result is None

    def test_get_user_by_email_invalid_type_raises_error(self):
        """Test that get_user_by_email with non-string raises TypeError."""
        # Act & Assert
        with pytest.raises(TypeError, match="email must be a string"):
            self.repository.get_user_by_email(123)

        with pytest.raises(TypeError, match="email must be a string"):
            self.repository.get_user_by_email(None)

    def test_user_exists_true(self):
        """Test user_exists returns True for existing user."""
        # Arrange
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            created_at=datetime.now()
        )
        self.repository.add_user(user)

        # Act & Assert
        assert self.repository.user_exists("test@example.com") is True

    def test_user_exists_false(self):
        """Test user_exists returns False for non-existent user."""
        # Act & Assert
        assert self.repository.user_exists("nonexistent@example.com") is False

    def test_user_exists_invalid_type_raises_error(self):
        """Test that user_exists with non-string raises TypeError."""
        # Act & Assert
        with pytest.raises(TypeError, match="email must be a string"):
            self.repository.user_exists(123)

        with pytest.raises(TypeError, match="email must be a string"):
            self.repository.user_exists(None)

    def test_get_user_count_empty(self):
        """Test user count is zero when repository is empty."""
        # Act & Assert
        assert self.repository.get_user_count() == 0

    def test_get_user_count_multiple_users(self):
        """Test user count reflects actual number of users."""
        # Arrange
        users = [
            User(f"user{i}@example.com", f"hash{i}", datetime.now())
            for i in range(5)
        ]

        # Act
        for user in users:
            self.repository.add_user(user)

        # Assert
        assert self.repository.get_user_count() == 5

    def test_clear_all_users(self):
        """Test clearing all users from repository."""
        # Arrange
        users = [
            User(f"user{i}@example.com", f"hash{i}", datetime.now())
            for i in range(3)
        ]
        for user in users:
            self.repository.add_user(user)

        # Act
        self.repository.clear_all_users()

        # Assert
        assert self.repository.get_user_count() == 0
        assert not self.repository.user_exists("user0@example.com")

    def test_thread_safety_concurrent_adds(self):
        """Test thread safety with concurrent user additions."""
        # Arrange
        results = []
        errors = []

        def add_user_thread(user_id):
            try:
                user = User(
                    email=f"user{user_id}@example.com",
                    password_hash=f"hash{user_id}",
                    created_at=datetime.now()
                )
                self.repository.add_user(user)
                results.append(user_id)
            except Exception as e:
                errors.append((user_id, str(e)))

        # Act - Create multiple threads adding users concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=add_user_thread, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(results) == 10
        assert self.repository.get_user_count() == 10

        # Verify all users can be retrieved
        for i in range(10):
            user = self.repository.get_user_by_email(f"user{i}@example.com")
            assert user is not None
            assert user.password_hash == f"hash{i}"

    def test_thread_safety_concurrent_duplicate_adds(self):
        """Test thread safety when multiple threads try to add same email."""
        # Arrange
        success_count = 0
        error_count = 0
        lock = threading.Lock()

        def add_duplicate_user():
            nonlocal success_count, error_count
            try:
                user = User(
                    email="duplicate@example.com",
                    password_hash="hash",
                    created_at=datetime.now()
                )
                self.repository.add_user(user)
                with lock:
                    success_count += 1
            except ValueError:
                # Expected behavior for duplicate emails
                with lock:
                    error_count += 1

        # Act - Multiple threads trying to add same email
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_duplicate_user)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert
        assert success_count == 1, "Exactly one thread should succeed"
        assert error_count == 4, "Four threads should get duplicate email error"
        assert self.repository.get_user_count() == 1
        assert self.repository.user_exists("duplicate@example.com")

    def test_case_sensitive_emails(self):
        """Test that email addresses are case-sensitive."""
        # Arrange
        user1 = User("test@example.com", "hash1", datetime.now())
        user2 = User("TEST@EXAMPLE.COM", "hash2", datetime.now())

        # Act
        self.repository.add_user(user1)
        self.repository.add_user(user2)  # Should succeed - different case

        # Assert
        assert self.repository.get_user_count() == 2
        assert self.repository.user_exists("test@example.com")
        assert self.repository.user_exists("TEST@EXAMPLE.COM")
        assert not self.repository.user_exists("Test@Example.Com")


class TestUserRepositorySingleton:
    """Test the singleton user_repository instance."""

    def test_singleton_instance_exists(self):
        """Test that the singleton user_repository instance is available."""
        from api.services.user_repository import user_repository

        assert user_repository is not None
        assert isinstance(user_repository, UserRepository)

    def test_singleton_shared_state(self):
        """Test that singleton instance maintains state across imports."""
        from api.services.user_repository import user_repository

        # Clear and add a user
        user_repository.clear_all_users()
        user = User("singleton@example.com", "hash", datetime.now())
        user_repository.add_user(user)

        # Import again and verify state persists
        from api.services.user_repository import user_repository as repo2

        assert repo2.user_exists("singleton@example.com")
        assert repo2.get_user_count() == 1

        # Clean up
        user_repository.clear_all_users()