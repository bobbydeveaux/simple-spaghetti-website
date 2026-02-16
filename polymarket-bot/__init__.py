"""
Polymarket Bot Package

This package provides core data models, configuration management, and utilities
for building automated trading bots for the Polymarket prediction market platform.
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

__version__ = "0.1.0"

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
]
