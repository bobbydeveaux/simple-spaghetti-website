# Polymarket Bot

Automated trading bot for Polymarket prediction markets with technical analysis and market data integration.

## Features

- **Environment Configuration**: Secure API key management using `.env` files
- **Multi-Exchange Support**: Integration with Polymarket, Binance, and CoinGecko APIs
- **WebSocket Support**: Real-time market data streaming
- **Technical Analysis**: Built-in TA-Lib support for technical indicators
- **Configurable Risk Management**: Customizable position sizing and stop-loss parameters

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

## Usage

### Validate Configuration

Before running the bot, validate your configuration:

```bash
python config.py
```

This will check that all required environment variables are set and valid.

### Import in Your Code

```python
from config import get_config

# Get configuration instance
config = get_config()

# Access configuration values
print(f"Polymarket API URL: {config.polymarket_base_url}")
print(f"Max Position Size: {config.max_position_size}")
print(f"Risk Percentage: {config.risk_percentage}")
```

### Error Handling

The configuration module raises `ConfigurationError` for missing or invalid configuration:

```python
from config import get_config, ConfigurationError

try:
    config = get_config()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    exit(1)
```

## Testing

Run the test suite:

```bash
pytest test_config.py -v
```

Run with coverage:

```bash
pytest test_config.py -v --cov=config --cov-report=html
```

## Security

- **Never commit your `.env` file** - it contains sensitive API keys
- The `.env.example` file is safe to commit and serves as a template
- API keys are not exposed in logs or error messages
- The `Config.__repr__()` method excludes sensitive values

## Development

### Code Quality

Format code with Black:

```bash
black config.py test_config.py
```

Lint with flake8:

```bash
flake8 config.py test_config.py
```

Type check with mypy:

```bash
mypy config.py
```

## Dependencies

### Core Dependencies

- `python-dotenv`: Load environment variables from .env files
- `requests`: HTTP client for API calls
- `websocket-client`: WebSocket client for real-time data
- `TA-Lib`: Technical analysis library
- `pydantic`: Data validation

### Development Dependencies

- `pytest`: Testing framework
- `pytest-asyncio`: Async test support
- `black`: Code formatter
- `flake8`: Linter
- `mypy`: Type checker

See `requirements.txt` for full list with pinned versions.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
