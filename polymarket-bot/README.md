# Polymarket Bot - Core Data Models

A Python package providing core data models for building automated trading bots on the Polymarket prediction market platform.

## Overview

This package provides validated, serializable data models using Pydantic v2 for:
- **Bot State Management**: Track operational status, configuration, and performance metrics
- **Trade Execution**: Record and manage trading transactions
- **Position Tracking**: Monitor open and closed positions with P&L calculations
- **Market Data**: Store and validate market information and pricing data

All models include comprehensive validation, type safety, and serialization support for logging and persistence.

## Features

- ✅ **Type-Safe Models**: Full type hints and Pydantic validation
- ✅ **Comprehensive Validation**: Field-level and cross-field validation
- ✅ **Serialization Support**: Easy conversion to/from dictionaries for logging and storage
- ✅ **Enumerations**: Type-safe enums for status values and options
- ✅ **Business Logic Methods**: Built-in helpers for common calculations (P&L, win rate, etc.)
- ✅ **Test Coverage**: Comprehensive test suite with 100% model coverage

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/test_models.py -v
```

## Models

### BotState

Tracks the bot's operational state and configuration.

**Key Features:**
- Bot identity and status tracking
- Strategy configuration
- Risk management parameters (position size, exposure, risk per trade)
- Performance metrics (total trades, win rate, P&L)
- System health monitoring (heartbeat, API status)

**Example:**
```python
from models import BotState, BotStatus
from decimal import Decimal

bot = BotState(
    bot_id="my_bot_001",
    status=BotStatus.RUNNING,
    strategy_name="momentum_v1",
    max_position_size=Decimal("1000.00"),
    max_total_exposure=Decimal("5000.00"),
    risk_per_trade=Decimal("100.00"),
    active_markets=["market_123", "market_456"],
    total_trades=42,
    winning_trades=28,
    total_pnl=Decimal("350.50")
)

# Calculate metrics
win_rate = bot.get_win_rate()  # 66.67%
print(f"Win Rate: {win_rate:.2f}%")

# Update heartbeat
bot.update_heartbeat()

# Serialize
bot_dict = bot.to_dict()
```

**Validations:**
- Current exposure cannot exceed max total exposure
- Winning trades cannot exceed total trades
- Risk parameters must be positive

### Trade

Represents a single trade execution on Polymarket.

**Key Features:**
- Order details (side, type, outcome)
- Pricing and quantity tracking
- Fill status and execution timestamps
- Fee calculation
- Metadata storage

**Example:**
```python
from models import Trade, OrderSide, OrderType, OutcomeType, TradeStatus
from decimal import Decimal

trade = Trade(
    trade_id="trade_001",
    market_id="market_123",
    order_id="order_456",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    outcome=OutcomeType.YES,
    price=Decimal("0.65"),
    quantity=Decimal("100.00"),
    filled_quantity=Decimal("100.00"),
    status=TradeStatus.EXECUTED,
    fee=Decimal("0.50")
)

# Check if fully filled
if trade.is_filled():
    print(f"Trade filled at {trade.price}")

# Calculate total cost
total_cost = trade.get_total_cost()  # 65.50 (price * quantity + fee)

# Serialize
trade_dict = trade.to_dict()
```

**Validations:**
- Price must be between 0 and 1 (probability range)
- Filled quantity cannot exceed total quantity
- Quantity must be positive

### Position

Tracks open and closed positions with P&L calculations.

**Key Features:**
- Position status (open, closed, partially closed)
- Entry and exit price tracking
- Real-time P&L calculations (realized and unrealized)
- Related trade tracking
- Position value calculation

**Example:**
```python
from models import Position, PositionStatus, OutcomeType
from decimal import Decimal

position = Position(
    position_id="pos_001",
    market_id="market_123",
    outcome=OutcomeType.YES,
    status=PositionStatus.OPEN,
    quantity=Decimal("100.00"),
    entry_price=Decimal("0.65"),
    current_price=Decimal("0.70"),
    trade_ids=["trade_001", "trade_002"]
)

# Update P&L with new market price
position.update_pnl(Decimal("0.75"))

# Get P&L metrics
total_pnl = position.get_total_pnl()  # Realized + unrealized
position_value = position.get_position_value()  # Quantity * current_price

print(f"Total P&L: ${total_pnl}")
print(f"Position Value: ${position_value}")

# Serialize
position_dict = position.to_dict()
```

**Validations:**
- Prices must be between 0 and 1
- Automatic P&L recalculation based on position status

### MarketData

Represents market information and pricing data from Polymarket.

**Key Features:**
- Market question and metadata
- Real-time pricing (yes/no outcome prices)
- Volume and liquidity tracking
- Market status and resolution
- Price validation and calculations

**Example:**
```python
from models import MarketData, OutcomeType
from decimal import Decimal
from datetime import datetime, timedelta

market = MarketData(
    market_id="market_123",
    question="Will Bitcoin reach $100k in 2024?",
    end_date=datetime.utcnow() + timedelta(days=30),
    yes_price=Decimal("0.65"),
    no_price=Decimal("0.35"),
    yes_volume=Decimal("150000.00"),
    no_volume=Decimal("85000.00"),
    total_liquidity=Decimal("50000.00"),
    category="crypto",
    tags=["bitcoin", "price-prediction"]
)

# Calculate metrics
total_volume = market.get_total_volume()  # 235000.00
price_spread = market.get_price_spread()  # 0.30

# Validate prices sum to approximately 1.0
is_valid = market.validate_prices_sum()  # True

