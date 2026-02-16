#!/usr/bin/env python3
"""
Tests for polymarket-bot utility functions.

Tests cover:
- Retry decorator with exponential backoff
- Validation functions for data types and ranges
- Error handling utilities
- Logging configuration
- Helper functions
"""

import pytest
import logging
import time
from decimal import Decimal
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'polymarket-bot'))

from utils import (
    retry_with_backoff,
    validate_type,
    validate_range,
    validate_non_empty,
    validate_decimal,
    validate_probability,
    handle_errors,
    configure_logging,
    safe_divide,
    clamp,
    format_currency,
    truncate_string,
    RetryError,
    ValidationError,
)


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    def test_success_on_first_attempt(self):
        """Test that successful functions don't retry."""
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_success_after_retries(self):
        """Test that function succeeds after failing initially."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_successful()
        assert result == "success"
        assert call_count == 3

    def test_exhausted_retries(self):
        """Test that RetryError is raised when all attempts fail."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            always_fails()

        assert call_count == 3
        assert "failed after 3 attempts" in str(exc_info.value)

    def test_exponential_backoff_timing(self):
        """Test that exponential backoff delays are calculated correctly."""
        call_times = []

        @retry_with_backoff(max_attempts=3, base_delay=0.1, exponential_base=2.0)
        def timing_test():
            call_times.append(time.time())
            raise ValueError("Fail")

        with pytest.raises(RetryError):
            timing_test()

        # Verify we had 3 attempts
        assert len(call_times) == 3

        # Check approximate delays (allowing some variance)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # First delay should be ~0.1s, second should be ~0.2s
        assert 0.08 < delay1 < 0.15
        assert 0.18 < delay2 < 0.25

    def test_max_delay_cap(self):
        """Test that delays don't exceed max_delay."""
        call_times = []

        @retry_with_backoff(
            max_attempts=4,
            base_delay=10.0,
            max_delay=0.2,
            exponential_base=2.0
        )
        def max_delay_test():
            call_times.append(time.time())
            raise ValueError("Fail")

        with pytest.raises(RetryError):
            max_delay_test()

        # All delays should be capped at max_delay (0.2s)
        for i in range(1, len(call_times)):
            delay = call_times[i] - call_times[i-1]
            assert delay <= 0.25  # Allow small variance

    def test_specific_exception_types(self):
        """Test that only specified exceptions are retried."""
        @retry_with_backoff(max_attempts=3, base_delay=0.01, exceptions=(ValueError,))
        def specific_exception():
            raise TypeError("Wrong type")

        # TypeError should not be caught/retried, should raise immediately
        with pytest.raises(TypeError):
            specific_exception()


class TestValidateType:
    """Tests for the validate_type function."""

    def test_valid_type(self):
        """Test that valid types pass validation."""
        validate_type(5, int, "number")
        validate_type("hello", str, "text")
        validate_type([1, 2], list, "items")
        validate_type({"a": 1}, dict, "mapping")

    def test_invalid_type(self):
        """Test that invalid types raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_type("5", int, "number")

        assert "number must be of type int" in str(exc_info.value)
        assert "got str instead" in str(exc_info.value)

    def test_multiple_valid_types(self):
        """Test that tuples of types work correctly."""
        validate_type(5, (int, float), "number")
        validate_type(5.5, (int, float), "number")

        with pytest.raises(ValidationError):
            validate_type("5", (int, float), "number")


class TestValidateRange:
    """Tests for the validate_range function."""

    def test_value_in_range(self):
        """Test that values within range pass validation."""
        validate_range(5, 0, 10, "number")
        validate_range(0, 0, 10, "number")
        validate_range(10, 0, 10, "number")
        validate_range(5.5, 0.0, 10.0, "decimal")

    def test_value_below_minimum(self):
        """Test that values below minimum raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_range(-1, 0, 10, "number")

        assert "number must be >= 0" in str(exc_info.value)

    def test_value_above_maximum(self):
        """Test that values above maximum raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_range(11, 0, 10, "number")

        assert "number must be <= 10" in str(exc_info.value)

    def test_exclusive_range(self):
        """Test exclusive range validation."""
        validate_range(5, 0, 10, "number", inclusive=False)

        with pytest.raises(ValidationError) as exc_info:
            validate_range(0, 0, 10, "number", inclusive=False)
        assert "number must be > 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_range(10, 0, 10, "number", inclusive=False)
        assert "number must be < 10" in str(exc_info.value)

    def test_no_bounds(self):
        """Test that None bounds allow any value."""
        validate_range(100, None, None, "number")
        validate_range(-100, None, None, "number")
        validate_range(5, min_value=None, max_value=10, field_name="number")
        validate_range(5, min_value=0, max_value=None, field_name="number")

    def test_decimal_values(self):
        """Test that Decimal values work correctly."""
        validate_range(Decimal("5.5"), Decimal("0"), Decimal("10"), "decimal")

        with pytest.raises(ValidationError):
            validate_range(Decimal("11"), Decimal("0"), Decimal("10"), "decimal")

    def test_non_numeric_value(self):
        """Test that non-numeric values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_range("5", 0, 10, "value")

        assert "value must be numeric" in str(exc_info.value)


