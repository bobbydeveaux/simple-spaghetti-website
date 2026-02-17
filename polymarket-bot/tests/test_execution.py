"""
Unit tests for execution module.

Tests cover:
- Order submission with retry logic (PolymarketAPIClient and ExecutionEngine)
- Settlement polling and status checking
- Outcome determination (WIN/LOSS/PUSH)
- Trade and position updates
- Error handling and timeouts
- Authentication and API requests
"""

import pytest
import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import requests

from polymarket_bot.execution import (
    ExecutionEngine,
    PolymarketAPIClient,
    submit_order,
    submit_market_order,
    submit_limit_order,
    poll_settlement,
    update_trade_with_settlement,
    update_position_with_settlement,
    track_order_lifecycle,
    OrderStatus,
    SettlementOutcome,
    OrderExecutionError,
    OrderSettlementError,
    PolymarketAPIError,
    _determine_outcome
)
from polymarket_bot.models import (
    Trade,
    TradeStatus,
    OrderSide,
    OrderType,
    OutcomeType,
    Position,
    PositionStatus
)
from polymarket_bot.config import Config
from polymarket_bot.utils import ValidationError, RetryError


@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock(spec=Config)
    config.polymarket_base_url = "https://api.polymarket.com"
    config.polymarket_api_key = "test_api_key"
    config.polymarket_api_secret = "test_api_secret"
    config.execution_max_retries = 3
    config.execution_retry_base_delay = 0.1  # Fast for tests
    config.execution_settlement_poll_interval = 1
    config.execution_settlement_timeout = 10
    return config


@pytest.fixture
def execution_engine(mock_config):
    """Create an execution engine with mock config."""
    return ExecutionEngine(mock_config)


class TestPolymarketAPIClient:
    """Test cases for PolymarketAPIClient."""

    def test_client_initialization(self):
        """Test client initializes with correct credentials."""
        client = PolymarketAPIClient(
            api_key="test_key",
            api_secret="test_secret",
            base_url="https://api.polymarket.com"
        )

        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert client.base_url == "https://api.polymarket.com"
        assert isinstance(client._mock_orders, dict)

    def test_submit_order_success(self):
        """Test successful order submission."""
        client = PolymarketAPIClient("key", "secret", "url")

        result = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00"),
            order_type="MARKET"
        )

        assert "order_id" in result
        assert result["market_id"] == "market_123"
        assert result["side"] == "BUY"
        assert result["outcome"] == "YES"
        assert result["amount"] == 10.0
        assert result["status"] == OrderStatus.PENDING.value

    def test_submit_order_with_limit_price(self):
        """Test order submission with limit price."""
        client = PolymarketAPIClient("key", "secret", "url")

        result = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00"),
            order_type="LIMIT",
            price=Decimal("0.65")
        )

        assert result["order_type"] == "LIMIT"
        assert result["price"] == 0.65

    def test_submit_order_invalid_side(self):
        """Test order submission with invalid side."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(OrderExecutionError, match="Invalid side"):
            client.submit_order(
                market_id="market_123",
                side="INVALID",
                outcome="YES",
                amount=Decimal("10.00")
            )

    def test_submit_order_invalid_outcome(self):
        """Test order submission with invalid outcome."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(OrderExecutionError, match="Invalid outcome"):
            client.submit_order(
                market_id="market_123",
                side="BUY",
                outcome="MAYBE",
                amount=Decimal("10.00")
            )

    def test_submit_order_negative_amount(self):
        """Test order submission with negative amount."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(OrderExecutionError, match="Amount must be positive"):
            client.submit_order(
                market_id="market_123",
                side="BUY",
                outcome="YES",
                amount=Decimal("-10.00")
            )

    def test_submit_order_limit_without_price(self):
        """Test LIMIT order submission without price."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(OrderExecutionError, match="Price is required for LIMIT orders"):
            client.submit_order(
                market_id="market_123",
                side="BUY",
                outcome="YES",
                amount=Decimal("10.00"),
                order_type="LIMIT"
            )

    def test_get_order_status_success(self):
        """Test getting order status."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit an order first
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        # Get its status
        status = client.get_order_status(order["order_id"])

        assert status["order_id"] == order["order_id"]
        assert "status" in status

    def test_get_order_status_not_found(self):
        """Test getting status for non-existent order."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(OrderExecutionError, match="Order not found"):
            client.get_order_status("nonexistent_order")


