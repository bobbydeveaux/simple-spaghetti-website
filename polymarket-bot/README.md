# Polymarket Bot

Automated trading bot for Polymarket prediction markets with robust data models, utilities, and configuration management.

## Overview

This package provides:
- **Validated Data Models**: Type-safe Pydantic models for bot state, trades, positions, and market data
- **Configuration Management**: Secure API key management and environment-based configuration
- **Utility Functions**: Retry logic, validation, error handling, and helper functions
- **Multi-Exchange Support**: Integration with Polymarket, Binance, and CoinGecko APIs
- **Market Data Integration**: Real-time market discovery, odds retrieval, and technical indicators
- **Technical Analysis**: Built-in TA-Lib support for technical indicators (RSI, MACD)

## Features

### Core Data Models
- ✅ **Type-Safe Models**: Full type hints and Pydantic validation
- ✅ **Comprehensive Validation**: Field-level and cross-field validation
- ✅ **Serialization Support**: Easy conversion to/from dictionaries for logging and storage
- ✅ **Business Logic Methods**: Built-in helpers for common calculations (P&L, win rate, etc.)
- ✅ **Test Coverage**: Comprehensive test suite with 100% model coverage

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
├── __init__.py         # Package initialization
├── config.py           # Configuration management
├── models.py           # Core data models (BotState, Trade, Position, MarketData)
├── market_data.py      # Market data integration (PolymarketClient, BinanceWebSocketClient, indicators)
├── utils.py            # Utility functions (retry, validation, error handling)
├── tests/              # Comprehensive test suite
│   ├── test_models.py     # Model validation tests
│   └── test_market_data.py # Market data integration tests
├── test_config.py      # Configuration tests
└── README.md           # This file
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

## Market Data Integration

The `market_data` module provides comprehensive market data integration with Polymarket and Binance APIs, including technical indicator calculations.

### PolymarketClient

REST API client for discovering active markets and retrieving odds.

**Key Features:**
- Market discovery with BTC asset filtering
- Current odds retrieval for Yes/No positions
- Automatic retry logic with exponential backoff
- Data transformation to MarketData models
- Rate limit handling

**Example:**
```python
from market_data import PolymarketClient
from config import get_config

config = get_config()
client = PolymarketClient(
    api_key=config.polymarket_api_key,
    api_secret=config.polymarket_api_secret,
    base_url=config.polymarket_base_url
)

# Find active BTC markets
market_id = client.find_active_market("BTC")
if market_id:
    # Get current odds
    yes_odds, no_odds = client.get_market_odds(market_id)
    print(f"YES: {yes_odds}, NO: {no_odds}")

    # Get complete market details
    market_data = client.get_market_details(market_id)
    print(f"Question: {market_data.question}")
    print(f"Liquidity: ${market_data.total_liquidity}")

# Close client when done
client.close()
```

**API Methods:**
- `find_active_market(asset="BTC")`: Find active markets for the specified asset
- `get_market_odds(market_id)`: Retrieve current YES/NO odds
- `get_market_details(market_id)`: Get complete market information as MarketData object

**Error Handling:**
- Automatic retry on transient failures (3 attempts with exponential backoff)
- Graceful handling of rate limits (429 responses)
- Validation of probability values (must be 0.0 to 1.0)

### BinanceWebSocketClient

WebSocket client for real-time BTC price streaming from Binance.

**Key Features:**
- Real-time 1-minute kline (candlestick) data
- Price buffer for technical indicator calculations
- Automatic reconnection handling
- Thread-safe price access

**Example:**
```python
from market_data import BinanceWebSocketClient

# Initialize client
ws_client = BinanceWebSocketClient(symbol="btcusdt", buffer_size=100)

# Connect to WebSocket (in production, run in separate thread)
ws_client.connect()

# Get latest prices for indicator calculations
prices = ws_client.get_latest_prices(count=50)
if prices:
    latest_price = ws_client.get_latest_price()
    print(f"Current BTC price: ${latest_price}")

# Close when done
ws_client.close()
```

