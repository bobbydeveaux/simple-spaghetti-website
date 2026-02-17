"""
Trade Execution Module for Polymarket Bot.

This module handles order submission to the Polymarket API, including:
- Market and limit order placement
- Order status polling
- Settlement tracking
- Retry logic with exponential backoff
- Error handling and logging

All API calls use retry logic to handle transient failures gracefully.
"""

import logging
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from polymarket_bot.models import (
    Trade,
    OrderSide,
    OrderType,
    OutcomeType,
    TradeStatus
)
from polymarket_bot.config import Config, get_config
from polymarket_bot.utils import (
    retry_with_backoff,
    validate_non_empty,
    validate_range,
    validate_type,
    RetryError
)

# Configure module logger
logger = logging.getLogger(__name__)


class OrderExecutionError(Exception):
    """Exception raised when order execution fails."""
    pass


class OrderSettlementError(Exception):
    """Exception raised when order settlement tracking fails."""
    pass


class PolymarketAPIError(Exception):
    """Exception raised when Polymarket API returns an error."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class OrderStatus(str, Enum):
    """Order status from Polymarket API."""
    PENDING = "pending"
    OPEN = "open"
    MATCHED = "matched"
    SETTLED = "settled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ExecutionEngine:
    """
    Execution engine for submitting and tracking orders on Polymarket.

    Features:
    - Submit market and limit orders
    - Poll order status with configurable timeout
    - Track settlement and outcomes
    - Retry logic for transient failures
    - Comprehensive error handling and logging
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the execution engine.

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config or get_config()
        self.base_url = self.config.polymarket_base_url
        self.api_key = self.config.polymarket_api_key
        self.api_secret = self.config.polymarket_api_secret

        # Configure session with connection pooling and retries at transport level
        self.session = self._create_session()

        # Execution settings from config or defaults
        self.max_retries = getattr(self.config, 'execution_max_retries', 3)
        self.retry_base_delay = getattr(self.config, 'execution_retry_base_delay', 2.0)
        self.settlement_poll_interval = getattr(self.config, 'execution_settlement_poll_interval', 10)
        self.settlement_timeout = getattr(self.config, 'execution_settlement_timeout', 300)

        logger.info(
            f"ExecutionEngine initialized with base_url={self.base_url}, "
            f"max_retries={self.max_retries}, retry_base_delay={self.retry_base_delay}s"
        )

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic and connection pooling.

        Returns:
            Configured requests.Session instance
        """
        session = requests.Session()

        # Configure retry strategy for transport-level errors (connection, timeout)
        # Note: Application-level retries (4xx, 5xx) are handled by @retry_with_backoff
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],  # Retry on server errors
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "PolymarketBot/1.0",
            "Authorization": f"Bearer {self.api_key}"
        })

        return session

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Polymarket API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/orders")
            data: Request body data (for POST/PUT)
            params: Query parameters (for GET)

        Returns:
            Response data as dictionary

        Raises:
            PolymarketAPIError: If the API returns an error
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                json=data,
                params=params,
                timeout=30
            )

            # Log request details
            logger.debug(
                f"API Request: {method.upper()} {url} "
                f"(params={params}, data={data})"
            )

            # Check for HTTP errors
            if not response.ok:
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {"detail": response.text}

                error_msg = (
                    f"Polymarket API error: {response.status_code} - "
                    f"{error_data.get('detail', 'Unknown error')}"
                )

                logger.error(
                    f"{error_msg} (endpoint={endpoint}, "
                    f"response_data={error_data})"
                )

                raise PolymarketAPIError(
                    error_msg,
                    status_code=response.status_code,
                    response_data=error_data
                )

            # Parse response
            response_data = response.json()
            logger.debug(f"API Response: {response.status_code} - {response_data}")

            return response_data

        except requests.exceptions.Timeout as e:
            raise PolymarketAPIError(f"Request timeout: {str(e)}") from e
        except requests.exceptions.ConnectionError as e:
            raise PolymarketAPIError(f"Connection error: {str(e)}") from e
        except requests.exceptions.RequestException as e:
            raise PolymarketAPIError(f"Request error: {str(e)}") from e

    @retry_with_backoff(
        max_attempts=3,
        base_delay=2.0,
        exponential_base=2.0,
        exceptions=(PolymarketAPIError, requests.exceptions.RequestException)
    )
    def submit_order(
        self,
        market_id: str,
        side: OrderSide,
        outcome: OutcomeType,
        quantity: Decimal,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[Decimal] = None,
        trade_id: Optional[str] = None
    ) -> Trade:
        """
        Submit an order to Polymarket with retry logic.

        This method uses exponential backoff retry logic (3 attempts max) to handle
        transient API failures. Each retry has increasing delays: 2s, 4s, 8s.

        Args:
            market_id: Polymarket market identifier
            side: Order side (BUY or SELL)
            outcome: Market outcome to trade (YES or NO)
            quantity: Number of shares to trade
            order_type: Order type (MARKET or LIMIT)
            price: Limit price (required for LIMIT orders)
            trade_id: Optional trade identifier (generated if not provided)

        Returns:
            Trade object with order details and status

        Raises:
            OrderExecutionError: If order submission fails after all retries
            RetryError: If retries are exhausted
        """
        # Validate inputs
        validate_non_empty(market_id, "market_id")
        validate_type(side, OrderSide, "side")
        validate_type(outcome, OutcomeType, "outcome")
        validate_range(quantity, Decimal("0.01"), None, "quantity")

        if order_type == OrderType.LIMIT:
            if price is None:
                raise OrderExecutionError("price is required for LIMIT orders")
            validate_range(price, Decimal("0.01"), Decimal("0.99"), "price")

        # Generate trade_id if not provided
        if not trade_id:
            trade_id = f"trade_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        # Prepare order payload
        order_data = {
            "market_id": market_id,
            "side": side.value.upper(),  # API expects uppercase
            "outcome": outcome.value.upper(),  # YES or NO
            "amount": float(quantity),
            "type": order_type.value.upper()
        }

        # Add price for limit orders
        if order_type == OrderType.LIMIT and price is not None:
            order_data["price"] = float(price)

        logger.info(
            f"Submitting order: trade_id={trade_id}, market={market_id}, "
            f"side={side.value}, outcome={outcome.value}, qty={quantity}, "
            f"type={order_type.value}, price={price}"
        )

        try:
            # Submit order to Polymarket API
            response_data = self._make_request("POST", "/orders", data=order_data)

            # Extract order details from response
            order_id = response_data.get("order_id") or response_data.get("id")
            if not order_id:
                raise OrderExecutionError("No order_id in API response")

            # Determine initial filled quantity and status
            filled_qty = Decimal(str(response_data.get("filled_amount", 0)))
            status_str = response_data.get("status", "pending").lower()

            # Map API status to our TradeStatus
            status = TradeStatus.PENDING
            if status_str in ["matched", "filled", "executed"]:
                status = TradeStatus.EXECUTED
            elif status_str in ["cancelled", "canceled"]:
                status = TradeStatus.CANCELLED
            elif status_str == "failed":
                status = TradeStatus.FAILED

            # Create Trade object
            trade = Trade(
                trade_id=trade_id,
                market_id=market_id,
                order_id=order_id,
                side=side,
                order_type=order_type,
                outcome=outcome,
                price=price or Decimal("0"),  # Market orders have no price initially
                quantity=quantity,
                filled_quantity=filled_qty,
                status=status,
                created_at=datetime.now(timezone.utc),
                executed_at=datetime.now(timezone.utc) if status == TradeStatus.EXECUTED else None,
                fee=Decimal(str(response_data.get("fee", 0))),
                metadata={
                    "api_response": response_data,
                    "submitted_at": datetime.now(timezone.utc).isoformat()
                }
            )

            logger.info(
                f"Order submitted successfully: trade_id={trade_id}, "
                f"order_id={order_id}, status={status.value}, "
                f"filled_qty={filled_qty}/{quantity}"
            )

            return trade

        except PolymarketAPIError as e:
            logger.error(
                f"Order submission failed: trade_id={trade_id}, "
                f"error={str(e)}, status_code={e.status_code}"
            )
            raise OrderExecutionError(f"Failed to submit order: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during order submission: {str(e)}")
            raise OrderExecutionError(f"Order submission error: {str(e)}") from e

    @retry_with_backoff(
        max_attempts=3,
        base_delay=1.0,
        exponential_base=2.0,
        exceptions=(PolymarketAPIError, requests.exceptions.RequestException)
    )
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get current status of an order from Polymarket API.

        Args:
            order_id: Order identifier

        Returns:
            Order status data from API

        Raises:
            PolymarketAPIError: If API request fails
        """
        validate_non_empty(order_id, "order_id")

        logger.debug(f"Fetching order status for order_id={order_id}")

        try:
            response_data = self._make_request("GET", f"/orders/{order_id}")
            return response_data
        except PolymarketAPIError as e:
            logger.error(f"Failed to get order status: order_id={order_id}, error={str(e)}")
            raise

    def poll_settlement(
        self,
        order_id: str,
        timeout: Optional[int] = None,
        poll_interval: Optional[int] = None
    ) -> str:
        """
        Poll order status until settlement is complete.

        Continuously polls the order status at regular intervals until the order
        is settled or the timeout is reached.

        Args:
            order_id: Order identifier to poll
            timeout: Maximum time to wait in seconds (default: from config)
            poll_interval: Seconds between polls (default: from config)

        Returns:
            Settlement outcome: "WIN", "LOSS", or "CANCELLED"

        Raises:
            OrderSettlementError: If settlement times out or fails
        """
        validate_non_empty(order_id, "order_id")

        timeout = timeout or self.settlement_timeout
        poll_interval = poll_interval or self.settlement_poll_interval

        logger.info(
            f"Polling settlement for order_id={order_id}, "
            f"timeout={timeout}s, interval={poll_interval}s"
        )

        start_time = time.time()
        attempts = 0

        while True:
            attempts += 1
            elapsed = time.time() - start_time

            # Check timeout
            if elapsed >= timeout:
                logger.error(
                    f"Settlement polling timeout after {elapsed:.1f}s "
                    f"({attempts} attempts) for order_id={order_id}"
                )
                raise OrderSettlementError(
                    f"Settlement polling timeout after {timeout}s for order {order_id}"
                )

            try:
                # Get current order status
                order_data = self.get_order_status(order_id)
                status = order_data.get("status", "").lower()

                logger.debug(
                    f"Poll #{attempts} (elapsed={elapsed:.1f}s): "
                    f"order_id={order_id}, status={status}"
                )

                # Check if settled
                if status == "settled":
                    outcome = order_data.get("outcome", "").upper()

                    if outcome not in ["WIN", "LOSS"]:
                        logger.warning(
                            f"Unexpected settlement outcome '{outcome}' for "
                            f"order_id={order_id}, defaulting to LOSS"
                        )
                        outcome = "LOSS"

                    logger.info(
                        f"Order settled: order_id={order_id}, outcome={outcome}, "
                        f"elapsed={elapsed:.1f}s, attempts={attempts}"
                    )

                    return outcome

                # Check for terminal states
                if status in ["cancelled", "canceled"]:
                    logger.warning(f"Order cancelled: order_id={order_id}")
                    return "CANCELLED"

                if status == "failed":
                    logger.error(f"Order failed: order_id={order_id}")
                    raise OrderSettlementError(f"Order {order_id} failed")

                # Not settled yet, wait before next poll
                logger.debug(f"Order not settled yet, waiting {poll_interval}s...")
                time.sleep(poll_interval)

            except PolymarketAPIError as e:
                # Log API error but continue polling (might be transient)
                logger.warning(
                    f"API error during settlement polling (attempt #{attempts}): {str(e)}, "
                    f"continuing..."
                )
                time.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Unexpected error during settlement polling: {str(e)}")
                raise OrderSettlementError(f"Settlement polling error: {str(e)}") from e

    def update_trade_status(self, trade: Trade) -> Trade:
        """
        Update a trade object with current status from API.

        Args:
            trade: Trade object to update

        Returns:
            Updated Trade object

        Raises:
            PolymarketAPIError: If API request fails
        """
        logger.debug(f"Updating trade status: trade_id={trade.trade_id}, order_id={trade.order_id}")

        try:
            order_data = self.get_order_status(trade.order_id)

            # Update filled quantity
            filled_qty = Decimal(str(order_data.get("filled_amount", 0)))
            trade.filled_quantity = filled_qty

            # Update status
            status_str = order_data.get("status", "").lower()
            if status_str in ["matched", "filled", "executed"]:
                trade.status = TradeStatus.EXECUTED
                if not trade.executed_at:
                    trade.executed_at = datetime.now(timezone.utc)
            elif status_str in ["cancelled", "canceled"]:
                trade.status = TradeStatus.CANCELLED
            elif status_str == "failed":
                trade.status = TradeStatus.FAILED

            # Update fee
            trade.fee = Decimal(str(order_data.get("fee", trade.fee)))

            # Update metadata
            trade.metadata["last_status_update"] = datetime.now(timezone.utc).isoformat()
            trade.metadata["latest_api_response"] = order_data

            logger.info(
                f"Trade status updated: trade_id={trade.trade_id}, "
                f"status={trade.status.value}, filled_qty={filled_qty}"
            )

            return trade

        except Exception as e:
            logger.error(f"Failed to update trade status: {str(e)}")
            raise

    def close(self):
        """Close the session and cleanup resources."""
        if self.session:
            self.session.close()
            logger.info("ExecutionEngine session closed")


