# Polymarket Bot

Automated trading bot for Polymarket prediction markets with robust data models, utilities, and configuration management.

## Overview

This package provides:
- **Validated Data Models**: Type-safe Pydantic models for bot state, trades, positions, and market data
- **State Persistence**: JSON-based state management with atomic writes and crash recovery
- **Configuration Management**: Secure API key management and environment-based configuration
- **Utility Functions**: Retry logic, validation, error handling, and helper functions
- **Multi-Exchange Support**: Integration with Polymarket, Binance, and CoinGecko APIs
- **Technical Analysis**: Built-in TA-Lib support for technical indicators

## Features

### Core Data Models
- ✅ **Type-Safe Models**: Full type hints and Pydantic validation
- ✅ **Comprehensive Validation**: Field-level and cross-field validation
- ✅ **Serialization Support**: Easy conversion to/from dictionaries for logging and storage
- ✅ **Business Logic Methods**: Built-in helpers for common calculations (P&L, win rate, etc.)
- ✅ **Test Coverage**: Comprehensive test suite with 100% model coverage

### Polymarket API Integration
- ✅ **Market Discovery**: Search and filter active prediction markets
- ✅ **BTC Market Filtering**: Automatic discovery of Bitcoin-related markets
- ✅ **Odds Retrieval**: Real-time market odds and pricing data
- ✅ **Retry Logic**: Automatic retry with exponential backoff for API failures
- ✅ **Rate Limit Handling**: Monitor and respect API rate limits
- ✅ **Error Handling**: Comprehensive error handling for API interactions
- ✅ **Multiple Response Formats**: Parse various API response structures

### Technical Capabilities
- **Environment Configuration**: Secure API key management using `.env` files
- **WebSocket Support**: Real-time market data streaming
- **Configurable Risk Management**: Customizable position sizing and stop-loss parameters
- **Retry Logic**: Exponential backoff for resilient API calls
- **Validation Functions**: Type checking, range validation, and data validation
- **Error Handling**: Consistent error logging and handling across the bot

## Project Structure

```
polymarket-bot/
├── __init__.py            # Package initialization
├── config.py              # Configuration management
├── models.py              # Core data models (BotState, Trade, Position, MarketData)
├── market_data.py         # Polymarket API client for market discovery and odds
├── state.py               # State persistence and logging
├── utils.py               # Utility functions (retry, validation, error handling)
├── tests/                 # Comprehensive test suite
│   ├── test_models.py     # Model validation tests
│   ├── test_market_data.py # Polymarket API integration tests
│   └── test_state.py      # State persistence tests
├── test_config.py         # Configuration tests
└── README.md              # This file
```

## Installation

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

Note: TA-Lib requires system-level dependencies. On Ubuntu/Debian:

```bash
sudo apt-get install ta-lib
```

On macOS with Homebrew:

```bash
brew install ta-lib
```

2. Create your environment configuration:

```bash
cp .env.example .env
```

3. Edit `.env` and add your API keys:

```bash
# Required API keys
POLYMARKET_API_KEY=your_actual_key_here
POLYMARKET_API_SECRET=your_actual_secret_here
BINANCE_API_KEY=your_actual_key_here
BINANCE_API_SECRET=your_actual_secret_here
COINGECKO_API_KEY=your_actual_key_here
```

## Configuration

The bot uses environment variables for configuration. All required variables must be set in your `.env` file.

### Required Variables

- `POLYMARKET_API_KEY`: Your Polymarket API key
- `POLYMARKET_API_SECRET`: Your Polymarket API secret
- `BINANCE_API_KEY`: Your Binance API key
- `BINANCE_API_SECRET`: Your Binance API secret
- `COINGECKO_API_KEY`: Your CoinGecko API key

### Optional Variables (with defaults)

- `POLYMARKET_BASE_URL`: Polymarket API base URL (default: `https://api.polymarket.com`)
- `BINANCE_BASE_URL`: Binance API base URL (default: `https://api.binance.com`)
- `COINGECKO_BASE_URL`: CoinGecko API base URL (default: `https://api.coingecko.com/api/v3`)
- `MAX_POSITION_SIZE`: Maximum position size (default: `1000`)
- `RISK_PERCENTAGE`: Risk percentage per trade (default: `0.02` = 2%)
- `STOP_LOSS_PERCENTAGE`: Stop loss percentage (default: `0.05` = 5%)
- `WS_RECONNECT_DELAY`: WebSocket reconnection delay in seconds (default: `5`)
- `WS_MAX_RECONNECT_ATTEMPTS`: Maximum WebSocket reconnection attempts (default: `10`)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR, or CRITICAL (default: `INFO`)
- `LOG_FILE`: Log file path (default: `polymarket_bot.log`)

