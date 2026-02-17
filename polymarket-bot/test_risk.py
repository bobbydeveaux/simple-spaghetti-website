"""
Unit tests for risk management module.

Tests cover:
- Drawdown calculation and monitoring
- Volatility calculation and circuit breaker
- Pre-trade validation logic
- Boundary conditions and edge cases
"""

import pytest
from decimal import Decimal
from datetime import datetime

from risk import (
    RiskManager,
    RiskApprovalResult,
    RiskViolation,
    check_drawdown,
    check_volatility,
    approve_trade
)
from models import BotState, MarketData, BotStatus, OutcomeType


class TestDrawdownCalculation:
    """Tests for drawdown calculation logic."""

    def test_no_drawdown_at_peak(self):
        """Test that drawdown is 0% when at peak capital."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        drawdown = rm.calculate_drawdown(Decimal("100.0"))
        assert drawdown == Decimal("0.0")

    def test_basic_drawdown_calculation(self):
        """Test basic drawdown calculation."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        drawdown = rm.calculate_drawdown(Decimal("70.0"))
        assert drawdown == Decimal("30.0")

    def test_drawdown_at_exact_threshold(self):
        """Test drawdown at exactly 30%."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        drawdown = rm.calculate_drawdown(Decimal("70.0"))
        assert drawdown == Decimal("30.0")

    def test_drawdown_below_threshold(self):
        """Test drawdown below 30% threshold."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        drawdown = rm.calculate_drawdown(Decimal("75.0"))
        assert drawdown == Decimal("25.0")

    def test_drawdown_above_threshold(self):
        """Test drawdown above 30% threshold."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        drawdown = rm.calculate_drawdown(Decimal("65.0"))
        assert drawdown == Decimal("35.0")

    def test_drawdown_with_profit(self):
        """Test that drawdown is 0 when in profit."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        drawdown = rm.calculate_drawdown(Decimal("150.0"))
        assert drawdown == Decimal("0.0")

    def test_drawdown_tracks_peak(self):
        """Test that drawdown tracks highest peak."""
        rm = RiskManager(starting_capital=Decimal("100.0"))

        # Profit to $150
        rm.update_peak_capital(Decimal("150.0"))
        assert rm.peak_capital == Decimal("150.0")

        # Drawdown from peak of $150
        drawdown = rm.calculate_drawdown(Decimal("120.0"), rm.peak_capital)
        assert drawdown == Decimal("20.0")  # (150-120)/150 = 20%

    def test_total_loss(self):
        """Test drawdown with total capital loss."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        drawdown = rm.calculate_drawdown(Decimal("0.0"))
        assert drawdown == Decimal("100.0")

    def test_negative_capital_edge_case(self):
        """Test handling of negative capital (edge case)."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        # Negative capital should give 100% drawdown
        drawdown = rm.calculate_drawdown(Decimal("-10.0"))
        assert drawdown >= Decimal("100.0")


class TestDrawdownCheck:
    """Tests for drawdown threshold checking."""

    def test_drawdown_within_limit(self):
        """Test that 29% drawdown passes."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        is_ok, drawdown = rm.check_drawdown(Decimal("71.0"))
        assert is_ok is True
        assert drawdown == Decimal("29.0")

    def test_drawdown_at_exact_limit(self):
        """Test that exactly 30% drawdown fails (threshold is <30, not <=30)."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        is_ok, drawdown = rm.check_drawdown(Decimal("70.0"))
        assert is_ok is False
        assert drawdown == Decimal("30.0")

    def test_drawdown_exceeds_limit(self):
        """Test that 31% drawdown fails."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        is_ok, drawdown = rm.check_drawdown(Decimal("69.0"))
        assert is_ok is False
        assert drawdown == Decimal("31.0")

    def test_custom_drawdown_limit(self):
        """Test with custom drawdown limit."""
        rm = RiskManager(
            starting_capital=Decimal("100.0"),
            max_drawdown_percent=Decimal("20.0")
        )
        is_ok, drawdown = rm.check_drawdown(Decimal("81.0"))
        assert is_ok is True  # 19% drawdown

        is_ok, drawdown = rm.check_drawdown(Decimal("79.0"))
        assert is_ok is False  # 21% drawdown

    def test_boundary_29_percent(self):
        """Test boundary at 29% drawdown (should pass)."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        is_ok, drawdown = rm.check_drawdown(Decimal("71.0"))
        assert is_ok is True
        assert drawdown == Decimal("29.0")

    def test_boundary_30_percent(self):
        """Test boundary at 30% drawdown (should fail)."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        is_ok, drawdown = rm.check_drawdown(Decimal("70.0"))
        assert is_ok is False
        assert drawdown == Decimal("30.0")

    def test_boundary_31_percent(self):
        """Test boundary at 31% drawdown (should fail)."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        is_ok, drawdown = rm.check_drawdown(Decimal("69.0"))
        assert is_ok is False
        assert drawdown == Decimal("31.0")


