"""
Market Data Service for Polymarket Bot.

This module provides unified market data integration combining:
- Binance WebSocket for real-time BTC/USDT price data
- Technical indicator calculations (RSI, MACD)
- Order book imbalance analysis
- Polymarket API for market discovery and odds retrieval

The MarketDataService class orchestrates all data sources and provides
a unified interface for accessing market data throughout the bot.
"""

import json
import logging
import threading
import time
from collections import deque
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Deque
from datetime import datetime, timezone
import websocket
import requests

from .utils import retry_with_backoff, ValidationError
from .models import MarketData

# Configure module logger
logger = logging.getLogger(__name__)


class BinanceWebSocketClient:
    """
    WebSocket client for real-time BTC/USDT price data from Binance.

    Manages connection, message parsing, reconnection logic, and maintains
    a price buffer for technical indicator calculations.
    """

    def __init__(
        self,
        symbol: str = "btcusdt",
        interval: str = "1m",
        buffer_size: int = 100,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 5.0
    ):
        """
        Initialize Binance WebSocket client.

        Args:
            symbol: Trading pair symbol (default: btcusdt)
            interval: Kline interval (default: 1m)
            buffer_size: Maximum price history buffer size
            max_reconnect_attempts: Maximum reconnection attempts
            reconnect_delay: Delay between reconnection attempts in seconds
        """
        self.symbol = symbol.lower()
        self.interval = interval
        self.buffer_size = buffer_size
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay

        # Price buffer using deque for efficient append/pop
        self.price_buffer: Deque[float] = deque(maxlen=buffer_size)

        # WebSocket connection state
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None
        self.is_connected = False
        self.should_reconnect = True
        self.reconnect_count = 0

        # Latest price data
        self.latest_price: Optional[float] = None
        self.last_update_time: Optional[datetime] = None

        # Lock for thread-safe operations
        self._lock = threading.Lock()

        logger.info(f"Initialized BinanceWebSocketClient for {symbol} {interval}")

    def connect(self) -> None:
        """
        Connect to Binance WebSocket stream.

        Starts WebSocket connection in a background thread.
        """
        if self.is_connected:
            logger.warning("WebSocket already connected")
            return

        # Construct WebSocket URL
        ws_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@kline_{self.interval}"

        logger.info(f"Connecting to Binance WebSocket: {ws_url}")

        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )

        # Run WebSocket in background thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.ws_thread.start()

    def _on_open(self, ws) -> None:
        """Handle WebSocket connection opened."""
        with self._lock:
            self.is_connected = True
            self.reconnect_count = 0
        logger.info("Binance WebSocket connection established")

    def _on_message(self, ws, message: str) -> None:
        """
        Handle incoming WebSocket message.

        Args:
            ws: WebSocket instance
            message: JSON message from Binance
        """
        try:
            data = json.loads(message)

            # Extract kline data
            if 'k' in data:
                kline = data['k']
                close_price = float(kline['c'])
                is_closed = kline['x']  # Kline closed

                with self._lock:
                    self.latest_price = close_price
                    self.last_update_time = datetime.now(timezone.utc)

                    # Only add to buffer when kline is closed
                    if is_closed:
                        self.price_buffer.append(close_price)
                        logger.debug(f"BTC price updated: ${close_price:,.2f}")

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing WebSocket message: {e}")

    def _on_error(self, ws, error) -> None:
        """Handle WebSocket error."""
        logger.error(f"Binance WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """Handle WebSocket connection closed."""
        with self._lock:
            self.is_connected = False

        logger.warning(
            f"Binance WebSocket closed (code: {close_status_code}, msg: {close_msg})"
        )

        # Attempt reconnection
        if self.should_reconnect and self.reconnect_count < self.max_reconnect_attempts:
            self.reconnect_count += 1
            logger.info(
                f"Attempting reconnection {self.reconnect_count}/{self.max_reconnect_attempts}"
            )
            time.sleep(self.reconnect_delay)
            self.connect()
        else:
            logger.error("Max reconnection attempts reached or reconnect disabled")

    def get_latest_price(self) -> Optional[float]:
        """
        Get the most recent BTC price.

        Returns:
            Latest price or None if no data available
        """
        with self._lock:
            return self.latest_price

    def get_price_history(self, count: Optional[int] = None) -> List[float]:
        """
        Get historical price data from buffer.

        Args:
            count: Number of recent prices to return (default: all)

        Returns:
            List of prices (oldest to newest)
        """
        with self._lock:
            prices = list(self.price_buffer)
            if count is not None:
                prices = prices[-count:]
            return prices

    def close(self) -> None:
        """Close WebSocket connection and cleanup."""
        logger.info("Closing Binance WebSocket connection")
        self.should_reconnect = False

        if self.ws:
            self.ws.close()

        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)


class PolymarketClient:
    """
    REST API client for Polymarket market discovery and odds retrieval.

    Handles authentication, market queries, and odds fetching with
    retry logic and error handling.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.polymarket.com"
    ):
        """
        Initialize Polymarket API client.

        Args:
            api_key: Polymarket API key
            api_secret: Polymarket API secret
            base_url: API base URL
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')

        # Request headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info("Initialized PolymarketClient")

    @retry_with_backoff(max_attempts=3, base_delay=2.0)
    def find_active_btc_market(
        self,
        category: str = "crypto",
        interval: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find an active BTC-related prediction market.

        Args:
            category: Market category filter (default: crypto)
            interval: Optional interval filter (e.g., "5m")

        Returns:
            Market data dictionary or None if no market found
        """
        # Build query parameters
        params = {
            "category": category,
            "status": "active",
            "asset": "BTC"
        }

        if interval:
            params["interval"] = interval

        try:
            response = requests.get(
                f"{self.base_url}/markets",
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            markets = response.json()

            if not markets or len(markets) == 0:
                logger.warning("No active BTC markets found")
                return None

            # Return the first active market
            market = markets[0]
            logger.info(f"Found active market: {market.get('market_id', 'unknown')}")
            return market

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Polymarket markets: {e}")
            raise

    @retry_with_backoff(max_attempts=3, base_delay=2.0)
    def get_market_odds(self, market_id: str) -> Tuple[Decimal, Decimal]:
        """
        Get current odds for a specific market.

        Args:
            market_id: Polymarket market identifier

        Returns:
            Tuple of (yes_odds, no_odds) as Decimal

        Raises:
            ValidationError: If odds are invalid
        """
        try:
            response = requests.get(
                f"{self.base_url}/markets/{market_id}/odds",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            yes_odds = Decimal(str(data.get('yes_price', 0.5)))
            no_odds = Decimal(str(data.get('no_price', 0.5)))

            # Validate odds are in valid range
            if not (0 < yes_odds < 1 and 0 < no_odds < 1):
                raise ValidationError(f"Invalid odds: yes={yes_odds}, no={no_odds}")

            logger.debug(f"Market {market_id} odds: YES={yes_odds}, NO={no_odds}")

            return yes_odds, no_odds

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching market odds: {e}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing market odds: {e}")
            raise ValidationError(f"Invalid odds response: {e}")


class MarketDataService:
    """
    Unified market data service integrating all data sources.

    Orchestrates Binance WebSocket, technical indicators, and Polymarket API
    to provide comprehensive market data for trading decisions.
    """

    def __init__(
        self,
        binance_ws_client: BinanceWebSocketClient,
        polymarket_client: PolymarketClient
    ):
        """
        Initialize market data service.

        Args:
            binance_ws_client: Binance WebSocket client instance
            polymarket_client: Polymarket API client instance
        """
        self.binance_ws = binance_ws_client
        self.polymarket = polymarket_client
        self.active_market_id: Optional[str] = None

        logger.info("Initialized MarketDataService")

    def start(self) -> None:
        """Start all data sources."""
        logger.info("Starting market data service")
        self.binance_ws.connect()

        # Wait for initial price data
        max_wait = 10
        wait_time = 0
        while self.binance_ws.get_latest_price() is None and wait_time < max_wait:
            time.sleep(1)
            wait_time += 1

        if self.binance_ws.get_latest_price() is None:
            logger.warning("No initial price data received from Binance")

    def stop(self) -> None:
        """Stop all data sources and cleanup."""
        logger.info("Stopping market data service")
        self.binance_ws.close()

    def get_market_data(self) -> MarketData:
        """
        Get comprehensive market data from all sources.

        Returns:
            MarketData model with current prices, indicators, and odds

        Raises:
            ValidationError: If required data is unavailable
        """
        # Get BTC price
        latest_price = self.binance_ws.get_latest_price()
        if latest_price is None:
            raise ValidationError("No BTC price data available")

        # Get price history for indicators
        price_history = self.binance_ws.get_price_history()

        if len(price_history) < 26:  # Need at least 26 for MACD
            logger.warning(
                f"Insufficient price history ({len(price_history)} prices). "
                "Using default indicator values."
            )
            rsi = 50.0
            macd_line = 0.0
            macd_signal = 0.0
        else:
            # Calculate technical indicators
            rsi = calculate_rsi(price_history, period=14)
            macd_line, macd_signal = calculate_macd(price_history)

        # Get Polymarket market and odds
        if self.active_market_id is None:
            market = self.polymarket.find_active_btc_market()
            if market:
                self.active_market_id = market.get('market_id')

        if self.active_market_id:
            try:
                yes_odds, no_odds = self.polymarket.get_market_odds(self.active_market_id)
            except Exception as e:
                logger.warning(f"Failed to get market odds: {e}. Using defaults.")
                yes_odds = Decimal("0.5")
                no_odds = Decimal("0.5")
        else:
            logger.warning("No active market found. Using default odds.")
            yes_odds = Decimal("0.5")
            no_odds = Decimal("0.5")

        # Create and return MarketData
        return MarketData(
            market_id=self.active_market_id or "unknown",
            question=f"BTC Market Data",
            end_date=datetime.now(timezone.utc),
            yes_price=yes_odds,
            no_price=no_odds,
            metadata={
                "btc_price": latest_price,
                "rsi_14": rsi,
                "macd_line": macd_line,
                "macd_signal": macd_signal,
                "price_history_length": len(price_history)
            }
        )


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """
    Calculate Relative Strength Index (RSI).

    Args:
        prices: List of closing prices (oldest to newest)
        period: RSI period (default: 14)

    Returns:
        RSI value between 0 and 100

    Raises:
        ValidationError: If insufficient data
    """
    if len(prices) < period + 1:
        raise ValidationError(
            f"Insufficient data for RSI calculation. "
            f"Need at least {period + 1} prices, got {len(prices)}"
        )

    # Calculate price changes
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]

    # Separate gains and losses
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]

    # Calculate initial averages
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Calculate smoothed averages for remaining periods
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    # Calculate RSI
    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_macd(
    prices: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Tuple[float, float]:
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Args:
        prices: List of closing prices (oldest to newest)
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)

    Returns:
        Tuple of (macd_line, signal_line)

    Raises:
        ValidationError: If insufficient data
    """
    if len(prices) < slow_period + signal_period:
        raise ValidationError(
            f"Insufficient data for MACD calculation. "
            f"Need at least {slow_period + signal_period} prices, got {len(prices)}"
        )

    # Calculate EMAs
    fast_ema = _calculate_ema(prices, fast_period)
    slow_ema = _calculate_ema(prices, slow_period)

    # Calculate MACD line
    macd_values = [fast_ema[i] - slow_ema[i] for i in range(len(slow_ema))]

    # Calculate signal line (EMA of MACD)
    signal_line_values = _calculate_ema(macd_values, signal_period)

    # Return latest values
    macd_line = macd_values[-1]
    signal_line = signal_line_values[-1]

    return macd_line, signal_line


def _calculate_ema(prices: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average.

    Args:
        prices: List of prices
        period: EMA period

    Returns:
        List of EMA values
    """
    if len(prices) < period:
        return []

    # Smoothing multiplier
    multiplier = 2 / (period + 1)

    # Initial SMA
    ema_values = [sum(prices[:period]) / period]

    # Calculate EMA for remaining prices
    for i in range(period, len(prices)):
        ema = (prices[i] - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(ema)

    return ema_values


def get_order_book_imbalance(
    binance_api_key: str,
    binance_api_secret: str,
    symbol: str = "BTCUSDT",
    limit: int = 100
) -> float:
    """
    Calculate order book imbalance from Binance.

    Order book imbalance = total_bid_volume / total_ask_volume
    Values > 1 indicate buying pressure, < 1 indicate selling pressure.

    Args:
        binance_api_key: Binance API key
        binance_api_secret: Binance API secret
        symbol: Trading pair symbol (default: BTCUSDT)
        limit: Order book depth limit (default: 100)

    Returns:
        Imbalance ratio (bid_volume / ask_volume)

    Raises:
        ValidationError: If order book data is invalid
    """
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/depth",
            params={"symbol": symbol, "limit": limit},
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        # Calculate bid and ask volumes
        bid_volume = sum(float(bid[1]) for bid in data['bids'])
        ask_volume = sum(float(ask[1]) for ask in data['asks'])

        if ask_volume == 0:
            raise ValidationError("Ask volume is zero")

        imbalance = bid_volume / ask_volume

        logger.debug(f"Order book imbalance: {imbalance:.4f}")

        return imbalance

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching order book: {e}")
        raise ValidationError(f"Failed to fetch order book: {e}")
    except (KeyError, ValueError, ZeroDivisionError) as e:
        logger.error(f"Error calculating order book imbalance: {e}")
        raise ValidationError(f"Invalid order book data: {e}")
