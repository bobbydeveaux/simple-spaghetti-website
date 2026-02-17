"""
Trade Execution Module for Polymarket Bot.

This module handles order submission and settlement polling for the Polymarket API.
It implements:
- Order submission with authentication and request signing
- Settlement polling with timeout handling
- Retry logic with exponential backoff
- Order response parsing and validation
- Error handling for API failures
"""

import time
import logging
import hmac
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timezone
import requests

from .config import Config, get_config
from .models import OutcomeType, OrderType, OrderSide
from .utils import retry_with_backoff, validate_non_empty, ValidationError, RetryError


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


class PolymarketExecutionClient:
    """
    Client for executing trades on Polymarket.

    Handles order submission, authentication, request signing,
    and settlement polling for the Polymarket trading API.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Polymarket execution client.

        Args:
            config: Configuration object. If None, uses global config.
        """
        self.config = config or get_config()
        self.base_url = self.config.polymarket_base_url
        self.api_key = self.config.polymarket_api_key
        self.api_secret = self.config.polymarket_api_secret
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        logger.info(f"Initialized PolymarketExecutionClient with base URL: {self.base_url}")

    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """
        Generate HMAC signature for API request authentication.

        Args:
            timestamp: Request timestamp in milliseconds
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            body: Request body as JSON string

        Returns:
            Base64-encoded HMAC signature
        """
        # Create the message to sign
        message = f"{timestamp}{method}{path}{body}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Generate authentication headers for API request.

        Args:
            method: HTTP method
            path: API endpoint path
            body: Request body as JSON string

        Returns:
            Dictionary of authentication headers
        """
        timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))
        signature = self._generate_signature(timestamp, method, path, body)

        return {
            'Authorization': f'Bearer {self.api_key}',
            'X-Timestamp': timestamp,
            'X-Signature': signature
        }

    @retry_with_backoff(max_attempts=3, base_delay=2.0, exceptions=(requests.RequestException,))
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated HTTP request to the Polymarket API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            JSON response from the API

        Raises:
            ExecutionError: If the API request fails
        """
        url = f"{self.base_url}{endpoint}"
        body = json.dumps(data) if data else ""

        # Get authentication headers
        auth_headers = self._get_auth_headers(method, endpoint, body)
        headers = {**self.session.headers, **auth_headers}

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                data=body if body else None,
                params=params,
                timeout=30
            )

            # Log rate limit information if available
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = response.headers['X-RateLimit-Remaining']
                logger.debug(f"API rate limit remaining: {remaining}")

            response.raise_for_status()

            return response.json()

        except requests.HTTPError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ExecutionError(error_msg) from e

        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            raise ExecutionError(error_msg) from e

        except ValueError as e:
            error_msg = f"Invalid JSON response: {str(e)}"
            logger.error(error_msg)
            raise ExecutionError(error_msg) from e

    def submit_order(
        self,
        market_id: str,
        direction: str,
        size: float,
        order_type: str = "MARKET"
    ) -> str:
        """
        Submit an order to Polymarket.

        Args:
            market_id: Unique market identifier
            direction: Trade direction ("UP" for YES, "DOWN" for NO)
            size: Order size in USD
            order_type: Order type (default: "MARKET")

        Returns:
            Order ID from Polymarket API

        Raises:
            OrderSubmissionError: If order submission fails
            ValidationError: If parameters are invalid
        """
        # Validate inputs
        validate_non_empty(market_id, "market_id")
        validate_non_empty(direction, "direction")

        if size <= 0:
            raise ValidationError(f"Order size must be positive, got: {size}")

        # Map direction to Polymarket outcome
        if direction.upper() == "UP":
            side = "YES"
        elif direction.upper() == "DOWN":
            side = "NO"
        else:
            raise ValidationError(f"Invalid direction: {direction}. Must be 'UP' or 'DOWN'")

        # Prepare order payload
        order_data = {
            "market_id": market_id,
            "side": side,
            "amount": float(size),
            "type": order_type
        }

        logger.info(
            f"Submitting {order_type} order: market={market_id}, side={side}, "
            f"amount=${size:.2f}"
        )

        try:
            # Submit order to API
            response = self._make_request("POST", "/orders", data=order_data)

            # Extract order ID from response
            order_id = response.get('order_id') or response.get('id') or response.get('orderId')

            if not order_id:
                raise OrderSubmissionError(
                    f"Order response missing 'order_id' field: {response}"
                )

            # Extract order status
            status = response.get('status', 'UNKNOWN')

            logger.info(
                f"Order submitted successfully: order_id={order_id}, status={status}"
            )

            return str(order_id)

        except ExecutionError as e:
            logger.error(f"Failed to submit order: {e}")
            raise OrderSubmissionError(f"Order submission failed: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error during order submission: {e}")
            raise OrderSubmissionError(f"Unexpected error: {e}") from e

    def poll_settlement(
        self,
        order_id: str,
        timeout: int = 300,
        poll_interval: int = 10
    ) -> str:
        """
        Poll for order settlement status.

        Continuously checks the order status until it's settled or timeout is reached.

        Args:
            order_id: Order identifier to poll
            timeout: Maximum time to wait in seconds (default: 300)
            poll_interval: Seconds between polling attempts (default: 10)

        Returns:
            Settlement outcome: "WIN" or "LOSS"

        Raises:
            SettlementTimeoutError: If settlement doesn't occur within timeout
            ExecutionError: If polling fails
            ValidationError: If order_id is invalid
        """
        validate_non_empty(order_id, "order_id")

        if timeout <= 0:
            raise ValidationError(f"Timeout must be positive, got: {timeout}")

        if poll_interval <= 0:
            raise ValidationError(f"Poll interval must be positive, got: {poll_interval}")

        logger.info(
            f"Starting settlement polling: order_id={order_id}, "
            f"timeout={timeout}s, interval={poll_interval}s"
        )

        start_time = time.time()
        attempts = 0

        while True:
            attempts += 1
            elapsed = time.time() - start_time

            # Check if timeout reached
            if elapsed >= timeout:
                raise SettlementTimeoutError(
                    f"Order settlement timed out after {timeout}s "
                    f"(order_id={order_id}, attempts={attempts})"
                )

            try:
                # Query order status
                endpoint = f"/orders/{order_id}"
                response = self._make_request("GET", endpoint)

                status = response.get('status', '').upper()
                logger.debug(f"Order status check {attempts}: {status}")

                # Check if order is settled
                if status == "SETTLED" or status == "FILLED" or status == "COMPLETED":
                    # Determine win/loss outcome
                    outcome = self._parse_settlement_outcome(response)

                    logger.info(
                        f"Order settled: order_id={order_id}, outcome={outcome}, "
                        f"elapsed={elapsed:.1f}s, attempts={attempts}"
                    )

                    return outcome

                # Check if order failed
                elif status in ["FAILED", "CANCELLED", "REJECTED"]:
                    logger.error(f"Order failed with status: {status}")
                    raise ExecutionError(f"Order failed: {status}")

                # Order still pending, continue polling
                else:
                    logger.debug(
                        f"Order still pending (status={status}), "
                        f"waiting {poll_interval}s..."
                    )
                    time.sleep(poll_interval)

            except ExecutionError as e:
                # If this is a settlement timeout, raise it
                if isinstance(e, SettlementTimeoutError):
                    raise

                # For other errors, log and retry (unless we've hit timeout)
                logger.warning(f"Error polling order status: {e}")

                if elapsed + poll_interval >= timeout:
                    raise SettlementTimeoutError(
                        f"Failed to poll order status within timeout: {e}"
                    ) from e

                time.sleep(poll_interval)

    def _parse_settlement_outcome(self, order_response: Dict[str, Any]) -> str:
        """
        Parse settlement outcome from order response.

        Args:
            order_response: Order response from API

        Returns:
            Settlement outcome: "WIN" or "LOSS"

        Raises:
            ExecutionError: If outcome cannot be determined
        """
        # Try different possible fields for outcome
        outcome_str = (
            order_response.get('outcome') or
            order_response.get('result') or
            order_response.get('settlement')
        )

        if not outcome_str:
            # If no explicit outcome, try to infer from profit/loss
            pnl = order_response.get('pnl') or order_response.get('profit_loss')
            if pnl is not None:
                try:
                    pnl_value = float(pnl)
                    return "WIN" if pnl_value > 0 else "LOSS"
                except (ValueError, TypeError):
                    pass

        # Parse outcome string
        if outcome_str:
            outcome_upper = str(outcome_str).upper()
            if outcome_upper in ["WIN", "WON", "SUCCESS", "PROFIT"]:
                return "WIN"
            elif outcome_upper in ["LOSS", "LOST", "LOSE", "FAIL"]:
                return "LOSS"

        # If we still can't determine outcome, raise error
        logger.error(f"Cannot determine outcome from response: {order_response}")
        raise ExecutionError(
            f"Unable to determine settlement outcome from order response"
        )

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get current status of an order.

        Args:
            order_id: Order identifier

        Returns:
            Order status information

        Raises:
            ExecutionError: If request fails
            ValidationError: If order_id is invalid
        """
        validate_non_empty(order_id, "order_id")

        logger.debug(f"Fetching order status: order_id={order_id}")

        endpoint = f"/orders/{order_id}"
        response = self._make_request("GET", endpoint)

        return response

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: Order identifier to cancel

        Returns:
            True if cancellation succeeded, False otherwise

        Raises:
            ExecutionError: If cancellation request fails
            ValidationError: If order_id is invalid
        """
        validate_non_empty(order_id, "order_id")

        logger.info(f"Cancelling order: order_id={order_id}")

        endpoint = f"/orders/{order_id}/cancel"

        try:
            response = self._make_request("POST", endpoint)
            success = response.get('success', False) or response.get('cancelled', False)

            if success:
                logger.info(f"Order cancelled successfully: order_id={order_id}")
            else:
                logger.warning(f"Order cancellation may have failed: {response}")

            return success

        except ExecutionError as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("Closed PolymarketExecutionClient session")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def submit_order(
    market_id: str,
    direction: str,
    size: float,
    config: Optional[Config] = None
) -> str:
    """
    Submit an order to Polymarket (convenience function).

    Args:
        market_id: Unique market identifier
        direction: Trade direction ("UP" for YES, "DOWN" for NO)
        size: Order size in USD
        config: Optional configuration object

    Returns:
        Order ID from Polymarket API

    Raises:
        OrderSubmissionError: If order submission fails
        ValidationError: If parameters are invalid
    """
    client = PolymarketExecutionClient(config)
    try:
        return client.submit_order(market_id, direction, size)
    finally:
        client.close()


