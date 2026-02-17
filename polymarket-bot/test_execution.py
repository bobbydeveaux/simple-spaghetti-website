"""
Unit tests for the trade execution module.

Tests cover:
- Order submission (market and limit orders)
- Retry logic and error handling
- Settlement polling
- Trade status updates
- API error scenarios
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, call
import requests

from polymarket_bot.execution import (
    ExecutionEngine,
    OrderExecutionError,
    OrderSettlementError,
    PolymarketAPIError,
    submit_market_order,
    submit_limit_order
)
from polymarket_bot.models import (
    Trade,
    OrderSide,
    OrderType,
    OutcomeType,
    TradeStatus
)
from polymarket_bot.config import Config
from polymarket_bot.utils import RetryError


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.polymarket_base_url = "https://api.test.polymarket.com"
    config.polymarket_api_key = "test_api_key"
    config.polymarket_api_secret = "test_api_secret"
    config.execution_max_retries = 3
    config.execution_retry_base_delay = 0.1  # Fast retries for testing
    config.execution_settlement_poll_interval = 1
    config.execution_settlement_timeout = 10
    return config


@pytest.fixture
def execution_engine(mock_config):
    """Create an ExecutionEngine instance for testing."""
    with patch('polymarket_bot.execution.get_config', return_value=mock_config):
        engine = ExecutionEngine(mock_config)
        yield engine
        engine.close()


class TestExecutionEngineInit:
    """Tests for ExecutionEngine initialization."""

    def test_init_with_config(self, mock_config):
        """Test initialization with provided config."""
        engine = ExecutionEngine(mock_config)

        assert engine.config == mock_config
        assert engine.base_url == "https://api.test.polymarket.com"
        assert engine.api_key == "test_api_key"
        assert engine.api_secret == "test_api_secret"
        assert engine.max_retries == 3
        assert engine.session is not None

        engine.close()

    def test_init_without_config(self):
        """Test initialization without config loads from environment."""
        mock_config = Mock(spec=Config)
        mock_config.polymarket_base_url = "https://api.polymarket.com"
        mock_config.polymarket_api_key = "env_key"
        mock_config.polymarket_api_secret = "env_secret"
        mock_config.execution_max_retries = 3
        mock_config.execution_retry_base_delay = 2.0
        mock_config.execution_settlement_poll_interval = 10
        mock_config.execution_settlement_timeout = 300

        with patch('polymarket_bot.execution.get_config', return_value=mock_config):
            engine = ExecutionEngine()

            assert engine.config == mock_config
            assert engine.api_key == "env_key"

            engine.close()

    def test_session_configured(self, execution_engine):
        """Test that session is properly configured with headers."""
        session = execution_engine.session

        assert "Authorization" in session.headers
        assert session.headers["Authorization"] == "Bearer test_api_key"
        assert session.headers["Content-Type"] == "application/json"
        assert "User-Agent" in session.headers


class TestSubmitOrder:
    """Tests for submit_order method."""

    def test_submit_market_order_success(self, execution_engine):
        """Test successful market order submission."""
        # Mock API response
        mock_response = {
            "order_id": "order_123",
            "status": "pending",
            "filled_amount": 0,
            "fee": 0.5
        }

        with patch.object(execution_engine, '_make_request', return_value=mock_response):
            trade = execution_engine.submit_order(
                market_id="market_456",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("100"),
                order_type=OrderType.MARKET
            )

            assert trade.order_id == "order_123"
            assert trade.market_id == "market_456"
            assert trade.side == OrderSide.BUY
            assert trade.outcome == OutcomeType.YES
            assert trade.quantity == Decimal("100")
            assert trade.order_type == OrderType.MARKET
            assert trade.status == TradeStatus.PENDING
            assert trade.fee == Decimal("0.5")

    def test_submit_limit_order_success(self, execution_engine):
        """Test successful limit order submission."""
        mock_response = {
            "order_id": "order_789",
            "status": "matched",
            "filled_amount": 50,
            "fee": 0.25
        }

        with patch.object(execution_engine, '_make_request', return_value=mock_response):
            trade = execution_engine.submit_order(
                market_id="market_111",
                side=OrderSide.SELL,
                outcome=OutcomeType.NO,
                quantity=Decimal("50"),
                order_type=OrderType.LIMIT,
                price=Decimal("0.75")
            )

            assert trade.order_id == "order_789"
            assert trade.status == TradeStatus.EXECUTED
            assert trade.filled_quantity == Decimal("50")
            assert trade.price == Decimal("0.75")

    def test_submit_limit_order_without_price_raises_error(self, execution_engine):
        """Test that limit order without price raises error."""
        with pytest.raises(OrderExecutionError, match="price is required"):
            execution_engine.submit_order(
                market_id="market_456",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("100"),
                order_type=OrderType.LIMIT
            )

    def test_submit_order_validates_inputs(self, execution_engine):
        """Test that order submission validates inputs."""
        # Test empty market_id
        with pytest.raises(Exception):
            execution_engine.submit_order(
                market_id="",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("100")
            )

        # Test invalid quantity
        with pytest.raises(Exception):
            execution_engine.submit_order(
                market_id="market_456",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("0")
            )

    def test_submit_order_api_error_raises_exception(self, execution_engine):
        """Test that API errors are properly raised."""
        with patch.object(
            execution_engine,
            '_make_request',
            side_effect=PolymarketAPIError("API Error", status_code=500)
        ):
            with pytest.raises(OrderExecutionError):
                execution_engine.submit_order(
                    market_id="market_456",
                    side=OrderSide.BUY,
                    outcome=OutcomeType.YES,
                    quantity=Decimal("100")
                )

    def test_submit_order_missing_order_id_raises_error(self, execution_engine):
        """Test that missing order_id in response raises error."""
        mock_response = {
            "status": "pending"
            # Missing order_id
        }

        with patch.object(execution_engine, '_make_request', return_value=mock_response):
            with pytest.raises(OrderExecutionError, match="No order_id"):
                execution_engine.submit_order(
                    market_id="market_456",
                    side=OrderSide.BUY,
                    outcome=OutcomeType.YES,
                    quantity=Decimal("100")
                )

    def test_submit_order_with_custom_trade_id(self, execution_engine):
        """Test order submission with custom trade_id."""
        mock_response = {
            "order_id": "order_123",
            "status": "pending",
            "filled_amount": 0,
            "fee": 0.5
        }

        with patch.object(execution_engine, '_make_request', return_value=mock_response):
            trade = execution_engine.submit_order(
                market_id="market_456",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("100"),
                trade_id="custom_trade_123"
            )

            assert trade.trade_id == "custom_trade_123"

    def test_submit_order_retry_logic(self, execution_engine):
        """Test that retry logic works for transient failures."""
        # First two calls fail, third succeeds
        mock_responses = [
            PolymarketAPIError("Timeout", status_code=504),
            PolymarketAPIError("Server Error", status_code=500),
            {
                "order_id": "order_123",
                "status": "pending",
                "filled_amount": 0,
                "fee": 0.5
            }
        ]

        def side_effect(*args, **kwargs):
            response = mock_responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        with patch.object(execution_engine, '_make_request', side_effect=side_effect):
            # Should succeed on third attempt
            trade = execution_engine.submit_order(
                market_id="market_456",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("100")
            )

            assert trade.order_id == "order_123"


class TestGetOrderStatus:
    """Tests for get_order_status method."""

    def test_get_order_status_success(self, execution_engine):
        """Test successful order status retrieval."""
        mock_response = {
            "order_id": "order_123",
            "status": "matched",
            "filled_amount": 100,
            "fee": 0.5
        }

        with patch.object(execution_engine, '_make_request', return_value=mock_response):
            status = execution_engine.get_order_status("order_123")

            assert status["order_id"] == "order_123"
            assert status["status"] == "matched"
            assert status["filled_amount"] == 100

    def test_get_order_status_validates_order_id(self, execution_engine):
        """Test that empty order_id is rejected."""
        with pytest.raises(Exception):
            execution_engine.get_order_status("")

    def test_get_order_status_api_error(self, execution_engine):
        """Test API error handling in get_order_status."""
        with patch.object(
            execution_engine,
            '_make_request',
            side_effect=PolymarketAPIError("Not Found", status_code=404)
        ):
            with pytest.raises(PolymarketAPIError):
                execution_engine.get_order_status("order_123")


class TestPollSettlement:
    """Tests for poll_settlement method."""

    def test_poll_settlement_immediate_success(self, execution_engine):
        """Test settlement polling when order is already settled."""
        mock_response = {
            "order_id": "order_123",
            "status": "settled",
            "outcome": "WIN"
        }

        with patch.object(execution_engine, 'get_order_status', return_value=mock_response):
            outcome = execution_engine.poll_settlement("order_123")

            assert outcome == "WIN"

    def test_poll_settlement_after_multiple_polls(self, execution_engine):
        """Test settlement polling that requires multiple attempts."""
        # Sequence: pending -> pending -> matched -> settled
        responses = [
            {"status": "pending"},
            {"status": "pending"},
            {"status": "matched"},
            {"status": "settled", "outcome": "LOSS"}
        ]

        with patch.object(execution_engine, 'get_order_status', side_effect=responses):
            with patch('time.sleep'):  # Speed up test by mocking sleep
                outcome = execution_engine.poll_settlement("order_123")

                assert outcome == "LOSS"

    def test_poll_settlement_cancelled_order(self, execution_engine):
        """Test polling for cancelled order."""
        mock_response = {
            "status": "cancelled"
        }

        with patch.object(execution_engine, 'get_order_status', return_value=mock_response):
            outcome = execution_engine.poll_settlement("order_123")

            assert outcome == "CANCELLED"

    def test_poll_settlement_failed_order(self, execution_engine):
        """Test polling for failed order raises error."""
        mock_response = {
            "status": "failed"
        }

        with patch.object(execution_engine, 'get_order_status', return_value=mock_response):
            with pytest.raises(OrderSettlementError, match="failed"):
                execution_engine.poll_settlement("order_123")

    def test_poll_settlement_timeout(self, execution_engine):
        """Test settlement polling timeout."""
        mock_response = {
            "status": "pending"  # Never settles
        }

        with patch.object(execution_engine, 'get_order_status', return_value=mock_response):
            with patch('time.sleep'):  # Speed up test
                with pytest.raises(OrderSettlementError, match="timeout"):
                    execution_engine.poll_settlement("order_123", timeout=2)

    def test_poll_settlement_handles_api_errors_gracefully(self, execution_engine):
        """Test that transient API errors during polling don't stop polling."""
        responses = [
            PolymarketAPIError("Timeout"),  # Transient error
            {"status": "pending"},
            {"status": "settled", "outcome": "WIN"}
        ]

        def side_effect(*args, **kwargs):
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        with patch.object(execution_engine, 'get_order_status', side_effect=side_effect):
            with patch('time.sleep'):
                outcome = execution_engine.poll_settlement("order_123")

                assert outcome == "WIN"

    def test_poll_settlement_unexpected_outcome_defaults_to_loss(self, execution_engine):
        """Test that unexpected outcomes default to LOSS."""
        mock_response = {
            "status": "settled",
            "outcome": "UNKNOWN"
        }

        with patch.object(execution_engine, 'get_order_status', return_value=mock_response):
            outcome = execution_engine.poll_settlement("order_123")

            assert outcome == "LOSS"


