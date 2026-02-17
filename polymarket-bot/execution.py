"""
Trade Execution Module for Polymarket Bot.

This module handles order submission to the Polymarket API and settlement polling.
It includes:
- Order submission with retry logic
- Settlement status polling
- Outcome tracking (WIN/LOSS determination)
- Trade record updates
"""

import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from polymarket_bot.utils import (
    retry_with_backoff,
    validate_non_empty,
    validate_type,
    RetryError
)
from polymarket_bot.models import (
    Trade,
    TradeStatus,
    OrderSide,
    OrderType,
    OutcomeType,
    Position,
    PositionStatus
)

# Configure logger
logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """Order status enumeration for Polymarket orders."""
    PENDING = "pending"
    OPEN = "open"
    MATCHED = "matched"
    SETTLED = "settled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SettlementOutcome(str, Enum):
    """Settlement outcome enumeration."""
    WIN = "WIN"
    LOSS = "LOSS"
    PUSH = "PUSH"  # Tie or market cancelled
    UNKNOWN = "UNKNOWN"


class ExecutionError(Exception):
    """Exception raised when order execution fails."""
    pass


class SettlementError(Exception):
    """Exception raised when settlement polling fails."""
    pass


class PolymarketAPIClient:
    """
    Client for interacting with the Polymarket API.

    This is a mock implementation for development purposes.
    In production, this would make actual HTTP requests to the Polymarket API.
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str):
        """
        Initialize the Polymarket API client.

        Args:
            api_key: Polymarket API key
            api_secret: Polymarket API secret
            base_url: Base URL for Polymarket API
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

        # Mock order storage for testing
        self._mock_orders: Dict[str, Dict[str, Any]] = {}
        # Mock settlement outcomes for testing (order_id -> SettlementOutcome)
        self._mock_settlement_outcomes: Dict[str, SettlementOutcome] = {}

    def submit_order(
        self,
        market_id: str,
        side: str,
        outcome: str,
        amount: Decimal,
        order_type: str = "MARKET",
        price: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Submit an order to the Polymarket API.

        Args:
            market_id: The market ID to trade on
            side: "BUY" or "SELL"
            outcome: "YES" or "NO"
            amount: Order amount in USD
            order_type: "MARKET" or "LIMIT"
            price: Limit price (required for LIMIT orders)

        Returns:
            Dictionary containing order details including order_id

        Raises:
            ExecutionError: If order submission fails
        """
        # Validate inputs
        validate_non_empty(market_id, "market_id")
        validate_non_empty(side, "side")
        validate_non_empty(outcome, "outcome")

        if side not in ["BUY", "SELL"]:
            raise ExecutionError(f"Invalid side: {side}. Must be BUY or SELL")

        if outcome not in ["YES", "NO"]:
            raise ExecutionError(f"Invalid outcome: {outcome}. Must be YES or NO")

        if order_type not in ["MARKET", "LIMIT"]:
            raise ExecutionError(f"Invalid order_type: {order_type}. Must be MARKET or LIMIT")

        if order_type == "LIMIT" and price is None:
            raise ExecutionError("Price is required for LIMIT orders")

        if amount <= 0:
            raise ExecutionError(f"Amount must be positive, got {amount}")

        # Mock implementation - in production, this would make an HTTP POST request
        order_id = f"order_{market_id}_{int(time.time() * 1000)}"

        order_data = {
            "order_id": order_id,
            "market_id": market_id,
            "side": side,
            "outcome": outcome,
            "amount": float(amount),
            "order_type": order_type,
            "price": float(price) if price else None,
            "status": OrderStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "filled_amount": 0.0
        }

        # Store in mock storage
        self._mock_orders[order_id] = order_data

        logger.info(
            f"Order submitted successfully: {order_id} - "
            f"{side} {outcome} on market {market_id}, amount: {amount}"
        )

        return order_data

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get the current status of an order.

        Args:
            order_id: The order ID to check

        Returns:
            Dictionary containing order status and details

        Raises:
            ExecutionError: If order is not found or API call fails
        """
        validate_non_empty(order_id, "order_id")

        # Mock implementation - in production, this would make an HTTP GET request
        if order_id not in self._mock_orders:
            raise ExecutionError(f"Order not found: {order_id}")

        # Get the stored order but don't mutate it
        stored_order = self._mock_orders[order_id]

        # Create a copy to return with calculated current state
        order = stored_order.copy()

        # Simulate order progression: PENDING -> OPEN -> MATCHED -> SETTLED
        # In real implementation, this would come from the API
        current_status = stored_order.get("status", OrderStatus.PENDING.value)

        # For testing purposes, advance status based on time
        created_at = datetime.fromisoformat(stored_order["created_at"].replace('Z', '+00:00'))
        elapsed_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()

        # Calculate current state without mutating stored order
        if elapsed_seconds > 60 and current_status == OrderStatus.PENDING.value:
            order["status"] = OrderStatus.SETTLED.value
            order["filled_amount"] = order["amount"]
            # Use configurable settlement outcome if set, otherwise default to WIN
            settlement_outcome = self._mock_settlement_outcomes.get(
                order_id,
                SettlementOutcome.WIN  # Default for backward compatibility
            )
            order["settlement_outcome"] = settlement_outcome.value
            order["settled_at"] = datetime.now(timezone.utc).isoformat()
        elif elapsed_seconds > 30 and current_status == OrderStatus.PENDING.value:
            order["status"] = OrderStatus.MATCHED.value
            order["filled_amount"] = order["amount"]
        elif elapsed_seconds > 10 and current_status == OrderStatus.PENDING.value:
            order["status"] = OrderStatus.OPEN.value

        return order

    def get_market_resolution(self, market_id: str) -> Optional[str]:
        """
        Get the resolution outcome for a market.

        Args:
            market_id: The market ID to check

        Returns:
            "YES", "NO", or None if not yet resolved
        """
        # Mock implementation - in production, this would make an HTTP GET request
        # For now, return None (unresolved) to simulate pending resolution
        return None

    def set_mock_settlement_outcome(self, order_id: str, outcome: SettlementOutcome) -> None:
        """
        Set the mock settlement outcome for an order (for testing purposes).

        Args:
            order_id: The order ID to set outcome for
            outcome: The settlement outcome to use

        Note:
            This method is only available in the mock implementation and is used
            for testing different settlement scenarios.
        """
        self._mock_settlement_outcomes[order_id] = outcome
        logger.debug(f"Mock settlement outcome set for {order_id}: {outcome.value}")


def submit_order(
    client: PolymarketAPIClient,
    market_id: str,
    direction: str,
    size: Decimal,
    price: Optional[Decimal] = None,
    order_type: str = "MARKET"
) -> Tuple[str, Trade]:
    """
    Submit an order to Polymarket with retry logic.

    This function wraps the API client's submit_order method and creates
    a Trade object to track the order.

    Args:
        client: PolymarketAPIClient instance
        market_id: Market ID to trade on
        direction: "UP" or "DOWN" (converted to YES/NO)
        size: Order size in USD
        price: Optional limit price for LIMIT orders
        order_type: "MARKET" or "LIMIT" (default: MARKET)

    Returns:
        Tuple of (order_id, Trade object)

    Raises:
        ExecutionError: If order submission fails after retries

    Example:
        order_id, trade = submit_order(
            client=api_client,
            market_id="market_123",
            direction="UP",
            size=Decimal("10.00")
        )
    """
    validate_non_empty(market_id, "market_id")
    validate_non_empty(direction, "direction")

    if direction not in ["UP", "DOWN"]:
        raise ExecutionError(f"Invalid direction: {direction}. Must be UP or DOWN")

    # Convert direction to outcome
    outcome = "YES" if direction == "UP" else "NO"
    side = "BUY"  # Always buying the outcome

    # Submit order with retry logic
    @retry_with_backoff(
        max_attempts=3,
        base_delay=2.0,
        exponential_base=2.0,
        exceptions=(Exception,)
    )
    def _submit_with_retry():
        return client.submit_order(
            market_id=market_id,
            side=side,
            outcome=outcome,
            amount=size,
            order_type=order_type,
            price=price
        )

    try:
        order_response = _submit_with_retry()
    except RetryError as e:
        raise ExecutionError(f"Failed to submit order after retries: {str(e)}") from e

    # Create Trade object
    trade = Trade(
        trade_id=f"trade_{order_response['order_id']}",
        market_id=market_id,
        order_id=order_response["order_id"],
        side=OrderSide.BUY,
        order_type=OrderType.MARKET if order_type == "MARKET" else OrderType.LIMIT,
        outcome=OutcomeType.YES if outcome == "YES" else OutcomeType.NO,
        price=Decimal(str(price)) if price else Decimal("0.5"),  # Default mock price
        quantity=size,
        filled_quantity=Decimal("0.00"),
        status=TradeStatus.PENDING
    )

    logger.info(
        f"Order submitted: {order_response['order_id']} - "
        f"{direction} ({outcome}) on {market_id}, size: {size}"
    )

    return order_response["order_id"], trade


def poll_settlement(
    client: PolymarketAPIClient,
    order_id: str,
    timeout: int = 300,
    poll_interval: int = 10
) -> SettlementOutcome:
    """
    Poll for order settlement and determine outcome.

    This function polls the Polymarket API until the order is settled
    or the timeout is reached. It respects API rate limits by using
    configurable polling intervals.

    Args:
        client: PolymarketAPIClient instance
        order_id: Order ID to poll
        timeout: Maximum time to poll in seconds (default: 300)
        poll_interval: Seconds between poll attempts (default: 10)

    Returns:
        SettlementOutcome (WIN, LOSS, PUSH, or UNKNOWN)

    Raises:
        SettlementError: If polling fails or times out

    Example:
        outcome = poll_settlement(
            client=api_client,
            order_id="order_123",
            timeout=300
        )
        if outcome == SettlementOutcome.WIN:
            print("Trade won!")
    """
    validate_non_empty(order_id, "order_id")

    if timeout <= 0:
        raise SettlementError("Timeout must be positive")

    if poll_interval <= 0:
        raise SettlementError("Poll interval must be positive")

    start_time = time.time()
    attempts = 0

    logger.info(
        f"Starting settlement polling for order {order_id} "
        f"(timeout: {timeout}s, interval: {poll_interval}s)"
    )

    while True:
        attempts += 1
        elapsed = time.time() - start_time

        if elapsed > timeout:
            raise SettlementError(
                f"Settlement polling timed out after {timeout}s "
                f"({attempts} attempts) for order {order_id}"
            )

        try:
            # Get order status with retry
            @retry_with_backoff(
                max_attempts=3,
                base_delay=1.0,
                exceptions=(Exception,)
            )
            def _get_status():
                return client.get_order_status(order_id)

            order_status = _get_status()

            current_status = order_status.get("status")
            logger.debug(
                f"Poll attempt {attempts} for {order_id}: "
                f"status={current_status}, elapsed={elapsed:.1f}s"
            )

            # Check if order is settled
            if current_status == OrderStatus.SETTLED.value:
                outcome = _determine_outcome(order_status)
                logger.info(
                    f"Order {order_id} settled after {elapsed:.1f}s "
                    f"({attempts} attempts): {outcome.value}"
                )
                return outcome

            # Check if order failed or was cancelled
            elif current_status in [OrderStatus.FAILED.value, OrderStatus.CANCELLED.value]:
                raise SettlementError(
                    f"Order {order_id} ended with status: {current_status}"
                )

        except RetryError as e:
            logger.warning(
                f"Failed to get order status for {order_id} "
                f"on attempt {attempts}: {str(e)}"
            )
            # Continue polling even if one attempt fails

        # Wait before next poll
        remaining_time = timeout - (time.time() - start_time)
        sleep_time = min(poll_interval, remaining_time)

        if sleep_time > 0:
            time.sleep(sleep_time)


def _determine_outcome(order_data: Dict[str, Any]) -> SettlementOutcome:
    """
    Determine the WIN/LOSS outcome from settled order data.

    Args:
        order_data: Order data from API including settlement info

    Returns:
        SettlementOutcome based on market resolution
    """
    # Check if settlement outcome is directly provided
    if "settlement_outcome" in order_data:
        outcome_str = order_data["settlement_outcome"].upper()
        if outcome_str in [e.value for e in SettlementOutcome]:
            return SettlementOutcome(outcome_str)

    # Determine outcome based on market resolution and position
    market_resolution = order_data.get("market_resolution")
    traded_outcome = order_data.get("outcome")

    if not market_resolution or not traded_outcome:
        logger.warning(
            f"Missing resolution data for order {order_data.get('order_id')}: "
            f"market_resolution={market_resolution}, traded_outcome={traded_outcome}"
        )
        return SettlementOutcome.UNKNOWN

    # If market resolved to the outcome we bet on, it's a WIN
    if market_resolution.upper() == traded_outcome.upper():
        return SettlementOutcome.WIN
    else:
        return SettlementOutcome.LOSS


def update_trade_with_settlement(
    trade: Trade,
    outcome: SettlementOutcome,
    realized_pnl: Optional[Decimal] = None
) -> Trade:
    """
    Update a Trade object with settlement outcome.

    This function creates a copy of the Trade object with updated settlement
    information, preserving immutability and avoiding side effects.

    Args:
        trade: Trade object to update
        outcome: Settlement outcome (WIN/LOSS/PUSH/UNKNOWN)
        realized_pnl: Optional realized profit/loss

    Returns:
        New Trade object with settlement updates applied

    Example:
        updated_trade = update_trade_with_settlement(
            trade=my_trade,
            outcome=SettlementOutcome.WIN,
            realized_pnl=Decimal("5.00")
        )
    """
    # Create a copy to avoid mutating the input object
    updated_metadata = trade.metadata.copy()
    updated_metadata["settlement_outcome"] = outcome.value
    if realized_pnl is not None:
        updated_metadata["realized_pnl"] = float(realized_pnl)

    # Determine new status based on outcome
    if outcome == SettlementOutcome.WIN:
        new_status = TradeStatus.EXECUTED
        new_filled_quantity = trade.quantity
        new_executed_at = datetime.now(timezone.utc)
    elif outcome == SettlementOutcome.LOSS:
        new_status = TradeStatus.EXECUTED
        new_filled_quantity = trade.quantity
        new_executed_at = datetime.now(timezone.utc)
    elif outcome == SettlementOutcome.PUSH:
        new_status = TradeStatus.CANCELLED
        new_filled_quantity = trade.filled_quantity
        new_executed_at = trade.executed_at
    else:
        new_status = TradeStatus.FAILED
        new_filled_quantity = trade.filled_quantity
        new_executed_at = trade.executed_at

    # Create new Trade object with updated values
    updated_trade = trade.model_copy(update={
        "status": new_status,
        "filled_quantity": new_filled_quantity,
        "executed_at": new_executed_at,
        "metadata": updated_metadata
    })

    logger.info(
        f"Trade {updated_trade.trade_id} updated with settlement: "
        f"outcome={outcome.value}, status={updated_trade.status.value}"
    )

    return updated_trade


def update_position_with_settlement(
    position: Position,
    outcome: SettlementOutcome,
    exit_price: Decimal
) -> Position:
    """
    Update a Position object with settlement outcome.

    This function creates a copy of the Position object with updated settlement
    information, preserving immutability and avoiding side effects.

    Args:
        position: Position object to update
        outcome: Settlement outcome (WIN/LOSS/PUSH/UNKNOWN)
        exit_price: Final exit price (1.0 for WIN, 0.0 for LOSS)

    Returns:
        New Position object with settlement updates applied

    Example:
        updated_position = update_position_with_settlement(
            position=my_position,
            outcome=SettlementOutcome.WIN,
            exit_price=Decimal("1.00")
        )
    """
    # Create a copy of metadata to avoid mutating the input object
    updated_metadata = position.metadata.copy()
    updated_metadata["settlement_outcome"] = outcome.value

    # Calculate realized PnL
    price_diff = exit_price - position.entry_price
    new_realized_pnl = price_diff * position.quantity
    new_unrealized_pnl = Decimal("0.00")

    current_time = datetime.now(timezone.utc)

    # Create new Position object with updated values
    updated_position = position.model_copy(update={
        "status": PositionStatus.CLOSED,
        "exit_price": exit_price,
        "closed_at": current_time,
        "realized_pnl": new_realized_pnl,
        "unrealized_pnl": new_unrealized_pnl,
        "metadata": updated_metadata,
        "updated_at": current_time
    })

    logger.info(
        f"Position {updated_position.position_id} settled: "
        f"outcome={outcome.value}, realized_pnl={updated_position.realized_pnl}"
    )

    return updated_position


def track_order_lifecycle(
    client: PolymarketAPIClient,
    order_id: str,
    trade: Trade,
    position: Optional[Position] = None,
    timeout: int = 300,
    poll_interval: int = 10
) -> Tuple[Trade, Optional[Position], SettlementOutcome]:
    """
    Track complete order lifecycle from submission to settlement.

    This is a convenience function that polls for settlement and updates
    both the Trade and Position objects with the final outcome.

    Args:
        client: PolymarketAPIClient instance
        order_id: Order ID to track
        trade: Trade object to update
        position: Optional Position object to update
        timeout: Maximum polling time in seconds
        poll_interval: Seconds between polls

    Returns:
        Tuple of (updated_trade, updated_position, outcome)

    Raises:
        SettlementError: If settlement polling fails

    Example:
        trade, position, outcome = track_order_lifecycle(
            client=api_client,
            order_id="order_123",
            trade=my_trade,
            position=my_position
        )
    """
    # Poll for settlement
    outcome = poll_settlement(
        client=client,
        order_id=order_id,
        timeout=timeout,
        poll_interval=poll_interval
    )

    # Calculate realized PnL based on outcome
    if outcome == SettlementOutcome.WIN:
        # For prediction markets, winning pays out $1.00 per share
        cost = trade.price * trade.quantity
        payout = Decimal("1.00") * trade.quantity  # $1.00 per share
        realized_pnl = payout - cost - trade.fee
        exit_price = Decimal("1.00")
    elif outcome == SettlementOutcome.LOSS:
        # Losing means shares are worth $0.00
        cost = trade.price * trade.quantity
        realized_pnl = Decimal("0.00") - cost - trade.fee
        exit_price = Decimal("0.00")
    else:
        # PUSH or UNKNOWN
        realized_pnl = Decimal("0.00")
        exit_price = trade.price

    # Update trade
    trade = update_trade_with_settlement(
        trade=trade,
        outcome=outcome,
        realized_pnl=realized_pnl
    )

    # Update position if provided
    if position:
        position = update_position_with_settlement(
            position=position,
            outcome=outcome,
            exit_price=exit_price
        )

    return trade, position, outcome
