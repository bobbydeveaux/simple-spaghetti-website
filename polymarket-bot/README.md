# Polymarket Bot

Automated trading bot for Polymarket prediction markets with robust data models, utilities, and configuration management.

## Overview

This package provides:
- **Validated Data Models**: Type-safe Pydantic models for bot state, trades, positions, and market data
- **State Persistence**: JSON-based state management with atomic writes and crash recovery
- **Configuration Management**: Secure API key management and environment-based configuration
- **State Persistence**: Atomic file operations with crash recovery and audit logging
- **Utility Functions**: Retry logic, validation, error handling, and helper functions
- **Multi-Exchange Support**: Integration with Polymarket, Binance, and CoinGecko APIs
- **Market Data Integration**: Real-time market discovery, odds retrieval, and technical indicators
- **Real-Time Market Data**: WebSocket streaming from Binance with automatic reconnection
- **Technical Analysis**: RSI, MACD indicators, and order book imbalance calculations using TA-Lib

## Features

### Core Data Models
- ✅ **Type-Safe Models**: Full type hints and Pydantic validation
- ✅ **Comprehensive Validation**: Field-level and cross-field validation
- ✅ **Serialization Support**: Easy conversion to/from dictionaries for logging and storage
- ✅ **Business Logic Methods**: Built-in helpers for common calculations (P&L, win rate, etc.)
- ✅ **Test Coverage**: Comprehensive test suite with 100% model coverage

### Prediction Engine
- ✅ **Rule-Based Signals**: Deterministic UP/DOWN/SKIP signal generation
- ✅ **Technical Indicators**: RSI (overbought/oversold) and MACD (momentum) analysis
- ✅ **Order Book Analysis**: Bid/ask imbalance for market pressure assessment
- ✅ **Confidence Scoring**: 0-100 confidence based on indicator agreement
- ✅ **Edge Case Handling**: Graceful handling of insufficient data and invalid inputs
- ✅ **Comprehensive Tests**: 40+ test cases covering all scenarios

### Market Data Integration
- ✅ **Binance WebSocket**: Real-time BTC/USDT price streaming with automatic reconnection
- ✅ **Technical Indicators**: RSI and MACD calculations for price analysis
- ✅ **Order Book Analysis**: Real-time order book imbalance metrics
- ✅ **Polymarket API**: Market discovery and odds retrieval
- ✅ **Unified Service Interface**: Single interface for all market data needs
- ✅ **Comprehensive Tests**: Integration tests verify complete data flow

### State Persistence & Logging
- ✅ **Atomic Writes**: Crash-safe file operations using temp file + rename pattern
- ✅ **Trade Audit Trail**: Append-only JSON Lines logging for complete trade history
- ✅ **Metrics Tracking**: Performance metrics logging with automatic rotation
- ✅ **Crash Recovery**: Automatic cleanup of temporary files on startup
- ✅ **Log Rotation**: Automatic rotation when files exceed 10MB (keeps 5 backups)
- ✅ **State Validation**: Full Pydantic validation on load/save operations

### Polymarket API Integration
- ✅ **Market Discovery**: Search and filter active prediction markets
- ✅ **BTC Market Filtering**: Automatic discovery of Bitcoin-related markets
- ✅ **Odds Retrieval**: Real-time market odds and pricing data
- ✅ **Retry Logic**: Automatic retry with exponential backoff for API failures
- ✅ **Rate Limit Handling**: Monitor and respect API rate limits
- ✅ **Error Handling**: Comprehensive error handling for API interactions
- ✅ **Multiple Response Formats**: Parse various API response structures

### Binance WebSocket Integration
- ✅ **Real-time BTC Price Feed**: Live BTC/USDT price updates via WebSocket
- ✅ **Automatic Reconnection**: Exponential backoff reconnection logic
- ✅ **Price History**: Configurable in-memory storage of recent price updates
- ✅ **Health Monitoring**: Connection health checks and message age validation
- ✅ **24h Statistics**: Volume, high, low, and price change tracking
- ✅ **Callback Support**: Custom handlers for price updates

### Risk Management System
- ✅ **Max Drawdown Monitoring**: Automatic tracking of 30% drawdown threshold from peak equity
- ✅ **Volatility Circuit Breaker**: 3% 5-minute price range checks to prevent trading in unstable markets
- ✅ **Pre-Trade Validation**: Comprehensive trade approval logic with detailed rejection reasons
- ✅ **Risk Metrics**: Real-time risk metrics including drawdown, exposure, and win rate
- ✅ **Configurable Thresholds**: Customizable risk parameters for different strategies
- ✅ **Peak Tracking**: Automatic peak capital tracking for accurate drawdown calculations
- ✅ **Position Sizing**: Dynamic calculation based on risk parameters and exposure limits
- ✅ **Market Validation**: Active market, liquidity, and closure checks
- ✅ **Comprehensive Testing**: 50+ test cases covering boundary conditions and edge cases

### Capital Allocation
- ✅ **Win-Streak Position Sizing**: Dynamic position sizing based on consecutive wins
- ✅ **Base Size**: $5 starting position with zero streak
- ✅ **Multiplier**: 1.5x scaling per consecutive win
- ✅ **Position Cap**: Maximum $25 position size regardless of streak
- ✅ **Capital Safety**: Automatic 50% capital constraint to prevent over-leverage
- ✅ **Streak Reset**: Automatic streak reset to zero on any loss
- ✅ **Configurable Parameters**: Customizable base size, multiplier, and maximum cap
- ✅ **Automatic Streak Tracking**: Integration with StateManager for win/loss tracking
- ✅ **Comprehensive Testing**: Full test coverage including edge cases and boundary conditions

### Technical Capabilities
- **Environment Configuration**: Secure API key management using `.env` files
- **WebSocket Streaming**: Real-time BTC/USDT price streaming from Binance with automatic reconnection
- **Technical Indicators**: RSI(14) and MACD calculations using TA-Lib for momentum analysis
- **Order Book Analysis**: Real-time bid/ask imbalance calculations for market pressure detection
- **Prediction Engine**: Deterministic signal generation based on RSI, MACD, and order book imbalance
- **Multi-Source Data**: Aggregates data from Binance, Polymarket, with CoinGecko fallback
- **Configurable Risk Management**: Customizable position sizing and stop-loss parameters
- **Retry Logic**: Exponential backoff for resilient API calls and WebSocket reconnection
- **Validation Functions**: Type checking, range validation, and data validation
- **Error Handling**: Consistent error logging and handling across the bot

