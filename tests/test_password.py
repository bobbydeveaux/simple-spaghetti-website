"""
Tests for password hashing utilities.
"""
import pytest
from api.utils.password import hash_password, verify_password


class TestPasswordUtils:
    """Test suite for password utility functions."""

    def test_hash_password_success(self):
        """Test password hashing works correctly."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert hashed != password  # Should be different from original
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_hash_password_empty_raises_error(self):
        """Test that empty password raises ValueError."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            hash_password("")

        with pytest.raises(ValueError, match="Password cannot be empty"):
            hash_password(None)

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_passwords_raise_error(self):
        """Test that empty passwords raise ValueError."""
        hashed = hash_password("test_password")

        with pytest.raises(ValueError, match="Passwords cannot be empty"):
            verify_password("", hashed)

        with pytest.raises(ValueError, match="Passwords cannot be empty"):
            verify_password("test", "")

        with pytest.raises(ValueError, match="Passwords cannot be empty"):
            verify_password(None, hashed)

    def test_different_passwords_produce_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Should be different due to salt
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_bcrypt_rounds_configuration(self):
        """Test that bcrypt uses 12 rounds as required."""
        password = "test_password"
        hashed = hash_password(password)

        # Extract rounds from hash (format: $2b$rounds$salt+hash)
        parts = hashed.split('$')
        rounds = int(parts[2])

        assert rounds == 12  # Verify 12 rounds as per security requirement