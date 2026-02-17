"""
Tests for Capital Allocation Module

Tests verify win-streak position sizing logic according to the specification:
- Base position size returns $5 with zero streak
- Win streak multiplies position size by 1.5x per consecutive win
- Position size caps at $25 regardless of streak length
- Streak resets to 0 on any loss
"""

import pytest
from polymarket_bot.capital import (
    calculate_position_size,
    update_win_streak,
    get_position_size_for_streak,
    BASE_SIZE,
    MULTIPLIER,
    MAX_SIZE
)


class MockBotState:
    """Mock BotState for testing capital allocation."""

    def __init__(self, current_capital: float = 100.0, win_streak: int = 0):
        self.current_capital = current_capital
        self.win_streak = win_streak


class TestCalculatePositionSize:
    """Test suite for calculate_position_size function."""

    def test_base_position_no_streak(self):
        """Test that base position size returns $5 with zero streak."""
        bot_state = MockBotState(current_capital=100.0, win_streak=0)
        position_size = calculate_position_size(bot_state)
        assert position_size == 5.0, "Base position size should be $5 with zero streak"

    def test_position_with_one_win_streak(self):
        """Test position size with one win streak."""
        bot_state = MockBotState(current_capital=100.0, win_streak=1)
        position_size = calculate_position_size(bot_state)
        expected = BASE_SIZE * MULTIPLIER  # 5.0 * 1.5 = 7.5
        assert position_size == expected, f"Position size should be ${expected} with one win streak"

    def test_position_with_two_win_streak(self):
        """Test position size with two win streak."""
        bot_state = MockBotState(current_capital=100.0, win_streak=2)
        position_size = calculate_position_size(bot_state)
        expected = BASE_SIZE * (MULTIPLIER ** 2)  # 5.0 * 1.5^2 = 11.25
        assert position_size == expected, f"Position size should be ${expected} with two win streak"

    def test_position_with_three_win_streak(self):
        """Test position size with three win streak."""
        bot_state = MockBotState(current_capital=100.0, win_streak=3)
        position_size = calculate_position_size(bot_state)
        expected = BASE_SIZE * (MULTIPLIER ** 3)  # 5.0 * 1.5^3 = 16.875
        assert position_size == expected, f"Position size should be ${expected} with three win streak"

    def test_position_cap_at_max_size(self):
        """Test that position size caps at $25 regardless of streak length."""
        # With streak=4: 5.0 * 1.5^4 = 25.3125, should cap at 25.0
        bot_state = MockBotState(current_capital=100.0, win_streak=4)
        position_size = calculate_position_size(bot_state)
        assert position_size == MAX_SIZE, f"Position size should cap at ${MAX_SIZE}"

        # Test with higher streak values
        for streak in [5, 6, 7, 8, 10, 20]:
            bot_state = MockBotState(current_capital=100.0, win_streak=streak)
            position_size = calculate_position_size(bot_state)
            assert position_size == MAX_SIZE, f"Position size should cap at ${MAX_SIZE} for streak={streak}"

    def test_capital_constraint_50_percent(self):
        """Test that position size never exceeds 50% of current capital."""
        # With low capital, the 50% constraint should kick in
        bot_state = MockBotState(current_capital=10.0, win_streak=0)
        position_size = calculate_position_size(bot_state)
        max_allowed = bot_state.current_capital * 0.5
        assert position_size == max_allowed, f"Position size should not exceed 50% of capital ({max_allowed})"
        assert position_size == 5.0, "With $10 capital and 0 streak, position should be $5"

        # With very low capital
        bot_state = MockBotState(current_capital=8.0, win_streak=0)
        position_size = calculate_position_size(bot_state)
        max_allowed = bot_state.current_capital * 0.5
        assert position_size == max_allowed, f"Position size should not exceed 50% of capital ({max_allowed})"
        assert position_size == 4.0, "With $8 capital, position should be $4 (50% of capital)"

    def test_capital_constraint_with_win_streak(self):
        """Test capital constraint with active win streak."""
        # With streak=2 and low capital: base * 1.5^2 = 11.25, but capital = 20, so max = 10
        bot_state = MockBotState(current_capital=20.0, win_streak=2)
        position_size = calculate_position_size(bot_state)
        max_allowed = bot_state.current_capital * 0.5
        assert position_size == max_allowed, f"Position size should be limited by 50% of capital ({max_allowed})"
        assert position_size == 10.0, "With $20 capital and streak=2, position should be $10 (50% of capital)"

    def test_insufficient_capital(self):
        """Test behavior with very low capital."""
        bot_state = MockBotState(current_capital=2.0, win_streak=0)
        position_size = calculate_position_size(bot_state)
        assert position_size == 1.0, "With $2 capital, position should be $1 (50% of capital)"

    def test_zero_capital(self):
        """Test behavior with zero capital."""
        bot_state = MockBotState(current_capital=0.0, win_streak=0)
        position_size = calculate_position_size(bot_state)
        assert position_size == 0.0, "With zero capital, position should be zero"

    def test_negative_capital_handled(self):
        """Test that negative capital is handled (returns 0)."""
        bot_state = MockBotState(current_capital=-10.0, win_streak=0)
        position_size = calculate_position_size(bot_state)
        assert position_size == 0.0, "Negative capital should result in zero position size"


