"""
Tests for User model validation and Pydantic schemas.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from api.models.user import User, RegisterRequest, LoginRequest


class TestUserDataclass:
    """Test suite for User dataclass."""

    def test_user_creation_success(self):
        """Test successful user creation."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            created_at=datetime.now(timezone.utc)
        )

        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert isinstance(user.created_at, datetime)

    def test_user_valid_email_formats(self):
        """Test that valid email formats are accepted."""
        valid_emails = [
            "test@example.com",
            "user123@domain.org",
            "name.surname@company.co.uk",
            "user+tag@example.com",
            "user_name@example-domain.com"
        ]

        for email in valid_emails:
            user = User(
                email=email,
                password_hash="hash",
                created_at=datetime.now(timezone.utc)
            )
            assert user.email == email

    def test_user_invalid_email_formats_raise_error(self):
        """Test that invalid email formats raise ValueError."""
        invalid_emails = [
            "",  # Empty string
            "invalid",  # No @ symbol
            "@domain.com",  # Missing local part
            "user@",  # Missing domain
            "user@domain",  # Missing TLD
            "user..double@domain.com",  # Double dots
            "user@domain..com",  # Double dots in domain
        ]

        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                User(
                    email=email,
                    password_hash="hash",
                    created_at=datetime.now(timezone.utc)
                )

    def test_user_empty_email_raises_error(self):
        """Test that None email raises ValueError."""
        with pytest.raises((ValueError, TypeError)):
            User(
                email=None,
                password_hash="hash",
                created_at=datetime.now(timezone.utc)
            )

    def test_user_empty_password_hash_raises_error(self):
        """Test that empty password hash raises ValueError."""
        with pytest.raises(ValueError, match="Password hash cannot be empty"):
            User(
                email="test@example.com",
                password_hash="",
                created_at=datetime.now(timezone.utc)
            )

        with pytest.raises(ValueError, match="Password hash cannot be empty"):
            User(
                email="test@example.com",
                password_hash=None,
                created_at=datetime.now(timezone.utc)
            )


class TestRegisterRequest:
    """Test suite for RegisterRequest Pydantic model."""

    def test_register_request_valid(self):
        """Test valid registration request."""
        request = RegisterRequest(
            email="test@example.com",
            password="validpassword123"
        )

        assert request.email == "test@example.com"
        assert request.password == "validpassword123"

    def test_register_request_password_validation_success(self):
        """Test valid passwords pass validation."""
        valid_passwords = [
            "password123",  # Letters + numbers
            "mypassword1",  # Letters + numbers
            "SecurePass99",  # Mixed case + numbers
            "test1234567",  # Minimum length with requirements
        ]

        for password in valid_passwords:
            request = RegisterRequest(
                email="test@example.com",
                password=password
            )
            assert request.password == password

    def test_register_request_password_too_short_raises_error(self):
        """Test that password shorter than 8 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="test@example.com",
                password="short1"  # 6 characters
            )

        errors = exc_info.value.errors()
        assert any("Password must be at least 8 characters long" in str(error) for error in errors)

    def test_register_request_password_no_letters_raises_error(self):
        """Test that password without letters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="test@example.com",
                password="12345678"  # Only numbers
            )

        errors = exc_info.value.errors()
        assert any("Password must contain at least one letter" in str(error) for error in errors)

    def test_register_request_password_no_digits_raises_error(self):
        """Test that password without digits raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="test@example.com",
                password="password"  # Only letters
            )

        errors = exc_info.value.errors()
        assert any("Password must contain at least one digit" in str(error) for error in errors)

    def test_register_request_invalid_email_raises_error(self):
        """Test that invalid email raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                email="invalid-email",
                password="password123"
            )

        errors = exc_info.value.errors()
        assert any("value is not a valid email address" in str(error) for error in errors)


class TestLoginRequest:
    """Test suite for LoginRequest Pydantic model."""

    def test_login_request_valid(self):
        """Test valid login request."""
        request = LoginRequest(
            email="test@example.com",
            password="password123"
        )

        assert request.email == "test@example.com"
        assert request.password == "password123"

    def test_login_request_invalid_email_raises_error(self):
        """Test that invalid email raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest(
                email="invalid-email",
                password="password123"
            )

        errors = exc_info.value.errors()
        assert any("value is not a valid email address" in str(error) for error in errors)