"""
Capital Allocation Module

This module implements position sizing with win-streak capital allocation logic.
Position sizes scale with consecutive wins using a multiplier system, with a
maximum cap to manage risk.

Formula:
    position_size = min(base_size * (multiplier ** win_streak), max_size)

Default Parameters:
    - base_size: $5.00
    - multiplier: 1.5x
    - max_size: $25.00
"""

from decimal import Decimal
from typing import Optional
from models import BotState


class CapitalAllocator:
    """
    Capital allocator implementing win-streak position sizing.

    Scales position size based on consecutive winning trades, with configurable
    base size, multiplier, and maximum cap.
    """

    def __init__(
        self,
        base_size: Decimal = Decimal("5.00"),
        multiplier: Decimal = Decimal("1.5"),
        max_size: Decimal = Decimal("25.00")
    ):
        """
        Initialize the capital allocator.

        Args:
            base_size: Base position size in USD (default: $5.00)
            multiplier: Multiplier per consecutive win (default: 1.5)
            max_size: Maximum position size cap in USD (default: $25.00)

        Raises:
            ValueError: If parameters are invalid
        """
        if base_size <= 0:
            raise ValueError("base_size must be positive")
        if multiplier <= 1:
            raise ValueError("multiplier must be greater than 1")
        if max_size < base_size:
            raise ValueError("max_size must be greater than or equal to base_size")

        self.base_size = base_size
        self.multiplier = multiplier
        self.max_size = max_size

    def calculate_position_size(self, win_streak: int, current_capital: Optional[Decimal] = None) -> Decimal:
        """
        Calculate position size based on current win streak.

        Implements the formula: position_size = min(base_size * (multiplier ** win_streak), max_size)

        Args:
            win_streak: Current number of consecutive wins (0 for no streak)
            current_capital: Current available capital (optional, for additional safety checks)

        Returns:
            Position size in USD

        Raises:
            ValueError: If win_streak is negative
        """
        if win_streak < 0:
            raise ValueError("win_streak cannot be negative")

        # Calculate position size with win-streak multiplier
        if win_streak == 0:
            position_size = self.base_size
        else:
            position_size = self.base_size * (self.multiplier ** win_streak)

        # Apply maximum cap
        position_size = min(position_size, self.max_size)

        # Additional safety check: never exceed 50% of current capital
        if current_capital is not None and current_capital > 0:
            max_allowed = current_capital * Decimal("0.5")
            position_size = min(position_size, max_allowed)

        return position_size

    def get_position_sizes_for_streaks(self, max_streak: int = 10) -> list:
        """
        Get position sizes for a range of win streaks (useful for testing/display).

        Args:
            max_streak: Maximum streak to calculate (default: 10)

        Returns:
            List of tuples (streak, position_size)
        """
        return [
            (streak, self.calculate_position_size(streak))
            for streak in range(max_streak + 1)
        ]

    def reset_streak(self) -> int:
        """
        Reset win streak to 0 (to be called after a loss).

        Returns:
            New win streak value (always 0)
        """
        return 0

    def increment_streak(self, current_streak: int) -> int:
        """
        Increment win streak by 1 (to be called after a win).

        Args:
            current_streak: Current win streak

        Returns:
            New win streak value (current_streak + 1)
        """
        return current_streak + 1


def calculate_position_size(
    win_streak: int,
    current_capital: Optional[Decimal] = None,
    base_size: Decimal = Decimal("5.00"),
    multiplier: Decimal = Decimal("1.5"),
    max_size: Decimal = Decimal("25.00")
) -> Decimal:
    """
    Calculate position size based on win streak (convenience function).

    This is a standalone function that provides the same functionality as
    CapitalAllocator.calculate_position_size() without requiring class instantiation.

    Args:
        win_streak: Current number of consecutive wins (0 for no streak)
        current_capital: Current available capital (optional, for additional safety checks)
        base_size: Base position size in USD (default: $5.00)
        multiplier: Multiplier per consecutive win (default: 1.5)
        max_size: Maximum position size cap in USD (default: $25.00)

    Returns:
        Position size in USD

    Examples:
        >>> calculate_position_size(0)  # First trade or after a loss
        Decimal('5.00')

        >>> calculate_position_size(1)  # After 1 win
        Decimal('7.50')

        >>> calculate_position_size(2)  # After 2 consecutive wins
        Decimal('11.25')

        >>> calculate_position_size(3)  # After 3 consecutive wins
        Decimal('16.88')

        >>> calculate_position_size(4)  # After 4 consecutive wins
        Decimal('25.00')  # Capped at max_size

        >>> calculate_position_size(5)  # After 5 consecutive wins
        Decimal('25.00')  # Still capped at max_size
    """
    allocator = CapitalAllocator(base_size=base_size, multiplier=multiplier, max_size=max_size)
    return allocator.calculate_position_size(win_streak, current_capital)


def calculate_position_size_from_bot_state(
    bot_state: BotState,
    win_streak: int,
    base_size: Decimal = Decimal("5.00"),
    multiplier: Decimal = Decimal("1.5"),
    max_size: Decimal = Decimal("25.00")
) -> Decimal:
    """
    Calculate position size using BotState for capital information.

    Args:
        bot_state: BotState object containing current capital
        win_streak: Current number of consecutive wins
        base_size: Base position size in USD (default: $5.00)
        multiplier: Multiplier per consecutive win (default: 1.5)
        max_size: Maximum position size cap in USD (default: $25.00)

    Returns:
        Position size in USD
    """
    # Extract current capital from bot state
    # Using current_exposure as a proxy for available capital
    current_capital = bot_state.max_total_exposure - bot_state.current_exposure

    return calculate_position_size(
        win_streak=win_streak,
        current_capital=current_capital,
        base_size=base_size,
        multiplier=multiplier,
        max_size=max_size
    )


if __name__ == "__main__":
    # Example usage
    allocator = CapitalAllocator()

    print("Win-Streak Capital Allocation")
    print("=" * 50)
    print(f"Base Size: ${allocator.base_size}")
    print(f"Multiplier: {allocator.multiplier}x")
    print(f"Max Size: ${allocator.max_size}")
    print("\nPosition Sizes by Win Streak:")
    print("-" * 50)

    for streak, size in allocator.get_position_sizes_for_streaks(6):
        print(f"Streak {streak}: ${size:.2f}")
