"""
Polymarket Bot Risk Management Module

This module implements pre-trade validation, drawdown monitoring, and volatility
circuit breaker functionality to enforce risk limits before executing trades.

Key Functions:
- check_drawdown: Validates current drawdown against threshold
- check_volatility: Validates price volatility against threshold
- approve_trade: Combines all risk checks for trade approval
"""

from typing import List, Optional, Tuple
from decimal import Decimal
import logging

from models import BotState, MarketData

logger = logging.getLogger(__name__)


class RiskController:
    """
    Risk controller for pre-trade validation and risk management.

    Implements:
    - Maximum drawdown monitoring (30% threshold)
    - Volatility circuit breaker (3% 5-minute range threshold)
    - Trade approval logic combining all risk checks
    """

    def __init__(
        self,
        max_drawdown_percent: float = 30.0,
        max_volatility_percent: float = 3.0,
        starting_capital: float = 100.0
    ):
        """
        Initialize the risk controller.

        Args:
            max_drawdown_percent: Maximum allowed drawdown percentage (default: 30%)
            max_volatility_percent: Maximum allowed volatility percentage (default: 3%)
            starting_capital: Starting capital in USD (default: 100.0)
        """
        self.max_drawdown_percent = max_drawdown_percent
        self.max_volatility_percent = max_volatility_percent
        self.starting_capital = starting_capital

    def check_drawdown(
        self,
        current_capital: float,
        starting_capital: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if current drawdown is within acceptable limits.

        Drawdown is calculated as: (starting_capital - current_capital) / starting_capital * 100

        Args:
            current_capital: Current capital in USD
            starting_capital: Starting capital in USD (uses instance default if not provided)

        Returns:
            Tuple of (passes_check: bool, rejection_reason: Optional[str])
            - passes_check: True if drawdown is within limits, False otherwise
            - rejection_reason: String explaining why check failed, None if passed
        """
        if starting_capital is None:
            starting_capital = self.starting_capital

        # Handle edge cases
        if starting_capital <= 0:
            logger.error(f"Invalid starting capital: {starting_capital}")
            return False, "Invalid starting capital (must be positive)"

        if current_capital < 0:
            logger.error(f"Invalid current capital: {current_capital}")
            return False, "Invalid current capital (cannot be negative)"

        # Calculate drawdown percentage
        drawdown_amount = starting_capital - current_capital
        drawdown_percent = (drawdown_amount / starting_capital) * 100

        # Check against threshold
        if drawdown_percent > self.max_drawdown_percent:
            reason = f"Drawdown {drawdown_percent:.2f}% exceeds maximum {self.max_drawdown_percent}%"
            logger.warning(reason)
            return False, reason

        logger.debug(f"Drawdown check passed: {drawdown_percent:.2f}% <= {self.max_drawdown_percent}%")
        return True, None

    def check_volatility(
        self,
        price_history: List[float],
        lookback_periods: int = 5
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if recent price volatility is within acceptable limits.

        Volatility is calculated as the price range over the lookback period:
        range = (max(prices) - min(prices)) / min(prices) * 100

        Args:
            price_history: List of recent prices (most recent last)
            lookback_periods: Number of recent periods to analyze (default: 5)

        Returns:
            Tuple of (passes_check: bool, rejection_reason: Optional[str])
            - passes_check: True if volatility is within limits, False otherwise
            - rejection_reason: String explaining why check failed, None if passed
        """
        # Validate input
        if not price_history:
            logger.error("Empty price history provided")
            return False, "Empty price history"

        if len(price_history) < lookback_periods:
            logger.warning(
                f"Insufficient price history: {len(price_history)} < {lookback_periods}"
            )
            return False, f"Insufficient price history (need {lookback_periods}, got {len(price_history)})"

        # Get the last N prices
        recent_prices = price_history[-lookback_periods:]

        # Check for invalid prices
        if any(p <= 0 for p in recent_prices):
            logger.error("Invalid prices in history (must be positive)")
            return False, "Invalid prices in history"

        # Calculate volatility
        max_price = max(recent_prices)
        min_price = min(recent_prices)
        price_range = max_price - min_price
        volatility_percent = (price_range / min_price) * 100

        # Check against threshold
        if volatility_percent > self.max_volatility_percent:
            reason = f"Volatility {volatility_percent:.2f}% exceeds maximum {self.max_volatility_percent}%"
            logger.warning(reason)
            return False, reason

        logger.debug(f"Volatility check passed: {volatility_percent:.2f}% <= {self.max_volatility_percent}%")
        return True, None

    def approve_trade(
        self,
        signal: str,
        current_capital: float,
        price_history: List[float],
        starting_capital: Optional[float] = None,
        bot_state: Optional[BotState] = None,
        market_data: Optional[MarketData] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Approve or reject a trade based on all risk checks.

        Combines drawdown and volatility checks to make final trade approval decision.
        A trade is approved only if ALL checks pass.

        Args:
            signal: Trading signal ("UP", "DOWN", or "SKIP")
            current_capital: Current capital in USD
            price_history: List of recent prices
            starting_capital: Starting capital in USD (optional)
            bot_state: Current bot state (optional, for future use)
            market_data: Current market data (optional, for future use)

        Returns:
            Tuple of (approved: bool, rejection_reason: Optional[str])
            - approved: True if trade is approved, False otherwise
            - rejection_reason: String explaining why trade was rejected, None if approved
        """
        # SKIP signals are always approved (they don't trigger trades)
        if signal == "SKIP":
            logger.debug("Trade approved: SKIP signal requires no validation")
            return True, None

        # Validate signal
        if signal not in ["UP", "DOWN", "SKIP"]:
            reason = f"Invalid signal: {signal}"
            logger.error(reason)
            return False, reason

        # Check drawdown
        drawdown_ok, drawdown_reason = self.check_drawdown(
            current_capital=current_capital,
            starting_capital=starting_capital
        )

        if not drawdown_ok:
            logger.warning(f"Trade rejected: {drawdown_reason}")
            return False, drawdown_reason

        # Check volatility
        volatility_ok, volatility_reason = self.check_volatility(
            price_history=price_history
        )

        if not volatility_ok:
            logger.warning(f"Trade rejected: {volatility_reason}")
            return False, volatility_reason

        # All checks passed
        logger.info(f"Trade approved: signal={signal}, capital={current_capital}")
        return True, None


# Convenience functions for backward compatibility
def check_drawdown(
    current_capital: float,
    starting_capital: float = 100.0,
    max_drawdown_percent: float = 30.0
) -> bool:
    """
    Check if current drawdown is within acceptable limits.

    Convenience function that wraps RiskController.check_drawdown().

    Args:
        current_capital: Current capital in USD
        starting_capital: Starting capital in USD (default: 100.0)
        max_drawdown_percent: Maximum allowed drawdown percentage (default: 30%)

    Returns:
        True if drawdown is within limits, False otherwise
    """
    controller = RiskController(
        max_drawdown_percent=max_drawdown_percent,
        starting_capital=starting_capital
    )
    passed, _ = controller.check_drawdown(current_capital)
    return passed


def check_volatility(
    price_history: List[float],
    max_volatility_percent: float = 3.0,
    lookback_periods: int = 5
) -> bool:
    """
    Check if recent price volatility is within acceptable limits.

    Convenience function that wraps RiskController.check_volatility().

    Args:
        price_history: List of recent prices (most recent last)
        max_volatility_percent: Maximum allowed volatility percentage (default: 3%)
        lookback_periods: Number of recent periods to analyze (default: 5)

    Returns:
        True if volatility is within limits, False otherwise
    """
    controller = RiskController(max_volatility_percent=max_volatility_percent)
    passed, _ = controller.check_volatility(price_history, lookback_periods)
    return passed


def approve_trade(
    signal: str,
    current_capital: float,
    price_history: List[float],
    starting_capital: float = 100.0,
    max_drawdown_percent: float = 30.0,
    max_volatility_percent: float = 3.0,
    bot_state: Optional[BotState] = None,
    market_data: Optional[MarketData] = None
) -> bool:
    """
    Approve or reject a trade based on all risk checks.

    Convenience function that wraps RiskController.approve_trade().

    Args:
        signal: Trading signal ("UP", "DOWN", or "SKIP")
        current_capital: Current capital in USD
        price_history: List of recent prices
        starting_capital: Starting capital in USD (default: 100.0)
        max_drawdown_percent: Maximum allowed drawdown percentage (default: 30%)
        max_volatility_percent: Maximum allowed volatility percentage (default: 3%)
        bot_state: Current bot state (optional, for future use)
        market_data: Current market data (optional, for future use)

    Returns:
        True if trade is approved, False otherwise
    """
    controller = RiskController(
        max_drawdown_percent=max_drawdown_percent,
        max_volatility_percent=max_volatility_percent,
        starting_capital=starting_capital
    )
    approved, _ = controller.approve_trade(
        signal=signal,
        current_capital=current_capital,
        price_history=price_history,
        starting_capital=starting_capital,
        bot_state=bot_state,
        market_data=market_data
    )
    return approved
