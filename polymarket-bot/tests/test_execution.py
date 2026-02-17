"""
Unit tests for the execution module.

Tests cover:
- Order submission with retry logic
- Settlement polling and status checking
- Outcome determination (WIN/LOSS/PUSH)
- Trade and position updates
- Error handling and timeouts
"""

import pytest
import time
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from polymarket_bot.execution import (
    PolymarketAPIClient,
    submit_order,
    poll_settlement,
    update_trade_with_settlement,
    update_position_with_settlement,
    track_order_lifecycle,
    OrderStatus,
    SettlementOutcome,
    ExecutionError,
    SettlementError,
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

        with pytest.raises(ExecutionError, match="Invalid side"):
            client.submit_order(
                market_id="market_123",
                side="INVALID",
                outcome="YES",
                amount=Decimal("10.00")
            )

    def test_submit_order_invalid_outcome(self):
        """Test order submission with invalid outcome."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(ExecutionError, match="Invalid outcome"):
            client.submit_order(
                market_id="market_123",
                side="BUY",
                outcome="MAYBE",
                amount=Decimal("10.00")
            )

    def test_submit_order_negative_amount(self):
        """Test order submission with negative amount."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(ExecutionError, match="Amount must be positive"):
            client.submit_order(
                market_id="market_123",
                side="BUY",
                outcome="YES",
                amount=Decimal("-10.00")
            )

    def test_submit_order_limit_without_price(self):
        """Test LIMIT order submission without price."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(ExecutionError, match="Price is required for LIMIT orders"):
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

        with pytest.raises(ExecutionError, match="Order not found"):
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

        with pytest.raises(ExecutionError, match="Invalid direction"):
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
                with pytest.raises(SettlementError, match="timed out"):
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

        with pytest.raises(SettlementError, match="CANCELLED"):
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

        with pytest.raises(SettlementError, match="FAILED"):
            poll_settlement(
                client=client,
                order_id=order["order_id"],
                timeout=10,
                poll_interval=1
            )

    def test_poll_settlement_invalid_timeout(self):
        """Test poll_settlement with invalid timeout."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(SettlementError, match="Timeout must be positive"):
            poll_settlement(
                client=client,
                order_id="order_123",
                timeout=-1
            )

    def test_poll_settlement_invalid_interval(self):
        """Test poll_settlement with invalid poll interval."""
        client = PolymarketAPIClient("key", "secret", "url")

        with pytest.raises(SettlementError, match="Poll interval must be positive"):
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
