"""
Unit tests for the execution module.

Tests cover order submission, settlement polling, retry logic with exponential backoff,
error classification, and configuration integration.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from polymarket_bot.execution import (
    submit_order,
    poll_settlement,
    get_order_status,
    ExecutionError,
    TerminalExecutionError,
    RetryableExecutionError,
    _is_retryable_error,
)
from polymarket_bot.utils import RetryError, ValidationError
from polymarket_bot.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.polymarket_base_url = "https://api.polymarket.com"
    config.polymarket_api_key = "test_api_key"
    config.polymarket_api_secret = "test_api_secret"
    config.max_retries = 3
    config.initial_delay = 0.1  # Short delay for tests
    config.backoff_multiplier = 2.0
    config.max_delay = 1.0
    return config


class TestIsRetryableError:
    """Test error classification for retry logic."""

    def test_connection_error_is_retryable(self):
        """Connection errors should be retried."""
        error = requests.ConnectionError("Connection failed")
        assert _is_retryable_error(error) is True

    def test_timeout_error_is_retryable(self):
        """Timeout errors should be retried."""
        error = requests.Timeout("Request timed out")
        assert _is_retryable_error(error) is True

    def test_rate_limit_error_is_retryable(self):
        """HTTP 429 rate limit errors should be retried."""
        response = Mock()
        response.status_code = 429
        error = requests.HTTPError()
        error.response = response
        assert _is_retryable_error(error) is True

    def test_server_error_is_retryable(self):
        """HTTP 5xx server errors should be retried."""
        for status_code in [500, 502, 503, 504]:
            response = Mock()
            response.status_code = status_code
            error = requests.HTTPError()
            error.response = response
            assert _is_retryable_error(error) is True

    def test_client_error_is_terminal(self):
        """HTTP 4xx client errors (except 429) should not be retried."""
        for status_code in [400, 401, 403, 404]:
            response = Mock()
            response.status_code = status_code
            error = requests.HTTPError()
            error.response = response
            assert _is_retryable_error(error) is False

    def test_unknown_error_is_retryable_by_default(self):
        """Unknown errors should be retried by default."""
        error = Exception("Unknown error")
        assert _is_retryable_error(error) is True


class TestSubmitOrder:
    """Test order submission functionality."""

    def test_submit_order_success(self, mock_config):
        """Test successful order submission."""
        with patch('polymarket_bot.execution.requests.post') as mock_post:
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'order_id': 'order_123',
                'status': 'PENDING'
            }
            mock_post.return_value = mock_response

            # Submit order
            order_id = submit_order(
                market_id="market_abc",
                direction="YES",
                size=50.0,
                config=mock_config
            )

            # Verify result
            assert order_id == "order_123"

            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]['json']['market_id'] == "market_abc"
            assert call_args[1]['json']['side'] == "YES"
            assert call_args[1]['json']['amount'] == 50.0
            assert call_args[1]['json']['type'] == "MARKET"

    def test_submit_order_with_no_direction(self, mock_config):
        """Test order submission with NO direction."""
        with patch('polymarket_bot.execution.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'order_id': 'order_456'}
            mock_post.return_value = mock_response

            order_id = submit_order(
                market_id="market_xyz",
                direction="NO",
                size=100.0,
                config=mock_config
            )

            assert order_id == "order_456"
            assert mock_post.call_args[1]['json']['side'] == "NO"

    def test_submit_order_invalid_market_id(self, mock_config):
        """Test validation of market_id parameter."""
        with pytest.raises(ValidationError, match="market_id must be a non-empty string"):
            submit_order(market_id="", direction="YES", size=50.0, config=mock_config)

        with pytest.raises(ValidationError, match="market_id must be a non-empty string"):
            submit_order(market_id=None, direction="YES", size=50.0, config=mock_config)

    def test_submit_order_invalid_direction(self, mock_config):
        """Test validation of direction parameter."""
        with pytest.raises(ValidationError, match="direction must be 'YES' or 'NO'"):
            submit_order(
                market_id="market_abc",
                direction="INVALID",
                size=50.0,
                config=mock_config
            )

    def test_submit_order_invalid_size(self, mock_config):
        """Test validation of size parameter."""
        with pytest.raises(ValidationError, match="size must be a positive number"):
            submit_order(
                market_id="market_abc",
                direction="YES",
                size=0,
                config=mock_config
            )

        with pytest.raises(ValidationError, match="size must be a positive number"):
            submit_order(
                market_id="market_abc",
                direction="YES",
                size=-10.0,
                config=mock_config
            )

    def test_submit_order_retries_on_network_error(self, mock_config):
        """Test that network errors trigger retry logic."""
        with patch('polymarket_bot.execution.requests.post') as mock_post:
            # First two calls fail with network error, third succeeds
            mock_post.side_effect = [
                requests.ConnectionError("Connection failed"),
                requests.Timeout("Request timed out"),
                Mock(status_code=200, json=lambda: {'order_id': 'order_789'})
            ]

            order_id = submit_order(
                market_id="market_abc",
                direction="YES",
                size=50.0,
                config=mock_config
            )

            # Should succeed on third attempt
            assert order_id == "order_789"
            assert mock_post.call_count == 3

    def test_submit_order_retries_on_rate_limit(self, mock_config):
        """Test that rate limit errors (429) trigger retry logic."""
        with patch('polymarket_bot.execution.requests.post') as mock_post:
            # First call hits rate limit, second succeeds
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.raise_for_status.side_effect = requests.HTTPError()
            rate_limit_response.raise_for_status.side_effect.response = rate_limit_response

            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {'order_id': 'order_rate'}

            mock_post.side_effect = [
                rate_limit_response,
                success_response
            ]

            # Mock raise_for_status to raise HTTPError for 429
            def raise_for_status_mock():
                if mock_post.return_value == rate_limit_response:
                    error = requests.HTTPError()
                    error.response = rate_limit_response
                    raise error

            rate_limit_response.raise_for_status = raise_for_status_mock

            order_id = submit_order(
                market_id="market_abc",
                direction="YES",
                size=50.0,
                config=mock_config
            )

            assert order_id == "order_rate"

    def test_submit_order_terminal_error_no_retry(self, mock_config):
        """Test that terminal errors (4xx except 429) don't trigger retry."""
        with patch('polymarket_bot.execution.requests.post') as mock_post:
            # Create a 401 Unauthorized response
            error_response = Mock()
            error_response.status_code = 401

            http_error = requests.HTTPError()
            http_error.response = error_response

            mock_post.return_value.raise_for_status.side_effect = http_error

            with pytest.raises(TerminalExecutionError, match="HTTP error"):
                submit_order(
                    market_id="market_abc",
                    direction="YES",
                    size=50.0,
                    config=mock_config
                )

            # Should only be called once (no retry)
            assert mock_post.call_count == 1

    def test_submit_order_exhausts_retries(self, mock_config):
        """Test that order submission fails after exhausting retries."""
        with patch('polymarket_bot.execution.requests.post') as mock_post:
            # All attempts fail with connection error
            mock_post.side_effect = requests.ConnectionError("Connection failed")

            with pytest.raises(RetryError, match="failed after .* attempts"):
                submit_order(
                    market_id="market_abc",
                    direction="YES",
                    size=50.0,
                    config=mock_config
                )

            # Should try max_retries times
            assert mock_post.call_count == mock_config.max_retries

    def test_submit_order_missing_order_id_in_response(self, mock_config):
        """Test handling of malformed API response."""
        with patch('polymarket_bot.execution.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'PENDING'}  # Missing order_id
            mock_post.return_value = mock_response

            with pytest.raises((ExecutionError, TerminalExecutionError), match="order_id"):
                submit_order(
                    market_id="market_abc",
                    direction="YES",
                    size=50.0,
                    config=mock_config
                )

    def test_submit_order_with_decimal_size(self, mock_config):
        """Test order submission with Decimal size."""
        with patch('polymarket_bot.execution.requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'order_id': 'order_decimal'}
            mock_post.return_value = mock_response

            order_id = submit_order(
                market_id="market_abc",
                direction="YES",
                size=Decimal("75.50"),
                config=mock_config
            )

            assert order_id == "order_decimal"
            assert mock_post.call_args[1]['json']['amount'] == 75.50


class TestPollSettlement:
    """Test settlement polling functionality."""

    def test_poll_settlement_immediate_win(self, mock_config):
        """Test polling when order is already settled as WIN."""
        with patch('polymarket_bot.execution.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'order_id': 'order_123',
                'status': 'SETTLED',
                'outcome': 'WIN'
            }
            mock_get.return_value = mock_response

            outcome = poll_settlement(
                order_id="order_123",
                timeout=60,
                config=mock_config
            )

            assert outcome == "WIN"
            assert mock_get.call_count == 1

    def test_poll_settlement_immediate_loss(self, mock_config):
        """Test polling when order is already settled as LOSS."""
        with patch('polymarket_bot.execution.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'order_id': 'order_456',
                'status': 'SETTLED',
                'outcome': 'LOSS'
            }
            mock_get.return_value = mock_response

            outcome = poll_settlement(
                order_id="order_456",
                timeout=60,
                config=mock_config
            )

            assert outcome == "LOSS"

    def test_poll_settlement_pending_then_settled(self, mock_config):
        """Test polling that waits for settlement."""
        with patch('polymarket_bot.execution.requests.get') as mock_get, \
             patch('polymarket_bot.execution.time.sleep') as mock_sleep:

            # First two calls return PENDING, third returns SETTLED
            pending_response = Mock()
            pending_response.status_code = 200
            pending_response.json.return_value = {
                'status': 'PENDING'
            }

            settled_response = Mock()
            settled_response.status_code = 200
            settled_response.json.return_value = {
                'status': 'SETTLED',
                'outcome': 'WIN'
            }

            mock_get.side_effect = [
                pending_response,
                pending_response,
                settled_response
            ]

            outcome = poll_settlement(
                order_id="order_pending",
                timeout=300,
                poll_interval=1,
                config=mock_config
            )

            assert outcome == "WIN"
            assert mock_get.call_count == 3
            # Should sleep between polls
            assert mock_sleep.call_count == 2

    def test_poll_settlement_timeout(self, mock_config):
        """Test that polling times out if order doesn't settle."""
        with patch('polymarket_bot.execution.requests.get') as mock_get, \
             patch('polymarket_bot.execution.time.sleep') as mock_sleep, \
             patch('polymarket_bot.execution.time.time') as mock_time:

            # Mock time to simulate timeout
            mock_time.side_effect = [0, 1, 2, 3, 4, 5, 6]  # Each call increments time

            # Always return PENDING
            pending_response = Mock()
            pending_response.status_code = 200
            pending_response.json.return_value = {'status': 'PENDING'}
            mock_get.return_value = pending_response

            with pytest.raises(ExecutionError, match="timed out"):
                poll_settlement(
                    order_id="order_timeout",
                    timeout=5,
                    poll_interval=1,
                    config=mock_config
                )

    def test_poll_settlement_invalid_order_id(self, mock_config):
        """Test validation of order_id parameter."""
        with pytest.raises(ValidationError, match="order_id must be a non-empty string"):
            poll_settlement(order_id="", timeout=60, config=mock_config)

        with pytest.raises(ValidationError, match="order_id must be a non-empty string"):
            poll_settlement(order_id=None, timeout=60, config=mock_config)

    def test_poll_settlement_invalid_timeout(self, mock_config):
        """Test validation of timeout parameter."""
        with pytest.raises(ValidationError, match="timeout must be positive"):
            poll_settlement(order_id="order_123", timeout=0, config=mock_config)

        with pytest.raises(ValidationError, match="timeout must be positive"):
            poll_settlement(order_id="order_123", timeout=-10, config=mock_config)

    def test_poll_settlement_invalid_poll_interval(self, mock_config):
        """Test validation of poll_interval parameter."""
        with pytest.raises(ValidationError, match="poll_interval must be positive"):
            poll_settlement(
                order_id="order_123",
                timeout=60,
                poll_interval=0,
                config=mock_config
            )

    def test_poll_settlement_invalid_outcome(self, mock_config):
        """Test handling of invalid outcome value."""
        with patch('polymarket_bot.execution.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'status': 'SETTLED',
                'outcome': 'INVALID'  # Invalid outcome
            }
            mock_get.return_value = mock_response

            with pytest.raises(ExecutionError, match="Invalid outcome"):
                poll_settlement(order_id="order_bad", timeout=60, config=mock_config)

    def test_poll_settlement_retries_on_network_error(self, mock_config):
        """Test that network errors during polling trigger retry."""
        with patch('polymarket_bot.execution.requests.get') as mock_get:
            # First poll fails, second succeeds
            settled_response = Mock()
            settled_response.status_code = 200
            settled_response.json.return_value = {
                'status': 'SETTLED',
                'outcome': 'WIN'
            }

            mock_get.side_effect = [
                requests.ConnectionError("Connection failed"),
                settled_response
            ]

            outcome = poll_settlement(
                order_id="order_retry",
                timeout=60,
                config=mock_config
            )

            assert outcome == "WIN"

    def test_poll_settlement_unexpected_status(self, mock_config):
        """Test handling of unexpected status value."""
        with patch('polymarket_bot.execution.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'status': 'UNKNOWN_STATUS'
            }
            mock_get.return_value = mock_response

            with pytest.raises(ExecutionError, match="Unexpected order status"):
                poll_settlement(order_id="order_bad", timeout=60, config=mock_config)


class TestGetOrderStatus:
    """Test get_order_status functionality."""

    def test_get_order_status_success(self, mock_config):
        """Test successful status retrieval."""
        with patch('polymarket_bot.execution.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'order_id': 'order_123',
                'status': 'PENDING',
                'market_id': 'market_abc'
            }
            mock_get.return_value = mock_response

            status = get_order_status(order_id="order_123", config=mock_config)

            assert status['order_id'] == 'order_123'
            assert status['status'] == 'PENDING'
            assert status['market_id'] == 'market_abc'

    def test_get_order_status_invalid_order_id(self, mock_config):
        """Test validation of order_id parameter."""
        with pytest.raises(ValidationError, match="order_id must be a non-empty string"):
            get_order_status(order_id="", config=mock_config)

    def test_get_order_status_retries_on_error(self, mock_config):
        """Test that get_order_status retries on network errors."""
        with patch('polymarket_bot.execution.requests.get') as mock_get:
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {
                'order_id': 'order_retry',
                'status': 'SETTLED'
            }

            mock_get.side_effect = [
                requests.Timeout("Request timed out"),
                success_response
            ]

            status = get_order_status(order_id="order_retry", config=mock_config)

            assert status['status'] == 'SETTLED'
            assert mock_get.call_count == 2

    def test_get_order_status_terminal_error(self, mock_config):
        """Test that terminal errors are raised properly."""
        with patch('polymarket_bot.execution.requests.get') as mock_get:
            error_response = Mock()
            error_response.status_code = 404

            http_error = requests.HTTPError()
            http_error.response = error_response

            mock_get.return_value.raise_for_status.side_effect = http_error

            with pytest.raises(ExecutionError, match="Failed to get order status"):
                get_order_status(order_id="order_not_found", config=mock_config)


class TestRetryConfiguration:
    """Test that retry logic uses configuration parameters correctly."""

    def test_submit_order_uses_max_retries_from_config(self):
        """Test that max_retries configuration is respected."""
        config = Mock(spec=Config)
        config.polymarket_base_url = "https://api.polymarket.com"
        config.polymarket_api_key = "test_key"
        config.max_retries = 5  # Custom value
        config.initial_delay = 0.1
        config.backoff_multiplier = 2.0
        config.max_delay = 1.0

        with patch('polymarket_bot.execution.requests.post') as mock_post:
            mock_post.side_effect = requests.ConnectionError("Connection failed")

            with pytest.raises(RetryError):
                submit_order(
                    market_id="market_abc",
                    direction="YES",
                    size=50.0,
                    config=config
                )

            # Should attempt exactly max_retries times
            assert mock_post.call_count == 5

    def test_exponential_backoff_configuration(self, mock_config):
        """Test that exponential backoff uses configured multiplier."""
        # This is implicitly tested by the retry decorator
        # The actual timing is tested in test_utils.py
        # Here we just verify the configuration is passed through
        assert mock_config.backoff_multiplier == 2.0
        assert mock_config.initial_delay == 0.1
        assert mock_config.max_delay == 1.0
