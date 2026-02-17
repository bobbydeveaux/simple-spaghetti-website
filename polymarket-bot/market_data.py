"""
Market Data Service for Polymarket Bot.

This module provides real-time market data integration including:
- Polymarket API client for market discovery and odds retrieval
- BTC-related market filtering
- Real-time market data fetching with retry logic
- Market metadata and pricing data management
- Binance WebSocket client for real-time BTC/USDT price feed with BTCPriceData model
- Technical indicator calculations (RSI, MACD)
- Order book imbalance metrics

The service manages WebSocket connections with automatic reconnection logic,
provides fallback mechanisms for data retrieval, and handles API interactions
with retry logic and error handling.
"""

import json
import time
import logging
import requests
import threading
from typing import List, Dict, Any, Optional, Callable, Tuple
from decimal import Decimal
from threading import Thread, Lock
from collections import deque
from datetime import datetime, timezone
import numpy as np
import talib
import websocket
from websocket import WebSocketApp, WebSocketConnectionClosedException

from .config import Config, get_config
from .models import MarketData, OutcomeType, BTCPriceData
from .utils import (
    retry_with_backoff,
    validate_non_empty,
    validate_probability,
    ValidationError,
    RetryError
)


# Setup logging
logger = logging.getLogger(__name__)


class PolymarketAPIError(Exception):
    """Exception raised for Polymarket API errors."""
    pass


