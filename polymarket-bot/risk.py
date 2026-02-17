"""
Polymarket Bot Risk Management Module

This module implements pre-trade validation with risk controls including:
- Max drawdown monitoring (30% threshold)
- Volatility circuit breaker (3% 5-minute price range check)
- Trade approval logic with clear pass/fail decisions

All risk checks integrate with BotState for historical context and
provide detailed rejection reasons when trades are blocked.
"""

from typing import List, Tuple, Optional
from decimal import Decimal
import logging

from .models import BotState, MarketData

# Configure module logger
logger = logging.getLogger(__name__)

# Risk thresholds
MAX_DRAWDOWN_PERCENT = Decimal("30.0")  # Maximum allowed drawdown percentage
MAX_VOLATILITY_PERCENT = Decimal("3.0")  # Maximum 5-minute price range percentage


def check_drawdown(
    current_capital: Decimal,
    starting_capital: Decimal = Decimal("100.0")
) -> Tuple[bool, Optional[str]]:
    """
    Check if current drawdown is within acceptable limits.

    Calculates drawdown as percentage loss from starting capital and
    validates it against the maximum allowable threshold.

    Args:
        current_capital: Current account capital in USD
        starting_capital: Initial account capital in USD (default: 100.0)

    Returns:
        Tuple of (approved: bool, rejection_reason: Optional[str])
        - (True, None) if drawdown is within limits
        - (False, reason) if drawdown exceeds threshold

    Examples:
        >>> check_drawdown(Decimal("75.0"), Decimal("100.0"))
        (True, None)

        >>> check_drawdown(Decimal("69.0"), Decimal("100.0"))
        (False, "Drawdown of 31.00% exceeds maximum threshold of 30.00%")
    """
    if starting_capital <= 0:
        error_msg = f"Invalid starting capital: {starting_capital}. Must be greater than 0."
        logger.error(error_msg)
        return False, error_msg

    if current_capital < 0:
        error_msg = f"Invalid current capital: {current_capital}. Must be non-negative."
        logger.error(error_msg)
        return False, error_msg

    # Calculate drawdown percentage
    drawdown_amount = starting_capital - current_capital
    drawdown_percent = (drawdown_amount / starting_capital) * Decimal("100.0")

    if drawdown_percent > MAX_DRAWDOWN_PERCENT:
        rejection_reason = (
            f"Drawdown of {drawdown_percent:.2f}% exceeds maximum threshold "
            f"of {MAX_DRAWDOWN_PERCENT}%"
        )
        logger.warning(
            f"Trade blocked: {rejection_reason} "
            f"(Current: ${current_capital}, Starting: ${starting_capital})"
        )
        return False, rejection_reason

    logger.debug(
        f"Drawdown check passed: {drawdown_percent:.2f}% "
        f"(Current: ${current_capital}, Starting: ${starting_capital})"
    )
    return True, None


def check_volatility(price_history: List[Decimal]) -> Tuple[bool, Optional[str]]:
    """
    Check if recent price volatility is within acceptable limits.

    Calculates the price range over the last 5 data points (representing
    5 minutes of price history) and validates it doesn't exceed the
    maximum volatility threshold.

    Args:
        price_history: List of recent prices (most recent last)

    Returns:
        Tuple of (approved: bool, rejection_reason: Optional[str])
        - (True, None) if volatility is within limits
        - (False, reason) if volatility exceeds threshold

    Examples:
        >>> prices = [Decimal("100"), Decimal("101"), Decimal("102")]
        >>> check_volatility(prices)
        (True, None)

        >>> prices = [Decimal("100"), Decimal("95"), Decimal("104")]
        >>> check_volatility(prices)
        (False, "Volatility of 9.00% exceeds maximum threshold of 3.00%")
    """
    if not price_history:
        error_msg = "Price history is empty. Cannot calculate volatility."
        logger.error(error_msg)
        return False, error_msg

    # Validate all prices are positive
    if any(price <= 0 for price in price_history):
        error_msg = "Price history contains non-positive values."
        logger.error(error_msg)
        return False, error_msg

    # Use last 5 prices for 5-minute volatility window
    # If less than 5 prices available, use all available
    recent_prices = price_history[-5:] if len(price_history) >= 5 else price_history

    if len(recent_prices) < 2:
        # Not enough data to calculate range, approve by default
        logger.debug("Insufficient price history for volatility check. Approving by default.")
        return True, None

    # Calculate price range as percentage of minimum price
    max_price = max(recent_prices)
    min_price = min(recent_prices)
    price_range = max_price - min_price
    volatility_percent = (price_range / min_price) * Decimal("100.0")

    if volatility_percent > MAX_VOLATILITY_PERCENT:
        rejection_reason = (
            f"Volatility of {volatility_percent:.2f}% exceeds maximum threshold "
            f"of {MAX_VOLATILITY_PERCENT}%"
        )
        logger.warning(
            f"Trade blocked: {rejection_reason} "
            f"(Price range: ${min_price} - ${max_price})"
        )
        return False, rejection_reason

    logger.debug(
        f"Volatility check passed: {volatility_percent:.2f}% "
        f"(Price range: ${min_price} - ${max_price})"
    )
    return True, None


