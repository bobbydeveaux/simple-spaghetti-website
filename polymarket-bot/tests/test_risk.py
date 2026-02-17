"""
Comprehensive tests for risk management module.

Tests cover:
- Drawdown threshold boundary conditions (29%, 30%, 31%)
- Volatility circuit breaker at boundary (2.9%, 3%, 3.1%)
- Trade approval/rejection logic with various state combinations
- Edge cases and error handling
"""

import pytest
from pathlib import Path
from decimal import Decimal

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from risk import (
    RiskController,
    check_drawdown,
    check_volatility,
    approve_trade
)
from models import BotState, MarketData, BotStatus, OutcomeType
from datetime import datetime


class TestRiskController:
    """Test RiskController class functionality."""

    @pytest.fixture
    def risk_controller(self):
        """Create a RiskController instance with default settings."""
        return RiskController(
            max_drawdown_percent=30.0,
            max_volatility_percent=3.0,
            starting_capital=100.0
        )

    @pytest.fixture
    def custom_risk_controller(self):
        """Create a RiskController instance with custom settings."""
        return RiskController(
            max_drawdown_percent=20.0,
            max_volatility_percent=5.0,
            starting_capital=1000.0
        )

    # ========================================
    # Drawdown Tests
    # ========================================

    def test_check_drawdown_below_threshold(self, risk_controller):
        """Test drawdown check when drawdown is below threshold (29%)."""
        # 29% drawdown: current_capital = 71.0 (100 - 29)
        passed, reason = risk_controller.check_drawdown(
            current_capital=71.0,
            starting_capital=100.0
        )

        assert passed is True
        assert reason is None

    def test_check_drawdown_at_threshold(self, risk_controller):
        """Test drawdown check when exactly at threshold (30%)."""
        # Exactly 30% drawdown: current_capital = 70.0 (100 - 30)
        passed, reason = risk_controller.check_drawdown(
            current_capital=70.0,
            starting_capital=100.0
        )

        # At exactly 30%, should still pass (not exceeding)
        assert passed is True
        assert reason is None

    def test_check_drawdown_above_threshold(self, risk_controller):
        """Test drawdown check when above threshold (31%)."""
        # 31% drawdown: current_capital = 69.0 (100 - 31)
        passed, reason = risk_controller.check_drawdown(
            current_capital=69.0,
            starting_capital=100.0
        )

        assert passed is False
        assert reason is not None
        assert "31.00%" in reason
        assert "exceeds" in reason.lower()

    def test_check_drawdown_zero_drawdown(self, risk_controller):
        """Test drawdown check with no drawdown (0%)."""
        # No drawdown: current_capital = starting_capital
        passed, reason = risk_controller.check_drawdown(
            current_capital=100.0,
            starting_capital=100.0
        )

        assert passed is True
        assert reason is None

    def test_check_drawdown_negative_drawdown_profit(self, risk_controller):
        """Test drawdown check with profit (negative drawdown)."""
        # Profit scenario: current_capital > starting_capital
        passed, reason = risk_controller.check_drawdown(
            current_capital=150.0,
            starting_capital=100.0
        )

        assert passed is True
        assert reason is None

    def test_check_drawdown_total_loss(self, risk_controller):
        """Test drawdown check with total loss (100% drawdown)."""
        # Total loss: current_capital = 0
        passed, reason = risk_controller.check_drawdown(
            current_capital=0.0,
            starting_capital=100.0
        )

        assert passed is False
        assert reason is not None
        assert "100.00%" in reason

    def test_check_drawdown_invalid_starting_capital(self, risk_controller):
        """Test drawdown check with invalid starting capital."""
        # Zero starting capital
        passed, reason = risk_controller.check_drawdown(
            current_capital=50.0,
            starting_capital=0.0
        )

        assert passed is False
        assert reason is not None
        assert "starting capital" in reason.lower()

        # Negative starting capital
        passed, reason = risk_controller.check_drawdown(
            current_capital=50.0,
            starting_capital=-100.0
        )

        assert passed is False
        assert reason is not None

    def test_check_drawdown_invalid_current_capital(self, risk_controller):
        """Test drawdown check with negative current capital."""
        passed, reason = risk_controller.check_drawdown(
            current_capital=-50.0,
            starting_capital=100.0
        )

        assert passed is False
        assert reason is not None
        assert "current capital" in reason.lower()

    def test_check_drawdown_uses_default_starting_capital(self, risk_controller):
        """Test that drawdown check uses instance's starting capital when not provided."""
        # Don't provide starting_capital, should use instance default (100.0)
        passed, reason = risk_controller.check_drawdown(current_capital=71.0)

        assert passed is True
        assert reason is None

    def test_check_drawdown_boundary_29_percent(self, risk_controller):
        """Test drawdown at exact 29% boundary."""
        passed, reason = risk_controller.check_drawdown(
            current_capital=71.0,
            starting_capital=100.0
        )

        assert passed is True
        assert reason is None

    def test_check_drawdown_boundary_30_percent(self, risk_controller):
        """Test drawdown at exact 30% boundary."""
        passed, reason = risk_controller.check_drawdown(
            current_capital=70.0,
            starting_capital=100.0
        )

        assert passed is True
        assert reason is None

    def test_check_drawdown_boundary_31_percent(self, risk_controller):
        """Test drawdown at exact 31% boundary."""
        passed, reason = risk_controller.check_drawdown(
            current_capital=69.0,
            starting_capital=100.0
        )

        assert passed is False
        assert reason is not None

    # ========================================
    # Volatility Tests
    # ========================================

    def test_check_volatility_below_threshold(self, risk_controller):
        """Test volatility check when volatility is below threshold (2.9%)."""
        # Prices with 2.9% range: min=100, max=102.9, range=2.9%
        price_history = [100.0, 101.0, 102.0, 101.5, 102.9]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is True
        assert reason is None

    def test_check_volatility_at_threshold(self, risk_controller):
        """Test volatility check when exactly at threshold (3%)."""
        # Prices with exactly 3% range: min=100, max=103, range=3%
        price_history = [100.0, 101.0, 103.0, 102.0, 101.5]

        passed, reason = risk_controller.check_volatility(price_history)

        # At exactly 3%, should still pass (not exceeding)
        assert passed is True
        assert reason is None

    def test_check_volatility_above_threshold(self, risk_controller):
        """Test volatility check when above threshold (3.1%)."""
        # Prices with 3.1% range: min=100, max=103.1, range=3.1%
        price_history = [100.0, 101.0, 103.1, 102.0, 101.5]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is False
        assert reason is not None
        assert "3.10%" in reason
        assert "exceeds" in reason.lower()

    def test_check_volatility_zero_volatility(self, risk_controller):
        """Test volatility check with zero volatility (flat prices)."""
        # All prices the same
        price_history = [100.0, 100.0, 100.0, 100.0, 100.0]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is True
        assert reason is None

    def test_check_volatility_high_volatility(self, risk_controller):
        """Test volatility check with very high volatility (>10%)."""
        # Prices with 10% range: min=100, max=110
        price_history = [100.0, 105.0, 110.0, 107.0, 103.0]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is False
        assert reason is not None

    def test_check_volatility_insufficient_history(self, risk_controller):
        """Test volatility check with insufficient price history."""
        # Only 3 prices, but need 5
        price_history = [100.0, 101.0, 102.0]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is False
        assert reason is not None
        assert "insufficient" in reason.lower()

    def test_check_volatility_empty_history(self, risk_controller):
        """Test volatility check with empty price history."""
        price_history = []

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is False
        assert reason is not None
        assert "empty" in reason.lower()

    def test_check_volatility_invalid_prices(self, risk_controller):
        """Test volatility check with invalid (non-positive) prices."""
        # Price history with zero price
        price_history = [100.0, 101.0, 0.0, 102.0, 103.0]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is False
        assert reason is not None
        assert "invalid" in reason.lower()

        # Price history with negative price
        price_history = [100.0, 101.0, -50.0, 102.0, 103.0]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is False
        assert reason is not None

    def test_check_volatility_uses_last_n_prices(self, risk_controller):
        """Test that volatility check uses only the last N prices."""
        # Long price history where only last 5 matter
        # First 10 prices have high volatility, last 5 have low volatility
        price_history = [
            100.0, 90.0, 110.0, 95.0, 105.0,  # High volatility
            100.0, 100.5, 101.0, 100.8, 101.2  # Low volatility (last 5)
        ]

        passed, reason = risk_controller.check_volatility(price_history, lookback_periods=5)

        # Should pass because only last 5 prices are checked
        assert passed is True
        assert reason is None

    def test_check_volatility_custom_lookback(self, risk_controller):
        """Test volatility check with custom lookback period."""
        # Price history with different volatility patterns
        price_history = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]

        # Check last 3 prices (104, 105): ~1% range
        passed, reason = risk_controller.check_volatility(price_history, lookback_periods=3)
        assert passed is True

        # Check last 6 prices (100-105): 5% range
        passed, reason = risk_controller.check_volatility(price_history, lookback_periods=6)
        assert passed is False

    def test_check_volatility_boundary_2_9_percent(self, risk_controller):
        """Test volatility at exact 2.9% boundary."""
        price_history = [100.0, 101.0, 102.9, 101.5, 102.0]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is True
        assert reason is None

    def test_check_volatility_boundary_3_percent(self, risk_controller):
        """Test volatility at exact 3% boundary."""
        price_history = [100.0, 101.0, 103.0, 101.5, 102.0]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is True
        assert reason is None

    def test_check_volatility_boundary_3_1_percent(self, risk_controller):
        """Test volatility at exact 3.1% boundary."""
        price_history = [100.0, 101.0, 103.1, 101.5, 102.0]

        passed, reason = risk_controller.check_volatility(price_history)

        assert passed is False
        assert reason is not None

    # ========================================
    # Trade Approval Tests
    # ========================================

    def test_approve_trade_all_checks_pass(self, risk_controller):
        """Test trade approval when all checks pass."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]  # ~2.5% volatility

        approved, reason = risk_controller.approve_trade(
            signal="UP",
            current_capital=80.0,  # 20% drawdown
            price_history=price_history,
            starting_capital=100.0
        )

        assert approved is True
        assert reason is None

    def test_approve_trade_drawdown_fails(self, risk_controller):
        """Test trade rejection when drawdown check fails."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]  # Low volatility

        approved, reason = risk_controller.approve_trade(
            signal="UP",
            current_capital=65.0,  # 35% drawdown (exceeds 30% threshold)
            price_history=price_history,
            starting_capital=100.0
        )

        assert approved is False
        assert reason is not None
        assert "drawdown" in reason.lower()

    def test_approve_trade_volatility_fails(self, risk_controller):
        """Test trade rejection when volatility check fails."""
        price_history = [100.0, 101.0, 105.0, 102.0, 103.0]  # High volatility (5%)

        approved, reason = risk_controller.approve_trade(
            signal="UP",
            current_capital=80.0,  # 20% drawdown (OK)
            price_history=price_history,
            starting_capital=100.0
        )

        assert approved is False
        assert reason is not None
        assert "volatility" in reason.lower()

    def test_approve_trade_both_checks_fail(self, risk_controller):
        """Test trade rejection when both checks fail."""
        price_history = [100.0, 101.0, 110.0, 105.0, 108.0]  # High volatility

        approved, reason = risk_controller.approve_trade(
            signal="DOWN",
            current_capital=60.0,  # 40% drawdown
            price_history=price_history,
            starting_capital=100.0
        )

        assert approved is False
        assert reason is not None
        # Should fail on first check (drawdown)
        assert "drawdown" in reason.lower()

    def test_approve_trade_skip_signal_always_approved(self, risk_controller):
        """Test that SKIP signals are always approved without validation."""
        # Even with terrible conditions, SKIP should be approved
        price_history = [100.0, 101.0, 150.0, 105.0, 148.0]  # Extreme volatility

        approved, reason = risk_controller.approve_trade(
            signal="SKIP",
            current_capital=10.0,  # 90% drawdown
            price_history=price_history,
            starting_capital=100.0
        )

        assert approved is True
        assert reason is None

    def test_approve_trade_invalid_signal(self, risk_controller):
        """Test trade rejection with invalid signal."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]

        approved, reason = risk_controller.approve_trade(
            signal="INVALID",
            current_capital=80.0,
            price_history=price_history,
            starting_capital=100.0
        )

        assert approved is False
        assert reason is not None
        assert "invalid signal" in reason.lower()

    def test_approve_trade_up_signal(self, risk_controller):
        """Test trade approval with UP signal."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]

        approved, reason = risk_controller.approve_trade(
            signal="UP",
            current_capital=80.0,
            price_history=price_history,
            starting_capital=100.0
        )

        assert approved is True
        assert reason is None

    def test_approve_trade_down_signal(self, risk_controller):
        """Test trade approval with DOWN signal."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]

        approved, reason = risk_controller.approve_trade(
            signal="DOWN",
            current_capital=80.0,
            price_history=price_history,
            starting_capital=100.0
        )

        assert approved is True
        assert reason is None

    def test_approve_trade_with_bot_state(self, risk_controller):
        """Test trade approval with BotState object (for future use)."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]
        bot_state = BotState(
            bot_id="test_bot",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00")
        )

        approved, reason = risk_controller.approve_trade(
            signal="UP",
            current_capital=80.0,
            price_history=price_history,
            starting_capital=100.0,
            bot_state=bot_state
        )

        assert approved is True
        assert reason is None

    def test_approve_trade_with_market_data(self, risk_controller):
        """Test trade approval with MarketData object (for future use)."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]
        market_data = MarketData(
            market_id="test_market",
            question="Test question?",
            end_date=datetime.utcnow(),
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35")
        )

        approved, reason = risk_controller.approve_trade(
            signal="UP",
            current_capital=80.0,
            price_history=price_history,
            starting_capital=100.0,
            market_data=market_data
        )

        assert approved is True
        assert reason is None

    # ========================================
    # Custom Configuration Tests
    # ========================================

    def test_custom_drawdown_threshold(self, custom_risk_controller):
        """Test risk controller with custom drawdown threshold (20%)."""
        # 21% drawdown: should fail with 20% threshold
        passed, reason = custom_risk_controller.check_drawdown(
            current_capital=790.0,
            starting_capital=1000.0
        )

        assert passed is False
        assert reason is not None

        # 19% drawdown: should pass
        passed, reason = custom_risk_controller.check_drawdown(
            current_capital=810.0,
            starting_capital=1000.0
        )

        assert passed is True
        assert reason is None

    def test_custom_volatility_threshold(self, custom_risk_controller):
        """Test risk controller with custom volatility threshold (5%)."""
        # 5.1% volatility: should fail with 5% threshold
        price_history = [100.0, 101.0, 105.1, 102.0, 103.0]

        passed, reason = custom_risk_controller.check_volatility(price_history)

        assert passed is False
        assert reason is not None

        # 4.9% volatility: should pass
        price_history = [100.0, 101.0, 104.9, 102.0, 103.0]

        passed, reason = custom_risk_controller.check_volatility(price_history)

        assert passed is True
        assert reason is None

    def test_custom_starting_capital(self, custom_risk_controller):
        """Test risk controller with custom starting capital (1000)."""
        # Uses instance's starting capital (1000)
        passed, reason = custom_risk_controller.check_drawdown(current_capital=810.0)

        assert passed is True
        assert reason is None


class TestConvenienceFunctions:
    """Test standalone convenience functions."""

    def test_check_drawdown_function(self):
        """Test standalone check_drawdown function."""
        # Should pass at 29% drawdown
        assert check_drawdown(71.0, 100.0, 30.0) is True

        # Should fail at 31% drawdown
        assert check_drawdown(69.0, 100.0, 30.0) is False

    def test_check_volatility_function(self):
        """Test standalone check_volatility function."""
        # Low volatility (should pass)
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]
        assert check_volatility(price_history, 3.0, 5) is True

        # High volatility (should fail)
        price_history = [100.0, 101.0, 105.0, 102.0, 103.0]
        assert check_volatility(price_history, 3.0, 5) is False

    def test_approve_trade_function(self):
        """Test standalone approve_trade function."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]

        # Should approve with good conditions
        assert approve_trade("UP", 80.0, price_history, 100.0, 30.0, 3.0) is True

        # Should reject with bad drawdown
        assert approve_trade("UP", 60.0, price_history, 100.0, 30.0, 3.0) is False

        # Should always approve SKIP
        assert approve_trade("SKIP", 10.0, price_history, 100.0, 30.0, 3.0) is True

    def test_convenience_functions_with_defaults(self):
        """Test that convenience functions use default parameters correctly."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]

        # Test with defaults (30% drawdown, 3% volatility, $100 starting capital)
        result = approve_trade("UP", 80.0, price_history)
        assert result is True


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def risk_controller(self):
        """Create a RiskController instance for testing."""
        return RiskController()

    def test_very_small_capital_amounts(self, risk_controller):
        """Test with very small capital amounts."""
        passed, reason = risk_controller.check_drawdown(
            current_capital=0.01,
            starting_capital=0.10
        )

        # 90% drawdown - should fail
        assert passed is False

    def test_very_large_capital_amounts(self, risk_controller):
        """Test with very large capital amounts."""
        passed, reason = risk_controller.check_drawdown(
            current_capital=1_000_000.0,
            starting_capital=1_500_000.0
        )

        # ~33% drawdown - should fail
        assert passed is False

    def test_fractional_drawdown_percentages(self, risk_controller):
        """Test drawdown calculations with fractional percentages."""
        # 29.99% drawdown
        passed, reason = risk_controller.check_drawdown(
            current_capital=70.01,
            starting_capital=100.0
        )
        assert passed is True

        # 30.01% drawdown
        passed, reason = risk_controller.check_drawdown(
            current_capital=69.99,
            starting_capital=100.0
        )
        assert passed is False

    def test_fractional_volatility_percentages(self, risk_controller):
        """Test volatility calculations with fractional percentages."""
        # 2.99% volatility
        price_history = [100.0, 100.5, 102.99, 101.0, 102.0]
        passed, reason = risk_controller.check_volatility(price_history)
        assert passed is True

        # 3.01% volatility
        price_history = [100.0, 100.5, 103.01, 101.0, 102.0]
        passed, reason = risk_controller.check_volatility(price_history)
        assert passed is False

    def test_price_history_exactly_minimum_length(self, risk_controller):
        """Test with price history exactly at minimum required length."""
        price_history = [100.0, 101.0, 102.0, 101.5, 102.5]  # Exactly 5

        passed, reason = risk_controller.check_volatility(price_history, lookback_periods=5)

        assert passed is True
        assert reason is None

    def test_rejection_reasons_are_descriptive(self, risk_controller):
        """Test that rejection reasons contain useful information."""
        # Test drawdown rejection reason
        passed, reason = risk_controller.check_drawdown(65.0, 100.0)
        assert passed is False
        assert "35.00%" in reason
        assert "30" in reason

        # Test volatility rejection reason
        price_history = [100.0, 101.0, 110.0, 105.0, 108.0]
        passed, reason = risk_controller.check_volatility(price_history)
        assert passed is False
        assert "%" in reason
        assert "3" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