## Project Structure

```
polymarket-bot/
├── __init__.py                 # Package initialization
├── config.py                   # Configuration management
├── models.py                   # Core data models (BotState, Trade, Position, MarketData, BTCPriceData, PredictionSignal)
├── market_data.py              # Market data service (Binance WebSocket, Polymarket API, technical indicators)
├── prediction.py               # Prediction engine (RSI/MACD-based signal generation)
├── risk.py                     # Risk management system (drawdown, volatility, trade approval)
├── capital.py                  # Capital allocation with win-streak position sizing
├── state.py                    # State persistence and logging
├── utils.py                    # Utility functions (retry, validation, error handling)
├── tests/                      # Comprehensive test suite
│   ├── test_models.py          # Model validation tests (including BTCPriceData, PredictionSignal)
│   ├── test_market_data.py     # Market data service and Polymarket API tests
│   ├── test_binance_websocket.py # Binance WebSocket tests
│   ├── test_prediction.py      # Prediction engine tests
│   ├── test_risk.py            # Risk management tests
│   ├── test_capital.py         # Capital allocation tests
│   └── test_state.py           # State persistence tests
├── test_config.py              # Configuration tests
├── test_risk.py                # Risk management tests
└── README.md                   # This file
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

### Prediction Engine Configuration

- `RSI_PERIOD`: RSI calculation period (default: `14`)
- `RSI_OVERSOLD_THRESHOLD`: RSI oversold threshold for UP signals (default: `30.0`)
- `RSI_OVERBOUGHT_THRESHOLD`: RSI overbought threshold for DOWN signals (default: `70.0`)
- `MACD_FAST_PERIOD`: MACD fast period (default: `12`)
- `MACD_SLOW_PERIOD`: MACD slow period (default: `26`)
- `MACD_SIGNAL_PERIOD`: MACD signal period (default: `9`)
- `ORDER_BOOK_BULLISH_THRESHOLD`: Order book imbalance threshold for bullish signals (default: `1.1`)
- `ORDER_BOOK_BEARISH_THRESHOLD`: Order book imbalance threshold for bearish signals (default: `0.9`)
- `PREDICTION_CONFIDENCE_SCORE`: Confidence score for actionable signals (default: `0.75`)

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

### BTCPriceData

Represents Bitcoin price data from Binance WebSocket feed.

**Key Features:**
- Real-time BTC/USDT price updates
- 24-hour trading statistics (volume, high, low)
- Price change tracking
- Volatility calculations
- Metadata storage for raw exchange data

**Example:**
```python
from models import BTCPriceData
from decimal import Decimal
from datetime import datetime

price_data = BTCPriceData(
    symbol="BTCUSDT",
    price=Decimal("45678.90"),
    timestamp=datetime.utcnow(),
    volume_24h=Decimal("123456789.50"),
    high_24h=Decimal("46000.00"),
    low_24h=Decimal("45000.00"),
    price_change_24h=Decimal("678.90"),
    price_change_percent_24h=Decimal("1.51")
)

# Calculate mid-range price
mid_range = price_data.get_mid_range_price()  # 45500.00

# Calculate volatility percentage
volatility = price_data.get_volatility_percent()  # ~2.20%

# Serialize
price_dict = price_data.to_dict()
```

**Validations:**
- Price must be greater than 0
- Optional 24h statistics (volume, high, low) must be non-negative if provided

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

REST API client for discovering active markets and retrieving odds with built-in retry logic and error handling.

**Key Features:**
- Secure HMAC-SHA256 request signing for API authentication
- Market discovery and search
- BTC-related market filtering
- Real-time odds retrieval
- Automatic retry logic with exponential backoff
- Data transformation to MarketData models
- Rate limit awareness and handling
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

## Binance WebSocket Integration

The `market_data.py` module includes a `BinanceWebSocket` client for real-time BTC/USDT price feed from Binance.

### BinanceWebSocket

WebSocket client for receiving real-time Bitcoin price updates from Binance with automatic reconnection and historical price tracking.

**Features:**
- Real-time BTC/USDT price updates via WebSocket
- Automatic reconnection with exponential backoff
- Configurable price history storage (default: 200 updates)
- Message parsing and validation
- Health monitoring
- Callback support for custom price handlers
- Context manager support

**Example Usage:**

```python
from market_data import BinanceWebSocket
from models import BTCPriceData

# Initialize WebSocket with custom callback
def on_price_update(price_data: BTCPriceData):
    print(f"BTC Price: ${price_data.price}")
    print(f"24h Change: {price_data.price_change_percent_24h}%")

ws = BinanceWebSocket(
    on_price_update=on_price_update,
    history_size=200
)

# Connect to Binance WebSocket
ws.connect()

# Get latest price
latest = ws.get_latest_price()
if latest:
    print(f"Current BTC: ${latest.price}")

# Get price history
history = ws.get_price_history(limit=50)
print(f"Received {len(history)} price updates")

# Get price series for technical analysis
prices = ws.get_price_series(limit=100)

# Check connection health
if ws.is_healthy():
    print("WebSocket connection is healthy")

# Disconnect when done
ws.disconnect()
```

**Using as Context Manager:**

```python
from market_data import BinanceWebSocket

# Automatically connects and disconnects
with BinanceWebSocket(history_size=100) as ws:
    # Wait for some price updates
    import time
    time.sleep(5)

    # Get latest price
    latest = ws.get_latest_price()
    if latest:
        print(f"BTC: ${latest.price}")
        print(f"Volatility: {latest.get_volatility_percent()}%")
```

### WebSocket Methods

#### connect()
Connect to Binance WebSocket and start receiving price updates in a background thread.

```python
ws = BinanceWebSocket()
ws.connect()
```

#### disconnect()
Gracefully disconnect from WebSocket and stop reconnection attempts.

```python
ws.disconnect()
```

#### get_latest_price()
Get the most recent BTC price update.

```python
latest = ws.get_latest_price()
if latest:
    print(f"Price: ${latest.price}")
    print(f"High 24h: ${latest.high_24h}")
    print(f"Low 24h: ${latest.low_24h}")
```

#### get_price_history(limit)
Get historical price data stored in memory.

```python
# Get all history
all_history = ws.get_price_history()

# Get last 50 updates
recent = ws.get_price_history(limit=50)
```

#### get_price_series(limit)
Get price values as a list of Decimal objects (useful for technical indicators).

```python
# Get last 100 prices
prices = ws.get_price_series(limit=100)

