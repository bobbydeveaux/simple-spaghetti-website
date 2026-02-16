"""
Polymarket Bot - Automated trading bot for Polymarket prediction markets.

This package provides configuration, data models, and trading logic for
automated trading on Polymarket using technical analysis and market data.
"""

from .config import Config, get_config, validate_config, ConfigurationError

__version__ = "0.1.0"
__all__ = ["Config", "get_config", "validate_config", "ConfigurationError"]