## Data Models

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

## Polymarket API Integration

The `market_data.py` module provides a complete Polymarket API client for market discovery, odds retrieval, and BTC market filtering.

### PolymarketClient

Client for interacting with the Polymarket API with built-in retry logic and error handling.

**Features:**
- Market discovery and search
- BTC-related market filtering
- Real-time odds retrieval
- Automatic retry logic with exponential backoff
- Rate limit awareness
- Comprehensive error handling

**Example Usage:**

```python
from market_data import PolymarketClient
from config import get_config

# Initialize client
config = get_config()
client = PolymarketClient(config)

# Get active markets
markets = client.get_active_markets(limit=100)
print(f"Found {len(markets)} active markets")

# Search for specific markets
btc_markets = client.search_markets("Bitcoin", limit=50)

# Get BTC-related markets (searches multiple keywords)
btc_markets = client.get_btc_markets(limit=50)

# Get specific market by ID
market = client.get_market_by_id("market_123")

# Get current odds for a market
yes_price, no_price = client.get_market_odds("market_123")
print(f"YES: {yes_price}, NO: {no_price}")

# Parse market data into MarketData model
market_data = client.parse_market_data(market)
print(f"Market: {market_data.question}")
print(f"Liquidity: ${market_data.total_liquidity}")

# Close client when done
client.close()
```

**Using as Context Manager:**

```python
from market_data import PolymarketClient
from config import get_config

config = get_config()

# Automatically closes connection
with PolymarketClient(config) as client:
    markets = client.get_btc_markets()
    for market in markets:
        market_data = client.parse_market_data(market)
        print(f"{market_data.question}: YES={market_data.yes_price}")
```

### Market Discovery Methods

#### get_active_markets(limit, offset, closed)
Fetch active markets from Polymarket.

```python
# Get first 100 active markets
markets = client.get_active_markets(limit=100, offset=0)

# Paginate through markets
markets_page_2 = client.get_active_markets(limit=100, offset=100)

# Include closed markets
all_markets = client.get_active_markets(closed=True)
```

#### search_markets(query, limit)
Search for markets matching a query string.

```python
# Search for Bitcoin markets
btc_markets = client.search_markets("Bitcoin", limit=50)

# Search for election markets
election_markets = client.search_markets("election", limit=25)
```

#### get_btc_markets(limit)
Fetch BTC-related prediction markets with automatic filtering.

Searches for multiple Bitcoin-related keywords ("BTC", "Bitcoin", "bitcoin") and:
- Deduplicates results
- Filters for active markets only
- Excludes closed or expired markets

```python
# Get top 50 BTC markets
btc_markets = client.get_btc_markets(limit=50)

# Process each market
for market in btc_markets:
    market_data = client.parse_market_data(market)
    if market_data.is_active:
        print(f"{market_data.question}: {market_data.yes_price}")
```

#### get_market_by_id(market_id)
Fetch a specific market by its unique identifier.

```python
market = client.get_market_by_id("0x1234567890abcdef")
market_data = client.parse_market_data(market)
```

### Odds Retrieval

#### get_market_odds(market_id)
Get current YES/NO odds for a specific market.

```python
yes_price, no_price = client.get_market_odds("market_123")
print(f"Market odds - YES: {yes_price}, NO: {no_price}")

# Verify prices sum to approximately 1.0
total = yes_price + no_price
if abs(total - 1.0) < 0.05:
    print("Prices are valid")
```

### Data Parsing

#### parse_market_data(market)
Parse raw API response into MarketData model with validation.

Handles multiple API response formats:
- Direct field names (e.g., `yes_price`, `no_price`)
- CamelCase field names (e.g., `yesPrice`, `noPrice`)
- Nested structures (e.g., `prices.yes`, `volumes.yes`)
- Outcomes arrays

```python
# Parse market data
raw_market = client.get_market_by_id("market_123")
market_data = client.parse_market_data(raw_market)

# Access parsed data
print(f"Question: {market_data.question}")
print(f"YES Price: {market_data.yes_price}")
print(f"NO Price: {market_data.no_price}")
print(f"Total Volume: ${market_data.get_total_volume()}")
print(f"Spread: {market_data.get_price_spread()}")
print(f"Active: {market_data.is_active}")
```

### Error Handling

The client includes comprehensive error handling:

```python
from market_data import PolymarketClient, PolymarketAPIError
from utils import ValidationError

try:
    client = PolymarketClient(config)

    # Handles HTTP errors, connection errors, rate limits
    markets = client.get_active_markets()

except PolymarketAPIError as e:
    print(f"API error: {e}")

except ValidationError as e:
    print(f"Validation error: {e}")
```