# Calculate simple moving average
if len(prices) >= 20:
    sma_20 = sum(prices[-20:]) / 20
    print(f"SMA(20): ${sma_20}")
```

#### is_healthy(max_message_age_seconds)
Check if WebSocket connection is healthy and receiving recent updates.

```python
# Check with default 60s timeout
if ws.is_healthy():
    print("Connection healthy")

# Check with custom timeout
if ws.is_healthy(max_message_age_seconds=120):
    print("Received update in last 2 minutes")
```

### Automatic Reconnection

The WebSocket client automatically handles disconnections:
- **Exponential backoff**: Delays increase for successive failures (max 5 minutes)
- **Infinite retries**: Continues reconnecting until manually stopped
- **Connection tracking**: Monitors connection state and error count

```python
ws = BinanceWebSocket()
ws.connect()

# WebSocket will automatically reconnect if disconnected
# To stop reconnection attempts:
ws.disconnect()
```

### Message Format

The WebSocket receives 24hr ticker data from Binance:

```json
{
  "e": "24hrTicker",
  "E": 1705318800000,
  "s": "BTCUSDT",
  "p": "678.90",
  "P": "1.51",
  "c": "45678.90",
  "h": "46000.00",
  "l": "45000.00",
  "q": "123456789.50"
}
```

This is automatically parsed into `BTCPriceData` model instances.

## Prediction Engine

The `prediction.py` module implements a deterministic rule-based signal generator that produces trading signals based on technical indicators and market analysis.

### Features

- **Technical Indicator Analysis**: RSI (Relative Strength Index) and MACD (Moving Average Convergence Divergence)
- **Order Book Analysis**: Bid/Ask imbalance for market pressure assessment
- **Confidence Scoring**: 0-100 confidence scores based on indicator agreement
- **Class-Based API**: `PredictionEngine` class for stateful prediction generation
- **Edge Case Handling**: Graceful handling of insufficient data, invalid inputs, and conflicting signals
- **Deterministic**: Same inputs always produce same outputs (no randomness)

### Signal Types

The prediction engine generates three types of signals:

- **UP**: Bullish signal indicating price expected to rise
- **DOWN**: Bearish signal indicating price expected to fall
- **SKIP**: No clear signal or conflicting indicators

### Confidence Levels

Confidence scores are calculated based on indicator conditions and configuration thresholds.

## Capital Allocation

The `capital.py` module implements win-streak capital allocation logic for position sizing. Position sizes scale with consecutive winning trades using a multiplier system, with a maximum cap to manage risk.

### Win-Streak Position Sizing

The capital allocator uses the following formula:

```
position_size = min(base_size * (multiplier ** win_streak), max_size)
```

**Default Parameters:**
- **Base Size**: $5.00
- **Multiplier**: 1.5x per consecutive win
- **Maximum Size**: $25.00 (position cap)

**Position Size Progression:**
- Streak 0 (first trade or after loss): $5.00
- Streak 1 (after 1 win): $7.50
- Streak 2 (after 2 consecutive wins): $11.25
- Streak 3 (after 3 consecutive wins): $16.88
- Streak 4+ (capped): $25.00

### CapitalAllocator Class

The `CapitalAllocator` class provides position sizing with configurable parameters:

```python
from capital import CapitalAllocator
from decimal import Decimal

# Initialize with default parameters
allocator = CapitalAllocator()

# Or customize parameters
allocator = CapitalAllocator(
    base_size=Decimal("10.00"),
    multiplier=Decimal("2.0"),
    max_size=Decimal("50.00")
)

# Calculate position size based on win streak
position_size = allocator.calculate_position_size(win_streak=2)
print(f"Position size: ${position_size}")  # Output: Position size: $11.25

# With capital safety check (never exceed 50% of available capital)
position_size = allocator.calculate_position_size(
    win_streak=2,
    current_capital=Decimal("100.00")
)
```

### Standalone Functions

For convenience, standalone functions are available:

```python
from capital import calculate_position_size
from decimal import Decimal

# Simple usage
size = calculate_position_size(win_streak=1)
print(f"${size}")  # Output: $7.50

# With custom parameters
size = calculate_position_size(
    win_streak=2,
    current_capital=Decimal("100.00"),
    base_size=Decimal("5.00"),
    multiplier=Decimal("1.5"),
    max_size=Decimal("25.00")
)
```

### Integration with StateManager

The capital allocator integrates with the `StateManager` to track win streaks:

```python
from state import StateManager
from capital import calculate_position_size

# Create state manager
state_manager = StateManager(state_dir="data")

# Get current win streak from metrics
metrics = state_manager.get_metrics()
win_streak = metrics['win_streak']

# Calculate position size
position_size = calculate_position_size(win_streak)

# After a winning trade
state_manager.update_metrics(
    trade_result="win",
    pnl=Decimal("5.50"),
    current_equity=Decimal("105.50")
)

# After a losing trade (resets streak to 0)
state_manager.update_metrics(
    trade_result="loss",
    pnl=Decimal("-3.25"),
    current_equity=Decimal("102.25")
)
```

### Streak Management

The allocator provides methods for streak management:

```python
allocator = CapitalAllocator()

# Increment streak after a win
current_streak = 2
new_streak = allocator.increment_streak(current_streak)
print(new_streak)  # Output: 3

# Reset streak after a loss
new_streak = allocator.reset_streak()
print(new_streak)  # Output: 0
```

### Safety Features

1. **Maximum Cap**: Position size is capped at `max_size` regardless of win streak
2. **Capital Safety Check**: Position size never exceeds 50% of current capital
3. **Parameter Validation**: Invalid parameters raise `ValueError` on initialization
4. **Negative Streak Protection**: Negative win streaks are rejected

### Prediction Engine Usage Example

```python
from prediction import PredictionEngine, generate_signal_from_market_data
from models import SignalType

# Initialize prediction engine
engine = PredictionEngine()

# Generate signal from price history
prices = [50000.0, 50100.0, 50200.0, ...]  # Historical prices
prediction = engine.generate_signal(prices=prices, btc_price=50250.0)

print(f"Signal: {prediction.signal.value}")  # "up", "down", or "skip"
print(f"Confidence: {prediction.confidence}")
print(f"Reasoning: {prediction.reasoning}")

