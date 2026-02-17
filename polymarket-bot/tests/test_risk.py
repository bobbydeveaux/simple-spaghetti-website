"""
Comprehensive tests for the risk management module.

Tests cover:
- Drawdown validation with various scenarios
- Volatility circuit breaker functionality
- Trade approval logic
- Edge cases and error handling
- Integration with BotState
"""

import pytest
from decimal import Decimal
from datetime import datetime

from polymarket_bot.risk import (
    check_drawdown,
    check_volatility,
    approve_trade,
    calculate_max_trade_size,
    get_risk_metrics,
    MAX_DRAWDOWN_PERCENT,
    MAX_VOLATILITY_PERCENT
)
from polymarket_bot.models import BotState, MarketData, BotStatus, OutcomeType


class TestCheckDrawdown:
    """Test suite for drawdown validation."""

    def test_drawdown_within_limit(self):
        """Test that trades are approved when drawdown is within limit."""
        # 25% drawdown (75/100) - should pass
        approved, reason = check_drawdown(
            current_capital=Decimal("75.0"),
            starting_capital=Decimal("100.0")
        )
        assert approved is True
        assert reason is None

    def test_drawdown_at_limit(self):
        """Test that trades are approved when drawdown is exactly at limit."""
        # 30% drawdown (70/100) - should pass (at threshold)
        approved, reason = check_drawdown(
            current_capital=Decimal("70.0"),
            starting_capital=Decimal("100.0")
        )
        assert approved is True
        assert reason is None

    def test_drawdown_exceeds_limit(self):
        """Test that trades are blocked when drawdown exceeds limit."""
        # 31% drawdown (69/100) - should fail
        approved, reason = check_drawdown(
            current_capital=Decimal("69.0"),
            starting_capital=Decimal("100.0")
        )
        assert approved is False
        assert reason is not None
        assert "31.00%" in reason
        assert "exceeds maximum threshold" in reason

    def test_drawdown_significant_loss(self):
        """Test drawdown check with significant loss."""
        # 50% drawdown - should fail
        approved, reason = check_drawdown(
            current_capital=Decimal("50.0"),
            starting_capital=Decimal("100.0")
        )
        assert approved is False
        assert "50.00%" in reason

    def test_drawdown_no_loss(self):
        """Test drawdown check with no loss (at starting capital)."""
        approved, reason = check_drawdown(
            current_capital=Decimal("100.0"),
            starting_capital=Decimal("100.0")
        )
        assert approved is True
        assert reason is None

    def test_drawdown_with_profit(self):
        """Test drawdown check when account is in profit."""
        # Account grew from 100 to 120 (negative drawdown)
        approved, reason = check_drawdown(
            current_capital=Decimal("120.0"),
            starting_capital=Decimal("100.0")
        )
        assert approved is True
        assert reason is None

    def test_drawdown_different_starting_capital(self):
        """Test drawdown calculation with different starting capital."""
        # 25% drawdown with starting capital of 500
        approved, reason = check_drawdown(
            current_capital=Decimal("375.0"),
            starting_capital=Decimal("500.0")
        )
        assert approved is True
        assert reason is None

    def test_drawdown_invalid_starting_capital_zero(self):
        """Test that zero starting capital is rejected."""
        approved, reason = check_drawdown(
            current_capital=Decimal("50.0"),
            starting_capital=Decimal("0.0")
        )
        assert approved is False
        assert "Invalid starting capital" in reason

    def test_drawdown_invalid_starting_capital_negative(self):
        """Test that negative starting capital is rejected."""
        approved, reason = check_drawdown(
            current_capital=Decimal("50.0"),
            starting_capital=Decimal("-100.0")
        )
        assert approved is False
        assert "Invalid starting capital" in reason

    def test_drawdown_invalid_current_capital_negative(self):
        """Test that negative current capital is rejected."""
        approved, reason = check_drawdown(
            current_capital=Decimal("-10.0"),
            starting_capital=Decimal("100.0")
        )
        assert approved is False
        assert "Invalid current capital" in reason

    def test_drawdown_precision(self):
        """Test drawdown calculation with high precision values."""
        # Exactly 30.00% drawdown
        approved, reason = check_drawdown(
            current_capital=Decimal("70.00"),
            starting_capital=Decimal("100.00")
        )
        assert approved is True

        # Slightly over 30% (30.01%)
        approved, reason = check_drawdown(
            current_capital=Decimal("69.99"),
            starting_capital=Decimal("100.00")
        )
        assert approved is False