class TestSubmitOrder:
    """Test cases for submit_order function."""

    def test_submit_order_up_direction(self):
        """Test order submission with UP direction."""
        client = PolymarketAPIClient("key", "secret", "url")

        order_id, trade = submit_order(
            client=client,
            market_id="market_123",
            direction="UP",
            size=Decimal("10.00")
        )

        assert order_id is not None
        assert isinstance(trade, Trade)
        assert trade.market_id == "market_123"
        assert trade.outcome == OutcomeType.YES
        assert trade.quantity == Decimal("10.00")
        assert trade.status == TradeStatus.PENDING

    def test_submit_order_down_direction(self):
        """Test order submission with DOWN direction."""
        client = PolymarketAPIClient("key", "secret", "url")

        order_id, trade = submit_order(
            client=client,
            market_id="market_123",
            direction="DOWN",
            size=Decimal("10.00")
        )

        assert trade.outcome == OutcomeType.NO

    def test_submit_order_invalid_direction(self):
        """Test order submission with invalid direction."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(OrderExecutionError, match="Invalid direction"):
            submit_order(
                client=client,
                market_id="market_123",
                direction="SIDEWAYS",
                size=Decimal("10.00")
            )

    def test_submit_order_with_limit_price(self):
        """Test order submission with limit price."""
        client = PolymarketAPIClient("key", "secret", "url")

        order_id, trade = submit_order(
            client=client,
            market_id="market_123",
            direction="UP",
            size=Decimal("10.00"),
            price=Decimal("0.65"),
            order_type="LIMIT"
        )

        assert trade.order_type == OrderType.LIMIT
        assert trade.price == Decimal("0.65")


class TestPollSettlement:
    """Test cases for poll_settlement function."""

    def test_poll_settlement_immediate_settled(self):
        """Test polling when order is already settled."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit and mock immediate settlement
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        # Mock the order as settled
        client._mock_orders[order["order_id"]]["status"] = OrderStatus.SETTLED.value
        client._mock_orders[order["order_id"]]["settlement_outcome"] = SettlementOutcome.WIN.value

        outcome = poll_settlement(
            client=client,
            order_id=order["order_id"],
            timeout=10,
            poll_interval=1
        )

        assert outcome == SettlementOutcome.WIN

    def test_poll_settlement_eventually_settles(self):
        """Test polling that waits for settlement."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit order
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        # The mock client will settle after 60 seconds elapsed time
        # We'll mock time to speed this up
        with patch('polymarket_bot.execution.time.time') as mock_time:
            # Start time
            start = 1000.0
            mock_time.side_effect = [
                start,  # Start
                start + 5,  # First poll
                start + 15,  # Second poll
                start + 70,  # Third poll - should be settled
            ]

            with patch('polymarket_bot.execution.time.sleep'):
                outcome = poll_settlement(
                    client=client,
                    order_id=order["order_id"],
                    timeout=300,
                    poll_interval=10
                )

                assert outcome == SettlementOutcome.WIN

    def test_poll_settlement_timeout(self):
        """Test polling timeout when order doesn't settle."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit order
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        # Mock time to simulate timeout
        with patch('polymarket_bot.execution.time.time') as mock_time:
            mock_time.side_effect = [1000.0, 1002.0, 1005.0, 1011.0]  # Exceeds 10s timeout

            with patch('polymarket_bot.execution.time.sleep'):
                with pytest.raises(OrderSettlementError, match="timed out"):
                    poll_settlement(
                        client=client,
                        order_id=order["order_id"],
                        timeout=10,
                        poll_interval=2
                    )

    def test_poll_settlement_cancelled_order(self):
        """Test polling for a cancelled order."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit and cancel order
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        client._mock_orders[order["order_id"]]["status"] = OrderStatus.CANCELLED.value

        with pytest.raises(OrderSettlementError, match="CANCELLED"):
            poll_settlement(
                client=client,
                order_id=order["order_id"],
                timeout=10,
                poll_interval=1
            )

    def test_poll_settlement_failed_order(self):
        """Test polling for a failed order."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit and fail order
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        client._mock_orders[order["order_id"]]["status"] = OrderStatus.FAILED.value

        with pytest.raises(OrderSettlementError, match="FAILED"):
            poll_settlement(
                client=client,
                order_id=order["order_id"],
                timeout=10,
                poll_interval=1
            )

    def test_poll_settlement_invalid_timeout(self):
        """Test poll_settlement with invalid timeout."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(OrderSettlementError, match="Timeout must be positive"):
            poll_settlement(
                client=client,
                order_id="order_123",
                timeout=-1
            )

    def test_poll_settlement_invalid_interval(self):
        """Test poll_settlement with invalid poll interval."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(OrderSettlementError, match="Poll interval must be positive"):
            poll_settlement(
                client=client,
                order_id="order_123",
                timeout=10,
                poll_interval=-1
            )


