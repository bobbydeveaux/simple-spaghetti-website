"""
Unit tests for execution module.

Tests order submission, settlement polling, authentication,
and error handling for the Polymarket execution client.
"""

import pytest
import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import requests

from polymarket_bot.execution import (
    PolymarketExecutionClient,
    submit_order,
    poll_settlement,
    execute_trade,
    ExecutionError,
    OrderSubmissionError,
    SettlementTimeoutError
)
from polymarket_bot.config import Config
from polymarket_bot.utils import ValidationError


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock(spec=Config)
    config.polymarket_base_url = "https://api.polymarket.com"
    config.polymarket_api_key = "test_api_key"
    config.polymarket_api_secret = "test_api_secret"
    return config


@pytest.fixture
def execution_client(mock_config):
    """Create an execution client with mock config."""
    return PolymarketExecutionClient(mock_config)


class TestPolymarketExecutionClient:
    """Tests for PolymarketExecutionClient class."""

    def test_initialization(self, mock_config):
        """Test client initialization."""
        client = PolymarketExecutionClient(mock_config)

        assert client.config == mock_config
        assert client.base_url == "https://api.polymarket.com"
        assert client.api_key == "test_api_key"
        assert client.api_secret == "test_api_secret"
        assert client.session is not None

    def test_generate_signature(self, execution_client):
        """Test HMAC signature generation."""
        timestamp = "1234567890000"
        method = "POST"
        path = "/orders"
        body = '{"market_id": "123"}'

        signature = execution_client._generate_signature(timestamp, method, path, body)

        # Signature should be a hex string
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest length
        assert all(c in '0123456789abcdef' for c in signature)

    def test_generate_signature_consistency(self, execution_client):
        """Test that signature generation is consistent."""
        timestamp = "1234567890000"
        method = "POST"
        path = "/orders"
        body = '{"market_id": "123"}'

        sig1 = execution_client._generate_signature(timestamp, method, path, body)
        sig2 = execution_client._generate_signature(timestamp, method, path, body)

        # Same inputs should produce same signature
        assert sig1 == sig2

    def test_get_auth_headers(self, execution_client):
        """Test authentication header generation."""
        method = "POST"
        path = "/orders"
        body = '{"market_id": "123"}'

        headers = execution_client._get_auth_headers(method, path, body)

        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test_api_key'
        assert 'X-Timestamp' in headers
        assert 'X-Signature' in headers

        # Timestamp should be numeric
        assert headers['X-Timestamp'].isdigit()

        # Signature should be hex
        assert len(headers['X-Signature']) == 64

    @patch('polymarket_bot.execution.requests.Session.request')
    def test_make_request_success(self, mock_request, execution_client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"order_id": "12345", "status": "pending"}
        mock_response.headers = {}
        mock_request.return_value = mock_response

        result = execution_client._make_request("POST", "/orders", data={"amount": 100})

        assert result == {"order_id": "12345", "status": "pending"}
        mock_request.assert_called_once()

    @patch('polymarket_bot.execution.requests.Session.request')
    def test_make_request_http_error(self, mock_request, execution_client):
        """Test API request with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_request.return_value = mock_response

        with pytest.raises(ExecutionError) as exc_info:
            execution_client._make_request("POST", "/orders", data={"amount": 100})

        assert "HTTP error" in str(exc_info.value)

    @patch('polymarket_bot.execution.requests.Session.request')
    def test_make_request_network_error(self, mock_request, execution_client):
        """Test API request with network error."""
        mock_request.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(ExecutionError) as exc_info:
            execution_client._make_request("GET", "/markets")

        assert "Request failed" in str(exc_info.value)

    @patch('polymarket_bot.execution.requests.Session.request')
    def test_make_request_with_retry(self, mock_request, execution_client):
        """Test that failed requests are retried."""
        # First two calls fail, third succeeds
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        mock_response_error.text = "Internal server error"
        mock_response_error.raise_for_status.side_effect = requests.HTTPError()

        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"success": True}
        mock_response_success.headers = {}

        mock_request.side_effect = [
            mock_response_error,
            mock_response_error,
            mock_response_success
        ]

        result = execution_client._make_request("GET", "/status")

        assert result == {"success": True}
        assert mock_request.call_count == 3


class TestSubmitOrder:
    """Tests for submit_order functionality."""

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_submit_order_up_direction(self, mock_request, execution_client):
        """Test submitting an UP (YES) order."""
        mock_request.return_value = {
            "order_id": "order_123",
            "status": "pending"
        }

        order_id = execution_client.submit_order(
            market_id="market_456",
            direction="UP",
            size=100.0
        )

        assert order_id == "order_123"

        # Verify the request was made with correct data
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/orders"

        data = call_args[1]['data']
        assert data['market_id'] == "market_456"
        assert data['side'] == "YES"
        assert data['amount'] == 100.0
        assert data['type'] == "MARKET"

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_submit_order_down_direction(self, mock_request, execution_client):
        """Test submitting a DOWN (NO) order."""
        mock_request.return_value = {
            "id": "order_789",
            "status": "pending"
        }

        order_id = execution_client.submit_order(
            market_id="market_456",
            direction="DOWN",
            size=50.0
        )

        assert order_id == "order_789"

        data = mock_request.call_args[1]['data']
        assert data['side'] == "NO"
        assert data['amount'] == 50.0

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_submit_order_case_insensitive(self, mock_request, execution_client):
        """Test that direction is case-insensitive."""
        mock_request.return_value = {"order_id": "order_123"}

        execution_client.submit_order("market_1", "up", 100.0)
        assert mock_request.call_args[1]['data']['side'] == "YES"

        execution_client.submit_order("market_1", "down", 100.0)
        assert mock_request.call_args[1]['data']['side'] == "NO"

    def test_submit_order_invalid_direction(self, execution_client):
        """Test submitting order with invalid direction."""
        with pytest.raises(ValidationError) as exc_info:
            execution_client.submit_order("market_1", "INVALID", 100.0)

        assert "Invalid direction" in str(exc_info.value)

    def test_submit_order_invalid_size(self, execution_client):
        """Test submitting order with invalid size."""
        with pytest.raises(ValidationError) as exc_info:
            execution_client.submit_order("market_1", "UP", -100.0)

        assert "must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError):
            execution_client.submit_order("market_1", "UP", 0.0)

    def test_submit_order_empty_market_id(self, execution_client):
        """Test submitting order with empty market ID."""
        with pytest.raises(ValidationError):
            execution_client.submit_order("", "UP", 100.0)

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_submit_order_missing_order_id(self, mock_request, execution_client):
        """Test handling response without order_id."""
        mock_request.return_value = {"status": "pending"}  # No order_id

        with pytest.raises(OrderSubmissionError) as exc_info:
            execution_client.submit_order("market_1", "UP", 100.0)

        assert "missing 'order_id'" in str(exc_info.value)

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_submit_order_api_error(self, mock_request, execution_client):
        """Test handling API errors during submission."""
        mock_request.side_effect = ExecutionError("API unavailable")

        with pytest.raises(OrderSubmissionError) as exc_info:
            execution_client.submit_order("market_1", "UP", 100.0)

        assert "Order submission failed" in str(exc_info.value)


class TestPollSettlement:
    """Tests for poll_settlement functionality."""

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_poll_settlement_immediate_win(self, mock_request, execution_client):
        """Test polling when order is immediately settled as WIN."""
        mock_request.return_value = {
            "order_id": "order_123",
            "status": "SETTLED",
            "outcome": "WIN"
        }

        outcome = execution_client.poll_settlement("order_123", timeout=60)

        assert outcome == "WIN"
        mock_request.assert_called_once()

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_poll_settlement_immediate_loss(self, mock_request, execution_client):
        """Test polling when order is immediately settled as LOSS."""
        mock_request.return_value = {
            "order_id": "order_123",
            "status": "SETTLED",
            "outcome": "LOSS"
        }

        outcome = execution_client.poll_settlement("order_123", timeout=60)

        assert outcome == "LOSS"

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    @patch('time.sleep')
    def test_poll_settlement_delayed(self, mock_sleep, mock_request, execution_client):
        """Test polling with delayed settlement."""
        # First call: pending, second call: settled
        mock_request.side_effect = [
            {"status": "PENDING"},
            {"status": "SETTLED", "outcome": "WIN"}
        ]

        outcome = execution_client.poll_settlement("order_123", timeout=60, poll_interval=10)

        assert outcome == "WIN"
        assert mock_request.call_count == 2
        mock_sleep.assert_called_once_with(10)

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    @patch('time.sleep')
    def test_poll_settlement_multiple_polls(self, mock_sleep, mock_request, execution_client):
        """Test polling with multiple attempts before settlement."""
        mock_request.side_effect = [
            {"status": "PENDING"},
            {"status": "PENDING"},
            {"status": "PENDING"},
            {"status": "SETTLED", "outcome": "WIN"}
        ]

        outcome = execution_client.poll_settlement("order_123", timeout=100, poll_interval=5)

        assert outcome == "WIN"
        assert mock_request.call_count == 4
        assert mock_sleep.call_count == 3

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    @patch('time.time')
    def test_poll_settlement_timeout(self, mock_time, mock_request, execution_client):
        """Test polling timeout."""
        # Simulate time passing
        mock_time.side_effect = [0, 0, 100, 200, 301]  # Exceeds 300s timeout

        mock_request.return_value = {"status": "PENDING"}

        with pytest.raises(SettlementTimeoutError) as exc_info:
            execution_client.poll_settlement("order_123", timeout=300, poll_interval=10)

        assert "timed out" in str(exc_info.value)

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_poll_settlement_failed_status(self, mock_request, execution_client):
        """Test handling failed order status."""
        mock_request.return_value = {"status": "FAILED"}

        with pytest.raises(ExecutionError) as exc_info:
            execution_client.poll_settlement("order_123", timeout=60)

        assert "Order failed" in str(exc_info.value)

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_poll_settlement_cancelled_status(self, mock_request, execution_client):
        """Test handling cancelled order status."""
        mock_request.return_value = {"status": "CANCELLED"}

        with pytest.raises(ExecutionError) as exc_info:
            execution_client.poll_settlement("order_123", timeout=60)

        assert "Order failed" in str(exc_info.value)

    def test_poll_settlement_invalid_order_id(self, execution_client):
        """Test polling with invalid order ID."""
        with pytest.raises(ValidationError):
            execution_client.poll_settlement("", timeout=60)

    def test_poll_settlement_invalid_timeout(self, execution_client):
        """Test polling with invalid timeout."""
        with pytest.raises(ValidationError):
            execution_client.poll_settlement("order_123", timeout=-1)

        with pytest.raises(ValidationError):
            execution_client.poll_settlement("order_123", timeout=0)

    def test_poll_settlement_invalid_poll_interval(self, execution_client):
        """Test polling with invalid poll interval."""
        with pytest.raises(ValidationError):
            execution_client.poll_settlement("order_123", timeout=60, poll_interval=-5)


class TestParseSettlementOutcome:
    """Tests for _parse_settlement_outcome method."""

    def test_parse_outcome_win(self, execution_client):
        """Test parsing WIN outcome."""
        response = {"outcome": "WIN"}
        assert execution_client._parse_settlement_outcome(response) == "WIN"

        response = {"outcome": "won"}
        assert execution_client._parse_settlement_outcome(response) == "WIN"

        response = {"result": "SUCCESS"}
        assert execution_client._parse_settlement_outcome(response) == "WIN"

    def test_parse_outcome_loss(self, execution_client):
        """Test parsing LOSS outcome."""
        response = {"outcome": "LOSS"}
        assert execution_client._parse_settlement_outcome(response) == "LOSS"

        response = {"outcome": "lost"}
        assert execution_client._parse_settlement_outcome(response) == "LOSS"

        response = {"settlement": "FAIL"}
        assert execution_client._parse_settlement_outcome(response) == "LOSS"

    def test_parse_outcome_from_pnl(self, execution_client):
        """Test inferring outcome from PnL."""
        response = {"pnl": 50.0}
        assert execution_client._parse_settlement_outcome(response) == "WIN"

        response = {"profit_loss": -25.0}
        assert execution_client._parse_settlement_outcome(response) == "LOSS"

        response = {"pnl": 0}
        assert execution_client._parse_settlement_outcome(response) == "LOSS"

    def test_parse_outcome_missing(self, execution_client):
        """Test parsing when outcome cannot be determined."""
        response = {"status": "SETTLED"}  # No outcome field

        with pytest.raises(ExecutionError) as exc_info:
            execution_client._parse_settlement_outcome(response)

        assert "Unable to determine" in str(exc_info.value)


class TestGetOrderStatus:
    """Tests for get_order_status method."""

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_get_order_status(self, mock_request, execution_client):
        """Test getting order status."""
        mock_request.return_value = {
            "order_id": "order_123",
            "status": "PENDING",
            "market_id": "market_456"
        }

        status = execution_client.get_order_status("order_123")

        assert status["order_id"] == "order_123"
        assert status["status"] == "PENDING"
        mock_request.assert_called_once_with("GET", "/orders/order_123")

    def test_get_order_status_invalid_id(self, execution_client):
        """Test getting status with invalid order ID."""
        with pytest.raises(ValidationError):
            execution_client.get_order_status("")


class TestCancelOrder:
    """Tests for cancel_order method."""

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_cancel_order_success(self, mock_request, execution_client):
        """Test successful order cancellation."""
        mock_request.return_value = {"success": True}

        result = execution_client.cancel_order("order_123")

        assert result is True
        mock_request.assert_called_once_with("POST", "/orders/order_123/cancel")

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_cancel_order_with_cancelled_field(self, mock_request, execution_client):
        """Test cancellation with 'cancelled' field in response."""
        mock_request.return_value = {"cancelled": True}

        result = execution_client.cancel_order("order_123")

        assert result is True

    @patch('polymarket_bot.execution.PolymarketExecutionClient._make_request')
    def test_cancel_order_failure(self, mock_request, execution_client):
        """Test failed order cancellation."""
        mock_request.return_value = {"success": False}

        result = execution_client.cancel_order("order_123")

        assert result is False

    def test_cancel_order_invalid_id(self, execution_client):
        """Test cancelling with invalid order ID."""
        with pytest.raises(ValidationError):
            execution_client.cancel_order("")


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('polymarket_bot.execution.PolymarketExecutionClient.submit_order')
    @patch('polymarket_bot.execution.PolymarketExecutionClient.close')
    def test_submit_order_function(self, mock_close, mock_submit):
        """Test submit_order convenience function."""
        mock_submit.return_value = "order_123"

        with patch('polymarket_bot.execution.get_config') as mock_get_config:
            mock_get_config.return_value = Mock()
            order_id = submit_order("market_1", "UP", 100.0)

        assert order_id == "order_123"
        mock_submit.assert_called_once_with("market_1", "UP", 100.0)
        mock_close.assert_called_once()

    @patch('polymarket_bot.execution.PolymarketExecutionClient.poll_settlement')
    @patch('polymarket_bot.execution.PolymarketExecutionClient.close')
    def test_poll_settlement_function(self, mock_close, mock_poll):
        """Test poll_settlement convenience function."""
        mock_poll.return_value = "WIN"

        with patch('polymarket_bot.execution.get_config') as mock_get_config:
            mock_get_config.return_value = Mock()
            outcome = poll_settlement("order_123", timeout=300)

        assert outcome == "WIN"
        mock_poll.assert_called_once_with("order_123", timeout=300)
        mock_close.assert_called_once()

    @patch('polymarket_bot.execution.PolymarketExecutionClient.submit_order')
    @patch('polymarket_bot.execution.PolymarketExecutionClient.poll_settlement')
    @patch('polymarket_bot.execution.PolymarketExecutionClient.close')
    def test_execute_trade_with_settlement(self, mock_close, mock_poll, mock_submit):
        """Test execute_trade with settlement wait."""
        mock_submit.return_value = "order_123"
        mock_poll.return_value = "WIN"

        with patch('polymarket_bot.execution.get_config') as mock_get_config:
            mock_get_config.return_value = Mock()
            order_id, outcome = execute_trade(
                "market_1", "UP", 100.0,
                wait_for_settlement=True,
                settlement_timeout=300
            )

        assert order_id == "order_123"
        assert outcome == "WIN"
        mock_submit.assert_called_once()
        mock_poll.assert_called_once_with("order_123", timeout=300)
        mock_close.assert_called_once()

    @patch('polymarket_bot.execution.PolymarketExecutionClient.submit_order')
    @patch('polymarket_bot.execution.PolymarketExecutionClient.poll_settlement')
    @patch('polymarket_bot.execution.PolymarketExecutionClient.close')
    def test_execute_trade_without_settlement(self, mock_close, mock_poll, mock_submit):
        """Test execute_trade without settlement wait."""
        mock_submit.return_value = "order_123"

        with patch('polymarket_bot.execution.get_config') as mock_get_config:
            mock_get_config.return_value = Mock()
            order_id, outcome = execute_trade(
                "market_1", "UP", 100.0,
                wait_for_settlement=False
            )

        assert order_id == "order_123"
        assert outcome is None
        mock_submit.assert_called_once()
        mock_poll.assert_not_called()
        mock_close.assert_called_once()


class TestContextManager:
    """Tests for context manager support."""

    def test_context_manager(self, mock_config):
        """Test using client as context manager."""
        with patch('polymarket_bot.execution.PolymarketExecutionClient.close') as mock_close:
            with PolymarketExecutionClient(mock_config) as client:
                assert client is not None

            mock_close.assert_called_once()