class TestCheckVolatility:
    """Test suite for volatility validation."""

    def test_volatility_within_limit(self):
        """Test that trades are approved when volatility is within limit."""
        # 2% volatility - should pass
        prices = [
            Decimal("100.0"),
            Decimal("101.0"),
            Decimal("102.0"),
            Decimal("101.5"),
            Decimal("100.5")
        ]
        approved, reason = check_volatility(prices)
        assert approved is True
        assert reason is None

    def test_volatility_exceeds_limit(self):
        """Test that trades are blocked when volatility exceeds limit."""
        # 4% volatility - should fail
        prices = [
            Decimal("100.0"),
            Decimal("96.0"),
            Decimal("104.0"),
            Decimal("100.0"),
            Decimal("98.0")
        ]
        approved, reason = check_volatility(prices)
        assert approved is False
        assert reason is not None
        assert "exceeds maximum threshold" in reason

    def test_volatility_at_limit(self):
        """Test volatility exactly at threshold."""
        # Create price range that results in exactly 3% volatility
        prices = [
            Decimal("100.0"),
            Decimal("103.0"),
            Decimal("100.0")
        ]
        approved, reason = check_volatility(prices)
        assert approved is True

    def test_volatility_uses_last_five_prices(self):
        """Test that volatility calculation uses only last 5 prices."""
        # Large volatility in older data, stable in recent 5
        prices = [
            Decimal("100.0"),
            Decimal("150.0"),  # Old spike
            Decimal("101.0"),
            Decimal("101.5"),
            Decimal("102.0"),
            Decimal("101.5"),
            Decimal("101.0")
        ]
        approved, reason = check_volatility(prices)
        assert approved is True  # Recent 5 prices are stable

    def test_volatility_with_fewer_than_five_prices(self):
        """Test volatility calculation with less than 5 prices."""
        prices = [
            Decimal("100.0"),
            Decimal("101.0"),
            Decimal("100.5")
        ]
        approved, reason = check_volatility(prices)
        assert approved is True

    def test_volatility_with_single_price(self):
        """Test volatility with only one price (insufficient data)."""
        prices = [Decimal("100.0")]
        approved, reason = check_volatility(prices)
        assert approved is True  # Approved by default with insufficient data

    def test_volatility_empty_list(self):
        """Test that empty price list is rejected."""
        prices = []
        approved, reason = check_volatility(prices)
        assert approved is False
        assert "empty" in reason.lower()

    def test_volatility_with_zero_price(self):
        """Test that zero prices are rejected."""
        prices = [
            Decimal("100.0"),
            Decimal("0.0"),
            Decimal("101.0")
        ]
        approved, reason = check_volatility(prices)
        assert approved is False
        assert "non-positive" in reason.lower()

    def test_volatility_with_negative_price(self):
        """Test that negative prices are rejected."""
        prices = [
            Decimal("100.0"),
            Decimal("-50.0"),
            Decimal("101.0")
        ]
        approved, reason = check_volatility(prices)
        assert approved is False
        assert "non-positive" in reason.lower()

    def test_volatility_high_price_range(self):
        """Test with high volatility scenario."""
        # 10% volatility
        prices = [
            Decimal("100.0"),
            Decimal("90.0"),
            Decimal("110.0"),
            Decimal("95.0"),
            Decimal("105.0")
        ]
        approved, reason = check_volatility(prices)
        assert approved is False

    def test_volatility_stable_prices(self):
        """Test with very stable prices (minimal volatility)."""
        prices = [
            Decimal("100.0"),
            Decimal("100.0"),
            Decimal("100.0"),
            Decimal("100.0"),
            Decimal("100.0")
        ]
        approved, reason = check_volatility(prices)
        assert approved is True


