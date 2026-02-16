# Polymarket Bot Utilities

This document describes the utility functions available in the `polymarket-bot/utils.py` module.

## Overview

The utilities module provides reusable functions for:
- **Retry Logic**: Exponential backoff for API calls
- **Validation**: Type checking, range validation, and data validation
- **Error Handling**: Consistent error logging and handling
- **Helper Functions**: Common operations like safe division, clamping, and formatting

## Retry Decorator

### `retry_with_backoff()`

Decorator that implements exponential backoff retry logic for API calls.

**Parameters:**
- `max_attempts` (int): Maximum number of retry attempts (default: 3)
- `base_delay` (float): Initial delay in seconds (default: 1.0)
- `max_delay` (float): Maximum delay between retries in seconds (default: 60.0)
- `exponential_base` (float): Base for exponential backoff calculation (default: 2.0)
- `exceptions` (tuple): Tuple of exceptions to catch and retry (default: (Exception,))
- `logger_name` (str, optional): Custom logger name for logging

**Example:**
```python
from polymarket_bot.utils import retry_with_backoff
import requests

@retry_with_backoff(max_attempts=5, base_delay=2.0)
def fetch_market_data(market_id: str):
    response = requests.get(f"https://api.polymarket.com/markets/{market_id}")
    response.raise_for_status()
    return response.json()
```

**Behavior:**
- First retry: waits `base_delay` seconds
- Second retry: waits `base_delay * exponential_base` seconds
- Third retry: waits `base_delay * exponential_base^2` seconds
- Maximum delay is capped at `max_delay`
- Raises `RetryError` when all attempts are exhausted

## Validation Functions

### `validate_type()`

Validates that a value matches the expected type.

**Parameters:**
- `value`: The value to validate
- `expected_type`: The expected type or tuple of types
- `field_name` (str): Name of the field for error messages (default: "value")

**Example:**
```python
from polymarket_bot.utils import validate_type

validate_type(user_id, int, "user_id")
validate_type(price, (int, float), "price")
```

### `validate_range()`

Validates that a numeric value is within a specified range.

**Parameters:**
- `value`: The numeric value to validate
- `min_value`: Minimum allowed value (None for no minimum)
- `max_value`: Maximum allowed value (None for no maximum)
- `field_name` (str): Name of the field for error messages (default: "value")
- `inclusive` (bool): Whether the range is inclusive (default: True)

**Example:**
```python
from polymarket_bot.utils import validate_range

validate_range(probability, 0.0, 1.0, "probability")
validate_range(amount, min_value=0, field_name="bet_amount")
```

### `validate_non_empty()`

Validates that a string, list, or dict is not empty.

**Parameters:**
- `value`: The value to validate
- `field_name` (str): Name of the field for error messages (default: "value")

**Example:**
```python
from polymarket_bot.utils import validate_non_empty

validate_non_empty(market_id, "market_id")
validate_non_empty(orders, "orders")
```

### `validate_decimal()`

Validates and converts a value to Decimal for precise financial calculations.

**Parameters:**
- `value`: The value to validate and convert
- `field_name` (str): Name of the field for error messages (default: "value")
- `allow_none` (bool): Whether None is an acceptable value (default: False)

**Returns:** Decimal representation of the value, or None if allow_none=True

**Example:**
```python
from polymarket_bot.utils import validate_decimal

price = validate_decimal("10.50", "price")
amount = validate_decimal(user_input, "bet_amount")
```

### `validate_probability()`

Validates that a value represents a valid probability (0.0 to 1.0).

**Parameters:**
- `value`: The probability value to validate
- `field_name` (str): Name of the field for error messages (default: "probability")

**Example:**
```python
from polymarket_bot.utils import validate_probability

validate_probability(0.75, "win_probability")
```

## Error Handling

### `handle_errors()`

Decorator for consistent error handling and logging.

**Parameters:**
- `default_return`: Value to return if an exception occurs (default: None)
- `log_level` (int): Logging level for caught exceptions (default: logging.ERROR)
- `raise_exception` (bool): Whether to re-raise the exception after logging (default: False)
- `logger_name` (str, optional): Custom logger name for logging

**Example:**
```python
from polymarket_bot.utils import handle_errors
import logging

@handle_errors(default_return={}, log_level=logging.WARNING)
def fetch_optional_data():
    return risky_api_call()
```

### `configure_logging()`

Configures logging with a consistent format.

**Parameters:**
- `level` (int): Logging level (default: logging.INFO)
- `format_string` (str, optional): Custom format string
- `logger_name` (str, optional): Name of the logger to configure

**Returns:** Configured logger instance

**Example:**
```python
from polymarket_bot.utils import configure_logging
import logging

logger = configure_logging(
    level=logging.DEBUG,
    logger_name="polymarket_bot"
)
```

## Helper Functions

### `safe_divide()`

Safely divides two numbers, returning a default value if division by zero occurs.

**Parameters:**
- `numerator`: The numerator
- `denominator`: The denominator
- `default`: Value to return if denominator is zero (default: 0)

**Example:**
```python
from polymarket_bot.utils import safe_divide

win_rate = safe_divide(wins, total_trades, default=0.0)
```

### `clamp()`

Clamps a value between a minimum and maximum.

**Parameters:**
- `value`: The value to clamp
- `min_value`: Minimum allowed value
- `max_value`: Maximum allowed value

**Example:**
```python
from polymarket_bot.utils import clamp

bet_size = clamp(calculated_size, min_bet, max_bet)
```

### `format_currency()`

Formats a numeric amount as a currency string.

**Parameters:**
- `amount`: The amount to format
- `currency` (str): Currency symbol or code (default: "USDC")
- `decimals` (int): Number of decimal places (default: 2)

**Example:**
```python
from polymarket_bot.utils import format_currency

formatted = format_currency(123.456, "USDC", 2)  # "123.46 USDC"
```

### `truncate_string()`

Truncates a string to a maximum length, adding a suffix if truncated.

**Parameters:**
- `text` (str): The string to truncate
- `max_length` (int): Maximum length before truncation (default: 50)
- `suffix` (str): Suffix to add if truncated (default: "...")

**Example:**
```python
from polymarket_bot.utils import truncate_string

short_desc = truncate_string(long_description, max_length=100)
```

## Exception Classes

### `RetryError`

Exception raised when retry attempts are exhausted.

**Inherits from:** Exception

### `ValidationError`

Exception raised when validation fails.

**Inherits from:** Exception

## Best Practices

1. **Use retry decorator for all external API calls** to handle transient failures
2. **Validate all user inputs and external data** to prevent errors and security issues
3. **Use Decimal for financial calculations** to avoid floating-point precision issues
4. **Configure logging consistently** across all modules
5. **Import utilities modularly** to keep dependencies minimal

## Testing

Comprehensive tests are available in `test_polymarket_utils.py`. Run tests with:

```bash
pytest test_polymarket_utils.py -v
```

The test suite covers:
- Retry logic with various failure scenarios
- All validation functions with edge cases
- Error handling with different configurations
- Logging configuration
- All helper functions
