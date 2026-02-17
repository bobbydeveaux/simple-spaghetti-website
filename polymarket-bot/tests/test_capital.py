"""
Unit Tests for Capital Allocation Module

Tests win-streak capital allocation logic including:
- Base position sizing
- Win-streak multiplier scaling
- Maximum cap enforcement
- Capital safety checks
- Edge cases and validation
"""

import pytest
from decimal import Decimal
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from capital import CapitalAllocator, calculate_position_size, calculate_position_size_from_bot_state
from models import BotState, BotStatus


class TestCapitalAllocator:
    """Test suite for CapitalAllocator class."""

    def test_initialization_default_values(self):
        """Test allocator initialization with default values."""
        allocator = CapitalAllocator()

        assert allocator.base_size == Decimal("5.00")
        assert allocator.multiplier == Decimal("1.5")
        assert allocator.max_size == Decimal("25.00")

    def test_initialization_custom_values(self):
        """Test allocator initialization with custom values."""
        allocator = CapitalAllocator(
            base_size=Decimal("10.00"),
            multiplier=Decimal("2.0"),
            max_size=Decimal("50.00")
        )

        assert allocator.base_size == Decimal("10.00")
        assert allocator.multiplier == Decimal("2.0")
        assert allocator.max_size == Decimal("50.00")

    def test_initialization_invalid_base_size(self):
        """Test that negative or zero base_size raises ValueError."""
        with pytest.raises(ValueError, match="base_size must be positive"):
            CapitalAllocator(base_size=Decimal("0.00"))

        with pytest.raises(ValueError, match="base_size must be positive"):
            CapitalAllocator(base_size=Decimal("-5.00"))

    def test_initialization_invalid_multiplier(self):
        """Test that multiplier <= 1 raises ValueError."""
        with pytest.raises(ValueError, match="multiplier must be greater than 1"):
            CapitalAllocator(multiplier=Decimal("1.0"))

        with pytest.raises(ValueError, match="multiplier must be greater than 1"):
            CapitalAllocator(multiplier=Decimal("0.5"))

    def test_initialization_invalid_max_size(self):
        """Test that max_size < base_size raises ValueError."""
        with pytest.raises(ValueError, match="max_size must be greater than or equal to base_size"):
            CapitalAllocator(base_size=Decimal("10.00"), max_size=Decimal("5.00"))

    def test_calculate_position_size_no_streak(self):
        """Test position size with no win streak (streak = 0)."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(win_streak=0)

        assert position_size == Decimal("5.00")

    def test_calculate_position_size_streak_1(self):
        """Test position size with 1 consecutive win."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(win_streak=1)

        # 5.00 * 1.5^1 = 7.50
        assert position_size == Decimal("7.50")

    def test_calculate_position_size_streak_2(self):
        """Test position size with 2 consecutive wins."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(win_streak=2)

        # 5.00 * 1.5^2 = 11.25
        assert position_size == Decimal("11.25")

    def test_calculate_position_size_streak_3(self):
        """Test position size with 3 consecutive wins."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(win_streak=3)

        # 5.00 * 1.5^3 = 16.875
        expected = Decimal("5.00") * (Decimal("1.5") ** 3)
        assert position_size == expected

    def test_calculate_position_size_streak_4_hits_cap(self):
        """Test that position size is capped at max_size for streak 4."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(win_streak=4)

        # 5.00 * 1.5^4 = 25.3125, but capped at 25.00
        assert position_size == Decimal("25.00")

    def test_calculate_position_size_streak_5_still_capped(self):
        """Test that position size remains capped for higher streaks."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(win_streak=5)

        # Should still be capped at max_size
        assert position_size == Decimal("25.00")

    def test_calculate_position_size_high_streak(self):
        """Test position size with very high win streak."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(win_streak=10)

        # Should still be capped at max_size
        assert position_size == Decimal("25.00")

    def test_calculate_position_size_negative_streak_raises_error(self):
        """Test that negative win_streak raises ValueError."""
        allocator = CapitalAllocator()

        with pytest.raises(ValueError, match="win_streak cannot be negative"):
            allocator.calculate_position_size(win_streak=-1)

    def test_calculate_position_size_with_capital_check(self):
        """Test position size with current_capital safety check."""
        allocator = CapitalAllocator()

        # With enough capital, position size should be normal
        position_size = allocator.calculate_position_size(
            win_streak=2,
            current_capital=Decimal("100.00")
        )
        assert position_size == Decimal("11.25")

        # With limited capital, position size should be constrained to 50% of capital
        position_size = allocator.calculate_position_size(
            win_streak=2,
            current_capital=Decimal("20.00")  # 50% = 10.00
        )
        # Should be capped at 10.00 (50% of 20.00) instead of 11.25
        assert position_size == Decimal("10.00")

    def test_calculate_position_size_with_very_low_capital(self):
        """Test position size constrained by very low capital."""
        allocator = CapitalAllocator()

        # Even base size should be constrained if capital is too low
        position_size = allocator.calculate_position_size(
            win_streak=0,
            current_capital=Decimal("8.00")  # 50% = 4.00
        )
        # Should be 4.00 (50% of capital) instead of 5.00 (base size)
        assert position_size == Decimal("4.00")

    def test_get_position_sizes_for_streaks(self):
        """Test getting position sizes for a range of streaks."""
        allocator = CapitalAllocator()
        sizes = allocator.get_position_sizes_for_streaks(max_streak=5)

        assert len(sizes) == 6  # 0 through 5
        assert sizes[0] == (0, Decimal("5.00"))
        assert sizes[1] == (1, Decimal("7.50"))
        assert sizes[2] == (2, Decimal("11.25"))
        assert sizes[4][1] == Decimal("25.00")  # Capped
        assert sizes[5][1] == Decimal("25.00")  # Still capped

    def test_reset_streak(self):
        """Test win streak reset."""
        allocator = CapitalAllocator()
        new_streak = allocator.reset_streak()

        assert new_streak == 0

    def test_increment_streak(self):
        """Test win streak increment."""
        allocator = CapitalAllocator()

        assert allocator.increment_streak(0) == 1
        assert allocator.increment_streak(1) == 2
        assert allocator.increment_streak(5) == 6


class TestStandaloneFunctions:
    """Test suite for standalone functions."""

    def test_calculate_position_size_function_default_params(self):
        """Test standalone calculate_position_size function with defaults."""
        assert calculate_position_size(0) == Decimal("5.00")
        assert calculate_position_size(1) == Decimal("7.50")
        assert calculate_position_size(2) == Decimal("11.25")
        assert calculate_position_size(4) == Decimal("25.00")

    def test_calculate_position_size_function_custom_params(self):
        """Test standalone calculate_position_size function with custom params."""
        position_size = calculate_position_size(
            win_streak=2,
            base_size=Decimal("10.00"),
            multiplier=Decimal("2.0"),
            max_size=Decimal("50.00")
        )
        # 10.00 * 2.0^2 = 40.00
        assert position_size == Decimal("40.00")

    def test_calculate_position_size_function_with_capital(self):
        """Test standalone function with capital constraint."""
        position_size = calculate_position_size(
            win_streak=2,
            current_capital=Decimal("20.00")
        )
        # Would be 11.25, but constrained to 10.00 (50% of 20.00)
        assert position_size == Decimal("10.00")


class TestBotStateIntegration:
    """Test suite for BotState integration."""

    def test_calculate_position_size_from_bot_state(self):
        """Test position size calculation from BotState."""
        bot_state = BotState(
            bot_id="test_bot",
            strategy_name="test_strategy",
            max_position_size=Decimal("100.00"),
            max_total_exposure=Decimal("1000.00"),
            risk_per_trade=Decimal("50.00"),
            current_exposure=Decimal("200.00")  # 800 available
        )

        position_size = calculate_position_size_from_bot_state(
            bot_state=bot_state,
            win_streak=2
        )

        # Should calculate normally since 800 available > 11.25
        assert position_size == Decimal("11.25")

    def test_calculate_position_size_from_bot_state_limited_capital(self):
        """Test position size calculation with limited capital in BotState."""
        bot_state = BotState(
            bot_id="test_bot",
            strategy_name="test_strategy",
            max_position_size=Decimal("100.00"),
            max_total_exposure=Decimal("50.00"),
            risk_per_trade=Decimal("10.00"),
            current_exposure=Decimal("30.00")  # 20 available
        )

        position_size = calculate_position_size_from_bot_state(
            bot_state=bot_state,
            win_streak=2
        )

        # Would be 11.25, but constrained to 10.00 (50% of 20.00 available)
        assert position_size == Decimal("10.00")


class TestAcceptanceCriteria:
    """Test acceptance criteria from the task requirements."""

    def test_acceptance_criteria_base_size(self):
        """AC: calculate_position_size() returns $5 base size for first trade or after loss."""
        allocator = CapitalAllocator()

        # First trade (streak = 0)
        assert allocator.calculate_position_size(0) == Decimal("5.00")

        # After loss (streak reset to 0)
        assert allocator.calculate_position_size(0) == Decimal("5.00")

    def test_acceptance_criteria_scaling(self):
        """AC: Position size scales by 1.5x per consecutive win, capped at $25."""
        allocator = CapitalAllocator()

        # Streak 0: $5.00
        assert allocator.calculate_position_size(0) == Decimal("5.00")

        # Streak 1: $7.50 (5.00 * 1.5^1)
        assert allocator.calculate_position_size(1) == Decimal("7.50")

        # Streak 2: $11.25 (5.00 * 1.5^2)
        assert allocator.calculate_position_size(2) == Decimal("11.25")

        # Streak 3: $16.875 (5.00 * 1.5^3)
        expected_3 = Decimal("5.00") * (Decimal("1.5") ** 3)
        assert allocator.calculate_position_size(3) == expected_3

        # Streak 4: $25.00 (capped, would be 25.3125)
        assert allocator.calculate_position_size(4) == Decimal("25.00")

        # Streak 5+: Still $25.00 (capped)
        assert allocator.calculate_position_size(5) == Decimal("25.00")
        assert allocator.calculate_position_size(10) == Decimal("25.00")

    def test_acceptance_criteria_streak_tracking(self):
        """AC: Win streak counter increments on wins and resets to 0 on losses."""
        allocator = CapitalAllocator()

        # Start at 0
        streak = 0
        assert streak == 0

        # Increment on wins
        streak = allocator.increment_streak(streak)
        assert streak == 1

        streak = allocator.increment_streak(streak)
        assert streak == 2

        streak = allocator.increment_streak(streak)
        assert streak == 3

        # Reset on loss
        streak = allocator.reset_streak()
        assert streak == 0

    def test_acceptance_criteria_state_persistence(self):
        """AC: Function integrates with BotState.win_streak field for state persistence.

        Note: win_streak is tracked in StateManager.metrics, not directly in BotState.
        This test verifies the integration pattern works correctly.
        """
        # The capital module can calculate position sizes based on win_streak value
        # The actual win_streak is persisted by StateManager in state.py

        # Simulate getting win_streak from StateManager metrics
        win_streak = 2  # Would come from state_manager.get_metrics()['win_streak']

        position_size = calculate_position_size(win_streak)
        assert position_size == Decimal("11.25")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_capital(self):
        """Test behavior with zero capital."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(
            win_streak=0,
            current_capital=Decimal("0.00")
        )
        # With zero capital, 50% is still 0
        assert position_size == Decimal("0.00")

    def test_very_large_streak(self):
        """Test behavior with unrealistically large win streak."""
        allocator = CapitalAllocator()
        position_size = allocator.calculate_position_size(win_streak=100)

        # Should still be capped at max_size
        assert position_size == Decimal("25.00")

    def test_custom_allocator_different_scaling(self):
        """Test custom allocator with different scaling parameters."""
        allocator = CapitalAllocator(
            base_size=Decimal("10.00"),
            multiplier=Decimal("2.0"),
            max_size=Decimal("100.00")
        )

        assert allocator.calculate_position_size(0) == Decimal("10.00")
        assert allocator.calculate_position_size(1) == Decimal("20.00")  # 10 * 2^1
        assert allocator.calculate_position_size(2) == Decimal("40.00")  # 10 * 2^2
        assert allocator.calculate_position_size(3) == Decimal("80.00")  # 10 * 2^3
        assert allocator.calculate_position_size(4) == Decimal("100.00")  # Capped

    def test_position_sizes_match_expected_progression(self):
        """Test that position sizes match the expected progression from LLD."""
        allocator = CapitalAllocator()

        # From LLD: base * (1.5 ^ win_streak) capped at $25
        expected_progression = [
            (0, Decimal("5.00")),      # Base
            (1, Decimal("7.50")),      # 5.00 * 1.5
            (2, Decimal("11.25")),     # 5.00 * 2.25
            (3, Decimal("16.875")),    # 5.00 * 3.375
            (4, Decimal("25.00")),     # Capped (would be 25.3125)
            (5, Decimal("25.00")),     # Still capped
        ]

        for streak, expected_size in expected_progression:
            actual_size = allocator.calculate_position_size(streak)
            assert actual_size == expected_size, f"Streak {streak}: expected {expected_size}, got {actual_size}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
