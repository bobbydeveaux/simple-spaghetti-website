"""
Polymarket Bot Package

This package provides core data models and utilities for building
automated trading bots for the Polymarket prediction market platform.
"""

from .models import (
    # Models
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
