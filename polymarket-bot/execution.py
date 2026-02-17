"""
Trade Execution Module for Polymarket Bot.

This module handles order submission and settlement polling for the Polymarket API.
It implements retry logic with exponential backoff for transient failures and
distinguishes between retryable and terminal errors.
"""

import logging
import time
from typing import Optional, Dict, Any
from decimal import Decimal
import requests

from .config import get_config
from .utils import retry_with_backoff, RetryError, ValidationError
from .models import OrderStatus, TradeOutcome

# Configure module logger
logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Base exception for execution-related errors."""
    pass


class TerminalExecutionError(ExecutionError):
    """Exception raised for terminal errors that should not be retried."""
    pass


class RetryableExecutionError(ExecutionError):
    """Exception raised for transient errors that can be retried."""
    pass


def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable or terminal.

    Args:
        error: The exception to classify

    Returns:
        True if the error is retryable, False if terminal
    """
    # Network-related errors are retryable
    if isinstance(error, (requests.ConnectionError, requests.Timeout)):
        return True

    # HTTP errors
    if isinstance(error, requests.HTTPError):
        response = getattr(error, 'response', None)
        if response is not None:
            status_code = response.status_code

            # Rate limiting (429) and server errors (5xx) are retryable
            if status_code == 429 or 500 <= status_code < 600:
                return True

            # Client errors (4xx except 429) are terminal
            if 400 <= status_code < 500:
                return False

    # By default, consider errors retryable
    return True


def submit_order(
    market_id: str,
    direction: str,
    size: float,
    config: Optional[Any] = None
) -> str:
    """
    Submit a market order to the Polymarket API with retry logic.

    This function places a market order for a prediction market position.
    It automatically retries failed submissions using exponential backoff
    for transient failures (network errors, rate limits, server errors).

    Args:
        market_id: The Polymarket market identifier
        direction: Order direction, either "YES" or "NO"
        size: Position size in USDC
        config: Optional configuration instance (uses global config if None)

    Returns:
        Order ID string returned by the Polymarket API

    Raises:
        ValidationError: If input parameters are invalid
        TerminalExecutionError: For non-retryable API errors (e.g., insufficient funds)
        RetryError: If all retry attempts are exhausted

    Example:
        order_id = submit_order(
            market_id="0x123abc",
            direction="YES",
            size=50.0
        )
    """
    # Load configuration
    if config is None:
        config = get_config()

    # Validate inputs
    if not market_id or not isinstance(market_id, str):
        raise ValidationError("market_id must be a non-empty string")

    if direction not in ["YES", "NO"]:
        raise ValidationError(f"direction must be 'YES' or 'NO', got: {direction}")

    if not isinstance(size, (int, float, Decimal)) or size <= 0:
        raise ValidationError(f"size must be a positive number, got: {size}")

    # Create retry decorator with configured parameters
    @retry_with_backoff(
        max_attempts=config.max_retries,
        base_delay=config.initial_delay,
        max_delay=config.max_delay,
        exponential_base=config.backoff_multiplier,
        exceptions=(RetryableExecutionError, requests.RequestException),
        logger_name=__name__
    )
    def _submit_with_retry():
        """Internal function that performs the actual API call."""
        try:
            # Prepare request
            url = f"{config.polymarket_base_url}/orders"
            headers = {
                "Authorization": f"Bearer {config.polymarket_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "market_id": market_id,
                "side": direction,
                "amount": float(size),
                "type": "MARKET"
            }

            logger.info(
                f"Submitting order: market={market_id}, "
                f"direction={direction}, size={size}"
            )

            # Make API request
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30.0
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Parse response
            data = response.json()
            order_id = data.get('order_id')

            if not order_id:
                raise ExecutionError(
                    f"API response missing order_id: {data}"
                )

            logger.info(f"Order submitted successfully: order_id={order_id}")
            return order_id

        except requests.HTTPError as e:
            # Classify HTTP errors as retryable or terminal
            if _is_retryable_error(e):
                logger.warning(f"Retryable HTTP error: {e}")
                raise RetryableExecutionError(f"HTTP error: {e}") from e
            else:
                logger.error(f"Terminal HTTP error: {e}")
                raise TerminalExecutionError(f"HTTP error: {e}") from e

        except requests.RequestException as e:
            # Network errors are retryable
            logger.warning(f"Retryable network error: {e}")
            raise RetryableExecutionError(f"Network error: {e}") from e

        except Exception as e:
            # Unexpected errors are terminal
            logger.error(f"Unexpected error in submit_order: {e}")
            raise TerminalExecutionError(f"Unexpected error: {e}") from e

    # Execute with retry
    try:
        return _submit_with_retry()
    except RetryError as e:
        logger.error(f"Order submission failed after all retries: {e}")
        raise
    except TerminalExecutionError:
        # Re-raise terminal errors without wrapping
        raise


