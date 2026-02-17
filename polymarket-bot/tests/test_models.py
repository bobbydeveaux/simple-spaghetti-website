"""
Tests for Polymarket Bot Core Data Models

This module contains comprehensive tests for all data models including:
- BotState
- Trade
- Position
- MarketData
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import ValidationError

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import (
    BotState,
    Trade,
    Position,
    MarketData,
    BTCPriceData,
    BotStatus,
    OrderSide,
    OrderType,
    TradeStatus,
    PositionStatus,
    OutcomeType,
)


class TestBotState:
    """Tests for BotState model."""

    def test_bot_state_creation_valid(self):
        """Test creating a valid BotState."""
        bot_state = BotState(
            bot_id="test_bot_001",
            status=BotStatus.RUNNING,
            strategy_name="momentum_v1",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00"),
        )

        assert bot_state.bot_id == "test_bot_001"
        assert bot_state.status == BotStatus.RUNNING
        assert bot_state.strategy_name == "momentum_v1"
        assert bot_state.max_position_size == Decimal("1000.00")
        assert bot_state.total_trades == 0
        assert bot_state.winning_trades == 0
        assert bot_state.api_key_active is True

    def test_bot_state_validation_exposure_limit(self):
        """Test that current exposure cannot exceed max exposure."""
        with pytest.raises(ValidationError) as exc_info:
            BotState(
                bot_id="test_bot_002",
                strategy_name="test_strategy",
                max_position_size=Decimal("1000.00"),
                max_total_exposure=Decimal("5000.00"),
                risk_per_trade=Decimal("100.00"),
                current_exposure=Decimal("6000.00"),  # Exceeds max
            )

        assert "exceeds max total exposure" in str(exc_info.value)

    def test_bot_state_validation_winning_trades(self):
        """Test that winning trades cannot exceed total trades."""
        with pytest.raises(ValidationError) as exc_info:
            BotState(
                bot_id="test_bot_003",
                strategy_name="test_strategy",
                max_position_size=Decimal("1000.00"),
                max_total_exposure=Decimal("5000.00"),
                risk_per_trade=Decimal("100.00"),
                total_trades=10,
                winning_trades=15,  # Exceeds total
            )

        assert "cannot exceed total trades" in str(exc_info.value)

    def test_bot_state_win_rate_calculation(self):
        """Test win rate calculation."""
        bot_state = BotState(
            bot_id="test_bot_004",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00"),
            total_trades=100,
            winning_trades=65,
        )

        assert bot_state.get_win_rate() == 65.0

        # Test zero trades
        bot_state_zero = BotState(
            bot_id="test_bot_005",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00"),
        )
        assert bot_state_zero.get_win_rate() == 0.0

    def test_bot_state_to_dict(self):
        """Test serialization to dictionary."""
        bot_state = BotState(
            bot_id="test_bot_006",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00"),
            active_markets=["market_1", "market_2"],
        )

        data = bot_state.to_dict()

        assert data["bot_id"] == "test_bot_006"
        assert data["strategy_name"] == "test_strategy"
        assert data["max_position_size"] == 1000.00
        assert data["active_markets"] == ["market_1", "market_2"]
        assert "created_at" in data
        assert isinstance(data["created_at"], str)

    def test_bot_state_update_heartbeat(self):
        """Test heartbeat update."""
        bot_state = BotState(
            bot_id="test_bot_007",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00"),
        )

        old_heartbeat = bot_state.last_heartbeat
        old_updated = bot_state.updated_at

        # Wait a small amount and update
        import time
        time.sleep(0.01)
        bot_state.update_heartbeat()

        assert bot_state.last_heartbeat > old_heartbeat
        assert bot_state.updated_at > old_updated


class TestTrade:
    """Tests for Trade model."""

    def test_trade_creation_valid(self):
        """Test creating a valid Trade."""
        trade = Trade(
            trade_id="trade_001",
            market_id="market_123",
            order_id="order_456",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("100.00"),
        )

        assert trade.trade_id == "trade_001"
        assert trade.side == OrderSide.BUY
        assert trade.price == Decimal("0.65")
        assert trade.quantity == Decimal("100.00")
        assert trade.status == TradeStatus.PENDING

    def test_trade_validation_price_range(self):
        """Test that price must be between 0 and 1."""
        with pytest.raises(ValidationError):
            Trade(
                trade_id="trade_002",
                market_id="market_123",
                order_id="order_456",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                outcome=OutcomeType.YES,
                price=Decimal("1.50"),  # Invalid price
                quantity=Decimal("100.00"),
            )

    def test_trade_validation_filled_quantity(self):
        """Test that filled quantity cannot exceed total quantity."""
        with pytest.raises(ValidationError) as exc_info:
            Trade(
                trade_id="trade_003",
                market_id="market_123",
                order_id="order_456",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                outcome=OutcomeType.YES,
                price=Decimal("0.65"),
                quantity=Decimal("100.00"),
                filled_quantity=Decimal("150.00"),  # Exceeds quantity
            )

        assert "cannot exceed total quantity" in str(exc_info.value)

    def test_trade_total_cost_calculation(self):
        """Test total cost calculation including fees."""
        trade = Trade(
            trade_id="trade_004",
            market_id="market_123",
            order_id="order_456",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            outcome=OutcomeType.YES,
            price=Decimal("0.50"),
            quantity=Decimal("100.00"),
            filled_quantity=Decimal("100.00"),
            fee=Decimal("2.50"),
        )

        # Base cost: 0.50 * 100 = 50.00, plus fee 2.50 = 52.50
        assert trade.get_total_cost() == Decimal("52.50")

    def test_trade_is_filled(self):
        """Test is_filled method."""
        trade = Trade(
            trade_id="trade_005",
            market_id="market_123",
            order_id="order_456",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            outcome=OutcomeType.YES,
            price=Decimal("0.50"),
            quantity=Decimal("100.00"),
            filled_quantity=Decimal("100.00"),
            status=TradeStatus.EXECUTED,
        )

        assert trade.is_filled() is True

        # Partial fill
        trade_partial = Trade(
            trade_id="trade_006",
            market_id="market_123",
            order_id="order_456",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            outcome=OutcomeType.YES,
            price=Decimal("0.50"),
            quantity=Decimal("100.00"),
            filled_quantity=Decimal("50.00"),
            status=TradeStatus.PENDING,
        )

        assert trade_partial.is_filled() is False

    def test_trade_to_dict(self):
        """Test serialization to dictionary."""
        trade = Trade(
            trade_id="trade_007",
            market_id="market_123",
            order_id="order_456",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("100.00"),
            metadata={"strategy": "momentum"},
        )

        data = trade.to_dict()

        assert data["trade_id"] == "trade_007"
        assert data["side"] == "buy"
        assert data["price"] == 0.65
        assert data["metadata"]["strategy"] == "momentum"


class TestPosition:
    """Tests for Position model."""

    def test_position_creation_valid(self):
        """Test creating a valid Position."""
        position = Position(
            position_id="pos_001",
            market_id="market_123",
            outcome=OutcomeType.YES,
            quantity=Decimal("100.00"),
            entry_price=Decimal("0.65"),
            current_price=Decimal("0.70"),
        )

        assert position.position_id == "pos_001"
        assert position.status == PositionStatus.OPEN
        assert position.quantity == Decimal("100.00")
        assert position.entry_price == Decimal("0.65")

    def test_position_update_pnl_open(self):
        """Test PnL update for open position."""
        position = Position(
            position_id="pos_002",
            market_id="market_123",
            outcome=OutcomeType.YES,
            quantity=Decimal("100.00"),
            entry_price=Decimal("0.60"),
            current_price=Decimal("0.60"),
        )

        # Update with new price
        position.update_pnl(Decimal("0.70"))

        # Price diff: 0.70 - 0.60 = 0.10, quantity: 100
        # Unrealized PnL: 0.10 * 100 = 10.00
        assert position.unrealized_pnl == Decimal("10.00")
        assert position.current_price == Decimal("0.70")

    def test_position_update_pnl_closed(self):
        """Test PnL update for closed position."""
        position = Position(
            position_id="pos_003",
            market_id="market_123",
            outcome=OutcomeType.YES,
            status=PositionStatus.CLOSED,
            quantity=Decimal("100.00"),
            entry_price=Decimal("0.60"),
            current_price=Decimal("0.60"),
            exit_price=Decimal("0.75"),
        )

        position.update_pnl(Decimal("0.80"))

        # For closed position: exit_price - entry_price = 0.75 - 0.60 = 0.15
        # Realized PnL: 0.15 * 100 = 15.00
        assert position.realized_pnl == Decimal("15.00")
        assert position.unrealized_pnl == Decimal("0.00")

    def test_position_total_pnl(self):
        """Test total PnL calculation."""
        position = Position(
            position_id="pos_004",
            market_id="market_123",
            outcome=OutcomeType.YES,
            quantity=Decimal("100.00"),
            entry_price=Decimal("0.60"),
            current_price=Decimal("0.70"),
            realized_pnl=Decimal("5.00"),
            unrealized_pnl=Decimal("10.00"),
        )

        assert position.get_total_pnl() == Decimal("15.00")

    def test_position_value_calculation(self):
        """Test position value calculation."""
        position = Position(
            position_id="pos_005",
            market_id="market_123",
            outcome=OutcomeType.YES,
            quantity=Decimal("100.00"),
            entry_price=Decimal("0.60"),
            current_price=Decimal("0.70"),
        )

        # 100 * 0.70 = 70.00
        assert position.get_position_value() == Decimal("70.00")

    def test_position_to_dict(self):
        """Test serialization to dictionary."""
        position = Position(
            position_id="pos_006",
            market_id="market_123",
            outcome=OutcomeType.YES,
            quantity=Decimal("100.00"),
            entry_price=Decimal("0.65"),
            current_price=Decimal("0.70"),
            trade_ids=["trade_1", "trade_2"],
        )

        data = position.to_dict()

        assert data["position_id"] == "pos_006"
        assert data["outcome"] == "yes"
        assert data["quantity"] == 100.00
        assert data["trade_ids"] == ["trade_1", "trade_2"]


class TestMarketData:
    """Tests for MarketData model."""

    def test_market_data_creation_valid(self):
        """Test creating valid MarketData."""
        end_date = datetime.utcnow() + timedelta(days=30)
        market = MarketData(
            market_id="market_001",
            question="Will Bitcoin reach $100k in 2024?",
            end_date=end_date,
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35"),
        )

        assert market.market_id == "market_001"
        assert market.question == "Will Bitcoin reach $100k in 2024?"
        assert market.yes_price == Decimal("0.65")
        assert market.is_active is True

    def test_market_data_validation_price_range(self):
        """Test that prices must be between 0 and 1."""
        end_date = datetime.utcnow() + timedelta(days=30)

        with pytest.raises(ValidationError):
            MarketData(
                market_id="market_002",
                question="Test question",
                end_date=end_date,
                yes_price=Decimal("1.50"),  # Invalid
                no_price=Decimal("0.35"),
            )

    def test_market_data_total_volume(self):
        """Test total volume calculation."""
        end_date = datetime.utcnow() + timedelta(days=30)
        market = MarketData(
            market_id="market_003",
            question="Test question",
            end_date=end_date,
            yes_price=Decimal("0.60"),
            no_price=Decimal("0.40"),
            yes_volume=Decimal("150000.00"),
            no_volume=Decimal("85000.00"),
        )

        assert market.get_total_volume() == Decimal("235000.00")

    def test_market_data_price_spread(self):
        """Test price spread calculation."""
        end_date = datetime.utcnow() + timedelta(days=30)
        market = MarketData(
            market_id="market_004",
            question="Test question",
            end_date=end_date,
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35"),
        )

        assert market.get_price_spread() == Decimal("0.30")

    def test_market_data_validate_prices_sum(self):
        """Test price sum validation."""
        end_date = datetime.utcnow() + timedelta(days=30)

        # Valid - prices sum to 1.0
        market_valid = MarketData(
            market_id="market_005",
            question="Test question",
            end_date=end_date,
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35"),
        )
        assert market_valid.validate_prices_sum() is True

        # Invalid - prices don't sum to 1.0
        market_invalid = MarketData(
            market_id="market_006",
            question="Test question",
            end_date=end_date,
            yes_price=Decimal("0.80"),
            no_price=Decimal("0.40"),
        )
        assert market_invalid.validate_prices_sum() is False

    def test_market_data_to_dict(self):
        """Test serialization to dictionary."""
        end_date = datetime.utcnow() + timedelta(days=30)
        market = MarketData(
            market_id="market_007",
            question="Test question",
            end_date=end_date,
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35"),
            tags=["crypto", "bitcoin"],
        )

        data = market.to_dict()

        assert data["market_id"] == "market_007"
        assert data["yes_price"] == 0.65
        assert data["tags"] == ["crypto", "bitcoin"]
        assert data["resolution"] is None

    def test_market_data_with_resolution(self):
        """Test market data with resolution."""
        end_date = datetime.utcnow() - timedelta(days=1)
        market = MarketData(
            market_id="market_008",
            question="Resolved market",
            end_date=end_date,
            yes_price=Decimal("1.00"),
            no_price=Decimal("0.00"),
            is_active=False,
            is_closed=True,
            resolution=OutcomeType.YES,
        )

        assert market.is_closed is True
        assert market.resolution == OutcomeType.YES

        data = market.to_dict()
        assert data["resolution"] == "yes"


class TestModelIntegration:
    """Integration tests for models working together."""

    def test_trade_to_position_workflow(self):
        """Test workflow from trade creation to position update."""
        # Create a trade
        trade = Trade(
            trade_id="trade_int_001",
            market_id="market_int_123",
            order_id="order_int_456",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            outcome=OutcomeType.YES,
            price=Decimal("0.60"),
            quantity=Decimal("100.00"),
            filled_quantity=Decimal("100.00"),
            status=TradeStatus.EXECUTED,
        )

        # Create corresponding position
        position = Position(
            position_id="pos_int_001",
            market_id="market_int_123",
            outcome=OutcomeType.YES,
            quantity=trade.quantity,
            entry_price=trade.price,
            current_price=trade.price,
            trade_ids=[trade.trade_id],
        )

        assert position.quantity == trade.quantity
        assert position.entry_price == trade.price
        assert trade.trade_id in position.trade_ids

        # Update position with market price change
        position.update_pnl(Decimal("0.70"))

        # Expected unrealized PnL: (0.70 - 0.60) * 100 = 10.00
        assert position.unrealized_pnl == Decimal("10.00")

    def test_bot_state_with_trades_and_positions(self):
        """Test bot state tracking with trades and positions."""
        bot = BotState(
            bot_id="bot_int_001",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00"),
            active_markets=["market_int_123"],
            total_trades=2,
            winning_trades=1,
            total_pnl=Decimal("50.00"),
            current_exposure=Decimal("200.00"),
        )

        assert bot.get_win_rate() == 50.0
        assert bot.current_exposure <= bot.max_total_exposure


class TestBTCPriceData:
    """Tests for BTCPriceData model."""

    def test_btc_price_data_creation_valid(self):
        """Test creating a valid BTCPriceData."""
        price_data = BTCPriceData(
            symbol="BTCUSDT",
            price=Decimal("45678.90"),
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            volume_24h=Decimal("123456789.50"),
            high_24h=Decimal("46000.00"),
            low_24h=Decimal("45000.00"),
            price_change_24h=Decimal("678.90"),
            price_change_percent_24h=Decimal("1.51"),
        )

        assert price_data.symbol == "BTCUSDT"
        assert price_data.price == Decimal("45678.90")
        assert price_data.volume_24h == Decimal("123456789.50")
        assert price_data.high_24h == Decimal("46000.00")
        assert price_data.low_24h == Decimal("45000.00")
        assert price_data.price_change_24h == Decimal("678.90")
        assert price_data.price_change_percent_24h == Decimal("1.51")

    def test_btc_price_data_creation_minimal(self):
        """Test creating BTCPriceData with minimal required fields."""
        price_data = BTCPriceData(
            price=Decimal("50000.00"),
            timestamp=datetime.utcnow(),
        )

        assert price_data.symbol == "BTCUSDT"  # default value
        assert price_data.price == Decimal("50000.00")
        assert price_data.volume_24h is None
        assert price_data.high_24h is None
        assert price_data.low_24h is None

    def test_btc_price_data_validation_positive_price(self):
        """Test BTCPriceData validates positive price."""
        with pytest.raises(ValidationError) as exc_info:
            BTCPriceData(
                price=Decimal("0.00"),
                timestamp=datetime.utcnow(),
            )

        assert "greater than 0" in str(exc_info.value).lower()

    def test_btc_price_data_validation_negative_price(self):
        """Test BTCPriceData rejects negative price."""
        with pytest.raises(ValidationError) as exc_info:
            BTCPriceData(
                price=Decimal("-100.00"),
                timestamp=datetime.utcnow(),
            )

        assert "greater than 0" in str(exc_info.value).lower()

    def test_btc_price_data_to_dict(self):
        """Test BTCPriceData to_dict serialization."""
        price_data = BTCPriceData(
            symbol="BTCUSDT",
            price=Decimal("45678.90"),
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            volume_24h=Decimal("123456789.50"),
            high_24h=Decimal("46000.00"),
            low_24h=Decimal("45000.00"),
        )

        data_dict = price_data.to_dict()

        assert data_dict["symbol"] == "BTCUSDT"
        assert data_dict["price"] == 45678.90
        assert data_dict["volume_24h"] == 123456789.50
        assert data_dict["high_24h"] == 46000.00
        assert data_dict["low_24h"] == 45000.00
        assert isinstance(data_dict["timestamp"], str)

    def test_btc_price_data_get_mid_range_price(self):
        """Test calculating mid-range price."""
        price_data = BTCPriceData(
            price=Decimal("45500.00"),
            timestamp=datetime.utcnow(),
            high_24h=Decimal("46000.00"),
            low_24h=Decimal("45000.00"),
        )

        mid_range = price_data.get_mid_range_price()

        assert mid_range == Decimal("45500.00")

    def test_btc_price_data_get_mid_range_price_none_when_missing_high(self):
        """Test mid-range price returns None when high is missing."""
        price_data = BTCPriceData(
            price=Decimal("45500.00"),
            timestamp=datetime.utcnow(),
            low_24h=Decimal("45000.00"),
        )

        mid_range = price_data.get_mid_range_price()

        assert mid_range is None

    def test_btc_price_data_get_mid_range_price_none_when_missing_low(self):
        """Test mid-range price returns None when low is missing."""
        price_data = BTCPriceData(
            price=Decimal("45500.00"),
            timestamp=datetime.utcnow(),
            high_24h=Decimal("46000.00"),
        )

        mid_range = price_data.get_mid_range_price()

        assert mid_range is None

    def test_btc_price_data_get_volatility_percent(self):
        """Test calculating volatility percentage."""
        price_data = BTCPriceData(
            price=Decimal("45500.00"),
            timestamp=datetime.utcnow(),
            high_24h=Decimal("46000.00"),
            low_24h=Decimal("45000.00"),
        )

        volatility = price_data.get_volatility_percent()

        # Range = 1000, Price = 45500, Volatility = (1000 / 45500) * 100 ≈ 2.20%
        assert volatility is not None
        assert abs(volatility - Decimal("2.20")) < Decimal("0.01")

    def test_btc_price_data_get_volatility_percent_none_when_no_range(self):
        """Test volatility returns None when price range data is missing."""
        price_data = BTCPriceData(
            price=Decimal("45500.00"),
            timestamp=datetime.utcnow(),
        )

        volatility = price_data.get_volatility_percent()

        assert volatility is None

    def test_btc_price_data_metadata(self):
        """Test BTCPriceData metadata storage."""
        metadata = {"exchange": "binance", "pair": "BTC/USDT"}
        price_data = BTCPriceData(
            price=Decimal("45678.90"),
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )

        assert price_data.metadata == metadata

    def test_btc_price_data_default_symbol(self):
        """Test BTCPriceData uses default symbol."""
        price_data = BTCPriceData(
            price=Decimal("45678.90"),
            timestamp=datetime.utcnow(),
        )

        assert price_data.symbol == "BTCUSDT"
