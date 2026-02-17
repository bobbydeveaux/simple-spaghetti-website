"""
Polymarket Bot Package

This package provides core data models, configuration management, market data
integration, and utilities for building automated trading bots for the
Polymarket prediction market platform.
"""

# Configuration
from .config import Config, get_config, validate_config, ConfigurationError

# Models
from .models import (
    BotState,
    Trade,
    Position,
    MarketData,
    # Enums
    BotStatus,
    OrderSide,
    OrderType,
    TradeStatus,
    PositionStatus,
    OutcomeType,
)

# Market Data
from .market_data import (
    MarketDataService,
    PolymarketAPIError,
    get_active_btc_markets,
    get_market_odds_by_id,
)

__version__ = "0.2.0"

__all__ = [
    # Configuration
    "Config",
    "get_config",
    "validate_config",
    "ConfigurationError",
    # Models
    "BotState",
    "Trade",
    "Position",
    "MarketData",
    # Enums
    "BotStatus",
    "OrderSide",
    "OrderType",
    "TradeStatus",
    "PositionStatus",
    "OutcomeType",
    # Market Data
    "MarketDataService",
    "PolymarketAPIError",
    "get_active_btc_markets",
    "get_market_odds_by_id",
]