def poll_settlement(
    order_id: str,
    timeout: int = 300,
    poll_interval: int = 10,
    config: Optional[Any] = None
) -> str:
    """
    Poll the Polymarket API to check order settlement status.

    This function repeatedly polls the order status endpoint until the order
    is settled or the timeout is reached. It uses retry logic with exponential
    backoff for transient API failures during polling.

    Args:
        order_id: The order ID to poll
        timeout: Maximum time to wait for settlement in seconds (default: 300)
        poll_interval: Time between polling attempts in seconds (default: 10)
        config: Optional configuration instance (uses global config if None)

    Returns:
        Settlement outcome: "WIN" or "LOSS"

    Raises:
        ValidationError: If input parameters are invalid
        ExecutionError: If settlement fails or times out
        RetryError: If all retry attempts are exhausted during polling

    Example:
        outcome = poll_settlement(
            order_id="order_123",
            timeout=300
        )
        if outcome == "WIN":
            print("Position won!")
    """
    # Load configuration
    if config is None:
        config = get_config()

    # Validate inputs
    if not order_id or not isinstance(order_id, str):
        raise ValidationError("order_id must be a non-empty string")

    if timeout <= 0:
        raise ValidationError(f"timeout must be positive, got: {timeout}")

    if poll_interval <= 0:
        raise ValidationError(f"poll_interval must be positive, got: {poll_interval}")

    # Create retry decorator for individual poll attempts
    @retry_with_backoff(
        max_attempts=config.max_retries,
        base_delay=config.initial_delay,
        max_delay=config.max_delay,
        exponential_base=config.backoff_multiplier,
        exceptions=(RetryableExecutionError, requests.RequestException),
        logger_name=__name__
    )
    def _poll_once():
        """Poll the order status once with retry logic."""
        try:
            url = f"{config.polymarket_base_url}/orders/{order_id}"
            headers = {
                "Authorization": f"Bearer {config.polymarket_api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=30.0
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Parse response
            data = response.json()
            return data

        except requests.HTTPError as e:
            # Classify HTTP errors
            if _is_retryable_error(e):
                raise RetryableExecutionError(f"HTTP error: {e}") from e
            else:
                raise TerminalExecutionError(f"HTTP error: {e}") from e

        except requests.RequestException as e:
            raise RetryableExecutionError(f"Network error: {e}") from e

        except Exception as e:
            raise TerminalExecutionError(f"Unexpected error: {e}") from e

    # Poll until settled or timeout
    logger.info(f"Starting settlement polling for order_id={order_id}")
    start_time = time.time()
    elapsed = 0

    while elapsed < timeout:
        try:
            # Poll order status with retry
            data = _poll_once()

            status = data.get('status')

            if status == 'SETTLED':
                # Order is settled, get outcome
                outcome = data.get('outcome')

                if outcome not in ['WIN', 'LOSS']:
                    raise ExecutionError(
                        f"Invalid outcome value: {outcome}"
                    )

                logger.info(
                    f"Order settled: order_id={order_id}, "
                    f"outcome={outcome}, elapsed={elapsed:.1f}s"
                )
                return outcome

            elif status == 'PENDING':
                # Still pending, continue polling
                logger.debug(
                    f"Order still pending: order_id={order_id}, "
                    f"elapsed={elapsed:.1f}s"
                )

            else:
                # Unexpected status
                raise ExecutionError(
                    f"Unexpected order status: {status}"
                )

        except (RetryError, TerminalExecutionError) as e:
            # Fatal error during polling
            logger.error(f"Fatal error during polling: {e}")
            raise ExecutionError(f"Polling failed: {e}") from e

        # Wait before next poll
        time.sleep(poll_interval)
        elapsed = time.time() - start_time

    # Timeout reached
    raise ExecutionError(
        f"Settlement polling timed out after {timeout}s for order_id={order_id}"
    )


def get_order_status(
    order_id: str,
    config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Get the current status of an order from the Polymarket API.

    This is a simple wrapper around a single status check without polling logic.
    Use poll_settlement() if you need to wait for settlement.

    Args:
        order_id: The order ID to check
        config: Optional configuration instance (uses global config if None)

    Returns:
        Dictionary containing order status information

    Raises:
        ValidationError: If order_id is invalid
        ExecutionError: If the API request fails
        RetryError: If all retry attempts are exhausted

    Example:
        status = get_order_status("order_123")
        print(f"Order status: {status['status']}")
    """
    # Load configuration
    if config is None:
        config = get_config()

    # Validate inputs
    if not order_id or not isinstance(order_id, str):
        raise ValidationError("order_id must be a non-empty string")

    # Create retry decorator
    @retry_with_backoff(
        max_attempts=config.max_retries,
        base_delay=config.initial_delay,
        max_delay=config.max_delay,
        exponential_base=config.backoff_multiplier,
        exceptions=(RetryableExecutionError, requests.RequestException),
        logger_name=__name__
    )
    def _get_status_with_retry():
        """Internal function that performs the actual API call."""
        try:
            url = f"{config.polymarket_base_url}/orders/{order_id}"
            headers = {
                "Authorization": f"Bearer {config.polymarket_api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=30.0
            )

            response.raise_for_status()
            return response.json()

        except requests.HTTPError as e:
            if _is_retryable_error(e):
                raise RetryableExecutionError(f"HTTP error: {e}") from e
            else:
                raise TerminalExecutionError(f"HTTP error: {e}") from e

        except requests.RequestException as e:
            raise RetryableExecutionError(f"Network error: {e}") from e

        except Exception as e:
            raise TerminalExecutionError(f"Unexpected error: {e}") from e

    # Execute with retry
    try:
        return _get_status_with_retry()
    except RetryError as e:
        logger.error(f"Failed to get order status after all retries: {e}")
        raise ExecutionError(f"Failed to get order status: {e}") from e
    except TerminalExecutionError as e:
        raise ExecutionError(f"Failed to get order status: {e}") from e