# Act on the signal
if prediction.signal == SignalType.UP and prediction.confidence >= 60:
    print("Strong bullish signal - consider buying")
elif prediction.signal == SignalType.DOWN and prediction.confidence >= 60:
    print("Strong bearish signal - consider selling")
else:
    print("No clear signal - skip this opportunity")
```

### Indicator Thresholds

The prediction engine uses configurable thresholds for signal generation:

**RSI (Relative Strength Index)**
- **Oversold**: RSI < configured threshold (default 30) - contributes to UP signal
- **Overbought**: RSI > configured threshold (default 70) - contributes to DOWN signal

**MACD (Moving Average Convergence Divergence)**
- **Bullish**: MACD line > signal line - contributes to UP signal
- **Bearish**: MACD line < signal line - contributes to DOWN signal

**Order Book Imbalance**
- **Buying Pressure**: bid/ask > configured threshold (default 1.1) - contributes to UP signal
- **Selling Pressure**: bid/ask < configured threshold (default 0.9) - contributes to DOWN signal

### Testing

The prediction engine includes comprehensive test cases covering:

- Signal generation based on indicator conditions
- Confidence score calculation
- Edge cases (invalid inputs, insufficient data)
- Realistic trading scenarios
- Integration with configuration

Run tests:
```bash
pytest tests/test_prediction.py -v
```

## Capital Allocation - Full Usage Example

```python
from capital import CapitalAllocator, calculate_position_size
from state import StateManager
from decimal import Decimal

# Initialize components
allocator = CapitalAllocator()
state_manager = StateManager(state_dir="data")

# Trading loop
for trade_number in range(10):
    # Get current metrics
    metrics = state_manager.get_metrics()
    win_streak = metrics['win_streak']

    # Calculate position size
    position_size = allocator.calculate_position_size(win_streak)

    print(f"Trade {trade_number + 1}: Win Streak = {win_streak}, Position Size = ${position_size}")

    # Simulate trade execution and result
    # ... (execute trade)

    # Update metrics based on trade result
    trade_result = "win" if trade_number % 3 != 0 else "loss"  # Example
    pnl = Decimal("5.00") if trade_result == "win" else Decimal("-3.00")

    state_manager.update_metrics(
        trade_result=trade_result,
        pnl=pnl,
        current_equity=Decimal("100.00") + pnl * (trade_number + 1)
    )
```

### Capital Allocation Testing

The capital allocation module includes comprehensive tests in `tests/test_capital.py`:

```bash
pytest tests/test_capital.py -v
```

**Test Coverage:**
- Base position sizing (streak = 0)
- Win-streak multiplier scaling (streaks 1-5+)
- Maximum cap enforcement
- Capital safety checks
- Parameter validation
- Edge cases and boundary conditions
- Integration with BotState
- Acceptance criteria verification
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

## Capital Allocation

The capital allocation module implements dynamic position sizing based on win-streak scaling. This approach rewards consecutive wins with larger positions while maintaining strict safety limits.

### Position Sizing Formula

```
position_size = min(base_size * (multiplier ^ win_streak), max_size)
```

**Constants:**
- **BASE_SIZE**: $5.00 (starting position with zero streak)
- **MULTIPLIER**: 1.5x (scaling per consecutive win)
- **MAX_SIZE**: $25.00 (maximum position cap)

**Additional Safety:** Position size is also capped at 50% of current capital to prevent over-leverage.

### Win-Streak Progression

| Streak | Formula | Position Size | Capped At |
|--------|---------|---------------|-----------|
| 0 | 5.0 × 1.5⁰ | $5.00 | - |
| 1 | 5.0 × 1.5¹ | $7.50 | - |
| 2 | 5.0 × 1.5² | $11.25 | - |
| 3 | 5.0 × 1.5³ | $16.88 | - |
| 4 | 5.0 × 1.5⁴ | $25.31 | $25.00 |
| 5+ | 5.0 × 1.5⁵⁺ | >$25.00 | $25.00 |

### Usage

```python
from polymarket_bot.capital import calculate_position_size, update_win_streak

# Mock bot state with current capital and win streak
class BotState:
    def __init__(self, current_capital, win_streak):
        self.current_capital = current_capital
        self.win_streak = win_streak

# Calculate position size for new trade
bot_state = BotState(current_capital=100.0, win_streak=0)
position = calculate_position_size(bot_state)
print(f"Position size: ${position}")  # $5.00

# After a winning trade
bot_state.win_streak = update_win_streak(bot_state, "WIN")
position = calculate_position_size(bot_state)
print(f"Position size after win: ${position}")  # $7.50

# After a losing trade (streak resets)
bot_state.win_streak = update_win_streak(bot_state, "LOSS")
position = calculate_position_size(bot_state)
print(f"Position size after loss: ${position}")  # $5.00 (back to base)
```

### Utility Function

For testing or analysis, use `get_position_size_for_streak` to calculate position sizes without modifying bot state:

```python
from polymarket_bot.capital import get_position_size_for_streak

# Calculate position for various streaks
for streak in range(6):
    size = get_position_size_for_streak(streak)
    print(f"Streak {streak}: ${size:.2f}")

# Output:
# Streak 0: $5.00
# Streak 1: $7.50
# Streak 2: $11.25
# Streak 3: $16.88
# Streak 4: $25.00
# Streak 5: $25.00 (capped)
```

### Capital Safety Features

1. **Maximum Position Cap**: No position exceeds $25 regardless of streak length
2. **Capital Constraint**: Position size limited to 50% of current capital
3. **Automatic Streak Reset**: Any loss resets the win streak to zero
4. **Low Capital Protection**: With capital < $10, positions automatically scale down

### Example Scenarios

**Scenario 1: Normal Trading**
```python
bot = BotState(current_capital=100.0, win_streak=2)
position = calculate_position_size(bot)  # $11.25
```

**Scenario 2: Low Capital Constraint**
```python
bot = BotState(current_capital=20.0, win_streak=2)
position = calculate_position_size(bot)  # $10.00 (50% of $20, not $11.25)
```

**Scenario 3: Very High Streak**
```python
bot = BotState(current_capital=100.0, win_streak=10)
position = calculate_position_size(bot)  # $25.00 (capped at max)
```

**Scenario 4: Win-Loss Pattern**
```python
bot = BotState(current_capital=100.0, win_streak=0)

# Win 1
bot.win_streak = update_win_streak(bot, "WIN")  # streak = 1
pos1 = calculate_position_size(bot)  # $7.50