class TestValidateNonEmpty:
    """Tests for the validate_non_empty function."""

    def test_valid_non_empty_values(self):
        """Test that non-empty values pass validation."""
        validate_non_empty("hello", "text")
        validate_non_empty([1, 2, 3], "items")
        validate_non_empty({"a": 1}, "mapping")

    def test_empty_string(self):
        """Test that empty strings raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty("", "text")

        assert "text cannot be empty" in str(exc_info.value)

    def test_empty_list(self):
        """Test that empty lists raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty([], "items")

        assert "items cannot be empty" in str(exc_info.value)

    def test_empty_dict(self):
        """Test that empty dicts raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty({}, "mapping")

        assert "mapping cannot be empty" in str(exc_info.value)

    def test_none_value(self):
        """Test that None values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_non_empty(None, "value")

        assert "value cannot be None" in str(exc_info.value)


class TestValidateDecimal:
    """Tests for the validate_decimal function."""

    def test_valid_decimal_conversion(self):
        """Test that valid values are converted to Decimal."""
        result = validate_decimal("10.50", "price")
        assert result == Decimal("10.50")
        assert isinstance(result, Decimal)

        result = validate_decimal(10.5, "price")
        assert result == Decimal("10.5")

        result = validate_decimal(10, "price")
        assert result == Decimal("10")

    def test_none_not_allowed(self):
        """Test that None raises ValidationError by default."""
        with pytest.raises(ValidationError) as exc_info:
            validate_decimal(None, "price")

        assert "price cannot be None" in str(exc_info.value)

    def test_none_allowed(self):
        """Test that None is allowed when allow_none=True."""
        result = validate_decimal(None, "price", allow_none=True)
        assert result is None

    def test_invalid_decimal(self):
        """Test that invalid values raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_decimal("not a number", "price")

        assert "price must be a valid decimal number" in str(exc_info.value)

        with pytest.raises(ValidationError):
            validate_decimal("10.5.5", "price")


class TestValidateProbability:
    """Tests for the validate_probability function."""

    def test_valid_probabilities(self):
        """Test that valid probabilities pass validation."""
        validate_probability(0.0, "prob")
        validate_probability(0.5, "prob")
        validate_probability(1.0, "prob")
        validate_probability(Decimal("0.75"), "prob")

    def test_probability_below_zero(self):
        """Test that probabilities below 0 raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_probability(-0.1, "prob")

        assert "prob must be >= 0.0" in str(exc_info.value)

    def test_probability_above_one(self):
        """Test that probabilities above 1 raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_probability(1.1, "prob")

        assert "prob must be <= 1.0" in str(exc_info.value)

    def test_invalid_type(self):
        """Test that non-numeric values raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_probability("0.5", "prob")