### Retry Logic

All API requests automatically retry with exponential backoff:
- **Max attempts:** 3
- **Base delay:** 1 second
- **Exponential backoff:** 2x multiplier
- **Handles:** Connection errors, timeouts, 5xx errors

```python
# Automatically retries on transient failures
@retry_with_backoff(max_attempts=3, base_delay=1.0)
def _make_request(self, method, endpoint, params=None, data=None):
    # Request implementation with automatic retry
    pass
```

### Rate Limit Handling

The client monitors rate limits when available:
- Logs remaining rate limit from API headers
- Respects rate limit restrictions
- Provides warnings when approaching limits

## State Persistence and Logging

The `state.py` module provides robust state management, trade logging, and metrics tracking with atomic writes and crash recovery.

### StateManager

The StateManager class handles:
- **JSON-based state persistence** with atomic writes
- **Trade history logging** with timestamps
- **Performance metrics tracking** (win/loss streaks, drawdown, total trades)
- **Crash recovery** using temporary files and renames

### Usage Example

```python
from state import StateManager, create_state_manager, recover_state
from models import BotState, Trade, OrderSide, OrderType, OutcomeType, TradeStatus, BotStatus
from decimal import Decimal

# Create state manager
state_manager = create_state_manager(state_dir="data")

# Initialize bot state
bot = BotState(
    bot_id="my_bot_001",
    status=BotStatus.RUNNING,
    strategy_name="momentum_v1",
    max_position_size=Decimal("1000.00"),
    max_total_exposure=Decimal("5000.00"),
    risk_per_trade=Decimal("100.00")
)

# Save state (atomic write)
state_manager.save_state(bot)

# Load state
loaded_state = state_manager.load_state()

# Validate loaded state
if loaded_state and state_manager.validate_state(loaded_state):
    print("State loaded successfully")

# Log a trade
trade = Trade(
    trade_id="trade_001",
    market_id="market_123",
    order_id="order_456",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    outcome=OutcomeType.YES,
    price=Decimal("0.65"),
    quantity=Decimal("100.00")
)
state_manager.log_trade(trade)

# Update metrics after trade
state_manager.update_metrics(
    trade_result="win",  # or "loss"
    pnl=Decimal("50.00"),
    current_equity=Decimal("1050.00")
)

# Get current metrics
metrics = state_manager.get_metrics()
print(f"Win Rate: {metrics['win_rate']:.2f}%")
print(f"Win Streak: {metrics['win_streak']}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")

# Save metrics to disk
state_manager.save_metrics()

# Load all trades
all_trades = state_manager.load_trades()
print(f"Total trades in log: {len(all_trades)}")
```

### Crash Recovery

The state manager uses atomic writes to prevent corruption during crashes:

```python
from state import recover_state, create_state_manager

# After a crash, attempt to recover state
state_manager = create_state_manager(state_dir="data")
recovered_state = recover_state(state_manager)

if recovered_state:
    print("Successfully recovered state from disk")
    # Reconstruct bot state from recovered data
    bot = BotState(**recovered_state)
else:
    print("No state to recover, starting fresh")
    # Initialize new bot state
```

### Atomic File Writes

All state and metrics saves use a temporary file + rename pattern:

1. Write to `bot_state.tmp` or `metrics.tmp`
2. Atomically rename to `bot_state.json` or `metrics.json`
3. If crash occurs during write, original file remains intact
4. Temporary files are automatically cleaned up on errors

### Metrics Tracked

- **win_streak**: Current consecutive wins
- **loss_streak**: Current consecutive losses
- **max_drawdown**: Maximum drawdown from peak equity
- **peak_equity**: Highest equity reached
- **total_trades**: Total number of trades
- **winning_trades**: Number of profitable trades
- **losing_trades**: Number of losing trades
- **win_rate**: Percentage of winning trades

### File Structure

```
data/
├── bot_state.json   # Current bot state (atomic writes)
├── metrics.json     # Performance metrics (atomic writes)
└── trades.log       # Trade history log (append-only)
```

## Utility Functions

### Configuration Management

```python
from config import get_config

# Get configuration instance
config = get_config()

# Access configuration values
print(f"Polymarket API URL: {config.polymarket_base_url}")
print(f"Max Position Size: {config.max_position_size}")
print(f"Risk Percentage: {config.risk_percentage}")
```

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
from config import get_config, ConfigurationError
import logging

# Configure logging
logger = configure_logging(level=logging.INFO, logger_name="polymarket_bot")

# Handle errors gracefully
@handle_errors(default_return={}, log_level=logging.WARNING)
def fetch_optional_data():
    return risky_api_call()