class TestDetermineOutcome:
    """Test cases for _determine_outcome function."""

    def test_determine_outcome_with_settlement_outcome(self):
        """Test outcome determination when settlement_outcome is provided."""
        order_data = {
            "order_id": "order_123",
            "settlement_outcome": "WIN"
        }

        outcome = _determine_outcome(order_data)
        assert outcome == SettlementOutcome.WIN

    def test_determine_outcome_win_from_resolution(self):
        """Test WIN outcome from market resolution."""
        order_data = {
            "order_id": "order_123",
            "outcome": "YES",
            "market_resolution": "YES"
        }

        outcome = _determine_outcome(order_data)
        assert outcome == SettlementOutcome.WIN

    def test_determine_outcome_loss_from_resolution(self):
        """Test LOSS outcome from market resolution."""
        order_data = {
            "order_id": "order_123",
            "outcome": "YES",
            "market_resolution": "NO"
        }

        outcome = _determine_outcome(order_data)
        assert outcome == SettlementOutcome.LOSS

    def test_determine_outcome_missing_data(self):
        """Test outcome determination with missing data."""
        order_data = {
            "order_id": "order_123"
        }

        outcome = _determine_outcome(order_data)
        assert outcome == SettlementOutcome.UNKNOWN


class TestUpdateTradeWithSettlement:
    """Test cases for update_trade_with_settlement function."""

    def test_update_trade_win_outcome(self):
        """Test updating trade with WIN outcome."""
        trade = Trade(
            trade_id="trade_123",
            market_id="market_123",
            order_id="order_123",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("10.00")
        )

        updated = update_trade_with_settlement(
            trade=trade,
            outcome=SettlementOutcome.WIN,
            realized_pnl=Decimal("3.50")
        )

        assert updated.status == TradeStatus.EXECUTED
        assert updated.filled_quantity == Decimal("10.00")
        assert updated.executed_at is not None
        assert updated.metadata["settlement_outcome"] == "WIN"
        assert updated.metadata["realized_pnl"] == 3.5

    def test_update_trade_loss_outcome(self):
        """Test updating trade with LOSS outcome."""
        trade = Trade(
            trade_id="trade_123",
            market_id="market_123",
            order_id="order_123",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("10.00")
        )

        updated = update_trade_with_settlement(
            trade=trade,
            outcome=SettlementOutcome.LOSS,
            realized_pnl=Decimal("-6.50")
        )

        assert updated.status == TradeStatus.EXECUTED
        assert updated.metadata["settlement_outcome"] == "LOSS"
        assert updated.metadata["realized_pnl"] == -6.5

    def test_update_trade_push_outcome(self):
        """Test updating trade with PUSH outcome."""
        trade = Trade(
            trade_id="trade_123",
            market_id="market_123",
            order_id="order_123",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("10.00")
        )

        updated = update_trade_with_settlement(
            trade=trade,
            outcome=SettlementOutcome.PUSH
        )

        assert updated.status == TradeStatus.CANCELLED
        assert updated.metadata["settlement_outcome"] == "PUSH"


class TestUpdatePositionWithSettlement:
    """Test cases for update_position_with_settlement function."""

    def test_update_position_win(self):
        """Test updating position with WIN outcome."""
        position = Position(
            position_id="pos_123",
            market_id="market_123",
            outcome=OutcomeType.YES,
            quantity=Decimal("10.00"),
            entry_price=Decimal("0.65"),
            current_price=Decimal("0.65")
        )

        updated = update_position_with_settlement(
            position=position,
            outcome=SettlementOutcome.WIN,
            exit_price=Decimal("1.00")
        )

        assert updated.status == PositionStatus.CLOSED
        assert updated.exit_price == Decimal("1.00")
        assert updated.closed_at is not None
        assert updated.realized_pnl == Decimal("3.50")  # (1.00 - 0.65) * 10
        assert updated.unrealized_pnl == Decimal("0.00")
        assert updated.metadata["settlement_outcome"] == "WIN"

    def test_update_position_loss(self):
        """Test updating position with LOSS outcome."""
        position = Position(
            position_id="pos_123",
            market_id="market_123",
            outcome=OutcomeType.YES,
            quantity=Decimal("10.00"),
            entry_price=Decimal("0.65"),
            current_price=Decimal("0.65")
        )

        updated = update_position_with_settlement(
            position=position,
            outcome=SettlementOutcome.LOSS,
            exit_price=Decimal("0.00")
        )

        assert updated.status == PositionStatus.CLOSED
        assert updated.exit_price == Decimal("0.00")
        assert updated.realized_pnl == Decimal("-6.50")  # (0.00 - 0.65) * 10
        assert updated.metadata["settlement_outcome"] == "LOSS"


