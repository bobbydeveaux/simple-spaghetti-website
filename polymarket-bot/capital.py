"""
Polymarket Bot Capital Allocation Module

This module implements position sizing logic with win-streak scaling.
The capital allocator determines position sizes based on the bot's current
win streak, starting with a base size and scaling up with consecutive wins,
while enforcing maximum position size limits.

Formula: position_size = min(base_size * (multiplier ^ win_streak), max_size)

Constants:
- BASE_SIZE: $5.00 (base position size with zero streak)
- MULTIPLIER: 1.5x (multiplier per consecutive win)
- MAX_SIZE: $25.00 (maximum position size cap)
"""

from typing import Protocol


# Position sizing constants
BASE_SIZE = 5.0
MULTIPLIER = 1.5
MAX_SIZE = 25.0


class BotStateProtocol(Protocol):
    """Protocol for BotState to support duck typing."""
    current_capital: float
    win_streak: int


def calculate_position_size(bot_state: BotStateProtocol) -> float:
    """
    Calculate position size based on win-streak scaling.

    Implements the formula: position_size = min(base_size * (multiplier ^ win_streak), max_size)
    with an additional safety check to ensure position doesn't exceed 50% of current capital.

    Args:
        bot_state: Bot state object containing current_capital and win_streak

    Returns:
        Position size in USD

    Examples:
        >>> class State:
        ...     def __init__(self, capital, streak):
        ...         self.current_capital = capital
        ...         self.win_streak = streak
        >>> calculate_position_size(State(100.0, 0))
        5.0
        >>> calculate_position_size(State(100.0, 1))
        7.5
        >>> calculate_position_size(State(100.0, 2))
        11.25
        >>> calculate_position_size(State(100.0, 5))
        25.0
    """
    # Calculate position size based on win streak
    position_size = BASE_SIZE * (MULTIPLIER ** bot_state.win_streak)

    # Apply maximum size cap
    position_size = min(position_size, MAX_SIZE)

    # Additional safety check: never exceed 50% of current capital
    max_allowed = bot_state.current_capital * 0.5
    position_size = min(position_size, max_allowed)

    return position_size


def update_win_streak(bot_state: BotStateProtocol, trade_outcome: str) -> int:
    """
    Update win streak based on trade outcome.

    Args:
        bot_state: Bot state object containing win_streak
        trade_outcome: Trade outcome ("WIN" or "LOSS")

    Returns:
        Updated win streak value

    Examples:
        >>> class State:
        ...     def __init__(self, streak):
        ...         self.win_streak = streak
        >>> state = State(3)
        >>> update_win_streak(state, "WIN")
        4
        >>> update_win_streak(state, "LOSS")
        0
    """
    if trade_outcome == "WIN":
        return bot_state.win_streak + 1
    else:
        return 0


def get_position_size_for_streak(win_streak: int, current_capital: float = float('inf')) -> float:
    """
    Get position size for a specific win streak without modifying bot state.

    Utility function for testing and analysis.

    Args:
        win_streak: Number of consecutive wins
        current_capital: Current capital (defaults to infinity for no capital constraint)

    Returns:
        Position size in USD

    Examples:
        >>> get_position_size_for_streak(0)
        5.0
        >>> get_position_size_for_streak(1)
        7.5
        >>> get_position_size_for_streak(2)
        11.25
        >>> get_position_size_for_streak(3)
        16.875
        >>> get_position_size_for_streak(4)
        25.0
        >>> get_position_size_for_streak(10)
        25.0
    """
    # Calculate position size based on win streak
    position_size = BASE_SIZE * (MULTIPLIER ** win_streak)

    # Apply maximum size cap
    position_size = min(position_size, MAX_SIZE)

    # Apply capital constraint
    max_allowed = current_capital * 0.5
    position_size = min(position_size, max_allowed)

    return position_size
