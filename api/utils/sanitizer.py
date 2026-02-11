"""
Input sanitization utilities for the PTA voting system.
Protects against XSS, injection attacks, and malformed input.
"""

import re
import html
from typing import Optional


def sanitize_text_input(text: str, max_length: int = 255, allow_html: bool = False) -> str:
    """
    Sanitize text input to prevent XSS and injection attacks.

    Args:
        text: Raw text input
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags (default: False)

    Returns:
        Sanitized text string

    Raises:
        ValueError: If input is invalid or too long
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    # Strip whitespace
    text = text.strip()

    # Check length
    if len(text) > max_length:
        raise ValueError(f"Input too long (max {max_length} characters)")

    if not allow_html:
        # HTML escape to prevent XSS
        text = html.escape(text, quote=True)

    # Remove null bytes and other control characters
    text = text.replace('\x00', '')
    text = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text


def sanitize_position_name(position: str) -> str:
    """
    Sanitize position name for election management.

    Args:
        position: Raw position name

    Returns:
        Sanitized position name

    Raises:
        ValueError: If position name is invalid
    """
    if not position or not isinstance(position, str):
        raise ValueError("Position name is required and must be a string")

    # Basic sanitization
    position = sanitize_text_input(position, max_length=50, allow_html=False)

    # Check if empty after sanitization
    if not position:
        raise ValueError("Position name cannot be empty")

    # Allow only letters, numbers, spaces, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', position):
        raise ValueError("Position name contains invalid characters")

    # Convert to lowercase with underscores (standard format)
    normalized = position.lower().replace(' ', '_').replace('-', '_')

    # Remove multiple consecutive underscores
    normalized = re.sub(r'_+', '_', normalized)

    # Remove leading/trailing underscores
    normalized = normalized.strip('_')

    if not normalized:
        raise ValueError("Position name is invalid after normalization")

    return normalized


def sanitize_email(email: str) -> str:
    """
    Sanitize email address input.

    Args:
        email: Raw email input

    Returns:
        Sanitized email address

    Raises:
        ValueError: If email is invalid
    """
    if not email or not isinstance(email, str):
        raise ValueError("Email is required and must be a string")

    # Basic sanitization
    email = sanitize_text_input(email, max_length=254, allow_html=False)
    email = email.lower().strip()

    # Basic email format validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValueError("Invalid email format")

    return email


def sanitize_name(name: str) -> str:
    """
    Sanitize full name input.

    Args:
        name: Raw name input

    Returns:
        Sanitized name

    Raises:
        ValueError: If name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValueError("Name is required and must be a string")

    # Basic sanitization
    name = sanitize_text_input(name, max_length=100, allow_html=False)

    if not name:
        raise ValueError("Name cannot be empty")

    # Allow letters, spaces, hyphens, apostrophes, and periods
    if not re.match(r"^[a-zA-Z\s\-'.]+$", name):
        raise ValueError("Name contains invalid characters")

    # Remove multiple consecutive spaces
    name = re.sub(r'\s+', ' ', name)

    return name.strip()


def sanitize_password(password: str) -> str:
    """
    Sanitize password input (basic validation only, no character restrictions).

    Args:
        password: Raw password input

    Returns:
        Password (unchanged if valid)

    Raises:
        ValueError: If password is invalid
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password is required and must be a string")

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")

    if len(password) > 128:
        raise ValueError("Password must be less than 128 characters")

    # Check for null bytes
    if '\x00' in password:
        raise ValueError("Password contains invalid characters")

    return password


def sanitize_verification_code(code: str) -> str:
    """
    Sanitize verification code input.

    Args:
        code: Raw verification code

    Returns:
        Sanitized verification code

    Raises:
        ValueError: If code is invalid
    """
    if not code or not isinstance(code, str):
        raise ValueError("Verification code is required and must be a string")

    # Remove whitespace
    code = code.strip()

    # Check format (6 digits)
    if not re.match(r'^\d{6}$', code):
        raise ValueError("Verification code must be exactly 6 digits")

    return code


def sanitize_json_string(data: str, max_length: int = 1000) -> str:
    """
    Sanitize JSON string data to prevent injection.

    Args:
        data: Raw JSON string
        max_length: Maximum allowed length

    Returns:
        Sanitized JSON string

    Raises:
        ValueError: If data is invalid
    """
    if not isinstance(data, str):
        raise ValueError("Data must be a string")

    if len(data) > max_length:
        raise ValueError(f"Data too long (max {max_length} characters)")

    # Remove null bytes and control characters
    data = data.replace('\x00', '')
    data = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', data)

    return data


# Validation utilities
def validate_position_name(position: str) -> bool:
    """
    Validate position name without sanitizing.

    Args:
        position: Position name to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        sanitize_position_name(position)
        return True
    except ValueError:
        return False


def validate_email_format(email: str) -> bool:
    """
    Validate email format without sanitizing.

    Args:
        email: Email to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        sanitize_email(email)
        return True
    except ValueError:
        return False