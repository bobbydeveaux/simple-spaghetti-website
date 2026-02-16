"""
Test suite for configuration module.

Tests the Config class and environment variable loading functionality.
"""

import os
import pytest
import tempfile
from pathlib import Path
from config import Config, ConfigurationError, get_config, validate_config


@pytest.fixture
def temp_env_file():
    """Create a temporary .env file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""
POLYMARKET_API_KEY=test_polymarket_key
POLYMARKET_API_SECRET=test_polymarket_secret
BINANCE_API_KEY=test_binance_key
BINANCE_API_SECRET=test_binance_secret
COINGECKO_API_KEY=test_coingecko_key
POLYMARKET_BASE_URL=https://test.polymarket.com
BINANCE_BASE_URL=https://test.binance.com
COINGECKO_BASE_URL=https://test.coingecko.com
MAX_POSITION_SIZE=500
RISK_PERCENTAGE=0.01
STOP_LOSS_PERCENTAGE=0.03
WS_RECONNECT_DELAY=3
WS_MAX_RECONNECT_ATTEMPTS=5
LOG_LEVEL=DEBUG
LOG_FILE=test.log
""")
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def minimal_env_file():
    """Create a minimal .env file with only required variables."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""
POLYMARKET_API_KEY=test_polymarket_key
POLYMARKET_API_SECRET=test_polymarket_secret
BINANCE_API_KEY=test_binance_key
BINANCE_API_SECRET=test_binance_secret
COINGECKO_API_KEY=test_coingecko_key
""")
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def incomplete_env_file():
    """Create an incomplete .env file missing required variables."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("""
POLYMARKET_API_KEY=test_polymarket_key
BINANCE_API_KEY=test_binance_key
""")
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


class TestConfig:
    """Test cases for Config class."""

    def test_load_full_config(self, temp_env_file):
        """Test loading a complete configuration."""
        config = Config(env_file=temp_env_file)

        # Check required API keys
        assert config.polymarket_api_key == 'test_polymarket_key'
        assert config.polymarket_api_secret == 'test_polymarket_secret'
        assert config.binance_api_key == 'test_binance_key'
        assert config.binance_api_secret == 'test_binance_secret'
        assert config.coingecko_api_key == 'test_coingecko_key'

        # Check URLs
        assert config.polymarket_base_url == 'https://test.polymarket.com'
        assert config.binance_base_url == 'https://test.binance.com'
        assert config.coingecko_base_url == 'https://test.coingecko.com'

        # Check trading config
        assert config.max_position_size == 500.0
        assert config.risk_percentage == 0.01
        assert config.stop_loss_percentage == 0.03

        # Check WebSocket config
        assert config.ws_reconnect_delay == 3
        assert config.ws_max_reconnect_attempts == 5

        # Check logging config
        assert config.log_level == 'DEBUG'
        assert config.log_file == 'test.log'

    def test_load_minimal_config_with_defaults(self, minimal_env_file):
        """Test loading configuration with only required fields (defaults for optional)."""
        config = Config(env_file=minimal_env_file)

        # Check required API keys are loaded
        assert config.polymarket_api_key == 'test_polymarket_key'
        assert config.binance_api_key == 'test_binance_key'

        # Check defaults are applied
        assert config.polymarket_base_url == 'https://api.polymarket.com'
        assert config.binance_base_url == 'https://api.binance.com'
        assert config.max_position_size == 1000.0
        assert config.risk_percentage == 0.02
        assert config.ws_reconnect_delay == 5
        assert config.log_level == 'INFO'

    def test_missing_required_key_raises_error(self, incomplete_env_file):
        """Test that missing required keys raise ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            Config(env_file=incomplete_env_file)

        assert 'POLYMARKET_API_SECRET' in str(exc_info.value)

    def test_invalid_risk_percentage_raises_error(self, temp_env_file):
        """Test that invalid risk percentage raises ConfigurationError."""
        # Create config with invalid risk percentage
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("""
POLYMARKET_API_KEY=test_key
POLYMARKET_API_SECRET=test_secret
BINANCE_API_KEY=test_key
BINANCE_API_SECRET=test_secret
COINGECKO_API_KEY=test_key
RISK_PERCENTAGE=1.5
""")
            invalid_file = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Config(env_file=invalid_file)
            assert 'RISK_PERCENTAGE' in str(exc_info.value)
        finally:
            os.unlink(invalid_file)

    def test_invalid_log_level_raises_error(self, temp_env_file):
        """Test that invalid log level raises ConfigurationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("""