### Technical Indicators

Calculate RSI (Relative Strength Index) and MACD (Moving Average Convergence Divergence) for trend analysis.

**Calculate RSI:**
```python
from market_data import calculate_rsi

# Get price history from WebSocket client
prices = ws_client.get_latest_prices(count=100)

# Calculate 14-period RSI
rsi = calculate_rsi(prices, period=14)
if rsi:
    if rsi < 30:
        print(f"Oversold: RSI = {rsi:.2f}")
    elif rsi > 70:
        print(f"Overbought: RSI = {rsi:.2f}")
    else:
        print(f"Neutral: RSI = {rsi:.2f}")
```

**Calculate MACD:**
```python
from market_data import calculate_macd

# Get price history
prices = ws_client.get_latest_prices(count=100)

# Calculate MACD with default periods (12, 26, 9)
result = calculate_macd(prices)
if result:
    macd_line, signal_line = result

    if macd_line > signal_line:
        print("Bullish crossover detected")
    elif macd_line < signal_line:
        print("Bearish crossover detected")
```

### Order Book Imbalance

Calculate order book imbalance from Binance to gauge buying/selling pressure.

**Example:**
```python
from market_data import get_order_book_imbalance

imbalance = get_order_book_imbalance("BTCUSDT")
if imbalance:
    if imbalance > 1.1:
        print(f"Strong buying pressure: {imbalance:.2f}")
    elif imbalance < 0.9:
        print(f"Strong selling pressure: {imbalance:.2f}")
    else:
        print(f"Balanced order book: {imbalance:.2f}")
```

**Interpretation:**
- Imbalance > 1.0: More bid volume than ask volume (buying pressure)
- Imbalance < 1.0: More ask volume than bid volume (selling pressure)
- Imbalance ≈ 1.0: Balanced order book

### Complete Market Data Workflow

```python
from market_data import (
    PolymarketClient,
    BinanceWebSocketClient,
    calculate_rsi,
    calculate_macd,
    get_order_book_imbalance
)
from config import get_config
from models import MarketData

# Initialize clients
config = get_config()
poly_client = PolymarketClient(
    api_key=config.polymarket_api_key,
    api_secret=config.polymarket_api_secret
)
ws_client = BinanceWebSocketClient(symbol="btcusdt")

# Connect to Binance WebSocket
ws_client.connect()

# Wait for price data to accumulate (in production, run in background)
# time.sleep(60)

# Get technical indicators
prices = ws_client.get_latest_prices(100)
rsi = calculate_rsi(prices, period=14)
macd_result = calculate_macd(prices)
imbalance = get_order_book_imbalance("BTCUSDT")

# Find active Polymarket markets
market_id = poly_client.find_active_market("BTC")
if market_id:
    market_data = poly_client.get_market_details(market_id)

    print(f"Market: {market_data.question}")
    print(f"YES odds: {market_data.yes_price}")
    print(f"NO odds: {market_data.no_price}")
    print(f"RSI: {rsi:.2f}")

    if macd_result:
        macd_line, signal_line = macd_result
        print(f"MACD: {macd_line:.2f}, Signal: {signal_line:.2f}")

    print(f"Order book imbalance: {imbalance:.2f}")

# Cleanup
poly_client.close()
ws_client.close()
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
- ✅ Configuration management
- ✅ Utility functions
- ✅ Market data integration (API clients, indicators)
- ✅ Integration scenarios

Run tests:
```bash
# All tests
pytest -v

# Specific test files
pytest tests/test_models.py -v
pytest tests/test_market_data.py -v
pytest test_config.py -v

# With coverage
pytest tests/test_models.py --cov=models --cov-report=html
pytest tests/test_market_data.py --cov=market_data --cov-report=html
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
