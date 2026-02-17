"""
Risk Management System for Polymarket Bot.

This module implements the complete risk management controller including:
- Max drawdown monitoring (30% threshold)
- Volatility circuit breaker (3% 5-minute range check)
- Pre-trade validation logic
- Risk assessment and approval/rejection with clear reasons

All risk checks integrate with BotState and MarketData models from models.py.
"""

from decimal import Decimal
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from .models import BotState, MarketData

# Configure logging
logger = logging.getLogger(__name__)

# Module-level constants for tests and external use
MAX_DRAWDOWN_PERCENT = Decimal("30.0")
MAX_VOLATILITY_PERCENT = Decimal("3.0")


class RiskViolation(Exception):
    """Exception raised when a risk threshold is violated."""

    def __init__(self, risk_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize a risk violation exception.

        Args:
            risk_type: Type of risk that was violated (e.g., 'DRAWDOWN', 'VOLATILITY')
            message: Human-readable error message
            details: Optional dictionary with additional violation details
        """
        self.risk_type = risk_type
        self.message = message
        self.details = details or {}
        super().__init__(f"{risk_type}: {message}")


class RiskApprovalResult:
    """Result of a pre-trade risk approval check."""

    def __init__(
        self,
        approved: bool,
        rejection_reasons: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a risk approval result.

        Args:
            approved: Whether the trade is approved
            rejection_reasons: List of reasons why trade was rejected (if not approved)
            warnings: List of non-blocking warnings
            details: Additional details about the risk assessment
        """
        self.approved = approved
        self.rejection_reasons = rejection_reasons or []
        self.warnings = warnings or []
        self.details = details or {}

    def __bool__(self) -> bool:
        """Allow result to be used as a boolean."""
        return self.approved

    def __str__(self) -> str:
        """String representation of the result."""
        if self.approved:
            status = "APPROVED"
            if self.warnings:
                status += f" (with {len(self.warnings)} warnings)"
        else:
            status = f"REJECTED ({len(self.rejection_reasons)} reasons)"
        return status

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "approved": self.approved,
            "rejection_reasons": self.rejection_reasons,
            "warnings": self.warnings,
            "details": self.details
        }