# Win 2
bot.win_streak = update_win_streak(bot, "WIN")  # streak = 2
pos2 = calculate_position_size(bot)  # $11.25

# Loss (resets streak)
bot.win_streak = update_win_streak(bot, "LOSS")  # streak = 0
pos3 = calculate_position_size(bot)  # $5.00 (back to base)
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

## Market Data Service

The `market_data.py` module provides real-time market data integration with WebSocket streaming, technical indicators, Polymarket API integration, and multi-exchange support.

### BinanceWebSocketClient

Real-time BTC/USDT price streaming via WebSocket with automatic reconnection.

**Features:**
- WebSocket connection to Binance with automatic reconnection
- Rolling price buffer for technical indicator calculations
- Thread-safe price retrieval
- Configurable reconnection attempts and delays
- Exponential backoff for connection failures

**Example:**

```python
from market_data import BinanceWebSocketClient

# Initialize and connect
client = BinanceWebSocketClient(buffer_size=100)
client.connect()

# Wait for price data to accumulate
import time
time.sleep(5)

# Get latest prices for indicator calculations
prices = client.get_latest_prices(count=50)
print(f"Collected {len(prices)} prices")

# Get single latest price
latest_price = client.get_latest_price()
print(f"Current BTC price: ${latest_price:.2f}")

# Close connection when done
client.close()
```

**Configuration:**
- `WS_RECONNECT_DELAY`: Seconds between reconnection attempts (default: 5)
- `WS_MAX_RECONNECT_ATTEMPTS`: Maximum reconnection attempts (default: 10)

### PolymarketClient

REST API client for Polymarket market discovery and odds retrieval with built-in retry logic and error handling.

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

### Technical Indicators

Calculate RSI and MACD indicators using TA-Lib for technical analysis.

**RSI (Relative Strength Index):**

```python
from market_data import calculate_rsi

# Calculate RSI from price data
prices = [45000, 45100, 45050, ...]  # List of prices
rsi = calculate_rsi(prices, period=14)

print(f"RSI(14): {rsi:.2f}")

# Interpret RSI
if rsi > 70:
    print("Overbought condition")
elif rsi < 30:
    print("Oversold condition")
```

**MACD (Moving Average Convergence Divergence):**

```python
from market_data import calculate_macd

# Calculate MACD
prices = [45000, 45100, 45050, ...]  # Need at least 34 prices
macd_line, signal_line = calculate_macd(prices)

print(f"MACD: {macd_line:.2f}, Signal: {signal_line:.2f}")

# Interpret MACD
if macd_line > signal_line:
    print("Bullish crossover - potential buy signal")
else:
    print("Bearish crossover - potential sell signal")
```

### Order Book Imbalance

Calculate bid/ask volume ratio to measure market pressure.

**Example:**

```python
from market_data import get_order_book_imbalance

# Get current order book imbalance
imbalance = get_order_book_imbalance()

print(f"Order book imbalance: {imbalance:.4f}")

# Interpret imbalance
if imbalance > 1.1:
    print("Strong buying pressure")
elif imbalance < 0.9:
    print("Strong selling pressure")
else:
    print("Neutral market")
```

### Market Data Aggregation

Combine all data sources into a single MarketData object.

**Example:**

```python
from market_data import (
    BinanceWebSocketClient,
    PolymarketClient,
    get_market_data
)
from config import get_config

# Initialize clients
config = get_config()
binance_client = BinanceWebSocketClient()
binance_client.connect()

polymarket_client = PolymarketClient(
    api_key=config.polymarket_api_key,
    api_secret=config.polymarket_api_secret
)

# Wait for price data to accumulate
import time
time.sleep(10)

# Aggregate all market data
market_data = get_market_data(
    binance_client=binance_client,
    polymarket_client=polymarket_client,
    market_id="market_123"  # Optional - will search if not provided
)

# Access aggregated data
print(f"Market: {market_data.market_id}")
print(f"YES odds: {market_data.yes_price}")
print(f"NO odds: {market_data.no_price}")

# Access technical indicators from metadata
print(f"BTC Price: ${market_data.metadata['btc_price']:.2f}")
print(f"RSI(14): {market_data.metadata['rsi_14']:.2f}")
print(f"MACD: {market_data.metadata['macd_line']:.2f}")
print(f"Signal: {market_data.metadata['macd_signal']:.2f}")
print(f"Order Book Imbalance: {market_data.metadata['order_book_imbalance']:.4f}")

# Clean up
binance_client.close()
```

### Fallback Price Retrieval

CoinGecko fallback when Binance is unavailable.

**Example:**

```python
from market_data import get_fallback_btc_price

try:
    # Use as fallback when WebSocket fails
    btc_price = get_fallback_btc_price()
    print(f"BTC price from CoinGecko: ${btc_price:.2f}")
except ConnectionError as e:
    print(f"Fallback failed: {e}")
```

### Error Handling

The market_data module implements robust error handling:

- **WebSocket disconnections**: Automatic reconnection with exponential backoff
- **API failures**: Retry logic with configurable attempts
- **Insufficient data**: Clear error messages for indicator calculations
- **Zero division**: Safe handling of edge cases in calculations
- **HTTP errors**: Comprehensive error handling for API interactions
- **Rate limits**: Monitoring and respect for API rate limits

**Example:**

```python
from market_data import calculate_rsi, PolymarketClient, PolymarketAPIError
from config import get_config

# Technical indicator error handling
try:
    prices = [100, 101, 102]  # Too few prices
    rsi = calculate_rsi(prices, period=14)
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Insufficient price data for RSI calculation. Need at least 15 prices, got 3"

# API error handling
try:
    config = get_config()
    client = PolymarketClient(config)
    markets = client.get_active_markets()
except PolymarketAPIError as e:
    print(f"API error: {e}")
```

## Prediction Engine

The `prediction.py` module provides deterministic signal generation based on technical indicators. It analyzes RSI, MACD, and order book imbalance to generate actionable UP/DOWN signals or SKIP when conditions aren't met.

### PredictionEngine

Main prediction engine class that generates trading signals with confidence scores and reasoning.

**Features:**
- Deterministic signal generation (no probabilistic models)
- Configurable RSI, MACD, and order book thresholds
- Confidence scoring for signal reliability
- Human-readable reasoning for transparency
- Comprehensive error handling and data validation

**Signal Logic:**