class TestApproveTrade:
    """Test suite for trade approval logic."""

    @pytest.fixture
    def bot_state(self):
        """Create a sample bot state for testing."""
        return BotState(
            bot_id="test_bot_001",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.0"),
            max_total_exposure=Decimal("5000.0"),
            risk_per_trade=Decimal("500.0"),
            total_trades=10,
            winning_trades=6,
            total_pnl=Decimal("250.0"),
            current_exposure=Decimal("1500.0")
        )

    @pytest.fixture
    def market_data(self):
        """Create sample market data for testing."""
        return MarketData(
            market_id="test_market_001",
            question="Will BTC reach $100k?",
            end_date=datetime(2024, 12, 31),
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35"),
            yes_volume=Decimal("50000.0"),
            no_volume=Decimal("30000.0"),
            total_liquidity=Decimal("10000.0"),
            is_active=True,
            is_closed=False
        )

    @pytest.fixture
    def price_history(self):
        """Create sample price history for testing."""
        return [
            Decimal("45000.0"),
            Decimal("45100.0"),
            Decimal("45200.0"),
            Decimal("45150.0"),
            Decimal("45100.0")
        ]

    def test_approve_trade_all_checks_pass(self, bot_state, market_data, price_history):
        """Test that trade is approved when all checks pass."""
        approved, reason = approve_trade(
            signal="UP",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is True
        assert reason is None

    def test_approve_trade_skip_signal(self, bot_state, market_data, price_history):
        """Test that SKIP signal is always approved."""
        approved, reason = approve_trade(
            signal="SKIP",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is True
        assert reason is None

    def test_approve_trade_invalid_signal(self, bot_state, market_data, price_history):
        """Test that invalid signal is rejected."""
        approved, reason = approve_trade(
            signal="INVALID",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is False
        assert "Invalid signal" in reason

    def test_approve_trade_high_drawdown(self, bot_state, market_data, price_history):
        """Test that trade is blocked when drawdown is too high."""
        # Set total_pnl to create >30% drawdown
        bot_state.total_pnl = Decimal("-2000.0")  # Results in 40% drawdown

        approved, reason = approve_trade(
            signal="UP",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is False
        assert "Drawdown" in reason

    def test_approve_trade_high_volatility(self, bot_state, market_data):
        """Test that trade is blocked when volatility is too high."""
        high_volatility_prices = [
            Decimal("45000.0"),
            Decimal("43000.0"),
            Decimal("47000.0"),
            Decimal("44000.0"),
            Decimal("46000.0")
        ]

        approved, reason = approve_trade(
            signal="DOWN",
            market_data=market_data,
            bot_state=bot_state,
            price_history=high_volatility_prices
        )
        assert approved is False
        assert "Volatility" in reason

    def test_approve_trade_market_not_active(self, bot_state, market_data, price_history):
        """Test that trade is blocked when market is not active."""
        market_data.is_active = False

        approved, reason = approve_trade(
            signal="UP",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is False
        assert "not active" in reason

    def test_approve_trade_market_closed(self, bot_state, market_data, price_history):
        """Test that trade is blocked when market is closed."""
        market_data.is_closed = True

        approved, reason = approve_trade(
            signal="UP",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is False
        assert "closed" in reason

    def test_approve_trade_insufficient_liquidity(self, bot_state, market_data, price_history):
        """Test that trade is blocked when market has no liquidity."""
        market_data.total_liquidity = Decimal("0.0")

        approved, reason = approve_trade(
            signal="UP",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is False
        assert "liquidity" in reason.lower()

    def test_approve_trade_max_exposure_reached(self, bot_state, market_data, price_history):
        """Test that trade is blocked when at max exposure."""
        bot_state.current_exposure = bot_state.max_total_exposure

        approved, reason = approve_trade(
            signal="UP",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is False
        assert "exposure" in reason.lower()

    def test_approve_trade_no_price_history(self, bot_state, market_data):
        """Test that trade can be approved without price history."""
        approved, reason = approve_trade(
            signal="UP",
            market_data=market_data,
            bot_state=bot_state,
            price_history=None
        )
        assert approved is True
        assert reason is None

    def test_approve_trade_empty_price_history(self, bot_state, market_data):
        """Test that trade can be approved with empty price history."""
        approved, reason = approve_trade(
            signal="DOWN",
            market_data=market_data,
            bot_state=bot_state,
            price_history=[]
        )
        assert approved is True

    def test_approve_trade_down_signal(self, bot_state, market_data, price_history):
        """Test approval with DOWN signal."""
        approved, reason = approve_trade(
            signal="DOWN",
            market_data=market_data,
            bot_state=bot_state,
            price_history=price_history
        )
        assert approved is True
        assert reason is None


class TestCalculateMaxTradeSize:
    """Test suite for maximum trade size calculation."""

    @pytest.fixture
    def bot_state(self):
        """Create a sample bot state for testing."""
        return BotState(
            bot_id="test_bot_001",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.0"),
            max_total_exposure=Decimal("5000.0"),
            risk_per_trade=Decimal("500.0"),
            current_exposure=Decimal("1500.0")
        )

    @pytest.fixture
    def market_data(self):
        """Create sample market data for testing."""
        return MarketData(
            market_id="test_market_001",
            question="Test market",
            end_date=datetime(2024, 12, 31),
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35"),
            total_liquidity=Decimal("10000.0")
        )

    def test_max_trade_size_limited_by_position_size(self, bot_state, market_data):
        """Test max trade size when limited by max position size."""
        # risk_per_trade (500) < max_position_size (1000) < remaining_exposure (3500)
        max_size = calculate_max_trade_size(bot_state, market_data)
        assert max_size == Decimal("500.0")  # Limited by risk_per_trade

    def test_max_trade_size_limited_by_remaining_exposure(self, bot_state, market_data):
        """Test max trade size when limited by remaining exposure."""
        bot_state.current_exposure = Decimal("4700.0")
        # Remaining exposure = 300, which is less than risk_per_trade and max_position_size

        max_size = calculate_max_trade_size(bot_state, market_data)
        assert max_size == Decimal("300.0")

    def test_max_trade_size_at_max_exposure(self, bot_state, market_data):
        """Test max trade size when at maximum exposure."""
        bot_state.current_exposure = bot_state.max_total_exposure

        max_size = calculate_max_trade_size(bot_state, market_data)
        assert max_size == Decimal("0.0")

    def test_max_trade_size_no_exposure(self, bot_state, market_data):
        """Test max trade size with no current exposure."""
        bot_state.current_exposure = Decimal("0.0")

        max_size = calculate_max_trade_size(bot_state, market_data)
        # Should be minimum of max_position_size (1000), max_exposure (5000), risk_per_trade (500)
        assert max_size == Decimal("500.0")


class TestGetRiskMetrics:
    """Test suite for risk metrics calculation."""

    @pytest.fixture
    def bot_state(self):
        """Create a sample bot state for testing."""
        return BotState(
            bot_id="test_bot_001",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.0"),
            max_total_exposure=Decimal("5000.0"),
            risk_per_trade=Decimal("500.0"),
            total_trades=20,
            winning_trades=12,
            total_pnl=Decimal("250.0"),
            current_exposure=Decimal("2000.0")
        )

    @pytest.fixture
    def price_history(self):
        """Create sample price history for testing."""
        return [
            Decimal("45000.0"),
            Decimal("45500.0"),
            Decimal("46000.0"),
            Decimal("45750.0"),
            Decimal("45500.0")
        ]

    def test_get_risk_metrics_complete(self, bot_state, price_history):
        """Test risk metrics calculation with all data."""
        metrics = get_risk_metrics(bot_state, price_history)

        assert "current_capital" in metrics
        assert "starting_capital" in metrics
        assert "drawdown_percent" in metrics
        assert "volatility_percent" in metrics
        assert "exposure_utilization_percent" in metrics
        assert "win_rate_percent" in metrics
        assert "total_pnl" in metrics

        # Verify values
        assert metrics["current_capital"] == 5250.0  # 5000 + 250
        assert metrics["starting_capital"] == 5000.0
        assert metrics["total_pnl"] == 250.0
        assert metrics["total_trades"] == 20
        assert metrics["winning_trades"] == 12
        assert metrics["win_rate_percent"] == 60.0  # 12/20 * 100

    def test_get_risk_metrics_no_price_history(self, bot_state):
        """Test risk metrics without price history."""
        metrics = get_risk_metrics(bot_state, None)

        assert metrics["volatility_percent"] is None
        assert "drawdown_percent" in metrics
        assert "win_rate_percent" in metrics

    def test_get_risk_metrics_with_loss(self, bot_state, price_history):
        """Test risk metrics with negative PnL."""
        bot_state.total_pnl = Decimal("-1000.0")

        metrics = get_risk_metrics(bot_state, price_history)

        assert metrics["current_capital"] == 4000.0  # 5000 - 1000
        assert metrics["drawdown_percent"] == 20.0  # 1000/5000 * 100

    def test_get_risk_metrics_exposure_utilization(self, bot_state, price_history):
        """Test exposure utilization calculation."""
        bot_state.current_exposure = Decimal("2500.0")
        bot_state.max_total_exposure = Decimal("5000.0")

        metrics = get_risk_metrics(bot_state, price_history)

        assert metrics["exposure_utilization_percent"] == 50.0

    def test_get_risk_metrics_zero_trades(self, bot_state, price_history):
        """Test risk metrics with no trades."""
        bot_state.total_trades = 0
        bot_state.winning_trades = 0

        metrics = get_risk_metrics(bot_state, price_history)

        assert metrics["win_rate_percent"] == 0.0
        assert metrics["total_trades"] == 0

    def test_get_risk_metrics_insufficient_price_data(self, bot_state):
        """Test risk metrics with insufficient price data."""
        prices = [Decimal("45000.0")]

        metrics = get_risk_metrics(bot_state, prices)

        assert metrics["volatility_percent"] is None


class TestRiskThresholds:
    """Test suite to verify risk threshold constants."""

    def test_max_drawdown_threshold(self):
        """Verify max drawdown threshold is set correctly."""
        assert MAX_DRAWDOWN_PERCENT == Decimal("30.0")

    def test_max_volatility_threshold(self):
        """Verify max volatility threshold is set correctly."""
        assert MAX_VOLATILITY_PERCENT == Decimal("3.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
