"""
Trade Execution Module for Polymarket Bot.

This module handles order submission and settlement polling for Polymarket trades.
It provides functions to:
- Submit market orders (YES/NO) to Polymarket
- Poll for settlement results
- Handle execution errors and retries

The execution module integrates with the main event loop to convert prediction
signals into actual trades on the Polymarket platform.
"""

import logging
import time
import requests
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timezone

from .config import Config, get_config
from .models import SignalType, OutcomeType
from .utils import retry_with_backoff, ValidationError

# Setup logging
logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Exception raised for trade execution errors."""
    pass


class OrderSubmissionError(ExecutionError):
    """Exception raised when order submission fails."""
    pass


class SettlementTimeoutError(ExecutionError):
    """Exception raised when settlement polling times out."""
    pass


class TradeExecutor:
    """
    Trade executor for submitting orders and monitoring settlements.

    Handles API interactions with Polymarket for order placement
    and settlement tracking.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the trade executor.

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config if config else get_config()
        self.base_url = self.config.polymarket_base_url
        self.api_key = self.config.polymarket_api_key
        self.api_secret = self.config.polymarket_api_secret

        # Setup HTTP session with auth headers
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        logger.info(f"Initialized TradeExecutor with base URL: {self.base_url}")

    @retry_with_backoff(max_attempts=3, base_delay=2.0, exceptions=(requests.RequestException,))
    def submit_order(
        self,
        market_id: str,
        signal: SignalType,
        size: Decimal
    ) -> str:
        """
        Submit a market order to Polymarket.

        Args:
            market_id: Unique market identifier
            signal: Trading signal (UP = YES, DOWN = NO)
            size: Position size in USD

        Returns:
            Order ID from Polymarket

        Raises:
            OrderSubmissionError: If order submission fails
            ValidationError: If parameters are invalid
        """
        # Validate parameters
        if not market_id:
            raise ValidationError("market_id cannot be empty")

        if signal not in [SignalType.UP, SignalType.DOWN]:
            raise ValidationError(f"Invalid signal for order: {signal}")

        if size <= 0:
            raise ValidationError(f"Position size must be positive, got: {size}")

        # Convert signal to side
        side = "YES" if signal == SignalType.UP else "NO"

        # Prepare order payload
        order_payload = {
            "market_id": market_id,
            "side": side,
            "amount": float(size),
            "type": "MARKET"
        }

        logger.info(
            f"Submitting {side} order for market {market_id}, "
            f"size: ${size:.2f}"
        )

        try:
            response = self.session.post(
                f"{self.base_url}/orders",
                json=order_payload,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            order_id = data.get('order_id') or data.get('id')
            if not order_id:
                raise OrderSubmissionError("Order response missing 'order_id' field")

            logger.info(f"Order submitted successfully: {order_id}")

            return str(order_id)

        except requests.HTTPError as e:
            error_msg = f"Order submission failed: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg)
            raise OrderSubmissionError(error_msg) from e

        except requests.RequestException as e:
            error_msg = f"Network error during order submission: {str(e)}"
            logger.error(error_msg)
            raise OrderSubmissionError(error_msg) from e

        except (KeyError, ValueError) as e:
            error_msg = f"Invalid order response: {str(e)}"
            logger.error(error_msg)
            raise OrderSubmissionError(error_msg) from e

    def poll_settlement(
        self,
        order_id: str,
        timeout: int = 300,
        poll_interval: int = 10
    ) -> Tuple[str, Decimal]:
        """
        Poll for order settlement and outcome.

        Waits for order to settle and returns the outcome. Polls every
        poll_interval seconds until settlement or timeout.

        Args:
            order_id: Order ID to monitor
            timeout: Maximum time to wait in seconds (default: 300s = 5 minutes)
            poll_interval: Seconds between polls (default: 10s)

        Returns:
            Tuple of (outcome, pnl) where:
                - outcome: "WIN" or "LOSS"
                - pnl: Profit/loss amount

        Raises:
            SettlementTimeoutError: If settlement doesn't occur within timeout
            ExecutionError: If unable to retrieve settlement status
        """
        if not order_id:
            raise ValidationError("order_id cannot be empty")

        logger.info(
            f"Starting settlement polling for order {order_id} "
            f"(timeout: {timeout}s, interval: {poll_interval}s)"
        )

        start_time = time.time()
        attempts = 0

        while time.time() - start_time < timeout:
            attempts += 1

            try:
                # Fetch order status
                response = self.session.get(
                    f"{self.base_url}/orders/{order_id}",
                    timeout=30
                )

                response.raise_for_status()
                data = response.json()

                status = data.get('status', '').upper()

                logger.debug(
                    f"Poll attempt {attempts}: order {order_id} status = {status}"
                )

                # Check if settled
                if status == 'SETTLED':
                    outcome = self._parse_outcome(data)
                    pnl = self._parse_pnl(data)

                    logger.info(
                        f"Order {order_id} settled: {outcome}, PnL: ${pnl:.2f}"
                    )

                    return outcome, pnl

                # Check for failure states
                if status in ['FAILED', 'CANCELLED', 'REJECTED']:
                    raise ExecutionError(
                        f"Order {order_id} ended in {status} state"
                    )

                # Order still pending, wait and retry
                if time.time() - start_time + poll_interval < timeout:
                    time.sleep(poll_interval)

            except requests.HTTPError as e:
                logger.error(
                    f"HTTP error polling order {order_id}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
                # Continue polling on HTTP errors (may be transient)
                time.sleep(poll_interval)

            except requests.RequestException as e:
                logger.error(f"Network error polling order {order_id}: {e}")
                # Continue polling on network errors (may be transient)
                time.sleep(poll_interval)

        # Timeout reached
        elapsed = time.time() - start_time
        raise SettlementTimeoutError(
            f"Settlement polling timed out after {elapsed:.1f}s "
            f"for order {order_id}"
        )

    def _parse_outcome(self, order_data: Dict[str, Any]) -> str:
        """
        Parse settlement outcome from order data.

        Args:
            order_data: Order response data

        Returns:
            "WIN" or "LOSS"

        Raises:
            ExecutionError: If outcome cannot be determined
        """
        # Try different possible field names
        outcome = (
            order_data.get('outcome') or
            order_data.get('winning_outcome') or
            order_data.get('result')
        )

        if outcome is None:
            raise ExecutionError("Order data missing outcome field")

        outcome_str = str(outcome).upper()

        if outcome_str in ['WIN', 'WINNER', 'WON', 'SUCCESS']:
            return "WIN"
        elif outcome_str in ['LOSS', 'LOSE', 'LOST', 'FAILURE']:
            return "LOSS"
        else:
            raise ExecutionError(f"Unknown outcome value: {outcome}")

    def _parse_pnl(self, order_data: Dict[str, Any]) -> Decimal:
        """
        Parse profit/loss from order data.

        Args:
            order_data: Order response data

        Returns:
            PnL amount (positive for profit, negative for loss)
        """
        # Try different possible field names
        pnl = (
            order_data.get('pnl') or
            order_data.get('profit_loss') or
            order_data.get('return') or
            0
        )

        try:
            return Decimal(str(pnl))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse PnL from: {pnl}, defaulting to 0")
            return Decimal("0.0")

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful, False otherwise
        """
        try:
            response = self.session.delete(
                f"{self.base_url}/orders/{order_id}",
                timeout=30
            )

            response.raise_for_status()
            logger.info(f"Order {order_id} cancelled successfully")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("TradeExecutor session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def submit_order(
    market_id: str,
    signal: SignalType,
    size: Decimal,
    config: Optional[Config] = None
) -> str:
    """
    Convenience function to submit an order without maintaining executor state.

    Args:
        market_id: Unique market identifier
        signal: Trading signal (UP = YES, DOWN = NO)
        size: Position size in USD
        config: Configuration object. If None, loads from environment.

    Returns:
        Order ID from Polymarket

    Raises:
        OrderSubmissionError: If order submission fails
    """
    executor = TradeExecutor(config=config)
    try:
        return executor.submit_order(market_id, signal, size)
    finally:
        executor.close()


def poll_settlement(
    order_id: str,
    timeout: int = 300,
    poll_interval: int = 10,
    config: Optional[Config] = None
) -> Tuple[str, Decimal]:
    """
    Convenience function to poll settlement without maintaining executor state.

    Args:
        order_id: Order ID to monitor
        timeout: Maximum time to wait in seconds (default: 300s = 5 minutes)
        poll_interval: Seconds between polls (default: 10s)
        config: Configuration object. If None, loads from environment.

    Returns:
        Tuple of (outcome, pnl)

    Raises:
        SettlementTimeoutError: If settlement doesn't occur within timeout
    """
    executor = TradeExecutor(config=config)
    try:
        return executor.poll_settlement(order_id, timeout, poll_interval)
    finally:
        executor.close()


def execute_trade(
    market_id: str,
    signal: SignalType,
    size: Decimal,
    settlement_timeout: int = 300,
    config: Optional[Config] = None
) -> Dict[str, Any]:
    """
    Execute a complete trade: submit order and wait for settlement.

    This is a high-level function that handles the full trade lifecycle
    from order submission to settlement.

    Args:
        market_id: Unique market identifier
        signal: Trading signal (UP = YES, DOWN = NO)
        size: Position size in USD
        settlement_timeout: Max time to wait for settlement (default: 300s)
        config: Configuration object. If None, loads from environment.

    Returns:
        Dictionary with trade results:
            - order_id: Order ID
            - outcome: "WIN" or "LOSS"
            - pnl: Profit/loss amount
            - execution_time: Time taken to execute and settle

    Raises:
        ExecutionError: If trade execution or settlement fails
    """
    start_time = time.time()

    with TradeExecutor(config=config) as executor:
        # Submit order
        order_id = executor.submit_order(market_id, signal, size)

        # Poll for settlement
        outcome, pnl = executor.poll_settlement(
            order_id,
            timeout=settlement_timeout
        )

        execution_time = time.time() - start_time

        return {
            "order_id": order_id,
            "outcome": outcome,
            "pnl": float(pnl),
            "execution_time": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