# Convenience functions for common operations

def submit_market_order(
    market_id: str,
    side: OrderSide,
    outcome: OutcomeType,
    quantity: Decimal,
    config: Optional[Config] = None
) -> Trade:
    """
    Submit a market order to Polymarket.

    Convenience function that creates an ExecutionEngine instance and submits
    a market order with default retry logic.

    Args:
        market_id: Polymarket market identifier
        side: Order side (BUY or SELL)
        outcome: Market outcome (YES or NO)
        quantity: Number of shares to trade
        config: Optional configuration object

    Returns:
        Trade object with order details

    Raises:
        OrderExecutionError: If order submission fails
    """
    engine = ExecutionEngine(config)
    try:
        return engine.submit_order(
            market_id=market_id,
            side=side,
            outcome=outcome,
            quantity=quantity,
            order_type=OrderType.MARKET
        )
    finally:
        engine.close()


def submit_limit_order(
    market_id: str,
    side: OrderSide,
    outcome: OutcomeType,
    quantity: Decimal,
    price: Decimal,
    config: Optional[Config] = None
) -> Trade:
    """
    Submit a limit order to Polymarket.

    Convenience function that creates an ExecutionEngine instance and submits
    a limit order with default retry logic.

    Args:
        market_id: Polymarket market identifier
        side: Order side (BUY or SELL)
        outcome: Market outcome (YES or NO)
        quantity: Number of shares to trade
        price: Limit price (0.01 to 0.99)
        config: Optional configuration object

    Returns:
        Trade object with order details

    Raises:
        OrderExecutionError: If order submission fails
    """
    engine = ExecutionEngine(config)
    try:
        return engine.submit_order(
            market_id=market_id,
            side=side,
            outcome=outcome,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            price=price
        )
    finally:
        engine.close()