class TestHandleErrors:
    """Tests for the handle_errors decorator."""

    def test_successful_execution(self):
        """Test that successful functions work normally."""
        @handle_errors(default_return="default")
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_error_with_default_return(self):
        """Test that errors return default value."""
        @handle_errors(default_return="default")
        def failing_function():
            raise ValueError("Error")

        result = failing_function()
        assert result == "default"

    def test_error_with_logging(self, caplog):
        """Test that errors are logged correctly."""
        @handle_errors(default_return=None, log_level=logging.ERROR)
        def failing_function():
            raise ValueError("Test error")

        with caplog.at_level(logging.ERROR):
            result = failing_function()

        assert result is None
        assert "Error in failing_function" in caplog.text
        assert "ValueError: Test error" in caplog.text

    def test_error_with_re_raise(self):
        """Test that errors can be re-raised after logging."""
        @handle_errors(raise_exception=True)
        def failing_function():
            raise ValueError("Error")

        with pytest.raises(ValueError):
            failing_function()


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_logger_creation(self):
        """Test that logger is created and configured."""
        logger = configure_logging(
            level=logging.DEBUG,
            logger_name="test_logger"
        )

        assert logger.name == "test_logger"
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0

    def test_custom_format(self):
        """Test that custom format strings work."""
        custom_format = "%(levelname)s - %(message)s"
        logger = configure_logging(
            format_string=custom_format,
            logger_name="test_custom_format"
        )

        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert handler.formatter._fmt == custom_format


class TestSafeDivide:
    """Tests for the safe_divide function."""

    def test_normal_division(self):
        """Test that normal division works correctly."""
        result = safe_divide(10, 2)
        assert result == 5.0

        result = safe_divide(7, 2)
        assert result == 3.5

    def test_division_by_zero(self):
        """Test that division by zero returns default value."""
        result = safe_divide(10, 0, default=0)
        assert result == 0

        result = safe_divide(10, 0, default=-1)
        assert result == -1

    def test_decimal_division(self):
        """Test that Decimal division works correctly."""
        result = safe_divide(Decimal("10"), Decimal("3"))
        assert isinstance(result, Decimal)

        result = safe_divide(Decimal("10"), Decimal("0"), default=Decimal("0"))
        assert result == Decimal("0")


class TestClamp:
    """Tests for the clamp function."""

    def test_value_in_range(self):
        """Test that values within range are unchanged."""
        assert clamp(5, 0, 10) == 5
        assert clamp(5.5, 0.0, 10.0) == 5.5

    def test_value_below_minimum(self):
        """Test that values below minimum are clamped to minimum."""
        assert clamp(-5, 0, 10) == 0
        assert clamp(-100, -50, 50) == -50

    def test_value_above_maximum(self):
        """Test that values above maximum are clamped to maximum."""
        assert clamp(15, 0, 10) == 10
        assert clamp(100, -50, 50) == 50

    def test_value_at_boundaries(self):
        """Test that boundary values work correctly."""
        assert clamp(0, 0, 10) == 0
        assert clamp(10, 0, 10) == 10


class TestFormatCurrency:
    """Tests for the format_currency function."""

    def test_basic_formatting(self):
        """Test basic currency formatting."""
        result = format_currency(123.456, "USDC", 2)
        assert result == "123.46 USDC"

        result = format_currency(100, "USDC", 2)
        assert result == "100.00 USDC"

    def test_different_decimals(self):
        """Test formatting with different decimal places."""
        result = format_currency(123.456789, "USDC", 4)
        assert result == "123.4568 USDC"

        result = format_currency(123.456789, "USDC", 0)
        assert result == "123 USDC"

    def test_different_currencies(self):
        """Test formatting with different currency codes."""
        result = format_currency(100, "ETH", 4)
        assert result == "100.0000 ETH"

        result = format_currency(50.5, "USD", 2)
        assert result == "50.50 USD"

    def test_decimal_input(self):
        """Test formatting with Decimal input."""
        result = format_currency(Decimal("123.45"), "USDC", 2)
        assert result == "123.45 USDC"


class TestTruncateString:
    """Tests for the truncate_string function."""

    def test_short_string(self):
        """Test that short strings are not truncated."""
        text = "Hello, World!"
        result = truncate_string(text, max_length=50)
        assert result == text

    def test_long_string(self):
        """Test that long strings are truncated."""
        text = "This is a very long string that should be truncated"
        result = truncate_string(text, max_length=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_custom_suffix(self):
        """Test that custom suffixes work."""
        text = "This is a very long string"
        result = truncate_string(text, max_length=15, suffix="[...]")
        assert result.endswith("[...]")
        assert len(result) == 15

    def test_exact_length(self):
        """Test that strings exactly at max_length are not truncated."""
        text = "Exactly 20 chars!!!!"
        result = truncate_string(text, max_length=20)
        assert result == text
        assert not result.endswith("...")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
