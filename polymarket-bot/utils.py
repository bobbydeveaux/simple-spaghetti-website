"""
Utility functions for the Polymarket Bot.

This module provides reusable utility functions including:
- API request retry logic with exponential backoff
- Input validation helpers
- Error handling wrappers
- Data validation and type checking
"""

import functools
import logging
import time
from typing import Any, Callable, Optional, Type, TypeVar, Union
from decimal import Decimal, InvalidOperation

# Configure module logger
logger = logging.getLogger(__name__)

# Type variable for generic function return types
T = TypeVar('T')


class RetryError(Exception):
    """Exception raised when retry attempts are exhausted."""
    pass


class ValidationError(Exception):
    """Exception raised when validation fails."""
    pass


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    logger_name: Optional[str] = None
) -> Callable:
    """
    Decorator that implements exponential backoff retry logic for API calls.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)
        exceptions: Tuple of exceptions to catch and retry (default: (Exception,))
        logger_name: Optional logger name for custom logging

    Returns:
        Decorated function with retry logic

    Raises:
        RetryError: When all retry attempts are exhausted

    Example:
        @retry_with_backoff(max_attempts=5, base_delay=2.0)
        def fetch_market_data(market_id: str):
            response = requests.get(f"https://api.polymarket.com/markets/{market_id}")
            response.raise_for_status()
            return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Use custom logger if provided, otherwise use module logger
            log = logging.getLogger(logger_name) if logger_name else logger

            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)

                    # Log success if this wasn't the first attempt
                    if attempt > 1:
                        log.info(
                            f"{func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                        )

                    return result

                except exceptions as e:
                    last_exception = e

                    # Don't sleep after the last attempt
                    if attempt == max_attempts:
                        log.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )
                        break

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                    log.warning(
                        f"{func.__name__} failed on attempt {attempt}/{max_attempts}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )

                    time.sleep(delay)

            # All attempts exhausted
            raise RetryError(
                f"{func.__name__} failed after {max_attempts} attempts. "
                f"Last error: {str(last_exception)}"
            ) from last_exception

        return wrapper
    return decorator


def validate_type(
    value: Any,
    expected_type: Type,
    field_name: str = "value"
) -> None:
    """
    Validate that a value matches the expected type.

    Args:
        value: The value to validate
        expected_type: The expected type or tuple of types
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If the value doesn't match the expected type

    Example:
        validate_type(user_id, int, "user_id")
        validate_type(price, (int, float), "price")
    """
    if not isinstance(value, expected_type):
        expected_type_name = (
            expected_type.__name__ if hasattr(expected_type, '__name__')
            else str(expected_type)
        )
        actual_type_name = type(value).__name__

        raise ValidationError(
            f"{field_name} must be of type {expected_type_name}, "
            f"got {actual_type_name} instead"
        )


def validate_range(
    value: Union[int, float, Decimal],
    min_value: Optional[Union[int, float, Decimal]] = None,
    max_value: Optional[Union[int, float, Decimal]] = None,
    field_name: str = "value",
    inclusive: bool = True
) -> None:
    """
    Validate that a numeric value is within a specified range.

    Args:
        value: The numeric value to validate
        min_value: Minimum allowed value (None for no minimum)
        max_value: Maximum allowed value (None for no maximum)
        field_name: Name of the field for error messages
        inclusive: Whether the range is inclusive (default: True)

    Raises:
        ValidationError: If the value is out of range

    Example:
        validate_range(probability, 0.0, 1.0, "probability")
        validate_range(amount, min_value=0, field_name="bet_amount")
    """
    # Validate that value is numeric
    if not isinstance(value, (int, float, Decimal)):
        raise ValidationError(
            f"{field_name} must be numeric, got {type(value).__name__}"
        )

    if inclusive:
        if min_value is not None and value < min_value:
            raise ValidationError(
                f"{field_name} must be >= {min_value}, got {value}"
            )
        if max_value is not None and value > max_value:
            raise ValidationError(
                f"{field_name} must be <= {max_value}, got {value}"
            )
    else:
        if min_value is not None and value <= min_value:
            raise ValidationError(
                f"{field_name} must be > {min_value}, got {value}"
            )
        if max_value is not None and value >= max_value:
            raise ValidationError(
                f"{field_name} must be < {max_value}, got {value}"
            )


def validate_non_empty(
    value: Union[str, list, dict],
    field_name: str = "value"
) -> None:
    """
    Validate that a string, list, or dict is not empty.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If the value is empty or None

    Example:
        validate_non_empty(market_id, "market_id")
        validate_non_empty(orders, "orders")
    """
    if value is None:
        raise ValidationError(f"{field_name} cannot be None")

    if isinstance(value, (str, list, dict)) and len(value) == 0:
        raise ValidationError(f"{field_name} cannot be empty")


def validate_decimal(
    value: Any,
    field_name: str = "value",
    allow_none: bool = False
) -> Optional[Decimal]:
    """
    Validate and convert a value to Decimal for precise financial calculations.

    Args:
        value: The value to validate and convert
        field_name: Name of the field for error messages
        allow_none: Whether None is an acceptable value

    Returns:
        Decimal representation of the value, or None if allow_none=True

    Raises:
        ValidationError: If the value cannot be converted to Decimal

    Example:
        price = validate_decimal("10.50", "price")
        amount = validate_decimal(user_input, "bet_amount")
    """
    if value is None:
        if allow_none:
            return None
        raise ValidationError(f"{field_name} cannot be None")

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValidationError(
            f"{field_name} must be a valid decimal number, got '{value}'"
        ) from e


def validate_probability(
    value: Union[int, float, Decimal],
    field_name: str = "probability"
) -> None:
    """
    Validate that a value represents a valid probability (0.0 to 1.0).

    Args:
        value: The probability value to validate
        field_name: Name of the field for error messages

    Raises:
        ValidationError: If the value is not a valid probability

    Example:
        validate_probability(0.75, "win_probability")
    """
    validate_type(value, (int, float, Decimal), field_name)
    validate_range(value, 0.0, 1.0, field_name, inclusive=True)


def handle_errors(
    default_return: Any = None,
    log_level: int = logging.ERROR,
    raise_exception: bool = False,
    logger_name: Optional[str] = None
) -> Callable:
    """
    Decorator for consistent error handling and logging.

    Args:
        default_return: Value to return if an exception occurs (default: None)
        log_level: Logging level for caught exceptions (default: ERROR)
        raise_exception: Whether to re-raise the exception after logging (default: False)
        logger_name: Optional logger name for custom logging

    Returns:
        Decorated function with error handling

    Example:
        @handle_errors(default_return={}, log_level=logging.WARNING)
        def fetch_optional_data():
            return risky_api_call()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Union[T, Any]:
            log = logging.getLogger(logger_name) if logger_name else logger

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Format error message with function name and error details
                error_msg = (
                    f"Error in {func.__name__}: {type(e).__name__}: {str(e)}"
                )

                # Log with specified level
                log.log(log_level, error_msg, exc_info=True)

                # Re-raise if requested
                if raise_exception:
                    raise

                return default_return

        return wrapper
    return decorator