def approve_trade(
    signal: str,
    market_data: MarketData,
    bot_state: BotState,
    price_history: Optional[List[Decimal]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Approve or reject a trade based on all risk management checks.

    Combines drawdown and volatility checks to make final trade approval
    decision. Returns clear pass/fail with detailed rejection reasons.

    Args:
        signal: Trading signal ("UP", "DOWN", or "SKIP")
        market_data: Current market data including prices
        bot_state: Current bot state with capital and performance metrics
        price_history: Optional list of recent BTC prices for volatility check

    Returns:
        Tuple of (approved: bool, rejection_reason: Optional[str])
        - (True, None) if all checks pass
        - (False, reason) if any check fails

    Examples:
        >>> approve_trade("UP", market_data, bot_state, prices)
        (True, None)

        >>> approve_trade("DOWN", market_data, bot_state_high_drawdown, prices)
        (False, "Drawdown of 32.00% exceeds maximum threshold of 30.00%")
    """
    # Skip signal doesn't require validation
    if signal == "SKIP":
        logger.debug("Signal is SKIP. No trade to approve.")
        return True, None

    # Validate signal is valid
    if signal not in ["UP", "DOWN"]:
        error_msg = f"Invalid signal: {signal}. Must be 'UP', 'DOWN', or 'SKIP'."
        logger.error(error_msg)
        return False, error_msg

    # Check 1: Drawdown validation
    # Extract capital information from bot_state
    # The BotState model has total_pnl and max_total_exposure fields
    # We need to calculate current capital and starting capital
    # Assuming starting capital is a fixed value (e.g., from config or state initialization)
    # For now, we'll use a placeholder approach based on the bot state structure

    # Calculate current capital from bot state
    # current_capital = starting_capital + total_pnl
    # Since we don't have explicit starting_capital in BotState, we'll use max_total_exposure
    # as a proxy for available capital

    current_capital = bot_state.max_total_exposure + bot_state.total_pnl

    # Use max_total_exposure as the starting capital reference
    # In a real implementation, this should be stored in bot_state
    starting_capital = bot_state.max_total_exposure

    drawdown_approved, drawdown_reason = check_drawdown(
        current_capital=current_capital,
        starting_capital=starting_capital
    )

    if not drawdown_approved:
        return False, drawdown_reason

    # Check 2: Volatility validation
    if price_history is not None and len(price_history) > 0:
        volatility_approved, volatility_reason = check_volatility(price_history)

        if not volatility_approved:
            return False, volatility_reason
    else:
        logger.debug("No price history provided. Skipping volatility check.")

    # Check 3: Ensure market is active
    if not market_data.is_active:
        rejection_reason = f"Market {market_data.market_id} is not active for trading."
        logger.warning(f"Trade blocked: {rejection_reason}")
        return False, rejection_reason

    # Check 4: Ensure market is not closed
    if market_data.is_closed:
        rejection_reason = f"Market {market_data.market_id} is closed."
        logger.warning(f"Trade blocked: {rejection_reason}")
        return False, rejection_reason

    # Check 5: Validate market has sufficient liquidity
    if market_data.total_liquidity <= 0:
        rejection_reason = f"Market {market_data.market_id} has insufficient liquidity."
        logger.warning(f"Trade blocked: {rejection_reason}")
        return False, rejection_reason

    # Check 6: Ensure bot is not at max exposure
    if bot_state.current_exposure >= bot_state.max_total_exposure:
        rejection_reason = (
            f"Current exposure ${bot_state.current_exposure} "
            f"meets or exceeds maximum ${bot_state.max_total_exposure}"
        )
        logger.warning(f"Trade blocked: {rejection_reason}")
        return False, rejection_reason

    # All checks passed
    logger.info(
        f"Trade approved: Signal={signal}, Market={market_data.market_id}, "
        f"Capital=${current_capital}, Exposure=${bot_state.current_exposure}"
    )
    return True, None


def calculate_max_trade_size(
    bot_state: BotState,
    market_data: MarketData
) -> Decimal:
    """
    Calculate the maximum allowable trade size based on risk parameters.

    Determines the maximum position size that can be taken while staying
    within risk limits including max position size, available capital,
    and remaining exposure capacity.

    Args:
        bot_state: Current bot state with risk parameters
        market_data: Current market data

    Returns:
        Maximum trade size in USD

    Examples:
        >>> calculate_max_trade_size(bot_state, market_data)
        Decimal('1000.00')
    """
    # Calculate remaining exposure capacity
    remaining_exposure = bot_state.max_total_exposure - bot_state.current_exposure

    # Maximum trade size is the minimum of:
    # 1. Max position size from config
    # 2. Remaining exposure capacity
    # 3. Risk per trade limit
    max_trade_size = min(
        bot_state.max_position_size,
        remaining_exposure,
        bot_state.risk_per_trade
    )

    # Ensure non-negative
    max_trade_size = max(max_trade_size, Decimal("0.00"))

    logger.debug(
        f"Calculated max trade size: ${max_trade_size} "
        f"(Position limit: ${bot_state.max_position_size}, "
        f"Remaining exposure: ${remaining_exposure}, "
        f"Risk per trade: ${bot_state.risk_per_trade})"
    )

    return max_trade_size


def get_risk_metrics(
    bot_state: BotState,
    price_history: Optional[List[Decimal]] = None
) -> dict:
    """
    Get current risk metrics for monitoring and reporting.

    Calculates and returns key risk metrics including drawdown,
    volatility, exposure utilization, and win rate.

    Args:
        bot_state: Current bot state
        price_history: Optional price history for volatility calculation

    Returns:
        Dictionary containing risk metrics

    Examples:
        >>> metrics = get_risk_metrics(bot_state, prices)
        >>> metrics['drawdown_percent']
        15.5
    """
    # Calculate current capital
    current_capital = bot_state.max_total_exposure + bot_state.total_pnl
    starting_capital = bot_state.max_total_exposure

    # Calculate drawdown
    if starting_capital > 0:
        drawdown_amount = starting_capital - current_capital
        drawdown_percent = float((drawdown_amount / starting_capital) * Decimal("100.0"))
    else:
        drawdown_percent = 0.0

    # Calculate volatility if price history provided
    volatility_percent = None
    if price_history and len(price_history) >= 2:
        recent_prices = price_history[-5:] if len(price_history) >= 5 else price_history
        max_price = max(recent_prices)
        min_price = min(recent_prices)
        price_range = max_price - min_price
        volatility_percent = float((price_range / min_price) * Decimal("100.0"))

    # Calculate exposure utilization
    if bot_state.max_total_exposure > 0:
        exposure_utilization = float(
            (bot_state.current_exposure / bot_state.max_total_exposure) * Decimal("100.0")
        )
    else:
        exposure_utilization = 0.0

    # Get win rate
    win_rate = bot_state.get_win_rate()

    metrics = {
        "current_capital": float(current_capital),
        "starting_capital": float(starting_capital),
        "drawdown_percent": drawdown_percent,
        "drawdown_threshold_percent": float(MAX_DRAWDOWN_PERCENT),
        "volatility_percent": volatility_percent,
        "volatility_threshold_percent": float(MAX_VOLATILITY_PERCENT),
        "current_exposure": float(bot_state.current_exposure),
        "max_exposure": float(bot_state.max_total_exposure),
        "exposure_utilization_percent": exposure_utilization,
        "total_trades": bot_state.total_trades,
        "winning_trades": bot_state.winning_trades,
        "win_rate_percent": win_rate,
        "total_pnl": float(bot_state.total_pnl)
    }

    return metrics