class TestTrackOrderLifecycle:
    """Test cases for track_order_lifecycle function."""

    def test_track_order_lifecycle_win(self):
        """Test tracking complete order lifecycle with WIN."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit order
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        # Create trade and position
        trade = Trade(
            trade_id="trade_123",
            market_id="market_123",
            order_id=order["order_id"],
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("10.00")
        )

        position = Position(
            position_id="pos_123",
            market_id="market_123",
            outcome=OutcomeType.YES,
            quantity=Decimal("10.00"),
            entry_price=Decimal("0.65"),
            current_price=Decimal("0.65")
        )

        # Mock immediate settlement
        client._mock_orders[order["order_id"]]["status"] = OrderStatus.SETTLED.value
        client._mock_orders[order["order_id"]]["settlement_outcome"] = SettlementOutcome.WIN.value

        updated_trade, updated_position, outcome = track_order_lifecycle(
            client=client,
            order_id=order["order_id"],
            trade=trade,
            position=position,
            timeout=10,
            poll_interval=1
        )

        assert outcome == SettlementOutcome.WIN
        assert updated_trade.status == TradeStatus.EXECUTED
        assert updated_position.status == PositionStatus.CLOSED
        assert updated_position.realized_pnl == Decimal("3.50")

    def test_track_order_lifecycle_loss(self):
        """Test tracking complete order lifecycle with LOSS."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit order
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        # Create trade
        trade = Trade(
            trade_id="trade_123",
            market_id="market_123",
            order_id=order["order_id"],
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("10.00")
        )

        # Mock immediate settlement with LOSS
        client._mock_orders[order["order_id"]]["status"] = OrderStatus.SETTLED.value
        client._mock_orders[order["order_id"]]["settlement_outcome"] = SettlementOutcome.LOSS.value

        updated_trade, updated_position, outcome = track_order_lifecycle(
            client=client,
            order_id=order["order_id"],
            trade=trade,
            position=None,
            timeout=10,
            poll_interval=1
        )

        assert outcome == SettlementOutcome.LOSS
        assert updated_trade.status == TradeStatus.EXECUTED
        assert updated_position is None
        # Cost = 0.65 * 10 = 6.5, Payout = 0, PnL = -6.5
        assert float(updated_trade.metadata["realized_pnl"]) == -6.5

    def test_track_order_lifecycle_no_position(self):
        """Test tracking order lifecycle without position."""
        client = PolymarketAPIClient("key", "secret", "url")

        # Submit order
        order = client.submit_order(
            market_id="market_123",
            side="BUY",
            outcome="YES",
            amount=Decimal("10.00")
        )

        # Create trade
        trade = Trade(
            trade_id="trade_123",
            market_id="market_123",
            order_id=order["order_id"],
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("10.00")
        )

        # Mock immediate settlement
        client._mock_orders[order["order_id"]]["status"] = OrderStatus.SETTLED.value
        client._mock_orders[order["order_id"]]["settlement_outcome"] = SettlementOutcome.WIN.value

        updated_trade, updated_position, outcome = track_order_lifecycle(
            client=client,
            order_id=order["order_id"],
            trade=trade,
            position=None,
            timeout=10,
            poll_interval=1
        )

        assert outcome == SettlementOutcome.WIN
        assert updated_trade.status == TradeStatus.EXECUTED
        assert updated_position is None