class RiskManager:
    """
    Risk management controller for the Polymarket Bot.

    Implements all risk control mechanisms including drawdown monitoring,
    volatility checks, and pre-trade validation.
    """

    # Risk thresholds
    MAX_DRAWDOWN_PERCENT = Decimal("30.0")  # 30% max drawdown from peak
    VOLATILITY_THRESHOLD_PERCENT = Decimal("3.0")  # 3% 5-minute range limit

    def __init__(
        self,
        max_drawdown_percent: Optional[Decimal] = None,
        volatility_threshold_percent: Optional[Decimal] = None,
        starting_capital: Decimal = Decimal("100.0")
    ):
        """
        Initialize the risk manager with configurable thresholds.

        Args:
            max_drawdown_percent: Maximum allowed drawdown percentage (default: 30%)
            volatility_threshold_percent: Maximum allowed 5-min volatility (default: 3%)
            starting_capital: Starting capital for drawdown calculations (default: $100)
        """
        self.max_drawdown_percent = max_drawdown_percent or self.MAX_DRAWDOWN_PERCENT
        self.volatility_threshold_percent = volatility_threshold_percent or self.VOLATILITY_THRESHOLD_PERCENT
        self.starting_capital = starting_capital
        self.peak_capital = starting_capital

        logger.info(
            f"RiskManager initialized: max_drawdown={self.max_drawdown_percent}%, "
            f"volatility_threshold={self.volatility_threshold_percent}%, "
            f"starting_capital=${self.starting_capital}"
        )

    def calculate_drawdown(
        self,
        current_capital: Decimal,
        peak_capital: Optional[Decimal] = None
    ) -> Decimal:
        """
        Calculate current drawdown percentage from peak equity.

        Drawdown is calculated as: ((peak - current) / peak) * 100

        Args:
            current_capital: Current capital/equity
            peak_capital: Peak capital (defaults to starting capital if not provided)

        Returns:
            Drawdown as a percentage (0-100)

        Examples:
            >>> rm = RiskManager(starting_capital=Decimal("100.0"))
            >>> rm.calculate_drawdown(Decimal("70.0"))
            Decimal('30.0')
            >>> rm.calculate_drawdown(Decimal("85.0"))
            Decimal('15.0')
        """
        if peak_capital is None:
            peak_capital = self.starting_capital

        # Update peak if current is higher
        if current_capital > peak_capital:
            peak_capital = current_capital
            self.peak_capital = peak_capital

        if peak_capital <= 0:
            logger.error(f"Invalid peak_capital: {peak_capital}")
            return Decimal("100.0")  # Total loss

        drawdown = ((peak_capital - current_capital) / peak_capital) * Decimal("100.0")

        # Ensure drawdown is non-negative
        drawdown = max(Decimal("0.0"), drawdown)

        return drawdown

    def check_drawdown(
        self,
        current_capital: Decimal,
        peak_capital: Optional[Decimal] = None
    ) -> Tuple[bool, Decimal]:
        """
        Check if drawdown is within acceptable limits.

        Args:
            current_capital: Current capital/equity
            peak_capital: Peak capital (defaults to starting capital if not provided)

        Returns:
            Tuple of (is_within_limit, current_drawdown_percent)

        Examples:
            >>> rm = RiskManager(starting_capital=Decimal("100.0"))
            >>> rm.check_drawdown(Decimal("75.0"))
            (True, Decimal('25.0'))
            >>> rm.check_drawdown(Decimal("69.0"))
            (False, Decimal('31.0'))
        """
        drawdown = self.calculate_drawdown(current_capital, peak_capital)
        is_within_limit = drawdown < self.max_drawdown_percent

        if not is_within_limit:
            logger.warning(
                f"Drawdown check FAILED: {drawdown:.2f}% exceeds limit of {self.max_drawdown_percent}% "
                f"(current: ${current_capital}, peak: ${peak_capital or self.starting_capital})"
            )
        else:
            logger.debug(
                f"Drawdown check passed: {drawdown:.2f}% within limit of {self.max_drawdown_percent}%"
            )

        return is_within_limit, drawdown

    def calculate_volatility(self, prices: List[Decimal]) -> Decimal:
        """
        Calculate volatility as the 5-minute price range percentage.

        Volatility is calculated as: ((max - min) / min) * 100

        Args:
            prices: List of prices over the 5-minute window

        Returns:
            Volatility as a percentage

        Raises:
            ValueError: If prices list is empty or contains invalid values

        Examples:
            >>> rm = RiskManager()
            >>> rm.calculate_volatility([Decimal("100"), Decimal("102"), Decimal("101")])
            Decimal('2.0')
            >>> rm.calculate_volatility([Decimal("100"), Decimal("104"), Decimal("98")])
            Decimal('6.122448979591836734693877551')
        """
        if not prices:
            raise ValueError("Price list cannot be empty")

        if len(prices) < 2:
            # Need at least 2 prices to calculate range
            return Decimal("0.0")

        max_price = max(prices)
        min_price = min(prices)

        if min_price <= 0:
            raise ValueError(f"Invalid minimum price: {min_price}")

        # Calculate percentage range
        price_range = max_price - min_price
        volatility = (price_range / min_price) * Decimal("100.0")

        return volatility

    def check_volatility(self, prices: List[Decimal]) -> Tuple[bool, Decimal]:
        """
        Check if 5-minute price volatility is within acceptable limits.

        Args:
            prices: List of prices over the 5-minute window

        Returns:
            Tuple of (is_within_limit, current_volatility_percent)

        Examples:
            >>> rm = RiskManager()
            >>> rm.check_volatility([Decimal("100"), Decimal("102")])
            (True, Decimal('2.0'))
            >>> rm.check_volatility([Decimal("100"), Decimal("105")])
            (False, Decimal('5.0'))
        """
        try:
            volatility = self.calculate_volatility(prices)
        except ValueError as e:
            logger.error(f"Volatility calculation failed: {e}")
            # On error, fail safe by rejecting the trade
            return False, Decimal("999.0")

        is_within_limit = volatility < self.volatility_threshold_percent

        if not is_within_limit:
            logger.warning(
                f"Volatility check FAILED: {volatility:.2f}% exceeds limit of {self.volatility_threshold_percent}% "
                f"(price range: ${min(prices):.2f} - ${max(prices):.2f})"
            )
        else:
            logger.debug(
                f"Volatility check passed: {volatility:.2f}% within limit of {self.volatility_threshold_percent}%"
            )

        return is_within_limit, volatility

    def approve_trade(
        self,
        bot_state: BotState,
        market_data: Optional[MarketData] = None,
        recent_prices: Optional[List[Decimal]] = None
    ) -> RiskApprovalResult:
        """
        Perform comprehensive pre-trade validation and return approval result.

        This function combines all risk checks (drawdown, volatility, etc.) and
        returns a detailed result with approval status and reasons for rejection.

        Args:
            bot_state: Current bot state containing capital and performance metrics
            market_data: Optional market data for additional validation
            recent_prices: Optional list of recent prices for volatility check

        Returns:
            RiskApprovalResult with approval status and detailed reasons

        Examples:
            >>> rm = RiskManager(starting_capital=Decimal("100.0"))
            >>> bot_state = BotState(
            ...     bot_id="test",
            ...     strategy_name="test",
            ...     max_position_size=Decimal("25.0"),
            ...     max_total_exposure=Decimal("100.0"),
            ...     risk_per_trade=Decimal("5.0"),
            ...     total_pnl=Decimal("-25.0")
            ... )
            >>> result = rm.approve_trade(bot_state)
            >>> result.approved
            True
        """
        rejection_reasons = []
        warnings = []
        details = {}

        # 1. Check drawdown
        current_capital = self.starting_capital + bot_state.total_pnl
        drawdown_ok, drawdown_percent = self.check_drawdown(current_capital, self.peak_capital)

        details['current_capital'] = float(current_capital)
        details['peak_capital'] = float(self.peak_capital)
        details['drawdown_percent'] = float(drawdown_percent)
        details['drawdown_limit'] = float(self.max_drawdown_percent)

        if not drawdown_ok:
            rejection_reasons.append(
                f"Drawdown of {drawdown_percent:.2f}% exceeds maximum allowed {self.max_drawdown_percent}%"
            )
        elif drawdown_percent >= self.max_drawdown_percent * Decimal("0.8"):
            # Warn if approaching limit (80% of max)
            warnings.append(
                f"Drawdown of {drawdown_percent:.2f}% is approaching limit of {self.max_drawdown_percent}%"
            )

        # 2. Check volatility (if recent prices provided)
        if recent_prices:
            volatility_ok, volatility_percent = self.check_volatility(recent_prices)

            details['volatility_percent'] = float(volatility_percent)
            details['volatility_limit'] = float(self.volatility_threshold_percent)
            details['price_count'] = len(recent_prices)

            if not volatility_ok:
                rejection_reasons.append(
                    f"Volatility of {volatility_percent:.2f}% exceeds maximum allowed {self.volatility_threshold_percent}%"
                )
            elif volatility_percent >= self.volatility_threshold_percent * Decimal("0.8"):
                # Warn if approaching limit (80% of max)
                warnings.append(
                    f"Volatility of {volatility_percent:.2f}% is approaching limit of {self.volatility_threshold_percent}%"
                )

        # 3. Check if bot has sufficient capital for minimum trade
        min_trade_size = Decimal("5.0")  # From LLD - base position size
        if current_capital < min_trade_size:
            rejection_reasons.append(
                f"Insufficient capital ${current_capital:.2f} for minimum trade size ${min_trade_size}"
            )

        # 4. Check exposure limits
        if bot_state.current_exposure >= bot_state.max_total_exposure:
            rejection_reasons.append(
                f"Current exposure ${bot_state.current_exposure} exceeds maximum ${bot_state.max_total_exposure}"
            )

        # 5. Check if bot is in operational status
        if bot_state.status.value not in ['running', 'initializing']:
            rejection_reasons.append(
                f"Bot status '{bot_state.status.value}' does not allow trading"
            )

        # Determine approval
        approved = len(rejection_reasons) == 0

        result = RiskApprovalResult(
            approved=approved,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            details=details
        )

        # Log result
        if approved:
            logger.info(f"Trade APPROVED: {result}")
            if warnings:
                for warning in warnings:
                    logger.warning(warning)
        else:
            logger.warning(f"Trade REJECTED: {result}")
            for reason in rejection_reasons:
                logger.warning(f"  - {reason}")

        return result

    def update_peak_capital(self, current_capital: Decimal) -> None:
        """
        Update the peak capital if current capital exceeds it.

        Args:
            current_capital: Current capital to compare against peak
        """
        if current_capital > self.peak_capital:
            logger.info(f"New peak capital: ${current_capital} (previous: ${self.peak_capital})")
            self.peak_capital = current_capital

    def reset(self, new_starting_capital: Optional[Decimal] = None) -> None:
        """
        Reset the risk manager to initial state.

        Args:
            new_starting_capital: Optional new starting capital (keeps current if None)
        """
        if new_starting_capital is not None:
            self.starting_capital = new_starting_capital

        self.peak_capital = self.starting_capital
        logger.info(f"RiskManager reset with starting capital: ${self.starting_capital}")

    def get_risk_metrics(self, bot_state: BotState) -> Dict[str, Any]:
        """
        Get current risk metrics for monitoring and reporting.

        Args:
            bot_state: Current bot state

        Returns:
            Dictionary containing current risk metrics
        """
        current_capital = self.starting_capital + bot_state.total_pnl
        drawdown_percent = self.calculate_drawdown(current_capital, self.peak_capital)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "starting_capital": float(self.starting_capital),
            "peak_capital": float(self.peak_capital),
            "current_capital": float(current_capital),
            "drawdown_percent": float(drawdown_percent),
            "drawdown_limit": float(self.max_drawdown_percent),
            "drawdown_remaining": float(self.max_drawdown_percent - drawdown_percent),
            "volatility_limit": float(self.volatility_threshold_percent),
            "current_exposure": float(bot_state.current_exposure),
            "max_exposure": float(bot_state.max_total_exposure),
            "total_trades": bot_state.total_trades,
            "winning_trades": bot_state.winning_trades,
            "win_rate": bot_state.get_win_rate()
        }


