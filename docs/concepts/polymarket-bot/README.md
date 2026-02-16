# Polymarket Bot

Automated trading bot for Polymarket prediction markets with technical analysis and market data integration.

## Overview

The Polymarket Bot is a Python-based automated trading system designed to trade on Polymarket prediction markets. It integrates with multiple data sources including Binance and CoinGecko to make informed trading decisions based on technical analysis.

## Features

- **Secure Configuration Management**: Environment-based configuration with validation
- **Multi-API Integration**: Supports Polymarket, Binance, and CoinGecko APIs
- **WebSocket Support**: Real-time market data streaming
- **Technical Analysis**: TA-Lib integration for technical indicators
- **Risk Management**: Configurable position sizing and stop-loss parameters
- **Comprehensive Testing**: Full test suite with pytest

## Project Structure

```
polymarket-bot/
├── __init__.py           # Package initialization
├── config.py             # Configuration management
├── test_config.py        # Configuration tests
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
└── README.md            # User documentation
```

## Getting Started

See the [main README](../../../polymarket-bot/README.md) in the polymarket-bot directory for installation and usage instructions.

## Development Status

### Sprint 1: Configuration and Data Models

- [x] Task 1: Environment configuration and dependencies
  - [x] Created `.env.example` with API key placeholders
  - [x] Created `requirements.txt` with pinned dependencies
  - [x] Implemented `config.py` with validation
  - [x] Added comprehensive test suite
  - [x] Documentation complete

## Documentation

- [Product Requirements (PRD)](./PRD.md) - *(To be created)*
- [High-Level Design (HLD)](./HLD.md) - *(To be created)*
- [Low-Level Design (LLD)](./LLD.md) - *(To be created)*
- [Epic Planning](./epic.yaml) - *(To be created)*
- [Tasks](./tasks.yaml) - *(To be created)*

## Security Considerations

- All API keys are managed through environment variables
- `.env` files are excluded from version control
- Configuration values are validated on load
- Secrets are not exposed in logs or error messages

## Dependencies

### Core Dependencies
- `python-dotenv`: Environment variable management
- `requests`: HTTP client
- `websocket-client`: WebSocket support
- `TA-Lib`: Technical analysis
- `pydantic`: Data validation

### Development Dependencies
- `pytest`: Testing framework
- `black`: Code formatting
- `flake8`: Linting
- `mypy`: Type checking

See [requirements.txt](../../../polymarket-bot/requirements.txt) for complete list.

## Testing

Run the test suite:

```bash
cd polymarket-bot
pytest test_config.py -v
```

## Contributing

Follow the project's coding standards:
- Use Black for code formatting
- Run flake8 for linting
- Ensure all tests pass
- Add tests for new features
