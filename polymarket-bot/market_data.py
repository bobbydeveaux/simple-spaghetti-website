"""
Market Data Service for Polymarket Bot.

This module provides market data integration from multiple sources:
- PolymarketClient: REST API wrapper for market discovery and odds fetching
- BinanceWebSocketClient: Real-time BTC price from Binance WebSocket
- Technical indicator calculations (RSI, MACD)
- Order book imbalance calculations

All API calls include retry logic with exponential backoff for reliability.
"""

import json
import logging
import time
import hmac
import hashlib
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
import requests
from websocket import WebSocketApp, WebSocketException
import threading
from collections import deque

from .models import MarketData, OutcomeType
from .utils import retry_with_backoff, validate_probability, validate_non_empty, RetryError
from .config import Config

# Configure module logger
logger = logging.getLogger(__name__)


class PolymarketAPIError(Exception):
    """Exception raised for Polymarket API errors."""
    pass


class BinanceAPIError(Exception):
    """Exception raised for Binance API errors."""
    pass


class PolymarketClient:
    """
    REST API wrapper for Polymarket market discovery and odds fetching.

    Provides methods to:
    - Discover active BTC-related prediction markets
    - Retrieve current odds for Yes/No positions
    - Handle API rate limiting with exponential backoff
    - Transform API responses into internal MarketData models
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.polymarket.com"):
        """
        Initialize Polymarket API client.

        Args:
            api_key: Polymarket API key for authentication
            api_secret: Polymarket API secret for signing requests with HMAC-SHA256
            base_url: Base URL for Polymarket API (default: https://api.polymarket.com)

        Raises:
            ValueError: If api_key or api_secret is empty
        """
        validate_non_empty(api_key, "api_key")
        validate_non_empty(api_secret, "api_secret")

        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')

        # Create a session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "PolymarketBot/1.0"
        })

        logger.info(f"PolymarketClient initialized with base_url: {self.base_url}")

    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """
        Generate HMAC-SHA256 signature for request authentication.

        Args:
            timestamp: Request timestamp in milliseconds
            method: HTTP method (GET, POST, etc.)
            path: Request path (e.g., "/markets")
            body: Request body as JSON string (empty for GET requests)

        Returns:
            Hexadecimal signature string
        """
        # Create the message to sign: timestamp + method + path + body
        message = f"{timestamp}{method}{path}{body}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _prepare_authenticated_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """
        Prepare headers with HMAC-SHA256 authentication.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            body: Request body as JSON string

        Returns:
            Dictionary of headers including authentication
        """
        # Generate timestamp in milliseconds
        timestamp = str(int(time.time() * 1000))

        # Generate signature
        signature = self._generate_signature(timestamp, method, path, body)

        # Return headers with authentication
        return {
            "X-API-KEY": self.api_key,
            "X-SIGNATURE": signature,
            "X-TIMESTAMP": timestamp
        }

    @retry_with_backoff(
        max_attempts=3,
        base_delay=2.0,
        max_delay=10.0,
        exponential_base=2.0,
        exceptions=(requests.RequestException, PolymarketAPIError),
        logger_name=__name__
    )
    def find_active_market(self, asset: str = "BTC") -> Optional[str]:
        """
        Find an active BTC prediction market.

        Queries the Polymarket API for active markets related to the specified asset.
        Returns the market ID of the next settling market.

        Args:
            asset: Asset symbol to search for (default: "BTC")

        Returns:
            Market ID string if an active market is found, None otherwise

        Raises:
            PolymarketAPIError: If the API request fails
            RetryError: If all retry attempts are exhausted

        Example:
            market_id = client.find_active_market("BTC")
            if market_id:
                print(f"Found active market: {market_id}")
        """
        path = "/markets"
        endpoint = f"{self.base_url}{path}"
        params = {
            "asset": asset,
            "status": "active",
            "limit": 10
        }

        try:
            logger.debug(f"Searching for active {asset} markets")
            # Prepare authenticated headers
            auth_headers = self._prepare_authenticated_headers("GET", path)
            response = self.session.get(endpoint, params=params, headers=auth_headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            markets = data.get("markets", [])

            if not markets:
                logger.info(f"No active {asset} markets found")
                return None

            # Return the first active market (would be sorted by settlement time)
            market_id = markets[0].get("market_id")
            logger.info(f"Found active market: {market_id}")
            return market_id

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"No markets endpoint found: {e}")
                return None
            elif e.response.status_code == 429:
                raise PolymarketAPIError(f"Rate limit exceeded: {e}")
            else:
                raise PolymarketAPIError(f"HTTP error occurred: {e}")
        except requests.RequestException as e:
            raise PolymarketAPIError(f"Request failed: {e}")
        except (KeyError, ValueError) as e:
            raise PolymarketAPIError(f"Invalid response format: {e}")

    @retry_with_backoff(
        max_attempts=3,
        base_delay=2.0,
        max_delay=10.0,
        exponential_base=2.0,
        exceptions=(requests.RequestException, PolymarketAPIError),
        logger_name=__name__
    )
    def get_market_odds(self, market_id: str) -> Tuple[Decimal, Decimal]:
        """
        Retrieve current odds for a specific market.

        Fetches the current YES and NO outcome prices (probabilities) for the
        specified market ID.

        Args:
            market_id: The Polymarket market identifier

        Returns:
            Tuple of (yes_odds, no_odds) as Decimal values (0.0 to 1.0)

        Raises:
            ValueError: If market_id is empty
            PolymarketAPIError: If the API request fails or returns invalid data
            RetryError: If all retry attempts are exhausted

        Example:
            yes_odds, no_odds = client.get_market_odds("market_123")
            print(f"YES: {yes_odds}, NO: {no_odds}")
        """
        validate_non_empty(market_id, "market_id")

        path = f"/markets/{market_id}"
        endpoint = f"{self.base_url}{path}"

        try:
            logger.debug(f"Fetching odds for market: {market_id}")
            # Prepare authenticated headers
            auth_headers = self._prepare_authenticated_headers("GET", path)
            response = self.session.get(endpoint, headers=auth_headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Extract odds from response
            yes_price = data.get("yes_price")
            no_price = data.get("no_price")

            if yes_price is None or no_price is None:
                raise PolymarketAPIError(
                    f"Missing price data in response for market {market_id}"
                )

            # Convert to Decimal for precision
            yes_odds = Decimal(str(yes_price))
            no_odds = Decimal(str(no_price))

            # Validate probabilities are in valid range
            validate_probability(yes_odds, "yes_odds")
            validate_probability(no_odds, "no_odds")

            logger.debug(f"Market {market_id} odds - YES: {yes_odds}, NO: {no_odds}")
            return yes_odds, no_odds

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise PolymarketAPIError(f"Market not found: {market_id}")
            elif e.response.status_code == 429:
                raise PolymarketAPIError(f"Rate limit exceeded: {e}")
            else:
                raise PolymarketAPIError(f"HTTP error occurred: {e}")
        except requests.RequestException as e:
            raise PolymarketAPIError(f"Request failed: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise PolymarketAPIError(f"Invalid response format: {e}")

    @retry_with_backoff(
        max_attempts=3,
        base_delay=2.0,
        max_delay=10.0,
        exponential_base=2.0,
        exceptions=(requests.RequestException, PolymarketAPIError),
        logger_name=__name__
    )
    def get_market_details(self, market_id: str) -> MarketData:
        """
        Fetch complete market details and transform into MarketData model.

        Retrieves all available information for a market and transforms it into
        the internal MarketData model for use by the trading bot.

        Args:
            market_id: The Polymarket market identifier

        Returns:
            MarketData object with market information and pricing

        Raises:
            ValueError: If market_id is empty
            PolymarketAPIError: If the API request fails or returns invalid data
            RetryError: If all retry attempts are exhausted

        Example:
            market_data = client.get_market_details("market_123")
            print(f"Question: {market_data.question}")
            print(f"YES price: {market_data.yes_price}")
        """
        validate_non_empty(market_id, "market_id")

        path = f"/markets/{market_id}"
        endpoint = f"{self.base_url}{path}"

        try:
            logger.debug(f"Fetching market details for: {market_id}")
            # Prepare authenticated headers
            auth_headers = self._prepare_authenticated_headers("GET", path)
            response = self.session.get(endpoint, headers=auth_headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Transform API response to MarketData model
            market_data = self._transform_to_market_data(data)
            logger.info(f"Successfully fetched market data for: {market_id}")
            return market_data

        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise PolymarketAPIError(f"Market not found: {market_id}")
            elif e.response.status_code == 429:
                raise PolymarketAPIError(f"Rate limit exceeded: {e}")
            else:
                raise PolymarketAPIError(f"HTTP error occurred: {e}")
        except requests.RequestException as e:
            raise PolymarketAPIError(f"Request failed: {e}")
        except (KeyError, ValueError, TypeError) as e:
            raise PolymarketAPIError(f"Invalid response format: {e}")

    def _transform_to_market_data(self, api_response: Dict[str, Any]) -> MarketData:
        """
        Transform Polymarket API response into MarketData model.

        Args:
            api_response: Raw API response dictionary

        Returns:
            MarketData object

        Raises:
            PolymarketAPIError: If required fields are missing or invalid
        """
        try:
            # Extract required fields
            market_id = api_response.get("market_id")
            question = api_response.get("question", api_response.get("title", "Unknown"))

            # Extract pricing data
            yes_price = Decimal(str(api_response.get("yes_price", 0.5)))
            no_price = Decimal(str(api_response.get("no_price", 0.5)))

            # Extract volume and liquidity
            yes_volume = Decimal(str(api_response.get("yes_volume", 0)))
            no_volume = Decimal(str(api_response.get("no_volume", 0)))
            total_liquidity = Decimal(str(api_response.get("liquidity", 0)))

            # Extract timestamps
            end_date_str = api_response.get("end_date", api_response.get("closing_time"))
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid timestamp format for end_date: {end_date_str}, error: {e}")
                    from datetime import timedelta, timezone
                    end_date = datetime.now(timezone.utc) + timedelta(hours=1)
            else:
                # Default to 1 hour from now if not provided
                from datetime import timedelta, timezone
                end_date = datetime.now(timezone.utc) + timedelta(hours=1)

            # Extract status
            is_active = api_response.get("is_active", True)
            is_closed = api_response.get("is_closed", False)

            # Extract optional fields
            description = api_response.get("description")
            category = api_response.get("category")
            tags = api_response.get("tags", [])

            # Create MarketData object
            return MarketData(
                market_id=market_id,
                question=question,
                description=description,
                end_date=end_date,
                yes_price=yes_price,
                no_price=no_price,
                yes_volume=yes_volume,
                no_volume=no_volume,
                total_liquidity=total_liquidity,
                is_active=is_active,
                is_closed=is_closed,
                category=category,
                tags=tags,
                metadata=api_response.get("metadata", {})
            )

        except (KeyError, ValueError, TypeError) as e:
            raise PolymarketAPIError(
                f"Failed to transform API response to MarketData: {e}"
            )

    def close(self):
        """Close the HTTP session and clean up resources."""
        self.session.close()
        logger.info("PolymarketClient session closed")


class BinanceWebSocketClient:
    """
    WebSocket client for real-time BTC price from Binance.

    Maintains a connection to Binance WebSocket API and buffers recent prices
    for technical indicator calculations.
    """

    def __init__(self, symbol: str = "btcusdt", buffer_size: int = 100):
        """
        Initialize Binance WebSocket client.

        Args:
            symbol: Trading pair symbol (default: "btcusdt")
            buffer_size: Number of recent prices to keep in buffer (default: 100)
        """
        self.symbol = symbol.lower()
        self.buffer_size = buffer_size
        # Use thread-safe deque for price buffer
        self.price_buffer: deque = deque(maxlen=buffer_size)
        self.ws_app: Optional[WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.is_connected = False
        self.buffer_lock = threading.Lock()

        # WebSocket endpoint for 1-minute klines
        self.ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_1m"

        logger.info(f"BinanceWebSocketClient initialized for {symbol}")

    def connect(self) -> None:
        """
        Establish WebSocket connection to Binance.

        Creates and starts the WebSocket connection in a background thread.
        This method is non-blocking and returns immediately after starting the thread.

        Raises:
            BinanceAPIError: If connection fails
        """
        try:
            self.ws_app = WebSocketApp(
                self.ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )

            logger.info(f"Connecting to Binance WebSocket: {self.ws_url}")

            # Start WebSocket in a background thread
            self.ws_thread = threading.Thread(
                target=self.ws_app.run_forever,
                daemon=True,
                name=f"BinanceWS-{self.symbol}"
            )
            self.ws_thread.start()

            logger.info(f"WebSocket thread started for {self.symbol}")

        except Exception as e:
            raise BinanceAPIError(f"Failed to create WebSocket connection: {e}")

    def _on_open(self, ws):
        """WebSocket connection opened callback."""
        self.is_connected = True
        logger.info("Binance WebSocket connection opened")

    def _on_message(self, ws, message):
        """
        Handle incoming WebSocket messages.

        Args:
            ws: WebSocket instance
            message: Raw message string
        """
        try:
            data = json.loads(message)
            kline = data.get('k', {})

            # Extract close price from kline data
            close_price = float(kline.get('c', 0))

            if close_price > 0:
                # Thread-safe append to deque (maxlen handles size automatically)
                with self.buffer_lock:
                    self.price_buffer.append(close_price)

                logger.debug(f"BTC price updated: {close_price}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error processing WebSocket message: {e}")

    def _on_error(self, ws, error):
        """WebSocket error callback."""
        logger.error(f"Binance WebSocket error: {error}")
        self.is_connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed callback."""
        logger.warning(f"Binance WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False

    def get_latest_prices(self, count: int = 100) -> List[float]:
        """
        Get the most recent prices from the buffer.

        Args:
            count: Number of recent prices to return (default: 100)

        Returns:
            List of recent prices, newest last

        Example:
            prices = client.get_latest_prices(50)
            latest_price = prices[-1] if prices else None
        """
        with self.buffer_lock:
            buffer_list = list(self.price_buffer)
            if count > len(buffer_list):
                return buffer_list
            return buffer_list[-count:]

    def get_latest_price(self) -> Optional[float]:
        """
        Get the most recent price.

        Returns:
            Latest price or None if no prices available
        """
        with self.buffer_lock:
            return self.price_buffer[-1] if self.price_buffer else None

    def close(self) -> None:
        """Close the WebSocket connection."""
        if self.ws_app:
            self.ws_app.close()
            self.is_connected = False
            logger.info("Binance WebSocket connection closed")


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        prices: List of prices (must have at least period + 1 values)
        period: RSI period (default: 14)

    Returns:
        RSI value (0-100) or None if insufficient data

    Example:
        rsi = calculate_rsi(price_history, period=14)
        if rsi and rsi < 30:
            print("Oversold condition")
    """
    if len(prices) < period + 1:
        logger.warning(f"Insufficient data for RSI calculation: need {period + 1}, got {len(prices)}")
        return None

    try:
        # Calculate price changes
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]

        # Calculate initial average gain and loss
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # Calculate smoothed averages
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        # Calculate RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        logger.debug(f"RSI calculated: {rsi:.2f}")
        return rsi

    except (ValueError, ZeroDivisionError) as e:
        logger.error(f"Error calculating RSI: {e}")
        return None


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Optional[Tuple[float, float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        prices: List of prices (must have at least slow_period + signal_period values)
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)

    Returns:
        Tuple of (macd_line, signal_line) or None if insufficient data

    Example:
        result = calculate_macd(price_history)
        if result:
            macd_line, signal_line = result
            if macd_line > signal_line:
                print("Bullish crossover")
    """
    min_length = slow_period + signal_period
    if len(prices) < min_length:
        logger.warning(f"Insufficient data for MACD calculation: need {min_length}, got {len(prices)}")
        return None

    try:
        def calculate_ema_series(data: List[float], period: int) -> List[float]:
            """Calculate exponential moving average series."""
            if len(data) < period:
                return []

            multiplier = 2 / (period + 1)
            ema_values = []

            # Initial SMA
            ema = sum(data[:period]) / period
            ema_values.append(ema)

            # Calculate EMA for remaining values
            for price in data[period:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
                ema_values.append(ema)

            return ema_values

        # Calculate fast and slow EMA series
        fast_ema_series = calculate_ema_series(prices, fast_period)
        slow_ema_series = calculate_ema_series(prices, slow_period)

        # We need to align the series - slow EMA starts later
        offset = slow_period - fast_period
        fast_ema_aligned = fast_ema_series[offset:]

        # Calculate MACD line series
        macd_series = [fast - slow for fast, slow in zip(fast_ema_aligned, slow_ema_series)]

        if len(macd_series) < signal_period:
            logger.warning(f"Insufficient MACD values for signal line: need {signal_period}, got {len(macd_series)}")
            return None

        # Calculate signal line (EMA of MACD values)
        multiplier = 2 / (signal_period + 1)
        signal = sum(macd_series[:signal_period]) / signal_period

        for macd_val in macd_series[signal_period:]:
            signal = (macd_val * multiplier) + (signal * (1 - multiplier))

        # Return the latest MACD and signal values
        macd_line = macd_series[-1]
        signal_line = signal

        logger.debug(f"MACD calculated - Line: {macd_line:.2f}, Signal: {signal_line:.2f}")
        return macd_line, signal_line

    except (ValueError, ZeroDivisionError) as e:
        logger.error(f"Error calculating MACD: {e}")
        return None


@retry_with_backoff(
    max_attempts=3,
    base_delay=1.0,
    exceptions=(requests.RequestException,),
    logger_name=__name__
)
def get_order_book_imbalance(symbol: str = "BTCUSDT") -> Optional[float]:
    """
    Calculate order book imbalance from Binance order book.

    Fetches the current order book and calculates the ratio of bid volume
    to ask volume as an indicator of buying/selling pressure.

    Args:
        symbol: Trading pair symbol (default: "BTCUSDT")

    Returns:
        Imbalance ratio (bid_volume / ask_volume) or None if request fails
        - Ratio > 1.0 indicates more buying pressure
        - Ratio < 1.0 indicates more selling pressure

    Example:
        imbalance = get_order_book_imbalance("BTCUSDT")
        if imbalance and imbalance > 1.1:
            print("Strong buying pressure")
    """
    try:
        url = "https://api.binance.com/api/v3/depth"
        params = {"symbol": symbol, "limit": 100}

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()

        # Calculate bid and ask volumes
        bid_volume = sum(float(bid[1]) for bid in data.get("bids", []))
        ask_volume = sum(float(ask[1]) for ask in data.get("asks", []))

        if ask_volume == 0:
            logger.warning("Ask volume is zero, cannot calculate imbalance")
            return None

        imbalance = bid_volume / ask_volume
        logger.debug(f"Order book imbalance: {imbalance:.4f}")
        return imbalance

    except requests.RequestException as e:
        logger.error(f"Failed to fetch order book: {e}")
        return None
    except (KeyError, ValueError, ZeroDivisionError) as e:
        logger.error(f"Error calculating order book imbalance: {e}")
        return None