# Convenience functions for backward compatibility and simpler usage

def check_drawdown(
    current_capital: Decimal,
    starting_capital: Decimal = Decimal("100.0"),
    max_drawdown_percent: Decimal = Decimal("30.0")
) -> bool:
    """
    Standalone function to check if drawdown is within limits.

    Args:
        current_capital: Current capital/equity
        starting_capital: Starting capital (default: $100)
        max_drawdown_percent: Maximum allowed drawdown (default: 30%)

    Returns:
        True if drawdown is within limit, False otherwise
    """
    rm = RiskManager(
        max_drawdown_percent=max_drawdown_percent,
        starting_capital=starting_capital
    )
    is_ok, _ = rm.check_drawdown(current_capital)
    return is_ok


def check_volatility(
    price_history: List[Decimal],
    volatility_threshold_percent: Decimal = Decimal("3.0")
) -> bool:
    """
    Standalone function to check if volatility is within limits.

    Args:
        price_history: List of recent prices for 5-minute window
        volatility_threshold_percent: Maximum allowed volatility (default: 3%)

    Returns:
        True if volatility is within limit, False otherwise
    """
    rm = RiskManager(volatility_threshold_percent=volatility_threshold_percent)
    is_ok, _ = rm.check_volatility(price_history)
    return is_ok


def approve_trade(
    signal: str,
    market_data: MarketData,
    bot_state: BotState,
    recent_prices: Optional[List[Decimal]] = None
) -> bool:
    """
    Standalone function for pre-trade approval (backward compatible interface).

    Args:
        signal: Trading signal (UP/DOWN/SKIP) - not currently used but kept for compatibility
        market_data: Market data for validation
        bot_state: Current bot state
        recent_prices: Optional recent prices for volatility check

    Returns:
        True if trade is approved, False otherwise
    """
    rm = RiskManager()
    result = rm.approve_trade(bot_state, market_data, recent_prices)
    return result.approved


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
    # Risk thresholds (module level constants)
    MAX_DRAWDOWN_PERCENT = Decimal("30.0")
    MAX_VOLATILITY_PERCENT = Decimal("3.0")

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