class TestVolatilityCalculation:
    """Tests for volatility calculation logic."""

    def test_zero_volatility(self):
        """Test volatility with constant prices."""
        rm = RiskManager()
        prices = [Decimal("100.0")] * 5
        volatility = rm.calculate_volatility(prices)
        assert volatility == Decimal("0.0")

    def test_basic_volatility_calculation(self):
        """Test basic volatility calculation."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("102.0"), Decimal("101.0")]
        volatility = rm.calculate_volatility(prices)
        assert volatility == Decimal("2.0")  # (102-100)/100 = 2%

    def test_volatility_below_threshold(self):
        """Test volatility below 3% threshold."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("102.0")]
        volatility = rm.calculate_volatility(prices)
        assert volatility == Decimal("2.0")
        assert volatility < Decimal("3.0")

    def test_volatility_at_threshold(self):
        """Test volatility at exactly 3%."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("103.0")]
        volatility = rm.calculate_volatility(prices)
        assert volatility == Decimal("3.0")

    def test_volatility_above_threshold(self):
        """Test volatility above 3% threshold."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("105.0")]
        volatility = rm.calculate_volatility(prices)
        assert volatility == Decimal("5.0")
        assert volatility > Decimal("3.0")

    def test_volatility_with_multiple_prices(self):
        """Test volatility calculation with multiple price points."""
        rm = RiskManager()
        prices = [
            Decimal("100.0"),
            Decimal("102.0"),
            Decimal("101.0"),
            Decimal("103.0"),
            Decimal("99.0")
        ]
        volatility = rm.calculate_volatility(prices)
        expected = (Decimal("103.0") - Decimal("99.0")) / Decimal("99.0") * Decimal("100.0")
        assert abs(volatility - expected) < Decimal("0.01")

    def test_volatility_empty_list(self):
        """Test that empty price list raises error."""
        rm = RiskManager()
        with pytest.raises(ValueError, match="Price list cannot be empty"):
            rm.calculate_volatility([])

    def test_volatility_single_price(self):
        """Test volatility with single price returns 0."""
        rm = RiskManager()
        volatility = rm.calculate_volatility([Decimal("100.0")])
        assert volatility == Decimal("0.0")

    def test_volatility_invalid_price(self):
        """Test that negative or zero prices raise error."""
        rm = RiskManager()
        with pytest.raises(ValueError, match="Invalid minimum price"):
            rm.calculate_volatility([Decimal("0.0"), Decimal("100.0")])