class TestUpdateTradeStatus:
    """Tests for update_trade_status method."""

    def test_update_trade_status_success(self, execution_engine):
        """Test successful trade status update."""
        trade = Trade(
            trade_id="trade_123",
            market_id="market_456",
            order_id="order_789",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("100"),
            filled_quantity=Decimal("0"),
            status=TradeStatus.PENDING
        )

        mock_response = {
            "status": "executed",
            "filled_amount": 100,
            "fee": 1.5
        }

        with patch.object(execution_engine, 'get_order_status', return_value=mock_response):
            updated_trade = execution_engine.update_trade_status(trade)

            assert updated_trade.status == TradeStatus.EXECUTED
            assert updated_trade.filled_quantity == Decimal("100")
            assert updated_trade.fee == Decimal("1.5")
            assert updated_trade.executed_at is not None

    def test_update_trade_status_preserves_executed_at(self, execution_engine):
        """Test that executed_at is not overwritten if already set."""
        original_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        trade = Trade(
            trade_id="trade_123",
            market_id="market_456",
            order_id="order_789",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("100"),
            status=TradeStatus.EXECUTED,
            executed_at=original_time
        )

        mock_response = {
            "status": "executed",
            "filled_amount": 100,
            "fee": 1.5
        }

        with patch.object(execution_engine, 'get_order_status', return_value=mock_response):
            updated_trade = execution_engine.update_trade_status(trade)

            assert updated_trade.executed_at == original_time


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('polymarket_bot.execution.ExecutionEngine')
    def test_submit_market_order_function(self, mock_engine_class):
        """Test submit_market_order convenience function."""
        mock_engine = Mock()
        mock_trade = Mock(spec=Trade)
        mock_engine.submit_order.return_value = mock_trade
        mock_engine_class.return_value = mock_engine

        result = submit_market_order(
            market_id="market_123",
            side=OrderSide.BUY,
            outcome=OutcomeType.YES,
            quantity=Decimal("100")
        )

        assert result == mock_trade
        mock_engine.submit_order.assert_called_once_with(
            market_id="market_123",
            side=OrderSide.BUY,
            outcome=OutcomeType.YES,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET
        )
        mock_engine.close.assert_called_once()

    @patch('polymarket_bot.execution.ExecutionEngine')
    def test_submit_limit_order_function(self, mock_engine_class):
        """Test submit_limit_order convenience function."""
        mock_engine = Mock()
        mock_trade = Mock(spec=Trade)
        mock_engine.submit_order.return_value = mock_trade
        mock_engine_class.return_value = mock_engine

        result = submit_limit_order(
            market_id="market_123",
            side=OrderSide.SELL,
            outcome=OutcomeType.NO,
            quantity=Decimal("50"),
            price=Decimal("0.80")
        )

        assert result == mock_trade
        mock_engine.submit_order.assert_called_once_with(
            market_id="market_123",
            side=OrderSide.SELL,
            outcome=OutcomeType.NO,
            quantity=Decimal("50"),
            order_type=OrderType.LIMIT,
            price=Decimal("0.80")
        )
        mock_engine.close.assert_called_once()


class TestMakeRequest:
    """Tests for _make_request method."""

    def test_make_request_success(self, execution_engine):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"data": "test"}

        with patch.object(execution_engine.session, 'request', return_value=mock_response):
            result = execution_engine._make_request("GET", "/test")

            assert result == {"data": "test"}

    def test_make_request_http_error(self, execution_engine):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Bad Request"}

        with patch.object(execution_engine.session, 'request', return_value=mock_response):
            with pytest.raises(PolymarketAPIError, match="400"):
                execution_engine._make_request("POST", "/orders")

    def test_make_request_timeout(self, execution_engine):
        """Test handling of request timeout."""
        with patch.object(
            execution_engine.session,
            'request',
            side_effect=requests.exceptions.Timeout("Timeout")
        ):
            with pytest.raises(PolymarketAPIError, match="timeout"):
                execution_engine._make_request("GET", "/test")

    def test_make_request_connection_error(self, execution_engine):
        """Test handling of connection errors."""
        with patch.object(
            execution_engine.session,
            'request',
            side_effect=requests.exceptions.ConnectionError("Connection failed")
        ):
            with pytest.raises(PolymarketAPIError, match="Connection error"):
                execution_engine._make_request("GET", "/test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
