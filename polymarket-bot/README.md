# Polymarket Bot

An automated trading bot for Polymarket prediction markets.

## Overview

The Polymarket Bot is designed to automate trading strategies on the Polymarket platform. It provides utilities for API interactions, data validation, error handling, and more.

## Project Structure

```
polymarket-bot/
├── __init__.py         # Package initialization
├── utils.py            # Utility functions (retry, validation, error handling)
└── README.md           # This file
```

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Modules

### `utils.py`

Provides reusable utility functions including:

- **Retry Logic**: `retry_with_backoff()` decorator with exponential backoff
- **Validation Functions**: Type checking, range validation, and data validation
- **Error Handling**: `handle_errors()` decorator and logging configuration
- **Helper Functions**: Safe division, clamping, currency formatting, etc.

See [utilities documentation](../docs/polymarket-bot/utilities.md) for detailed API reference.

## Usage Examples

### Retry Decorator

```python
from polymarket_bot.utils import retry_with_backoff

@retry_with_backoff(max_attempts=5, base_delay=2.0)
def fetch_market_data(market_id: str):
    # API call that might fail
    response = requests.get(f"https://api.polymarket.com/markets/{market_id}")
    response.raise_for_status()
    return response.json()
```

### Validation

```python
from polymarket_bot.utils import (
    validate_type,
    validate_range,
    validate_probability,
    validate_decimal
)

# Validate types
validate_type(user_id, int, "user_id")

# Validate ranges
validate_range(bet_amount, min_value=0, max_value=1000, field_name="bet_amount")

# Validate probabilities (0.0 to 1.0)
validate_probability(0.75, "win_probability")

# Convert to Decimal for precise calculations
price = validate_decimal("10.50", "price")
```

### Error Handling

```python
from polymarket_bot.utils import handle_errors, configure_logging
import logging

# Configure logging
logger = configure_logging(level=logging.INFO, logger_name="polymarket_bot")

# Handle errors gracefully
@handle_errors(default_return={}, log_level=logging.WARNING)
def fetch_optional_data():
    return risky_api_call()
```

### Helper Functions

```python
from polymarket_bot.utils import safe_divide, clamp, format_currency

# Safe division
win_rate = safe_divide(wins, total_trades, default=0.0)

# Clamp values
bet_size = clamp(calculated_size, min_bet=10, max_bet=1000)

# Format currency
display_amount = format_currency(123.456, "USDC", 2)  # "123.46 USDC"
```

## Testing

Run the test suite:

```bash
pytest test_polymarket_utils.py -v
```

## Development

### Adding New Utilities

1. Add the function to `utils.py` with comprehensive docstrings
2. Add corresponding tests to `test_polymarket_utils.py`
3. Update documentation in `docs/polymarket-bot/utilities.md`
4. Ensure utilities are modular and can be imported independently

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Provide detailed docstrings with examples
- Write comprehensive tests with edge cases

## Documentation

- [Utilities API Reference](../docs/polymarket-bot/utilities.md)

## License

See the main project README for license information.