class TestVolatilityCheck:
    """Tests for volatility threshold checking."""

    def test_volatility_within_limit(self):
        """Test that 2.9% volatility passes."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("102.9")]
        is_ok, volatility = rm.check_volatility(prices)
        assert is_ok is True
        assert volatility == Decimal("2.9")

    def test_volatility_at_exact_limit(self):
        """Test that exactly 3% volatility fails (threshold is <3, not <=3)."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("103.0")]
        is_ok, volatility = rm.check_volatility(prices)
        assert is_ok is False
        assert volatility == Decimal("3.0")

    def test_volatility_exceeds_limit(self):
        """Test that 3.1% volatility fails."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("103.1")]
        is_ok, volatility = rm.check_volatility(prices)
        assert is_ok is False
        assert volatility == Decimal("3.1")

    def test_custom_volatility_limit(self):
        """Test with custom volatility limit."""
        rm = RiskManager(volatility_threshold_percent=Decimal("5.0"))
        prices = [Decimal("100.0"), Decimal("104.0")]
        is_ok, volatility = rm.check_volatility(prices)
        assert is_ok is True  # 4% volatility

        prices = [Decimal("100.0"), Decimal("106.0")]
        is_ok, volatility = rm.check_volatility(prices)
        assert is_ok is False  # 6% volatility

    def test_boundary_2_9_percent(self):
        """Test boundary at 2.9% volatility (should pass)."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("102.9")]
        is_ok, volatility = rm.check_volatility(prices)
        assert is_ok is True

    def test_boundary_3_0_percent(self):
        """Test boundary at 3.0% volatility (should fail)."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("103.0")]
        is_ok, volatility = rm.check_volatility(prices)
        assert is_ok is False

    def test_boundary_3_1_percent(self):
        """Test boundary at 3.1% volatility (should fail)."""
        rm = RiskManager()
        prices = [Decimal("100.0"), Decimal("103.1")]
        is_ok, volatility = rm.check_volatility(prices)
        assert is_ok is False


class TestTradeApproval:
    """Tests for comprehensive trade approval logic."""

    def create_bot_state(
        self,
        total_pnl: Decimal = Decimal("0.0"),
        current_exposure: Decimal = Decimal("0.0"),
        status: BotStatus = BotStatus.RUNNING
    ) -> BotState:
        """Helper to create a bot state for testing."""
        return BotState(
            bot_id="test_bot",
            strategy_name="test_strategy",
            max_position_size=Decimal("25.0"),
            max_total_exposure=Decimal("100.0"),
            risk_per_trade=Decimal("5.0"),
            total_pnl=total_pnl,
            current_exposure=current_exposure,
            status=status
        )

    def test_approve_with_no_violations(self):
        """Test that trade is approved when all checks pass."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = self.create_bot_state(total_pnl=Decimal("10.0"))

        result = rm.approve_trade(bot_state)

        assert result.approved is True
        assert len(result.rejection_reasons) == 0

    def test_reject_on_drawdown_violation(self):
        """Test that trade is rejected when drawdown exceeds limit."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = self.create_bot_state(total_pnl=Decimal("-31.0"))  # 31% drawdown

        result = rm.approve_trade(bot_state)

        assert result.approved is False
        assert any("Drawdown" in reason for reason in result.rejection_reasons)

    def test_reject_on_volatility_violation(self):
        """Test that trade is rejected when volatility exceeds limit."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = self.create_bot_state()

        # Prices with >3% volatility
        prices = [Decimal("100.0"), Decimal("105.0")]

        result = rm.approve_trade(bot_state, recent_prices=prices)

        assert result.approved is False
        assert any("Volatility" in reason for reason in result.rejection_reasons)

    def test_reject_on_insufficient_capital(self):
        """Test that trade is rejected when capital is too low."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = self.create_bot_state(total_pnl=Decimal("-97.0"))  # Only $3 left

        result = rm.approve_trade(bot_state)

        assert result.approved is False
        assert any("Insufficient capital" in reason for reason in result.rejection_reasons)

    def test_reject_on_exposure_limit(self):
        """Test that trade is rejected when exposure limit exceeded."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = self.create_bot_state(
            current_exposure=Decimal("100.0")  # At max exposure
        )

        result = rm.approve_trade(bot_state)

        assert result.approved is False
        assert any("exposure" in reason for reason in result.rejection_reasons)

    def test_reject_on_bot_status(self):
        """Test that trade is rejected when bot is not in running status."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = self.create_bot_state(status=BotStatus.STOPPED)

        result = rm.approve_trade(bot_state)

        assert result.approved is False
        assert any("status" in reason for reason in result.rejection_reasons)

    def test_warnings_when_approaching_limits(self):
        """Test that warnings are issued when approaching risk limits."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        # 25% drawdown = 83.3% of 30% limit
        bot_state = self.create_bot_state(total_pnl=Decimal("-25.0"))

        result = rm.approve_trade(bot_state)

        assert result.approved is True
        assert len(result.warnings) > 0
        assert any("approaching" in warning.lower() for warning in result.warnings)

    def test_multiple_violations(self):
        """Test that multiple violations are all reported."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = self.create_bot_state(
            total_pnl=Decimal("-35.0"),  # Drawdown violation
            current_exposure=Decimal("100.0"),  # Exposure violation
            status=BotStatus.ERROR  # Status violation
        )

        result = rm.approve_trade(bot_state)

        assert result.approved is False
        assert len(result.rejection_reasons) >= 3

    def test_approval_result_details(self):
        """Test that approval result contains detailed metrics."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = self.create_bot_state(total_pnl=Decimal("-20.0"))

        result = rm.approve_trade(bot_state)

        assert 'current_capital' in result.details
        assert 'drawdown_percent' in result.details
        assert result.details['current_capital'] == 80.0
        assert result.details['drawdown_percent'] == 20.0