# Handle configuration errors
try:
    config = get_config()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    exit(1)
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

## Usage Example - Complete Trading Bot

```python
from models import (
    BotState, BotStatus,
    Trade, OrderSide, OrderType, OutcomeType, TradeStatus,
    Position, PositionStatus,
    MarketData
)
from polymarket_bot.utils import retry_with_backoff, validate_range, configure_logging
from config import get_config
from decimal import Decimal
from datetime import datetime
import logging

# Configure logging
logger = configure_logging(level=logging.INFO, logger_name="polymarket_bot")

# Load configuration
config = get_config()

# Initialize bot state
bot = BotState(
    bot_id="momentum_bot_v1",
    status=BotStatus.INITIALIZING,
    strategy_name="momentum_v1",
    max_position_size=Decimal(str(config.max_position_size)),
    max_total_exposure=Decimal("5000.00"),
    risk_per_trade=Decimal(str(config.max_position_size * config.risk_percentage))
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

## Testing

### Validate Configuration

Before running the bot, validate your configuration:

```bash
python config.py
```

This will check that all required environment variables are set and valid.

### Run Tests

The package includes comprehensive tests covering:
- ✅ Model creation and validation
- ✅ Cross-field validation
- ✅ Business logic methods
- ✅ Serialization
- ✅ State persistence and logging
- ✅ Atomic file writes and crash recovery
- ✅ Metrics tracking
- ✅ Configuration management
- ✅ Utility functions
- ✅ Polymarket API integration
- ✅ Market discovery and filtering
- ✅ Error handling and retry logic
- ✅ Integration scenarios

Run tests:
```bash
# All tests
pytest -v

# Specific test files
pytest tests/test_models.py -v
pytest tests/test_market_data.py -v
pytest tests/test_state.py -v
pytest test_config.py test_polymarket_utils.py -v

# With coverage
pytest tests/test_models.py --cov=models --cov-report=html
pytest tests/test_market_data.py --cov=market_data --cov-report=html
pytest tests/test_state.py --cov=state --cov-report=html
pytest test_config.py -v --cov=config --cov-report=html
```

## Dependencies

### Core Dependencies

- **pydantic[email]>=2.5.0**: Core validation and data models
- **python-dotenv**: Load environment variables from .env files
- **requests**: HTTP client for API calls
- **websocket-client**: WebSocket client for real-time data
- **TA-Lib**: Technical analysis library

### Development Dependencies

- **pytest>=7.4.0**: Testing framework
- **pytest-cov>=4.1.0**: Test coverage reporting
- **pytest-asyncio**: Async test support
- **black**: Code formatter
- **flake8**: Linter
- **mypy**: Type checker

See `requirements.txt` for full list with pinned versions.

## Security

- **Never commit your `.env` file** - it contains sensitive API keys
- The `.env.example` file is safe to commit and serves as a template
- API keys are not exposed in logs or error messages
- The `Config.__repr__()` method excludes sensitive values

## Development

### Adding New Models

When adding new models or modifying existing ones:
1. Ensure all fields have proper type hints
2. Add field-level validation where appropriate
3. Implement `to_dict()` method for serialization
4. Include comprehensive tests
5. Update this README with examples

### Adding New Utilities

1. Add the function to `utils.py` with comprehensive docstrings
2. Add corresponding tests to `test_polymarket_utils.py`
3. Update documentation in `docs/polymarket-bot/utilities.md`
4. Ensure utilities are modular and can be imported independently

### Code Quality

Format code with Black:

```bash
black config.py test_config.py models.py
```

Lint with flake8:

```bash
flake8 config.py test_config.py models.py
```

Type check with mypy:

```bash
mypy config.py models.py
```

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Provide detailed docstrings with examples
- Write comprehensive tests with edge cases

## Documentation

- [Utilities API Reference](../docs/polymarket-bot/utilities.md)
- [Main Project README](../README.md)

## Architecture Alignment

These models and utilities are designed to:
- Align with Polymarket API response formats
- Support logging and persistence through serialization
- Provide type safety and validation for trading operations
- Enable easy integration with bot strategy logic
- Provide resilient API interaction with retry mechanisms
- Ensure secure configuration management

## Future Enhancements

Potential future additions:
- SQLAlchemy ORM models for database persistence
- Additional validation rules based on Polymarket API constraints
- Performance analytics models
- Strategy configuration models
- Event/notification models
- Advanced technical analysis indicators
- Backtesting framework

## License

This package is part of the Simple Spaghetti Website project and follows the same MIT License.

## Contributing

See the main project README for contribution guidelines.