# Serialize
market_dict = market.to_dict()
```

**Validations:**
- Prices must be between 0 and 1
- Helper method to validate prices sum to ~1.0

## Enumerations

### BotStatus
- `INITIALIZING`: Bot is starting up
- `RUNNING`: Bot is actively trading
- `PAUSED`: Bot is paused
- `STOPPED`: Bot has been stopped
- `ERROR`: Bot encountered an error

### OrderSide
- `BUY`: Buy order
- `SELL`: Sell order

### OrderType
- `MARKET`: Market order (immediate execution)
- `LIMIT`: Limit order (specific price)

### TradeStatus
- `PENDING`: Trade submitted but not executed
- `EXECUTED`: Trade successfully executed
- `CANCELLED`: Trade cancelled
- `FAILED`: Trade failed

### PositionStatus
- `OPEN`: Position is currently open
- `CLOSED`: Position is closed
- `PARTIALLY_CLOSED`: Position is partially closed

### OutcomeType
- `YES`: Yes outcome
- `NO`: No outcome

## Validation Examples

### Cross-Field Validation

```python
from models import BotState
from decimal import Decimal

# This will raise ValidationError: current exposure exceeds max
bot = BotState(
    bot_id="bot_001",
    strategy_name="test",
    max_position_size=Decimal("1000.00"),
    max_total_exposure=Decimal("5000.00"),
    risk_per_trade=Decimal("100.00"),
    current_exposure=Decimal("6000.00")  # Exceeds max!
)
```

### Price Range Validation

```python
from models import Trade, OrderSide, OrderType, OutcomeType
from decimal import Decimal

# This will raise ValidationError: price must be between 0 and 1
trade = Trade(
    trade_id="trade_001",
    market_id="market_123",
    order_id="order_456",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    outcome=OutcomeType.YES,
    price=Decimal("1.50"),  # Invalid price!
    quantity=Decimal("100.00")
)
```

## Serialization

All models implement a `to_dict()` method for easy serialization:

```python
from models import BotState, BotStatus
from decimal import Decimal
import json

bot = BotState(
    bot_id="bot_001",
    status=BotStatus.RUNNING,
    strategy_name="momentum_v1",
    max_position_size=Decimal("1000.00"),
    max_total_exposure=Decimal("5000.00"),
    risk_per_trade=Decimal("100.00")
)

# Convert to dictionary
bot_dict = bot.to_dict()

# Serialize to JSON
json_str = json.dumps(bot_dict, indent=2)
print(json_str)
```

## Testing

The package includes comprehensive tests covering:
- ✅ Model creation and validation
- ✅ Cross-field validation
- ✅ Business logic methods
- ✅ Serialization
- ✅ Integration scenarios

Run tests:
```bash
pytest tests/test_models.py -v

# With coverage
pytest tests/test_models.py --cov=models --cov-report=html
```

## Dependencies

- **pydantic[email]>=2.5.0**: Core validation and data models
- **pytest>=7.4.0**: Testing framework
- **pytest-cov>=4.1.0**: Test coverage reporting

## Usage in a Trading Bot

```python
from models import (
    BotState, BotStatus,
    Trade, OrderSide, OrderType, OutcomeType, TradeStatus,
    Position, PositionStatus,
    MarketData
)
from decimal import Decimal
from datetime import datetime

# Initialize bot state
bot = BotState(
    bot_id="momentum_bot_v1",
    status=BotStatus.INITIALIZING,
    strategy_name="momentum_v1",
    max_position_size=Decimal("1000.00"),
    max_total_exposure=Decimal("5000.00"),
    risk_per_trade=Decimal("100.00")
)

# Update status to running
bot.status = BotStatus.RUNNING
bot.update_heartbeat()

# Fetch and store market data
market = MarketData(
    market_id="market_123",
    question="Will Bitcoin reach $100k in 2024?",
    end_date=datetime(2024, 12, 31, 23, 59, 59),
    yes_price=Decimal("0.65"),
    no_price=Decimal("0.35"),
    yes_volume=Decimal("150000.00"),
    no_volume=Decimal("85000.00"),
    total_liquidity=Decimal("50000.00")
)

# Create a trade
trade = Trade(
    trade_id="trade_001",
    market_id=market.market_id,
    order_id="order_456",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    outcome=OutcomeType.YES,
    price=market.yes_price,
    quantity=Decimal("100.00")
)

# After execution, create position
position = Position(
    position_id="pos_001",
    market_id=market.market_id,
    outcome=OutcomeType.YES,
    quantity=trade.quantity,
    entry_price=trade.price,
    current_price=trade.price,
    trade_ids=[trade.trade_id]
)

# Update bot metrics
bot.active_markets.append(market.market_id)
bot.total_trades += 1
bot.current_exposure += trade.get_total_cost()

# Update position P&L with new market price
position.update_pnl(Decimal("0.70"))

# Update bot P&L
bot.total_pnl = position.get_total_pnl()

# Check if trade was profitable
if position.unrealized_pnl > 0:
    bot.winning_trades += 1

print(f"Bot Win Rate: {bot.get_win_rate():.2f}%")
print(f"Position P&L: ${position.get_total_pnl()}")
```

## Architecture Alignment

These models are designed to:
- Align with Polymarket API response formats
- Support logging and persistence through serialization
- Provide type safety and validation for trading operations
- Enable easy integration with bot strategy logic

## Future Enhancements

Potential future additions:
- SQLAlchemy ORM models for database persistence
- Additional validation rules based on Polymarket API constraints
- Performance analytics models
- Strategy configuration models
- Event/notification models

## License

This package is part of the Simple Spaghetti Website project and follows the same MIT License.

## Contributing

When adding new models or modifying existing ones:
1. Ensure all fields have proper type hints
2. Add field-level validation where appropriate
3. Implement `to_dict()` method for serialization
4. Include comprehensive tests
5. Update this README with examples