```
UP Signal (Bullish):
  RSI < oversold_threshold (default: 30)
  AND MACD line > MACD signal (bullish crossover)
  AND order book imbalance > bullish_threshold (default: 1.1)

DOWN Signal (Bearish):
  RSI > overbought_threshold (default: 70)
  AND MACD line < MACD signal (bearish crossover)
  AND order book imbalance < bearish_threshold (default: 0.9)

SKIP Signal:
  All other conditions (no clear directional signal)
```

**Example Usage:**

```python
from prediction import PredictionEngine
from config import get_config

# Initialize engine
config = get_config()
engine = PredictionEngine(config=config)

# Generate signal from price data
prices = [45000, 45100, 45050, ...]  # Historical prices (oldest to newest)
signal = engine.generate_signal(prices, btc_price=45678.90)

# Check signal
print(f"Signal: {signal.signal.value.upper()}")  # UP, DOWN, or SKIP
print(f"Confidence: {signal.confidence}")  # 0.75 for UP/DOWN, 0.0 for SKIP
print(f"Reasoning: {signal.reasoning}")

# Access indicator values
print(f"RSI: {signal.rsi}")
print(f"MACD: {signal.macd_line} / {signal.macd_signal}")
print(f"Order Book Imbalance: {signal.order_book_imbalance}")

# Check if actionable
if signal.is_actionable():
    direction = signal.get_direction()  # "UP" or "DOWN"
    print(f"Trade direction: {direction}")
else:
    print("Skip trading - no clear signal")
```

**Convenience Function:**

```python
from prediction import generate_signal_from_market_data

# Generate signal without maintaining engine instance
signal = generate_signal_from_market_data(
    prices=prices,
    btc_price=45678.90
)

print(f"{signal.signal.value}: {signal.reasoning}")
```

### PredictionSignal Model

Represents a generated trading signal with metadata.

**Fields:**
- `signal`: SignalType (UP, DOWN, or SKIP)
- `confidence`: Confidence score (0.0-1.0)
- `rsi`: RSI value at signal generation
- `macd_line`: MACD line value
- `macd_signal`: MACD signal line value
- `order_book_imbalance`: Order book imbalance ratio
- `btc_price`: BTC price at signal time (optional)
- `timestamp`: Signal generation timestamp
- `reasoning`: Human-readable explanation

**Methods:**
- `is_actionable()`: Returns True for UP/DOWN, False for SKIP
- `get_direction()`: Returns "UP", "DOWN", or None
- `to_dict()`: Serialize to dictionary

**Example:**

```python
from models import PredictionSignal, SignalType
from decimal import Decimal

signal = PredictionSignal(
    signal=SignalType.UP,
    confidence=Decimal('0.75'),
    rsi=Decimal('28.5'),
    macd_line=Decimal('150.23'),
    macd_signal=Decimal('145.10'),
    order_book_imbalance=Decimal('1.15'),
    btc_price=Decimal('45678.90'),
    reasoning="RSI oversold (28.50 < 30.00), MACD bullish crossover, strong buying pressure"
)

# Check if should trade
if signal.is_actionable():
    print(f"Action: {signal.get_direction()}")
    print(f"Confidence: {signal.confidence}")

    # Serialize for logging
    signal_dict = signal.to_dict()
```

### Validation and Testing

**Validate Price Data:**

```python
from prediction import PredictionEngine

engine = PredictionEngine()

# Check if enough data for signal generation
prices = [...]  # Your price data
if engine.validate_price_data(prices):
    signal = engine.generate_signal(prices)
else:
    print("Insufficient price data for prediction")
```

**Test Signal Conditions:**

```python
from prediction import validate_signal_conditions

# Test specific indicator values
signal_type = validate_signal_conditions(
    rsi=25.0,
    macd_line=150.0,
    macd_signal=145.0,
    order_book_imbalance=1.2
)

print(f"Would generate: {signal_type.value}")  # "up"
```

### Integration with Main Loop

**Typical Usage Pattern:**

```python
from market_data import BinanceWebSocketClient, get_order_book_imbalance
from prediction import PredictionEngine
from config import get_config

# Initialize components
config = get_config()
ws_client = BinanceWebSocketClient(buffer_size=100)
ws_client.connect()
engine = PredictionEngine(config=config)

# Wait for price data to accumulate
import time
time.sleep(30)

# Get prices and generate signal
prices = ws_client.get_price_series(limit=50)

if engine.validate_price_data(prices):
    signal = engine.generate_signal(
        prices=[float(p) for p in prices],
        btc_price=float(ws_client.get_latest_price())
    )

    if signal.is_actionable():
        print(f"Signal: {signal.signal.value.upper()}")
        print(f"Reason: {signal.reasoning}")
        # Proceed with trading logic
    else:
        print("No actionable signal, waiting...")
else:
    print("Waiting for more price data...")

# Clean up
ws_client.disconnect()
```

### Error Handling

The prediction engine implements comprehensive error handling:

```python
from prediction import PredictionEngine, PredictionError

engine = PredictionEngine()

try:
    signal = engine.generate_signal(prices)
except PredictionError as e:
    print(f"Prediction error: {e}")
    # Handle insufficient data, indicator calculation errors, etc.
except Exception as e:
    print(f"Unexpected error: {e}")
```

**Common Errors:**
- **Insufficient Data**: Need at least 34 prices for MACD calculation
- **Invalid Prices**: Prices must be positive values
- **Order Book Unavailable**: Network error fetching order book data
- **Indicator Calculation**: TA-Lib errors during RSI/MACD calculation

### Configuration

Customize prediction engine behavior via environment variables:

```bash
# RSI Configuration
RSI_PERIOD=14                    # RSI calculation period
RSI_OVERSOLD_THRESHOLD=30.0      # Oversold level for UP signals
RSI_OVERBOUGHT_THRESHOLD=70.0    # Overbought level for DOWN signals

# MACD Configuration
MACD_FAST_PERIOD=12              # MACD fast EMA period
MACD_SLOW_PERIOD=26              # MACD slow EMA period
MACD_SIGNAL_PERIOD=9             # MACD signal line period

# Order Book Configuration
ORDER_BOOK_BULLISH_THRESHOLD=1.1 # Imbalance for bullish signals
ORDER_BOOK_BEARISH_THRESHOLD=0.9 # Imbalance for bearish signals

# Signal Configuration
PREDICTION_CONFIDENCE_SCORE=0.75 # Confidence for UP/DOWN signals
```

### Testing

Run prediction engine tests:

```bash
# All prediction tests
pytest tests/test_prediction.py -v

# With coverage
pytest tests/test_prediction.py --cov=prediction --cov-report=html

# Specific test classes
pytest tests/test_prediction.py::TestSignalGeneration -v
pytest tests/test_prediction.py::TestConditionEvaluation -v
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

## Risk Management

The `risk.py` module implements pre-trade validation with multiple risk controls to protect capital and ensure safe trading operations.

### Risk Controls

#### Drawdown Monitoring

Automatically blocks trades when account drawdown exceeds the maximum threshold:
- **Threshold**: 30% maximum drawdown
- **Calculation**: `(starting_capital - current_capital) / starting_capital * 100`
- **Action**: Trade rejected with detailed reason when threshold exceeded

```python
from risk import check_drawdown
from decimal import Decimal

# Example: 25% drawdown - approved
approved, reason = check_drawdown(
    current_capital=Decimal("75.0"),
    starting_capital=Decimal("100.0")
)
# Returns: (True, None)

# Example: 35% drawdown - rejected
approved, reason = check_drawdown(
    current_capital=Decimal("65.0"),
    starting_capital=Decimal("100.0")
)
# Returns: (False, "Drawdown of 35.00% exceeds maximum threshold of 30.00%")
```

#### Volatility Circuit Breaker

Blocks trades during periods of excessive price volatility:
- **Threshold**: 3% maximum 5-minute price range
- **Window**: Last 5 price updates
- **Calculation**: `(max_price - min_price) / min_price * 100`
- **Action**: Trade rejected during high volatility periods

```python
from risk import check_volatility
from decimal import Decimal

# Example: Low volatility (2%) - approved
prices = [
    Decimal("45000.0"),
    Decimal("45100.0"),
    Decimal("45200.0"),
    Decimal("45150.0"),
    Decimal("45100.0")
]
approved, reason = check_volatility(prices)
# Returns: (True, None)

# Example: High volatility (5%) - rejected
volatile_prices = [
    Decimal("45000.0"),
    Decimal("43000.0"),
    Decimal("47000.0")
]
approved, reason = check_volatility(volatile_prices)
# Returns: (False, "Volatility of 9.30% exceeds maximum threshold of 3.00%")
```

#### Trade Approval Logic

Combines all risk checks with market validation for final trade decision:
- Drawdown validation
- Volatility check
- Market active status
- Market closure check
- Liquidity verification
- Exposure limit validation

```python
from risk import approve_trade
from models import BotState, MarketData
from decimal import Decimal
from datetime import datetime

# Create bot state
bot_state = BotState(
    bot_id="bot_001",
    strategy_name="momentum_v1",
    max_position_size=Decimal("1000.0"),
    max_total_exposure=Decimal("5000.0"),
    risk_per_trade=Decimal("500.0"),
    total_pnl=Decimal("250.0"),
    current_exposure=Decimal("1500.0")
)

# Create market data
market_data = MarketData(
    market_id="market_123",
    question="Will BTC reach $100k?",
    end_date=datetime(2024, 12, 31),
    yes_price=Decimal("0.65"),
    no_price=Decimal("0.35"),
    total_liquidity=Decimal("10000.0"),
    is_active=True,
    is_closed=False
)

# Price history
price_history = [
    Decimal("45000.0"),
    Decimal("45100.0"),
    Decimal("45200.0"),
    Decimal("45150.0"),
    Decimal("45100.0")
]

# Approve trade with all checks
approved, reason = approve_trade(
    signal="UP",
    market_data=market_data,
    bot_state=bot_state,
    price_history=price_history
)
# Returns: (True, None) if all checks pass
# Returns: (False, "rejection reason") if any check fails
```

#### Position Sizing

Calculate maximum allowable trade size based on risk parameters:

```python
from risk import calculate_max_trade_size

max_size = calculate_max_trade_size(bot_state, market_data)
# Returns minimum of:
# - max_position_size
# - remaining_exposure (max_total_exposure - current_exposure)
# - risk_per_trade
```

#### Risk Metrics

Get comprehensive risk metrics for monitoring:

```python
from risk import get_risk_metrics

metrics = get_risk_metrics(bot_state, price_history)
# Returns dictionary with:
# - current_capital
# - starting_capital
# - drawdown_percent
# - volatility_percent
# - exposure_utilization_percent
# - win_rate_percent
# - total_pnl
```

### Risk Validation Workflow

```python
from risk import approve_trade, calculate_max_trade_size, get_risk_metrics
from models import BotState, MarketData

# 1. Get risk metrics for monitoring
metrics = get_risk_metrics(bot_state, price_history)
print(f"Drawdown: {metrics['drawdown_percent']:.2f}%")
print(f"Volatility: {metrics['volatility_percent']:.2f}%")

# 2. Approve trade with all risk checks
approved, reason = approve_trade(
    signal="UP",
    market_data=market_data,
    bot_state=bot_state,
    price_history=price_history
)

if not approved:
    print(f"Trade rejected: {reason}")
    return

# 3. Calculate safe position size
max_size = calculate_max_trade_size(bot_state, market_data)
print(f"Max trade size: ${max_size}")

# 4. Execute trade (if approved)
# ... execute trade with max_size
```

### Error Handling

All risk functions return tuples of `(approved: bool, reason: Optional[str])`:
- **Success**: `(True, None)` - validation passed
- **Failure**: `(False, "detailed reason")` - validation failed with explanation

Invalid inputs are caught and returned as rejections:
```python
# Invalid starting capital
approved, reason = check_drawdown(
    current_capital=Decimal("50.0"),
    starting_capital=Decimal("0.0")
)
# Returns: (False, "Invalid starting capital: 0. Must be greater than 0.")

# Empty price history
approved, reason = check_volatility([])
# Returns: (False, "Price history is empty. Cannot calculate volatility.")
```

Run tests:
```bash
# All tests
pytest -v

# Specific test files
pytest tests/test_models.py -v
pytest tests/test_market_data.py -v
pytest tests/test_risk.py -v
pytest tests/test_state.py -v
pytest test_config.py test_polymarket_utils.py -v