class TestExecutionEngine:
    """Tests for ExecutionEngine class."""

    def test_initialization(self, mock_config):
        """Test engine initialization."""
        engine = ExecutionEngine(mock_config)

        assert engine.config == mock_config
        assert engine.base_url == "https://api.polymarket.com"
        assert engine.api_key == "test_api_key"
        assert engine.api_secret == "test_api_secret"
        assert engine.session is not None
        assert engine.max_retries == 3
        assert engine.settlement_timeout == 10

    def test_session_creation(self, execution_engine):
        """Test that session is created with proper headers."""
        session = execution_engine.session

        assert session.headers['Content-Type'] == 'application/json'
        assert session.headers['User-Agent'] == 'PolymarketBot/1.0'
        assert 'Authorization' in session.headers

    @patch('polymarket_bot.execution.requests.Session.request')
    def test_make_request_success(self, mock_request, execution_engine):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"order_id": "12345", "status": "pending"}
        mock_request.return_value = mock_response

        result = execution_engine._make_request("POST", "/orders", data={"amount": 100})

        assert result == {"order_id": "12345", "status": "pending"}
        mock_request.assert_called_once()

    @patch('polymarket_bot.execution.requests.Session.request')
    def test_make_request_http_error(self, mock_request, execution_engine):
        """Test API request with HTTP error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Bad request"}
        mock_request.return_value = mock_response

        with pytest.raises(PolymarketAPIError) as exc_info:
            execution_engine._make_request("POST", "/orders", data={"amount": 100})

        assert "400" in str(exc_info.value)
        assert exc_info.value.status_code == 400

    @patch('polymarket_bot.execution.requests.Session.request')
    def test_make_request_network_error(self, mock_request, execution_engine):
        """Test API request with network error."""
        mock_request.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(PolymarketAPIError) as exc_info:
            execution_engine._make_request("GET", "/markets")

        assert "Connection error" in str(exc_info.value)


class TestExecutionEngineSubmitOrder:
    """Tests for ExecutionEngine submit_order functionality."""

    @patch('polymarket_bot.execution.ExecutionEngine._make_request')
    def test_submit_market_order_buy_yes(self, mock_request, execution_engine):
        """Test submitting a BUY YES market order."""
        mock_request.return_value = {
            "order_id": "order_123",
            "status": "pending",
            "filled_amount": 0,
            "fee": 0.05
        }

        trade = execution_engine.submit_order(
            market_id="market_456",
            side=OrderSide.BUY,
            outcome=OutcomeType.YES,
            quantity=Decimal("10.0"),
            order_type=OrderType.MARKET
        )

        assert trade.order_id == "order_123"
        assert trade.market_id == "market_456"
        assert trade.side == OrderSide.BUY
        assert trade.outcome == OutcomeType.YES
        assert trade.quantity == Decimal("10.0")
        assert trade.status == TradeStatus.PENDING

        # Verify the request was made with correct data
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/orders"

        data = call_args[1]['data']
        assert data['market_id'] == "market_456"
        assert data['side'] == "BUY"
        assert data['outcome'] == "YES"
        assert data['amount'] == 10.0
        assert data['type'] == "MARKET"

    @patch('polymarket_bot.execution.ExecutionEngine._make_request')
    def test_submit_limit_order(self, mock_request, execution_engine):
        """Test submitting a limit order with price."""
        mock_request.return_value = {
            "id": "order_789",
            "status": "open",
            "filled_amount": 0
        }

        trade = execution_engine.submit_order(
            market_id="market_456",
            side=OrderSide.SELL,
            outcome=OutcomeType.NO,
            quantity=Decimal("5.0"),
            order_type=OrderType.LIMIT,
            price=Decimal("0.65")
        )

        assert trade.order_id == "order_789"
        assert trade.order_type == OrderType.LIMIT
        assert trade.price == Decimal("0.65")

        data = mock_request.call_args[1]['data']
        assert data['type'] == "LIMIT"
        assert data['price'] == 0.65

    def test_submit_order_invalid_market_id(self, execution_engine):
        """Test submitting order with empty market ID."""
        with pytest.raises(ValidationError):
            execution_engine.submit_order(
                market_id="",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("10.0")
            )

    def test_submit_order_invalid_quantity(self, execution_engine):
        """Test submitting order with invalid quantity."""
        with pytest.raises(ValidationError):
            execution_engine.submit_order(
                market_id="market_1",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("0.001")  # Below minimum
            )

    def test_submit_limit_order_missing_price(self, execution_engine):
        """Test that limit order without price raises error."""
        with pytest.raises(OrderExecutionError) as exc_info:
            execution_engine.submit_order(
                market_id="market_1",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("10.0"),
                order_type=OrderType.LIMIT,
                price=None
            )

        assert "price is required" in str(exc_info.value)

    @patch('polymarket_bot.execution.ExecutionEngine._make_request')
    def test_submit_order_missing_order_id(self, mock_request, execution_engine):
        """Test handling response without order_id."""
        mock_request.return_value = {"status": "pending"}  # No order_id

        with pytest.raises(OrderExecutionError) as exc_info:
            execution_engine.submit_order(
                market_id="market_1",
                side=OrderSide.BUY,
                outcome=OutcomeType.YES,
                quantity=Decimal("10.0")
            )

        assert "No order_id" in str(exc_info.value)

    @patch('polymarket_bot.execution.ExecutionEngine._make_request')
    def test_submit_order_with_filled_status(self, mock_request, execution_engine):
        """Test order that is immediately filled."""
        mock_request.return_value = {
            "order_id": "order_123",
            "status": "matched",
            "filled_amount": 10.0,
            "fee": 0.1
        }

        trade = execution_engine.submit_order(
            market_id="market_1",
            side=OrderSide.BUY,
            outcome=OutcomeType.YES,
            quantity=Decimal("10.0")
        )

        assert trade.status == TradeStatus.EXECUTED
        assert trade.filled_quantity == Decimal("10.0")
        assert trade.executed_at is not None


class TestGetOrderStatus:
    """Tests for get_order_status method."""

    @patch('polymarket_bot.execution.ExecutionEngine._make_request')
    def test_get_order_status(self, mock_request, execution_engine):
        """Test getting order status."""
        mock_request.return_value = {
            "order_id": "order_123",
            "status": "pending",
            "market_id": "market_456"
        }

        status = execution_engine.get_order_status("order_123")

        assert status["order_id"] == "order_123"
        assert status["status"] == "pending"
        mock_request.assert_called_once_with("GET", "/orders/order_123")

    def test_get_order_status_invalid_id(self, execution_engine):
        """Test getting status with invalid order ID."""
        with pytest.raises(ValidationError):
            execution_engine.get_order_status("")


class TestExecutionEnginePollSettlement:
    """Tests for ExecutionEngine poll_settlement functionality."""

    @patch('polymarket_bot.execution.ExecutionEngine.get_order_status')
    def test_poll_settlement_immediate_win(self, mock_get_status, execution_engine):
        """Test polling when order is immediately settled as WIN."""
        mock_get_status.return_value = {
            "order_id": "order_123",
            "status": "settled",
            "outcome": "WIN"
        }

        outcome = execution_engine.poll_settlement("order_123")

        assert outcome == "WIN"
        mock_get_status.assert_called_once()

    @patch('polymarket_bot.execution.ExecutionEngine.get_order_status')
    def test_poll_settlement_immediate_loss(self, mock_get_status, execution_engine):
        """Test polling when order is immediately settled as LOSS."""
        mock_get_status.return_value = {
            "order_id": "order_123",
            "status": "settled",
            "outcome": "LOSS"
        }

        outcome = execution_engine.poll_settlement("order_123")

        assert outcome == "LOSS"

    @patch('polymarket_bot.execution.ExecutionEngine.get_order_status')
    @patch('time.sleep')
    def test_poll_settlement_delayed(self, mock_sleep, mock_get_status, execution_engine):
        """Test polling with delayed settlement."""
        # First call: pending, second call: settled
        mock_get_status.side_effect = [
            {"status": "pending"},
            {"status": "settled", "outcome": "WIN"}
        ]

        outcome = execution_engine.poll_settlement("order_123")

        assert outcome == "WIN"
        assert mock_get_status.call_count == 2
        mock_sleep.assert_called()

    @patch('polymarket_bot.execution.ExecutionEngine.get_order_status')
    @patch('time.time')
    def test_poll_settlement_timeout(self, mock_time, mock_get_status, execution_engine):
        """Test polling timeout."""
        # Simulate time passing
        mock_time.side_effect = [0, 0, 5, 11]  # Exceeds 10s timeout

        mock_get_status.return_value = {"status": "pending"}

        with pytest.raises(OrderSettlementError) as exc_info:
            execution_engine.poll_settlement("order_123")

        assert "timeout" in str(exc_info.value).lower()

    @patch('polymarket_bot.execution.ExecutionEngine.get_order_status')
    def test_poll_settlement_cancelled_status(self, mock_get_status, execution_engine):
        """Test handling cancelled order status."""
        mock_get_status.return_value = {"status": "cancelled"}

        outcome = execution_engine.poll_settlement("order_123")

        assert outcome == "CANCELLED"

    @patch('polymarket_bot.execution.ExecutionEngine.get_order_status')
    def test_poll_settlement_failed_status(self, mock_get_status, execution_engine):
        """Test handling failed order status."""
        mock_get_status.return_value = {"status": "failed"}

        with pytest.raises(OrderSettlementError) as exc_info:
            execution_engine.poll_settlement("order_123")

        assert "failed" in str(exc_info.value).lower()

    def test_poll_settlement_invalid_order_id(self, execution_engine):
        """Test polling with invalid order ID."""
        with pytest.raises(ValidationError):
            execution_engine.poll_settlement("")

    @patch('polymarket_bot.execution.ExecutionEngine.get_order_status')
    def test_poll_settlement_unexpected_outcome(self, mock_get_status, execution_engine):
        """Test polling with unexpected outcome value."""
        mock_get_status.return_value = {
            "status": "settled",
            "outcome": "DRAW"  # Unexpected
        }

        # Should default to LOSS
        outcome = execution_engine.poll_settlement("order_123")
        assert outcome == "LOSS"


class TestUpdateTradeStatus:
    """Tests for update_trade_status method."""

    @patch('polymarket_bot.execution.ExecutionEngine.get_order_status')
    def test_update_trade_status(self, mock_get_status, execution_engine):
        """Test updating trade status from API."""
        from polymarket_bot.models import Trade

        # Create a mock trade
        trade = Trade(
            trade_id="trade_123",
            market_id="market_456",
            order_id="order_789",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            outcome=OutcomeType.YES,
            price=Decimal("0"),
            quantity=Decimal("10.0"),
            filled_quantity=Decimal("0"),
            status=TradeStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            fee=Decimal("0")
        )

        mock_get_status.return_value = {
            "status": "matched",
            "filled_amount": 10.0,
            "fee": 0.15
        }

        updated_trade = execution_engine.update_trade_status(trade)

        assert updated_trade.status == TradeStatus.EXECUTED
        assert updated_trade.filled_quantity == Decimal("10.0")
        assert updated_trade.fee == Decimal("0.15")
        assert updated_trade.executed_at is not None


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('polymarket_bot.execution.ExecutionEngine.submit_order')
    @patch('polymarket_bot.execution.ExecutionEngine.close')
    def test_submit_market_order_function(self, mock_close, mock_submit):
        """Test submit_market_order convenience function."""
        from polymarket_bot.models import Trade

        mock_trade = Mock(spec=Trade)
        mock_submit.return_value = mock_trade

        with patch('polymarket_bot.execution.get_config') as mock_get_config:
            mock_get_config.return_value = Mock()
            trade = submit_market_order(
                "market_1",
                OrderSide.BUY,
                OutcomeType.YES,
                Decimal("10.0")
            )

        assert trade == mock_trade
        mock_submit.assert_called_once()
        mock_close.assert_called_once()

    @patch('polymarket_bot.execution.ExecutionEngine.submit_order')
    @patch('polymarket_bot.execution.ExecutionEngine.close')
    def test_submit_limit_order_function(self, mock_close, mock_submit):
        """Test submit_limit_order convenience function."""
        from polymarket_bot.models import Trade

        mock_trade = Mock(spec=Trade)
        mock_submit.return_value = mock_trade

        with patch('polymarket_bot.execution.get_config') as mock_get_config:
            mock_get_config.return_value = Mock()
            trade = submit_limit_order(
                "market_1",
                OrderSide.SELL,
                OutcomeType.NO,
                Decimal("5.0"),
                Decimal("0.45")
            )

        assert trade == mock_trade
        # Verify limit order was called with price
        call_kwargs = mock_submit.call_args[1]
        assert call_kwargs['price'] == Decimal("0.45")
        assert call_kwargs['order_type'] == OrderType.LIMIT
        mock_close.assert_called_once()


class TestCloseMethod:
    """Tests for close method."""

    def test_close_session(self, mock_config):
        """Test that close properly closes the session."""
        engine = ExecutionEngine(mock_config)

        with patch.object(engine.session, 'close') as mock_session_close:
            engine.close()
            mock_session_close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