class BinanceWebSocketClient:
    """
    WebSocket client for streaming real-time BTC/USDT prices from Binance.

    Manages WebSocket connection, maintains a rolling buffer of prices for
    technical indicator calculation, and provides automatic reconnection
    on network failures.
    """

    def __init__(self, buffer_size: int = 100):
        """
        Initialize the Binance WebSocket client.

        Args:
            buffer_size: Maximum number of price points to keep in memory
        """
        self.config = get_config()
        self.ws_url = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
        self.buffer_size = buffer_size
        self.price_buffer: deque = deque(maxlen=buffer_size)
        self.ws: Optional[WebSocketApp] = None
        self.ws_thread: Optional[Thread] = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.lock = Lock()

        logger.info(f"Initialized BinanceWebSocketClient with buffer_size={buffer_size}")

    def connect(self) -> None:
        """
        Establish WebSocket connection to Binance.

        Starts a background thread to handle WebSocket messages.
        Implements automatic reconnection logic on failures.
        """
        if self.is_connected:
            logger.warning("WebSocket already connected")
            return

        logger.info(f"Connecting to Binance WebSocket: {self.ws_url}")

        self.ws = WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        # Run WebSocket in a separate thread
        self.ws_thread = Thread(target=self.ws.run_forever, daemon=True)
        self.ws_thread.start()

        # Wait for connection to establish with proper synchronization
        timeout = 10
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.lock:
                if self.is_connected:
                    return
            time.sleep(0.1)

        # Check one final time after timeout
        with self.lock:
            if not self.is_connected:
                raise ConnectionError("Failed to connect to Binance WebSocket within timeout")

    def _on_open(self, ws) -> None:
        """Handle WebSocket connection opened."""
        with self.lock:
            self.is_connected = True
            self.reconnect_attempts = 0
        logger.info("Binance WebSocket connection established")

    def _on_message(self, ws, message: str) -> None:
        """
        Handle incoming WebSocket messages.

        Args:
            ws: WebSocket instance
            message: JSON message string from Binance
        """
        try:
            data = json.loads(message)

            # Extract close price from kline data
            if 'k' in data:
                close_price = float(data['k']['c'])

                with self.lock:
                    self.price_buffer.append(close_price)

                logger.debug(f"Received BTC price: {close_price:.2f} (buffer size: {len(self.price_buffer)})")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing WebSocket message: {e}")

    def _on_error(self, ws, error) -> None:
        """Handle WebSocket errors."""
        logger.error(f"Binance WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """
        Handle WebSocket connection closed.

        Implements automatic reconnection logic with exponential backoff.
        """
        with self.lock:
            self.is_connected = False
            current_attempts = self.reconnect_attempts

        logger.warning(f"Binance WebSocket closed: {close_status_code} - {close_msg}")

        # Attempt reconnection if within retry limit
        if current_attempts < self.config.ws_max_reconnect_attempts:
            with self.lock:
                self.reconnect_attempts += 1
                next_attempt = self.reconnect_attempts
            delay = min(self.config.ws_reconnect_delay * (2 ** (next_attempt - 1)), 60)

            logger.info(f"Attempting reconnection {next_attempt}/{self.config.ws_max_reconnect_attempts} in {delay}s")

            # Schedule reconnection in a separate thread to avoid blocking
            def delayed_reconnect():
                time.sleep(delay)
                try:
                    self.connect()
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")

            reconnect_thread = Thread(target=delayed_reconnect, daemon=True)
            reconnect_thread.start()
        else:
            logger.error(f"Max reconnection attempts ({self.config.ws_max_reconnect_attempts}) reached")

    def get_latest_prices(self, count: int = 100) -> List[float]:
        """
        Get the most recent prices from the buffer.

        Args:
            count: Number of recent prices to retrieve

        Returns:
            List of prices (oldest to newest)
        """
        with self.lock:
            prices = list(self.price_buffer)

        # Return up to 'count' most recent prices
        return prices[-count:] if len(prices) >= count else prices

    def get_latest_price(self) -> Optional[float]:
        """
        Get the most recent price.

        Returns:
            Latest BTC price or None if buffer is empty
        """
        with self.lock:
            if len(self.price_buffer) > 0:
                return self.price_buffer[-1]
        return None

    def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        logger.info("Closing Binance WebSocket connection")
        self.is_connected = False

        if self.ws:
            self.ws.close()

        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=2)


class PolymarketClient:
    """
    Client for interacting with the Polymarket API.

    Provides methods for discovering active markets, fetching market odds,
    and filtering BTC-related prediction markets.
    """

    def __init__(self, config: Config):
        """
        Initialize the Polymarket API client.

        Args:
            config: Configuration object containing API credentials and base URL
        """
        self.config = config
        self.base_url = config.polymarket_base_url
        self.api_key = config.polymarket_api_key
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        logger.info(f"Initialized PolymarketClient with base URL: {self.base_url}")

    @retry_with_backoff(max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,))
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Polymarket API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data

        Returns:
            JSON response from the API

        Raises:
            PolymarketAPIError: If the API request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
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
            raise PolymarketAPIError(error_msg) from e

        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            raise PolymarketAPIError(error_msg) from e

        except ValueError as e:
            error_msg = f"Invalid JSON response: {str(e)}"
            logger.error(error_msg)
            raise PolymarketAPIError(error_msg) from e

    def get_active_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        closed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch active markets from Polymarket.

        Args:
            limit: Maximum number of markets to retrieve (default: 100)
            offset: Number of markets to skip (default: 0)
            closed: Whether to include closed markets (default: False)

        Returns:
            List of market data dictionaries

        Raises:
            PolymarketAPIError: If the API request fails
        """
        endpoint = "/markets"
        params = {
            "limit": limit,
            "offset": offset,
            "closed": "true" if closed else "false"
        }

        logger.info(f"Fetching active markets (limit={limit}, offset={offset})")

        response = self._make_request("GET", endpoint, params=params)

        # Handle different response formats
        markets = response if isinstance(response, list) else response.get('markets', [])

        logger.info(f"Retrieved {len(markets)} markets from Polymarket")

        return markets

    def get_market_by_id(self, market_id: str) -> Dict[str, Any]:
        """
        Fetch a specific market by ID.

        Args:
            market_id: Unique market identifier

        Returns:
            Market data dictionary

        Raises:
            PolymarketAPIError: If the API request fails
            ValidationError: If market_id is invalid
        """
        validate_non_empty(market_id, "market_id")

        endpoint = f"/markets/{market_id}"

        logger.info(f"Fetching market {market_id}")

        return self._make_request("GET", endpoint)

    def search_markets(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for markets matching a query string.

        Args:
            query: Search query string
            limit: Maximum number of results (default: 50)

        Returns:
            List of matching market data dictionaries

        Raises:
            PolymarketAPIError: If the API request fails
            ValidationError: If query is empty
        """
        validate_non_empty(query, "query")

        endpoint = "/markets"
        params = {
            "query": query,
            "limit": limit
        }

        logger.info(f"Searching markets with query: '{query}'")

        response = self._make_request("GET", endpoint, params=params)

        markets = response if isinstance(response, list) else response.get('markets', [])

        logger.info(f"Found {len(markets)} markets matching '{query}'")

        return markets

    def get_btc_markets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch BTC-related prediction markets.

        Searches for markets containing Bitcoin-related keywords and filters
        for active markets with sufficient liquidity.

        Args:
            limit: Maximum number of markets to retrieve (default: 50)

        Returns:
            List of BTC-related market data dictionaries

        Raises:
            PolymarketAPIError: If the API request fails
        """
        # Search terms for BTC-related markets
        btc_keywords = ["BTC", "Bitcoin", "bitcoin"]

        all_markets = []
        seen_ids = set()

        for keyword in btc_keywords:
            try:
                markets = self.search_markets(keyword, limit=limit)

                # Add unique markets
                for market in markets:
                    market_id = market.get('id') or market.get('market_id')
                    if market_id and market_id not in seen_ids:
                        all_markets.append(market)
                        seen_ids.add(market_id)

            except PolymarketAPIError as e:
                logger.warning(f"Failed to search for '{keyword}': {e}")
                continue

        # Filter for active markets
        active_btc_markets = [
            market for market in all_markets
            if self._is_market_active(market)
        ]

        logger.info(f"Found {len(active_btc_markets)} active BTC-related markets")

        return active_btc_markets[:limit]

    def _is_market_active(self, market: Dict[str, Any]) -> bool:
        """
        Check if a market is active for trading.

        Args:
            market: Market data dictionary

        Returns:
            True if market is active, False otherwise
        """
        # Check if market is explicitly closed
        if market.get('closed') or market.get('is_closed'):
            return False

        # Check if market is active
        if not market.get('active', True) and not market.get('is_active', True):
            return False

        # Check if market has ended
        end_date_str = market.get('end_date') or market.get('end_time')
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                if end_date < datetime.now(end_date.tzinfo):
                    return False
            except (ValueError, AttributeError):
                # If we can't parse the date, assume it's active
                pass

        return True

    def parse_market_data(self, market: Dict[str, Any]) -> MarketData:
        """
        Parse raw market data from API into MarketData model.

        Args:
            market: Raw market data dictionary from API

        Returns:
            MarketData model instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        # Extract market ID
        market_id = market.get('id') or market.get('market_id') or market.get('marketId')
        if not market_id:
            raise ValidationError("Market data missing 'id' field")

        # Extract question/title
        question = (
            market.get('question') or
            market.get('title') or
            market.get('description', 'Unknown Market')
        )

        # Extract prices (probabilities)
        yes_price = self._extract_price(market, 'yes')
        no_price = self._extract_price(market, 'no')

        # Ensure prices sum to approximately 1.0
        if yes_price and no_price:
            total = yes_price + no_price
            if abs(total - Decimal("1.0")) > Decimal("0.05"):
                logger.warning(
                    f"Market {market_id} prices don't sum to 1.0: "
                    f"yes={yes_price}, no={no_price}, total={total}"
                )

        # Extract volumes
        yes_volume = self._extract_volume(market, 'yes')
        no_volume = self._extract_volume(market, 'no')

        # Extract liquidity
        liquidity = Decimal(str(market.get('liquidity', 0)))

        # Extract dates
        created_date = self._parse_datetime(
            market.get('created_at') or market.get('creation_date'),
            datetime.now(timezone.utc)
        )

        end_date = self._parse_datetime(
            market.get('end_date') or market.get('end_time'),
            datetime.now(timezone.utc)
        )

        # Extract market status
        is_active = self._is_market_active(market)
        is_closed = market.get('closed', False) or market.get('is_closed', False)

        # Extract resolution if available
        resolution = None
        if market.get('resolved'):
            resolution_str = market.get('resolution') or market.get('winning_outcome')
            if resolution_str:
                resolution = (
                    OutcomeType.YES if resolution_str.lower() == 'yes'
                    else OutcomeType.NO if resolution_str.lower() == 'no'
                    else None
                )

        # Extract metadata
        category = market.get('category')
        tags = market.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]

        description = market.get('description')

        return MarketData(
            market_id=str(market_id),
            question=question,
            description=description,
            created_date=created_date,
            end_date=end_date,
            yes_price=yes_price,
            no_price=no_price,
            yes_volume=yes_volume,
            no_volume=no_volume,
            total_liquidity=liquidity,
            is_active=is_active,
            is_closed=is_closed,
            resolution=resolution,
            category=category,
            tags=tags,
            metadata=market
        )

    def _extract_price(self, market: Dict[str, Any], outcome: str) -> Decimal:
        """Extract price for a specific outcome from market data."""
        price_key = f"{outcome}_price"
        price = market.get(price_key) or market.get(f"{outcome}Price")

        # Try nested structure
        if price is None and 'prices' in market:
            price = market['prices'].get(outcome)

        # Try outcomes array
        if price is None and 'outcomes' in market:
            for outcome_data in market['outcomes']:
                if outcome_data.get('name', '').lower() == outcome.lower():
                    price = outcome_data.get('price')
                    break

        if price is None:
            # Default to 0.5 if not found
            logger.warning(f"Could not find {outcome} price in market data, defaulting to 0.5")
            price = 0.5

        return Decimal(str(price))

    def _extract_volume(self, market: Dict[str, Any], outcome: str) -> Decimal:
        """Extract volume for a specific outcome from market data."""
        volume_key = f"{outcome}_volume"
        volume = market.get(volume_key) or market.get(f"{outcome}Volume")

        # Try nested structure
        if volume is None and 'volumes' in market:
            volume = market['volumes'].get(outcome)

        # Try outcomes array
        if volume is None and 'outcomes' in market:
            for outcome_data in market['outcomes']:
                if outcome_data.get('name', '').lower() == outcome.lower():
                    volume = outcome_data.get('volume')
                    break

        if volume is None:
            volume = 0

        return Decimal(str(volume))

    def _parse_datetime(self, date_str: Optional[str], default: datetime) -> datetime:
        """Parse datetime string from API response."""
        if not date_str:
            return default

        try:
            # Try ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try timestamp
                return datetime.fromtimestamp(float(date_str))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse datetime: {date_str}")
                return default

    def get_market_odds(self, market_id: str) -> tuple[Decimal, Decimal]:
        """
        Get current YES/NO odds for a specific market.

        Args:
            market_id: Unique market identifier

        Returns:
            Tuple of (yes_price, no_price) as Decimal values

        Raises:
            PolymarketAPIError: If the API request fails
            ValidationError: If market_id is invalid
        """
        market = self.get_market_by_id(market_id)
        market_data = self.parse_market_data(market)

        return (market_data.yes_price, market_data.no_price)

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("Closed PolymarketClient session")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class BinanceWebSocketError(Exception):
    """Exception raised for Binance WebSocket errors."""
    pass


class BinanceWebSocket:
    """
    WebSocket client for Binance BTC/USDT price feed.

    Connects to Binance WebSocket API to receive real-time BTC/USDT price updates.
    Implements automatic reconnection logic and maintains a history of recent prices
    for technical indicator calculations.
    """

    # Binance WebSocket endpoints
    STREAM_URL = "wss://stream.binance.com:9443/ws"
    TICKER_STREAM = "btcusdt@ticker"

    def __init__(
        self,
        on_price_update: Optional[Callable[[BTCPriceData], None]] = None,
        history_size: int = 200
    ):
        """
        Initialize Binance WebSocket client.

        Args:
            on_price_update: Optional callback function to call on each price update
            history_size: Number of recent price updates to keep in history (default: 200)
        """
        self.on_price_update = on_price_update
        self.history_size = history_size

        # Price data storage
        self.latest_price: Optional[BTCPriceData] = None
        self.price_history: deque = deque(maxlen=history_size)

        # WebSocket connection
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.is_connected: bool = False
        self.should_reconnect: bool = True
        self.reconnect_delay: int = 5  # seconds

        # Connection tracking
        self.connection_errors: int = 0
        self.last_message_time: Optional[datetime] = None

        logger.info(f"Initialized BinanceWebSocket with history size {history_size}")

    def connect(self) -> None:
        """
        Connect to Binance WebSocket and start receiving price updates.

        Starts the WebSocket connection in a background thread. Will automatically
        reconnect on disconnection unless explicitly stopped.
        """
        if self.is_connected:
            logger.warning("WebSocket is already connected")
            return

        self.should_reconnect = True
        self._start_websocket()

        logger.info("Started Binance WebSocket connection")

    def _start_websocket(self) -> None:
        """Start the WebSocket connection in a background thread."""
        url = f"{self.STREAM_URL}/{self.TICKER_STREAM}"

        self.ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        # Run WebSocket in background thread
        self.ws_thread = threading.Thread(
            target=self._run_websocket,
            daemon=True,
            name="BinanceWebSocketThread"
        )
        self.ws_thread.start()

    def _run_websocket(self) -> None:
        """Run the WebSocket connection with automatic reconnection."""
        while self.should_reconnect:
            try:
                logger.info("Connecting to Binance WebSocket...")
                self.ws.run_forever()

                # If we get here, connection was closed
                if self.should_reconnect:
                    logger.warning(
                        f"WebSocket disconnected. Reconnecting in {self.reconnect_delay}s..."
                    )
                    time.sleep(self.reconnect_delay)
                    self._start_websocket()
                    break

            except Exception as e:
                self.connection_errors += 1
                logger.error(f"WebSocket error: {e}")

                if self.should_reconnect:
                    # Exponential backoff for reconnection
                    delay = min(self.reconnect_delay * (2 ** min(self.connection_errors - 1, 5)), 300)
                    logger.warning(f"Reconnecting in {delay}s (attempt {self.connection_errors})...")
                    time.sleep(delay)
                else:
                    break

    def _on_open(self, ws) -> None:
        """WebSocket connection opened callback."""
        self.is_connected = True
        self.connection_errors = 0
        logger.info("WebSocket connection established")

    def _on_message(self, ws, message: str) -> None:
        """
        WebSocket message received callback.

        Args:
            ws: WebSocket instance
            message: JSON message from Binance
        """
        try:
            self.last_message_time = datetime.now(timezone.utc)
            data = json.loads(message)

            # Parse Binance ticker data
            price_data = self._parse_ticker_data(data)

            # Update latest price and history
            self.latest_price = price_data
            self.price_history.append(price_data)

            # Call user callback if provided
            if self.on_price_update:
                try:
                    self.on_price_update(price_data)
                except Exception as e:
                    logger.error(f"Error in price update callback: {e}")

            logger.debug(f"BTC price update: {price_data.price} USDT")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    def _on_error(self, ws, error) -> None:
        """
        WebSocket error callback.

        Args:
            ws: WebSocket instance
            error: Error that occurred
        """
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """
        WebSocket connection closed callback.

        Args:
            ws: WebSocket instance
            close_status_code: Close status code
            close_msg: Close message
        """
        self.is_connected = False
        logger.info(f"WebSocket connection closed (code: {close_status_code}, msg: {close_msg})")

    def _parse_ticker_data(self, data: Dict[str, Any]) -> BTCPriceData:
        """
        Parse Binance ticker data into BTCPriceData model.

        Args:
            data: Raw ticker data from Binance WebSocket

        Returns:
            BTCPriceData model instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        try:
            # Extract price data from Binance 24hr ticker format
            # Reference: https://binance-docs.github.io/apidocs/spot/en/#individual-symbol-ticker-streams
            price = Decimal(str(data.get('c', data.get('lastPrice', 0))))
            timestamp = datetime.fromtimestamp(int(data.get('E', 0)) / 1000)

            # 24-hour statistics
            volume_24h = data.get('q', data.get('quoteVolume'))
            high_24h = data.get('h', data.get('highPrice'))
            low_24h = data.get('l', data.get('lowPrice'))
            price_change_24h = data.get('p', data.get('priceChange'))
            price_change_percent_24h = data.get('P', data.get('priceChangePercent'))

            return BTCPriceData(
                symbol=data.get('s', 'BTCUSDT'),
                price=price,
                timestamp=timestamp if timestamp.year > 1970 else datetime.now(timezone.utc),
                volume_24h=Decimal(str(volume_24h)) if volume_24h else None,
                high_24h=Decimal(str(high_24h)) if high_24h else None,
                low_24h=Decimal(str(low_24h)) if low_24h else None,
                price_change_24h=Decimal(str(price_change_24h)) if price_change_24h else None,
                price_change_percent_24h=Decimal(str(price_change_percent_24h)) if price_change_percent_24h else None,
                metadata=data
            )

        except (KeyError, ValueError, TypeError) as e:
            raise ValidationError(f"Failed to parse Binance ticker data: {e}")

    def get_latest_price(self) -> Optional[BTCPriceData]:
        """
        Get the most recent BTC price update.

        Returns:
            Latest BTCPriceData or None if no data received yet
        """
        return self.latest_price

    def get_price_history(self, limit: Optional[int] = None) -> List[BTCPriceData]:
        """
        Get historical price data.

        Args:
            limit: Maximum number of price updates to return (default: all)

        Returns:
            List of BTCPriceData in chronological order
        """
        history = list(self.price_history)

        if limit and limit < len(history):
            return history[-limit:]

        return history

    def get_price_series(self, limit: Optional[int] = None) -> List[Decimal]:
        """
        Get price series as list of Decimal values.

        Args:
            limit: Maximum number of prices to return (default: all)

        Returns:
            List of price values in chronological order
        """
        history = self.get_price_history(limit)
        return [price_data.price for price_data in history]

    def is_healthy(self, max_message_age_seconds: int = 60) -> bool:
        """
        Check if WebSocket connection is healthy.

        Args:
            max_message_age_seconds: Maximum age of last message in seconds (default: 60)

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.is_connected:
            return False

        if not self.last_message_time:
            return False

        # Check if we've received a message recently
        age = (datetime.now(timezone.utc) - self.last_message_time).total_seconds()
        return age < max_message_age_seconds

    def disconnect(self) -> None:
        """
        Disconnect from WebSocket and stop reconnection attempts.

        Gracefully closes the WebSocket connection and stops the background thread.
        """
        logger.info("Disconnecting from Binance WebSocket...")

        self.should_reconnect = False
        self.is_connected = False

        if self.ws:
            self.ws.close()

        # Wait for thread to finish (with timeout)
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)

        logger.info("Disconnected from Binance WebSocket")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index (RSI) technical indicator.

    RSI is a momentum oscillator that measures the speed and magnitude
    of price changes. Values range from 0 to 100.
    - RSI > 70: Overbought condition
    - RSI < 30: Oversold condition

    Args:
        prices: List of price values (oldest to newest)
        period: RSI calculation period (default: 14)

    Returns:
        RSI value (0-100)

    Raises:
        ValueError: If insufficient price data
    """
    if len(prices) < period + 1:
        raise ValueError(f"Insufficient price data for RSI calculation. Need at least {period + 1} prices, got {len(prices)}")

    # Convert to numpy array for TA-Lib
    prices_array = np.array(prices, dtype=float)

    # Calculate RSI using TA-Lib
    rsi_values = talib.RSI(prices_array, timeperiod=period)

    # Return the most recent RSI value
    current_rsi = float(rsi_values[-1])

    logger.debug(f"Calculated RSI({period}): {current_rsi:.2f}")

    return current_rsi


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[float, float]:
    """
    Calculate MACD (Moving Average Convergence Divergence) indicator.

    MACD is a trend-following momentum indicator showing the relationship
    between two moving averages of prices.

    Args:
        prices: List of price values (oldest to newest)
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)

    Returns:
        Tuple of (macd_line, signal_line)
        - macd_line: MACD line value
        - signal_line: Signal line value
        - Crossover (MACD > signal) suggests bullish momentum
        - Crossover (MACD < signal) suggests bearish momentum

    Raises:
        ValueError: If insufficient price data
    """
    min_prices = slow_period + signal_period - 1
    if len(prices) < min_prices:
        raise ValueError(
            f"Insufficient price data for MACD calculation. "
            f"Need at least {min_prices} prices, got {len(prices)}"
        )

    # Convert to numpy array for TA-Lib
    prices_array = np.array(prices, dtype=float)

    # Calculate MACD using TA-Lib with configured periods
    macd_line, signal_line, _ = talib.MACD(
        prices_array,
        fastperiod=fast_period,
        slowperiod=slow_period,
        signalperiod=signal_period
    )

    # Return the most recent values
    current_macd = float(macd_line[-1])
    current_signal = float(signal_line[-1])

    logger.debug(
        f"Calculated MACD({fast_period},{slow_period},{signal_period}): "
        f"{current_macd:.2f}, Signal: {current_signal:.2f}"
    )

    return current_macd, current_signal


def get_order_book_imbalance() -> float:
    """
    Calculate order book imbalance from Binance order book.

    Order book imbalance measures the ratio of bid volume to ask volume,
    indicating buying vs selling pressure.
    - Imbalance > 1.0: More buying pressure
    - Imbalance < 1.0: More selling pressure

    Returns:
        Order book imbalance ratio (bid_volume / ask_volume)

    Raises:
        ConnectionError: If unable to fetch order book data
    """
    config = get_config()

    try:
        # Fetch order book from Binance REST API
        response = requests.get(
            f"{config.binance_base_url}/api/v3/depth",
            params={'symbol': 'BTCUSDT', 'limit': 10},
            timeout=5
        )
        response.raise_for_status()

        data = response.json()

        # Calculate total bid and ask volumes
        bids = data.get('bids', [])
        asks = data.get('asks', [])

        bid_volume = sum(float(bid[1]) for bid in bids)
        ask_volume = sum(float(ask[1]) for ask in asks)

        if ask_volume == 0:
            logger.warning("Ask volume is zero, returning neutral imbalance")
            return 1.0

        imbalance = bid_volume / ask_volume

        logger.debug(f"Order book imbalance: {imbalance:.4f} (bid: {bid_volume:.2f}, ask: {ask_volume:.2f})")

        return imbalance

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching order book: {e}")
        raise ConnectionError(f"Failed to fetch order book data: {e}")


def get_market_data(
    binance_client: BinanceWebSocketClient,
    polymarket_client: PolymarketClient,
    market_id: Optional[str] = None
) -> MarketData:
    """
    Aggregate market data from multiple sources.

    Combines real-time BTC prices, technical indicators, and Polymarket
    odds into a single MarketData object for strategy evaluation.

    Args:
        binance_client: Connected Binance WebSocket client
        polymarket_client: Initialized Polymarket API client
        market_id: Optional specific market ID (will search if not provided)

    Returns:
        MarketData object with all aggregated data

    Raises:
        ValueError: If insufficient data or market not available
    """
    logger.info("Aggregating market data from all sources")

    # Get configuration for indicator parameters
    config = get_config()

    # Get price data from Binance
    prices = binance_client.get_latest_prices(100)

    # Calculate minimum required prices based on MACD configuration
    min_prices = config.macd_slow_period + config.macd_signal_period - 1
    if len(prices) < min_prices:
        raise ValueError(
            f"Insufficient price data for indicators. "
            f"Need at least {min_prices}, got {len(prices)}"
        )

    latest_price = prices[-1]

    # Calculate technical indicators with configured parameters
    try:
        rsi_value = calculate_rsi(prices, period=config.rsi_period)
        macd_line, macd_signal = calculate_macd(
            prices,
            fast_period=config.macd_fast_period,
            slow_period=config.macd_slow_period,
            signal_period=config.macd_signal_period
        )
        order_book_imb = get_order_book_imbalance()
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        raise ValueError(f"Failed to calculate technical indicators: {e}")

    # Get Polymarket market and odds
    if market_id is None:
        # Search for active BTC markets
        btc_markets = polymarket_client.get_btc_markets(limit=10)
        if not btc_markets:
            raise ValueError("No active Polymarket markets found")
        # Use the first active market
        market_raw = btc_markets[0]
        market_data = polymarket_client.parse_market_data(market_raw)
        market_id = market_data.market_id
    else:
        # Get specific market
        try:
            yes_price, no_price = polymarket_client.get_market_odds(market_id)
            # Get full market data for additional fields
            market_raw = polymarket_client.get_market_by_id(market_id)
            market_data = polymarket_client.parse_market_data(market_raw)
        except Exception as e:
            logger.error(f"Error fetching Polymarket odds: {e}")
            raise ValueError(f"Failed to fetch market odds: {e}")

    # Add metadata with technical analysis
    market_data.metadata = market_data.metadata or {}
    market_data.metadata.update({
        'btc_price': latest_price,
        'rsi_14': rsi_value,
        'macd_line': macd_line,
        'macd_signal': macd_signal,
        'order_book_imbalance': order_book_imb,
        'price_buffer_size': len(prices)
    })

    logger.info(
        f"Market data aggregated - BTC: ${latest_price:.2f}, "
        f"RSI: {rsi_value:.2f}, MACD: {macd_line:.2f}/{macd_signal:.2f}, "
        f"OB Imbalance: {order_book_imb:.4f}"
    )

    return market_data


def get_fallback_btc_price() -> float:
    """
    Fallback method to get BTC price from CoinGecko API.

    Used when Binance WebSocket is unavailable or disconnected.

    Returns:
        Current BTC price in USD

    Raises:
        ConnectionError: If unable to fetch price
    """
    config = get_config()

    try:
        logger.info("Fetching BTC price from CoinGecko fallback")

        response = requests.get(
            f"{config.coingecko_base_url}/simple/price",
            params={'ids': 'bitcoin', 'vs_currencies': 'usd'},
            headers={'x-cg-demo-api-key': config.coingecko_api_key},
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        price = float(data['bitcoin']['usd'])

        logger.info(f"CoinGecko BTC price: ${price:.2f}")

        return price

    except requests.exceptions.RequestException as e:
        logger.error(f"CoinGecko fallback failed: {e}")
        raise ConnectionError(f"Failed to fetch BTC price from CoinGecko: {e}")