# With coverage
pytest tests/test_models.py --cov=models --cov-report=html
pytest tests/test_market_data.py --cov=market_data --cov-report=html
pytest tests/test_risk.py --cov=risk --cov-report=html
pytest tests/test_state.py --cov=state --cov-report=html
pytest test_config.py -v --cov=config --cov-report=html
pytest test_risk.py -v --cov=risk --cov-report=html
```

## Risk Management System

The `risk.py` module provides a comprehensive risk management system with max drawdown monitoring, volatility circuit breakers, and pre-trade validation logic.

### RiskManager

The main `RiskManager` class implements all risk control mechanisms for the trading bot.

**Features:**
- Max drawdown tracking (default: 30% threshold)
- Volatility circuit breaker (default: 3% 5-minute range)
- Pre-trade validation with detailed approval/rejection reasons
- Peak capital tracking for accurate drawdown calculations
- Risk metrics monitoring and reporting
- Configurable thresholds for different strategies

**Example Usage:**

```python
from risk import RiskManager
from models import BotState, BotStatus
from decimal import Decimal

# Initialize risk manager with default thresholds
rm = RiskManager(
    max_drawdown_percent=Decimal("30.0"),  # 30% max drawdown
    volatility_threshold_percent=Decimal("3.0"),  # 3% max volatility
    starting_capital=Decimal("100.0")  # Starting capital
)

# Create bot state
bot_state = BotState(
    bot_id="my_bot",
    strategy_name="momentum_v1",
    max_position_size=Decimal("25.0"),
    max_total_exposure=Decimal("100.0"),
    risk_per_trade=Decimal("5.0"),
    total_pnl=Decimal("-20.0"),  # Current P&L
    status=BotStatus.RUNNING
)

# Check if trade should be approved
recent_prices = [Decimal("45000"), Decimal("45500"), Decimal("45200")]
result = rm.approve_trade(bot_state, recent_prices=recent_prices)

if result.approved:
    print("✓ Trade APPROVED")
    if result.warnings:
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
else:
    print("✗ Trade REJECTED")
    for reason in result.rejection_reasons:
        print(f"  - {reason}")

# Get current risk metrics
metrics = rm.get_risk_metrics(bot_state)
print(f"Drawdown: {metrics['drawdown_percent']:.2f}%")
print(f"Current capital: ${metrics['current_capital']:.2f}")
print(f"Win rate: {metrics['win_rate']:.2f}%")
```

### Drawdown Monitoring

Tracks drawdown from peak equity and prevents trading when threshold is exceeded.

```python
# Calculate current drawdown
current_capital = Decimal("75.0")
drawdown = rm.calculate_drawdown(current_capital)
print(f"Current drawdown: {drawdown}%")  # 25%

# Check if drawdown is within limits
is_ok, drawdown_percent = rm.check_drawdown(current_capital)
if not is_ok:
    print(f"⚠ Drawdown {drawdown_percent}% exceeds limit!")

# Update peak capital on profitable trades
rm.update_peak_capital(Decimal("150.0"))  # New peak
```

**Drawdown Calculation:**
- Formula: `((peak_capital - current_capital) / peak_capital) * 100`
- Peak capital is automatically tracked (highest value seen)
- Default threshold: 30% (configurable)
- Trade is rejected if drawdown >= threshold

### Volatility Circuit Breaker

Prevents trading during high volatility periods by checking 5-minute price range.

```python
# Recent prices over 5-minute window
prices = [
    Decimal("45000"),
    Decimal("45200"),
    Decimal("45100"),
    Decimal("45300"),
    Decimal("44900")
]

# Calculate volatility
volatility = rm.calculate_volatility(prices)
print(f"Current volatility: {volatility:.2f}%")

# Check if volatility is within limits
is_ok, volatility_percent = rm.check_volatility(prices)
if not is_ok:
    print(f"⚠ Volatility {volatility_percent}% exceeds limit!")
```

**Volatility Calculation:**
- Formula: `((max_price - min_price) / min_price) * 100`
- Default threshold: 3% (configurable)
- Trade is rejected if volatility >= threshold
- Protects against trading in unstable market conditions

### Pre-Trade Validation

Comprehensive validation combining all risk checks before executing a trade.

```python
# Perform full pre-trade validation
result = rm.approve_trade(
    bot_state=bot_state,
    market_data=market_data,  # Optional
    recent_prices=recent_prices  # Optional
)

# Check result
if result:  # RiskApprovalResult acts as boolean
    print("Trade approved!")
else:
    print("Trade rejected:")
    for reason in result.rejection_reasons:
        print(f"  - {reason}")

# Access detailed information
print(f"Drawdown: {result.details['drawdown_percent']}%")
print(f"Current capital: ${result.details['current_capital']}")

# Check for warnings
for warning in result.warnings:
    print(f"⚠ {warning}")
```

**Validation Checks:**
1. **Drawdown**: Current drawdown must be below threshold
2. **Volatility**: Recent price volatility must be below threshold (if prices provided)
3. **Capital**: Must have sufficient capital for minimum trade ($5)
4. **Exposure**: Current exposure must be below maximum allowed
5. **Bot Status**: Bot must be in 'running' or 'initializing' status

**Approval Result:**
- `approved`: Boolean indicating if trade is approved
- `rejection_reasons`: List of reasons if rejected
- `warnings`: Non-blocking warnings (e.g., approaching limits)
- `details`: Detailed metrics (drawdown, capital, volatility, etc.)

### Standalone Functions

Convenience functions for simpler use cases:

```python
from risk import check_drawdown, check_volatility, approve_trade
from decimal import Decimal

# Simple drawdown check
is_ok = check_drawdown(
    current_capital=Decimal("75.0"),
    starting_capital=Decimal("100.0")
)

# Simple volatility check
prices = [Decimal("45000"), Decimal("45500")]
is_ok = check_volatility(prices)

# Simple trade approval (backward compatible)
approved = approve_trade(
    signal="UP",
    market_data=market_data,
    bot_state=bot_state,
    recent_prices=recent_prices
)
```

### Risk Metrics

Monitor comprehensive risk metrics:

```python
metrics = rm.get_risk_metrics(bot_state)

# Available metrics:
print(f"Timestamp: {metrics['timestamp']}")
print(f"Starting capital: ${metrics['starting_capital']}")
print(f"Peak capital: ${metrics['peak_capital']}")
print(f"Current capital: ${metrics['current_capital']}")
print(f"Drawdown: {metrics['drawdown_percent']:.2f}%")
print(f"Drawdown limit: {metrics['drawdown_limit']:.2f}%")
print(f"Drawdown remaining: {metrics['drawdown_remaining']:.2f}%")
print(f"Win rate: {metrics['win_rate']:.2f}%")
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