class TestUpdateWinStreak:
    """Test suite for update_win_streak function."""

    def test_streak_increments_on_win(self):
        """Test that streak increments on win."""
        bot_state = MockBotState(win_streak=0)
        new_streak = update_win_streak(bot_state, "WIN")
        assert new_streak == 1, "Streak should increment to 1 after first win"

        bot_state.win_streak = 1
        new_streak = update_win_streak(bot_state, "WIN")
        assert new_streak == 2, "Streak should increment to 2 after second win"

        bot_state.win_streak = 5
        new_streak = update_win_streak(bot_state, "WIN")
        assert new_streak == 6, "Streak should increment to 6 after sixth win"

    def test_streak_resets_on_loss(self):
        """Test that streak resets to 0 on any loss."""
        bot_state = MockBotState(win_streak=0)
        new_streak = update_win_streak(bot_state, "LOSS")
        assert new_streak == 0, "Streak should remain 0 after loss from 0"

        bot_state.win_streak = 1
        new_streak = update_win_streak(bot_state, "LOSS")
        assert new_streak == 0, "Streak should reset to 0 after loss from 1"

        bot_state.win_streak = 5
        new_streak = update_win_streak(bot_state, "LOSS")
        assert new_streak == 0, "Streak should reset to 0 after loss from 5"

        bot_state.win_streak = 10
        new_streak = update_win_streak(bot_state, "LOSS")
        assert new_streak == 0, "Streak should reset to 0 after loss from 10"


class TestGetPositionSizeForStreak:
    """Test suite for get_position_size_for_streak utility function."""

    def test_streak_zero(self):
        """Test position size for zero streak."""
        position_size = get_position_size_for_streak(0)
        assert position_size == 5.0, "Position size should be $5 for zero streak"

    def test_streak_one(self):
        """Test position size for one win streak."""
        position_size = get_position_size_for_streak(1)
        assert position_size == 7.5, "Position size should be $7.5 for one streak"

    def test_streak_two(self):
        """Test position size for two win streak."""
        position_size = get_position_size_for_streak(2)
        assert position_size == 11.25, "Position size should be $11.25 for two streak"

    def test_streak_three(self):
        """Test position size for three win streak."""
        position_size = get_position_size_for_streak(3)
        assert position_size == 16.875, "Position size should be $16.875 for three streak"

    def test_streak_four_caps_at_max(self):
        """Test that streak four caps at max size."""
        position_size = get_position_size_for_streak(4)
        assert position_size == 25.0, "Position size should cap at $25.0 for four streak"

    def test_high_streaks_cap_at_max(self):
        """Test that high streaks cap at max size."""
        for streak in [5, 10, 20, 100]:
            position_size = get_position_size_for_streak(streak)
            assert position_size == 25.0, f"Position size should cap at $25.0 for streak={streak}"

    def test_with_capital_constraint(self):
        """Test position size calculation with capital constraint."""
        position_size = get_position_size_for_streak(0, current_capital=8.0)
        assert position_size == 4.0, "Position size should be limited by 50% of capital ($4)"

        position_size = get_position_size_for_streak(2, current_capital=20.0)
        assert position_size == 10.0, "Position size should be limited by 50% of capital ($10)"