def poll_settlement(
    order_id: str,
    timeout: int = 300,
    config: Optional[Config] = None
) -> str:
    """
    Poll for order settlement (convenience function).

    Args:
        order_id: Order identifier to poll
        timeout: Maximum time to wait in seconds (default: 300)
        config: Optional configuration object

    Returns:
        Settlement outcome: "WIN" or "LOSS"

    Raises:
        SettlementTimeoutError: If settlement doesn't occur within timeout
        ExecutionError: If polling fails
        ValidationError: If order_id is invalid
    """
    client = PolymarketExecutionClient(config)
    try:
        return client.poll_settlement(order_id, timeout=timeout)
    finally:
        client.close()


def execute_trade(
    market_id: str,
    direction: str,
    size: float,
    wait_for_settlement: bool = True,
    settlement_timeout: int = 300,
    config: Optional[Config] = None
) -> Tuple[str, Optional[str]]:
    """
    Execute a complete trade: submit order and optionally wait for settlement.

    Args:
        market_id: Unique market identifier
        direction: Trade direction ("UP" for YES, "DOWN" for NO)
        size: Order size in USD
        wait_for_settlement: Whether to wait for settlement (default: True)
        settlement_timeout: Settlement timeout in seconds (default: 300)
        config: Optional configuration object

    Returns:
        Tuple of (order_id, outcome)
        - order_id: Order identifier
        - outcome: Settlement outcome ("WIN"/"LOSS") if wait_for_settlement=True, else None

    Raises:
        OrderSubmissionError: If order submission fails
        SettlementTimeoutError: If settlement times out
        ExecutionError: If execution fails
        ValidationError: If parameters are invalid
    """
    client = PolymarketExecutionClient(config)

    try:
        # Submit the order
        order_id = client.submit_order(market_id, direction, size)

        # Wait for settlement if requested
        outcome = None
        if wait_for_settlement:
            outcome = client.poll_settlement(order_id, timeout=settlement_timeout)

        return order_id, outcome

    finally:
        client.close()
