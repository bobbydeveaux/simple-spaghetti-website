"""
Market Data Service for Polymarket Bot.

This module provides real-time market data integration including:
- Binance WebSocket client for BTC/USDT price streaming
- Technical indicator calculations (RSI, MACD)
- Order book imbalance metrics
- Polymarket API integration for market discovery and odds

The service manages WebSocket connections with automatic reconnection logic
and provides fallback mechanisms for data retrieval.
"""

import json
import time
import logging
import requests
from typing import List, Tuple, Optional, Dict, Any
from decimal import Decimal
from threading import Thread, Lock
from collections import deque
import numpy as np
import talib

from websocket import WebSocketApp, WebSocketConnectionClosedException

from models import MarketData
from config import get_config


# Setup logging
logger = logging.getLogger(__name__)


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
    REST API client for Polymarket integration.

    Provides methods for market discovery and odds retrieval for BTC
    prediction markets.
    """

    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Polymarket API client.

        Args:
            api_key: Polymarket API key
            api_secret: Polymarket API secret
        """
        self.config = get_config()
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = self.config.polymarket_base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })

        logger.info(f"Initialized PolymarketClient with base_url={self.base_url}")

    def find_active_market(self) -> Optional[str]:
        """
        Find an active BTC prediction market.

        Searches for active markets related to BTC price movements with
        5-minute intervals.

        Returns:
            Market ID if found, None otherwise
        """
        try:
            # Query for active BTC markets
            params = {
                'asset': 'BTC',
                'interval': '5m',
                'status': 'active'
            }

            response = self.session.get(
                f"{self.base_url}/markets",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            markets = response.json()

            if markets and len(markets) > 0:
                # Return the first active market
                market_id = markets[0].get('market_id')
                logger.info(f"Found active market: {market_id}")
                return market_id

            logger.warning("No active BTC markets found")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error finding active market: {e}")
            return None

    def get_market_odds(self, market_id: str) -> Tuple[float, float, Dict[str, Any]]:
        """
        Get current odds and metadata for a specific market.

        Args:
            market_id: Polymarket market identifier

        Returns:
            Tuple of (yes_odds, no_odds, market_info) where market_info contains
            additional data like end_date, question, etc.

        Raises:
            ValueError: If market not found or invalid response
        """
        try:
            response = self.session.get(
                f"{self.base_url}/markets/{market_id}",
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            yes_odds = float(data.get('odds_yes', 0.5))
            no_odds = float(data.get('odds_no', 0.5))

            # Extract additional market metadata
            market_info = {
                'end_date': data.get('end_date'),
                'question': data.get('question', f"BTC 5-min prediction market {market_id}"),
                'created_date': data.get('created_date'),
            }

            logger.info(f"Market {market_id} odds - YES: {yes_odds:.4f}, NO: {no_odds:.4f}")

            return yes_odds, no_odds, market_info

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching market odds: {e}")
            raise ValueError(f"Failed to fetch odds for market {market_id}")


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


def calculate_macd(prices: List[float]) -> Tuple[float, float]:
    """
    Calculate MACD (Moving Average Convergence Divergence) indicator.

    MACD is a trend-following momentum indicator showing the relationship
    between two moving averages of prices.

    Args:
        prices: List of price values (oldest to newest)

    Returns:
        Tuple of (macd_line, signal_line)
        - macd_line: MACD line value
        - signal_line: Signal line value
        - Crossover (MACD > signal) suggests bullish momentum
        - Crossover (MACD < signal) suggests bearish momentum

    Raises:
        ValueError: If insufficient price data
    """
    if len(prices) < 34:  # Need at least 26 + 9 - 1 for MACD calculation
        raise ValueError(f"Insufficient price data for MACD calculation. Need at least 34 prices, got {len(prices)}")

    # Convert to numpy array for TA-Lib
    prices_array = np.array(prices, dtype=float)

    # Calculate MACD using TA-Lib (default: 12, 26, 9)
    macd_line, signal_line, _ = talib.MACD(
        prices_array,
        fastperiod=12,
        slowperiod=26,
        signalperiod=9
    )

    # Return the most recent values
    current_macd = float(macd_line[-1])
    current_signal = float(signal_line[-1])

    logger.debug(f"Calculated MACD: {current_macd:.2f}, Signal: {current_signal:.2f}")

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

    # Get price data from Binance
    prices = binance_client.get_latest_prices(100)

    if len(prices) < 34:
        raise ValueError(f"Insufficient price data for indicators. Need at least 34, got {len(prices)}")

    latest_price = prices[-1]

    # Calculate technical indicators
    try:
        rsi_value = calculate_rsi(prices, period=14)
        macd_line, macd_signal = calculate_macd(prices)
        order_book_imb = get_order_book_imbalance()
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        raise ValueError(f"Failed to calculate technical indicators: {e}")

    # Get Polymarket market and odds
    if market_id is None:
        market_id = polymarket_client.find_active_market()
        if market_id is None:
            raise ValueError("No active Polymarket markets found")

    try:
        yes_odds, no_odds, market_info = polymarket_client.get_market_odds(market_id)
    except Exception as e:
        logger.error(f"Error fetching Polymarket odds: {e}")
        raise ValueError(f"Failed to fetch market odds: {e}")

    # Parse end_date from market info
    from datetime import datetime
    end_date_str = market_info.get('end_date')
    if end_date_str:
        # Parse ISO format datetime string
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
    else:
        # Fallback: set end date to 5 minutes from now for 5-min markets
        from datetime import timedelta
        end_date = datetime.utcnow() + timedelta(minutes=5)

    # Create MarketData object
    market_data = MarketData(
        market_id=market_id,
        question=market_info.get('question', f"BTC 5-min prediction market {market_id}"),
        end_date=end_date,
        yes_price=Decimal(str(yes_odds)),
        no_price=Decimal(str(no_odds))
    )

    # Add metadata with technical analysis
    market_data.metadata = {
        'btc_price': latest_price,
        'rsi_14': rsi_value,
        'macd_line': macd_line,
        'macd_signal': macd_signal,
        'order_book_imbalance': order_book_imb,
        'price_buffer_size': len(prices)
    }

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
