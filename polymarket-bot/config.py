"""
Configuration module for Polymarket Bot.

This module loads and validates environment variables using python-dotenv.
It ensures all required configuration values are present before the bot starts.
"""

import os
import sys
from typing import Optional
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class Config:
    """
    Configuration management class for Polymarket Bot.

    Loads environment variables from .env file and validates required keys.
    Provides easy access to configuration values throughout the application.
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration by loading environment variables.

        Args:
            env_file: Path to .env file. If None, looks for .env in current directory.

        Raises:
            ConfigurationError: If required environment variables are missing.
        """
        # Load environment variables from .env file
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        # Validate and load configuration
        self._load_and_validate()

    def _load_and_validate(self):
        """Load and validate all configuration values."""
        # Required API keys
        self.polymarket_api_key = self._get_required_env('POLYMARKET_API_KEY')
        self.polymarket_api_secret = self._get_required_env('POLYMARKET_API_SECRET')
        self.binance_api_key = self._get_required_env('BINANCE_API_KEY')
        self.binance_api_secret = self._get_required_env('BINANCE_API_SECRET')
        self.coingecko_api_key = self._get_required_env('COINGECKO_API_KEY')

        # API Base URLs with defaults
        self.polymarket_base_url = self._get_env(
            'POLYMARKET_BASE_URL',
            'https://api.polymarket.com'
        )
        self.binance_base_url = self._get_env(
            'BINANCE_BASE_URL',
            'https://api.binance.com'
        )
        self.coingecko_base_url = self._get_env(
            'COINGECKO_BASE_URL',
            'https://api.coingecko.com/api/v3'
        )

        # Trading configuration with defaults
        self.max_position_size = self._get_float_env('MAX_POSITION_SIZE', 1000.0)
        self.risk_percentage = self._get_float_env('RISK_PERCENTAGE', 0.02)
        self.stop_loss_percentage = self._get_float_env('STOP_LOSS_PERCENTAGE', 0.05)

        # WebSocket configuration with defaults
        self.ws_reconnect_delay = self._get_int_env('WS_RECONNECT_DELAY', 5)
        self.ws_max_reconnect_attempts = self._get_int_env('WS_MAX_RECONNECT_ATTEMPTS', 10)

        # Logging configuration with defaults
        self.log_level = self._get_env('LOG_LEVEL', 'INFO')
        self.log_file = self._get_env('LOG_FILE', 'polymarket_bot.log')

        # Prediction engine configuration with defaults
        self.rsi_period = self._get_int_env('RSI_PERIOD', 14)
        self.rsi_oversold_threshold = self._get_float_env('RSI_OVERSOLD_THRESHOLD', 30.0)
        self.rsi_overbought_threshold = self._get_float_env('RSI_OVERBOUGHT_THRESHOLD', 70.0)
        self.macd_fast_period = self._get_int_env('MACD_FAST_PERIOD', 12)
        self.macd_slow_period = self._get_int_env('MACD_SLOW_PERIOD', 26)
        self.macd_signal_period = self._get_int_env('MACD_SIGNAL_PERIOD', 9)
        self.order_book_bullish_threshold = self._get_float_env('ORDER_BOOK_BULLISH_THRESHOLD', 1.1)
        self.order_book_bearish_threshold = self._get_float_env('ORDER_BOOK_BEARISH_THRESHOLD', 0.9)
        self.prediction_confidence_score = self._get_float_env('PREDICTION_CONFIDENCE_SCORE', 0.75)

        # Validate numeric ranges
        self._validate_ranges()

    def _get_required_env(self, key: str) -> str:
        """
        Get a required environment variable.

        Args:
            key: Environment variable name

        Returns:
            Value of the environment variable

        Raises:
            ConfigurationError: If the environment variable is not set or is empty
        """
        value = os.getenv(key)
        if not value or value.strip() == '':
            raise ConfigurationError(
                f"Required environment variable '{key}' is not set or is empty. "
                f"Please check your .env file."
            )
        return value.strip()

    def _get_env(self, key: str, default: str) -> str:
        """
        Get an optional environment variable with a default value.

        Args:
            key: Environment variable name
            default: Default value if not set

        Returns:
            Value of the environment variable or default
        """
        value = os.getenv(key)
        return value.strip() if value else default

    def _get_int_env(self, key: str, default: int) -> int:
        """
        Get an integer environment variable with a default value.

        Args:
            key: Environment variable name
            default: Default value if not set

        Returns:
            Integer value of the environment variable or default

        Raises:
            ConfigurationError: If the value cannot be converted to int
        """
        value = os.getenv(key)
        if not value:
            return default

        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(
                f"Environment variable '{key}' must be an integer, got: {value}"
            )

    def _get_float_env(self, key: str, default: float) -> float:
        """
        Get a float environment variable with a default value.

        Args:
            key: Environment variable name
            default: Default value if not set

        Returns:
            Float value of the environment variable or default

        Raises:
            ConfigurationError: If the value cannot be converted to float
        """
        value = os.getenv(key)
        if not value:
            return default

        try:
            return float(value)
        except ValueError:
            raise ConfigurationError(
                f"Environment variable '{key}' must be a number, got: {value}"
            )

    def _validate_ranges(self):
        """Validate that numeric configuration values are in valid ranges."""
        if self.risk_percentage <= 0 or self.risk_percentage > 1:
            raise ConfigurationError(
                f"RISK_PERCENTAGE must be between 0 and 1, got: {self.risk_percentage}"
            )

        if self.stop_loss_percentage <= 0 or self.stop_loss_percentage > 1:
            raise ConfigurationError(
                f"STOP_LOSS_PERCENTAGE must be between 0 and 1, got: {self.stop_loss_percentage}"
            )

        if self.max_position_size <= 0:
            raise ConfigurationError(
                f"MAX_POSITION_SIZE must be greater than 0, got: {self.max_position_size}"
            )

        if self.ws_reconnect_delay <= 0:
            raise ConfigurationError(
                f"WS_RECONNECT_DELAY must be greater than 0, got: {self.ws_reconnect_delay}"
            )

        if self.ws_max_reconnect_attempts <= 0:
            raise ConfigurationError(
                f"WS_MAX_RECONNECT_ATTEMPTS must be greater than 0, got: {self.ws_max_reconnect_attempts}"
            )

        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_log_levels:
            raise ConfigurationError(
                f"LOG_LEVEL must be one of {valid_log_levels}, got: {self.log_level}"
            )

        # Validate prediction engine parameters
        if self.rsi_period <= 0:
            raise ConfigurationError(
                f"RSI_PERIOD must be greater than 0, got: {self.rsi_period}"
            )

        if not (0 <= self.rsi_oversold_threshold <= 100):
            raise ConfigurationError(
                f"RSI_OVERSOLD_THRESHOLD must be between 0 and 100, got: {self.rsi_oversold_threshold}"
            )

        if not (0 <= self.rsi_overbought_threshold <= 100):
            raise ConfigurationError(
                f"RSI_OVERBOUGHT_THRESHOLD must be between 0 and 100, got: {self.rsi_overbought_threshold}"
            )

        if self.rsi_oversold_threshold >= self.rsi_overbought_threshold:
            raise ConfigurationError(
                f"RSI_OVERSOLD_THRESHOLD must be less than RSI_OVERBOUGHT_THRESHOLD"
            )

        if self.macd_fast_period <= 0 or self.macd_slow_period <= 0 or self.macd_signal_period <= 0:
            raise ConfigurationError(
                f"MACD periods must be greater than 0"
            )

        if self.macd_fast_period >= self.macd_slow_period:
            raise ConfigurationError(
                f"MACD_FAST_PERIOD must be less than MACD_SLOW_PERIOD"
            )

        if self.order_book_bullish_threshold <= 1.0:
            raise ConfigurationError(
                f"ORDER_BOOK_BULLISH_THRESHOLD must be greater than 1.0 (representing buying pressure), "
                f"got: {self.order_book_bullish_threshold}"
            )

        if self.order_book_bearish_threshold <= 0 or self.order_book_bearish_threshold >= 1.0:
            raise ConfigurationError(
                f"ORDER_BOOK_BEARISH_THRESHOLD must be between 0 and 1.0 (representing selling pressure), "
                f"got: {self.order_book_bearish_threshold}"
            )

        if not (0 <= self.prediction_confidence_score <= 1):
            raise ConfigurationError(
                f"PREDICTION_CONFIDENCE_SCORE must be between 0 and 1, got: {self.prediction_confidence_score}"
            )

    def __repr__(self) -> str:
        """Return a safe string representation (without exposing secrets)."""
        return (
            f"Config("
            f"polymarket_base_url='{self.polymarket_base_url}', "
            f"binance_base_url='{self.binance_base_url}', "
            f"coingecko_base_url='{self.coingecko_base_url}', "
            f"max_position_size={self.max_position_size}, "
            f"risk_percentage={self.risk_percentage}, "
            f"log_level='{self.log_level}'"
            f")"
        )


# Singleton instance
_config_instance: Optional[Config] = None


def get_config(env_file: Optional[str] = None, force_reload: bool = False) -> Config:
    """
    Get the global configuration instance.

    Args:
        env_file: Path to .env file (only used on first call or when force_reload=True)
        force_reload: If True, reload configuration even if already loaded

    Returns:
        Config instance

    Raises:
        ConfigurationError: If required configuration is missing
    """
    global _config_instance

    if _config_instance is None or force_reload:
        _config_instance = Config(env_file)

    return _config_instance


def validate_config() -> bool:
    """
    Validate that configuration can be loaded successfully.

    Returns:
        True if configuration is valid

    Raises:
        ConfigurationError: If configuration is invalid
    """
    try:
        get_config(force_reload=True)
        return True
    except ConfigurationError as e:
        print(f"Configuration validation failed: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    """Allow running as a script to validate configuration."""
    try:
        config = get_config()
        print("Configuration loaded successfully!")
        print(f"\n{config}")
        print("\nAll required API keys are present.")
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