class TestRiskApprovalResult:
    """Tests for RiskApprovalResult class."""

    def test_result_as_boolean(self):
        """Test that result can be used as boolean."""
        approved = RiskApprovalResult(approved=True)
        rejected = RiskApprovalResult(approved=False)

        assert bool(approved) is True
        assert bool(rejected) is False

    def test_result_string_representation(self):
        """Test string representation of results."""
        approved = RiskApprovalResult(approved=True)
        rejected = RiskApprovalResult(
            approved=False,
            rejection_reasons=["Reason 1", "Reason 2"]
        )

        assert "APPROVED" in str(approved)
        assert "REJECTED" in str(rejected)
        assert "2 reasons" in str(rejected)

    def test_result_with_warnings(self):
        """Test result with warnings."""
        result = RiskApprovalResult(
            approved=True,
            warnings=["Warning 1", "Warning 2"]
        )

        assert result.approved is True
        assert len(result.warnings) == 2
        assert "warnings" in str(result)

    def test_result_serialization(self):
        """Test result can be serialized to dict."""
        result = RiskApprovalResult(
            approved=False,
            rejection_reasons=["Test reason"],
            warnings=["Test warning"],
            details={"test": "value"}
        )

        data = result.to_dict()

        assert data['approved'] is False
        assert data['rejection_reasons'] == ["Test reason"]
        assert data['warnings'] == ["Test warning"]
        assert data['details']['test'] == "value"


class TestRiskManagerMethods:
    """Tests for additional RiskManager methods."""

    def test_update_peak_capital(self):
        """Test peak capital tracking."""
        rm = RiskManager(starting_capital=Decimal("100.0"))

        assert rm.peak_capital == Decimal("100.0")

        rm.update_peak_capital(Decimal("150.0"))
        assert rm.peak_capital == Decimal("150.0")

        # Should not decrease
        rm.update_peak_capital(Decimal("120.0"))
        assert rm.peak_capital == Decimal("150.0")

    def test_reset_risk_manager(self):
        """Test resetting risk manager."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        rm.update_peak_capital(Decimal("150.0"))

        assert rm.peak_capital == Decimal("150.0")

        rm.reset()
        assert rm.peak_capital == Decimal("100.0")

    def test_reset_with_new_capital(self):
        """Test resetting with new starting capital."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        rm.reset(new_starting_capital=Decimal("200.0"))

        assert rm.starting_capital == Decimal("200.0")
        assert rm.peak_capital == Decimal("200.0")

    def test_get_risk_metrics(self):
        """Test getting comprehensive risk metrics."""
        rm = RiskManager(starting_capital=Decimal("100.0"))
        bot_state = BotState(
            bot_id="test",
            strategy_name="test",
            max_position_size=Decimal("25.0"),
            max_total_exposure=Decimal("100.0"),
            risk_per_trade=Decimal("5.0"),
            total_pnl=Decimal("-20.0"),
            total_trades=10,
            winning_trades=6
        )

        metrics = rm.get_risk_metrics(bot_state)

        assert metrics['starting_capital'] == 100.0
        assert metrics['current_capital'] == 80.0
        assert metrics['drawdown_percent'] == 20.0
        assert metrics['win_rate'] == 60.0


class TestStandaloneFunctions:
    """Tests for standalone convenience functions."""

    def test_standalone_check_drawdown(self):
        """Test standalone check_drawdown function."""
        assert check_drawdown(Decimal("75.0"), Decimal("100.0")) is True
        assert check_drawdown(Decimal("69.0"), Decimal("100.0")) is False

    def test_standalone_check_volatility(self):
        """Test standalone check_volatility function."""
        prices_low = [Decimal("100.0"), Decimal("102.0")]
        prices_high = [Decimal("100.0"), Decimal("105.0")]

        assert check_volatility(prices_low) is True
        assert check_volatility(prices_high) is False

    def test_standalone_approve_trade(self):
        """Test standalone approve_trade function."""
        bot_state = BotState(
            bot_id="test",
            strategy_name="test",
            max_position_size=Decimal("25.0"),
            max_total_exposure=Decimal("100.0"),
            risk_per_trade=Decimal("5.0"),
            total_pnl=Decimal("10.0")
        )
        market_data = MarketData(
            market_id="test",
            question="Test market",
            end_date=datetime.utcnow(),
            yes_price=Decimal("0.5"),
            no_price=Decimal("0.5")
        )

        result = approve_trade("UP", market_data, bot_state)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