class TestWinStreakScenarios:
    """Test real-world win/loss scenarios."""

    def test_win_streak_flow(self):
        """Test position sizing through a win streak."""
        bot_state = MockBotState(current_capital=100.0, win_streak=0)

        # Initial position
        position = calculate_position_size(bot_state)
        assert position == 5.0, "Initial position should be $5"

        # First win
        bot_state.win_streak = update_win_streak(bot_state, "WIN")
        position = calculate_position_size(bot_state)
        assert position == 7.5, "After first win, position should be $7.5"

        # Second win
        bot_state.win_streak = update_win_streak(bot_state, "WIN")
        position = calculate_position_size(bot_state)
        assert position == 11.25, "After second win, position should be $11.25"

        # Third win
        bot_state.win_streak = update_win_streak(bot_state, "WIN")
        position = calculate_position_size(bot_state)
        assert position == 16.875, "After third win, position should be $16.875"

    def test_loss_resets_streak_flow(self):
        """Test that loss resets streak in a trading flow."""
        bot_state = MockBotState(current_capital=100.0, win_streak=3)

        # Position at streak 3
        position = calculate_position_size(bot_state)
        assert position == 16.875, "Position at streak 3 should be $16.875"

        # Loss resets streak
        bot_state.win_streak = update_win_streak(bot_state, "LOSS")
        assert bot_state.win_streak == 0, "Streak should reset to 0 after loss"

        # Back to base position
        position = calculate_position_size(bot_state)
        assert position == 5.0, "Position should return to base $5 after loss"

    def test_win_loss_win_pattern(self):
        """Test win-loss-win pattern."""
        bot_state = MockBotState(current_capital=100.0, win_streak=0)

        # Win
        bot_state.win_streak = update_win_streak(bot_state, "WIN")
        assert bot_state.win_streak == 1
        position = calculate_position_size(bot_state)
        assert position == 7.5

        # Loss
        bot_state.win_streak = update_win_streak(bot_state, "LOSS")
        assert bot_state.win_streak == 0
        position = calculate_position_size(bot_state)
        assert position == 5.0

        # Win again (restarts streak)
        bot_state.win_streak = update_win_streak(bot_state, "WIN")
        assert bot_state.win_streak == 1
        position = calculate_position_size(bot_state)
        assert position == 7.5


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_high_capital(self):
        """Test with very high capital (no constraint)."""
        bot_state = MockBotState(current_capital=10000.0, win_streak=4)
        position_size = calculate_position_size(bot_state)
        assert position_size == 25.0, "Position should still cap at $25 with high capital"

    def test_exact_threshold_capital(self):
        """Test with capital exactly at threshold."""
        # For streak=0, base_size=5, we need capital=10 for 50% to equal base
        bot_state = MockBotState(current_capital=10.0, win_streak=0)
        position_size = calculate_position_size(bot_state)
        assert position_size == 5.0, "Position should be $5 with $10 capital and 0 streak"

    def test_floating_point_precision(self):
        """Test that floating point calculations are precise."""
        bot_state = MockBotState(current_capital=100.0, win_streak=2)
        position_size = calculate_position_size(bot_state)
        # 5.0 * 1.5^2 = 5.0 * 2.25 = 11.25
        assert abs(position_size - 11.25) < 1e-10, "Position calculation should be precise"


class TestConstants:
    """Test that constants are set correctly."""

    def test_base_size_constant(self):
        """Test BASE_SIZE constant."""
        assert BASE_SIZE == 5.0, "BASE_SIZE should be $5.00"

    def test_multiplier_constant(self):
        """Test MULTIPLIER constant."""
        assert MULTIPLIER == 1.5, "MULTIPLIER should be 1.5x"

    def test_max_size_constant(self):
        """Test MAX_SIZE constant."""
        assert MAX_SIZE == 25.0, "MAX_SIZE should be $25.00"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