POLYMARKET_API_KEY=test_key
POLYMARKET_API_SECRET=test_secret
BINANCE_API_KEY=test_key
BINANCE_API_SECRET=test_secret
COINGECKO_API_KEY=test_key
LOG_LEVEL=INVALID
""")
            invalid_file = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Config(env_file=invalid_file)
            assert 'LOG_LEVEL' in str(exc_info.value)
        finally:
            os.unlink(invalid_file)

    def test_invalid_integer_raises_error(self, temp_env_file):
        """Test that invalid integer values raise ConfigurationError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("""
POLYMARKET_API_KEY=test_key
POLYMARKET_API_SECRET=test_secret
BINANCE_API_KEY=test_key
BINANCE_API_SECRET=test_secret
COINGECKO_API_KEY=test_key
WS_RECONNECT_DELAY=not_a_number
""")
            invalid_file = f.name

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                Config(env_file=invalid_file)
            assert 'WS_RECONNECT_DELAY' in str(exc_info.value)
            assert 'integer' in str(exc_info.value)
        finally:
            os.unlink(invalid_file)

    def test_repr_does_not_expose_secrets(self, temp_env_file):
        """Test that __repr__ doesn't expose API keys."""
        config = Config(env_file=temp_env_file)
        repr_str = repr(config)

        # Should not contain any API keys
        assert 'test_polymarket_key' not in repr_str
        assert 'test_binance_key' not in repr_str
        assert 'test_coingecko_key' not in repr_str

        # Should contain non-sensitive info
        assert 'max_position_size' in repr_str
        assert 'log_level' in repr_str


class TestConfigSingleton:
    """Test cases for singleton functionality."""

    def test_get_config_returns_singleton(self, temp_env_file):
        """Test that get_config returns the same instance."""
        config1 = get_config(env_file=temp_env_file)
        config2 = get_config()

        assert config1 is config2

    def test_force_reload_creates_new_instance(self, temp_env_file, minimal_env_file):
        """Test that force_reload creates a new config instance."""
        config1 = get_config(env_file=temp_env_file, force_reload=True)
        assert config1.max_position_size == 500.0

        config2 = get_config(env_file=minimal_env_file, force_reload=True)
        assert config2.max_position_size == 1000.0  # default value

    def test_validate_config_success(self, temp_env_file):
        """Test that validate_config returns True for valid config."""
        # First load the config
        get_config(env_file=temp_env_file, force_reload=True)
        assert validate_config() is True

    def test_validate_config_failure(self, incomplete_env_file):
        """Test that validate_config raises error for invalid config."""
        with pytest.raises(ConfigurationError):
            get_config(env_file=incomplete_env_file, force_reload=True)
            validate_config()


class TestConfigImport:
    """Test that config can be imported and used by other modules."""

    def test_import_config(self):
        """Test that config module can be imported."""
        from config import Config, get_config, ConfigurationError
        assert Config is not None
        assert get_config is not None
        assert ConfigurationError is not None

    def test_config_usage_pattern(self, temp_env_file):
        """Test typical usage pattern in other modules."""
        # Simulate how other modules would use the config
        config = get_config(env_file=temp_env_file, force_reload=True)

        # Access configuration values
        api_key = config.polymarket_api_key
        assert api_key == 'test_polymarket_key'

        # Access trading parameters
        risk = config.risk_percentage
        assert risk == 0.01