def configure_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    logger_name: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging with a consistent format.

    Args:
        level: Logging level (default: INFO)
        format_string: Custom format string (default: standard format)
        logger_name: Name of the logger to configure (default: root logger)

    Returns:
        Configured logger instance

    Example:
        logger = configure_logging(
            level=logging.DEBUG,
            logger_name="polymarket_bot"
        )
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(filename)s:%(lineno)d - %(message)s"
        )

    # Get or create logger
    log = logging.getLogger(logger_name)
    log.setLevel(level)

    # Remove existing handlers to avoid duplicates
    log.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Create formatter and add to handler
    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)

    # Add handler to logger
    log.addHandler(console_handler)

    return log


def safe_divide(
    numerator: Union[int, float, Decimal],
    denominator: Union[int, float, Decimal],
    default: Union[int, float, Decimal] = 0
) -> Union[float, Decimal]:
    """
    Safely divide two numbers, returning a default value if division by zero occurs.

    Args:
        numerator: The numerator
        denominator: The denominator
        default: Value to return if denominator is zero (default: 0)

    Returns:
        Result of division or default value

    Example:
        ratio = safe_divide(wins, total_trades, default=0.0)
    """
    if denominator == 0:
        logger.warning(
            f"Division by zero avoided: {numerator} / {denominator}, "
            f"returning default value {default}"
        )
        return default

    return numerator / denominator


def clamp(
    value: Union[int, float],
    min_value: Union[int, float],
    max_value: Union[int, float]
) -> Union[int, float]:
    """
    Clamp a value between a minimum and maximum.

    Args:
        value: The value to clamp
        min_value: Minimum allowed value
        max_value: Maximum allowed value

    Returns:
        Clamped value

    Example:
        bet_size = clamp(calculated_size, min_bet, max_bet)
    """
    return max(min_value, min(value, max_value))


def format_currency(
    amount: Union[int, float, Decimal],
    currency: str = "USDC",
    decimals: int = 2
) -> str:
    """
    Format a numeric amount as a currency string.

    Args:
        amount: The amount to format
        currency: Currency symbol or code (default: "USDC")
        decimals: Number of decimal places (default: 2)

    Returns:
        Formatted currency string

    Example:
        formatted = format_currency(123.456, "USDC", 2)  # "123.46 USDC"
    """
    formatted_amount = f"{float(amount):.{decimals}f}"
    return f"{formatted_amount} {currency}"


def truncate_string(
    text: str,
    max_length: int = 50,
    suffix: str = "..."
) -> str:
    """
    Truncate a string to a maximum length, adding a suffix if truncated.

    Args:
        text: The string to truncate
        max_length: Maximum length before truncation (default: 50)
        suffix: Suffix to add if truncated (default: "...")

    Returns:
        Truncated string

    Example:
        short_desc = truncate_string(long_description, max_length=100)
    """
    if len(text) <= max_length:
        return text

    truncate_at = max_length - len(suffix)
    return text[:truncate_at] + suffix
