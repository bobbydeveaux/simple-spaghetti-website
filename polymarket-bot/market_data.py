"""
Polymarket Bot Market Data Service

This module provides market data integration including:
- Binance WebSocket client for real-time BTC/USDT price feed
- Technical indicators (RSI, MACD) calculation
- Order book imbalance analysis
- Market data aggregation

The service maintains a price history buffer and calculates technical
indicators on each price update for use in trading signal generation.
"""

import json
import logging
import threading
import time
from collections import deque
from decimal import Decimal
from typing import Optional, Tuple, List, Dict, Any, Deque
from datetime import datetime

import numpy as np
import talib
import websocket
from websocket import WebSocketApp

# Configure logging
logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """
    Technical indicator calculation utilities.

    Provides methods for calculating RSI, MACD, and other technical
    indicators using TA-Lib library.
    """

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI).

        RSI is a momentum oscillator that measures the speed and magnitude
        of price changes. Values range from 0 to 100.
        - RSI > 70: Overbought condition
        - RSI < 30: Oversold condition

        Args:
            prices: List of historical prices (oldest to newest)
            period: RSI period (default: 14)

        Returns:
            Current RSI value, or None if insufficient data
        """
        if len(prices) < period + 1:
            logger.debug(f"Insufficient data for RSI calculation: {len(prices)} < {period + 1}")
            return None

        try:
            prices_array = np.array(prices, dtype=float)
            rsi_values = talib.RSI(prices_array, timeperiod=period)

            # Return the most recent RSI value (last non-NaN value)
            for i in range(len(rsi_values) - 1, -1, -1):
                if not np.isnan(rsi_values[i]):
                    return float(rsi_values[i])
            return None
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None

    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        MACD is a trend-following momentum indicator that shows the
        relationship between two moving averages.

        Args:
            prices: List of historical prices (oldest to newest)
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line period (default: 9)

        Returns:
            Tuple of (macd_line, signal_line, histogram)
            Returns (None, None, None) if insufficient data
        """
        required_periods = slow_period + signal_period
        if len(prices) < required_periods:
            logger.debug(f"Insufficient data for MACD calculation: {len(prices)} < {required_periods}")
            return None, None, None

        try:
            prices_array = np.array(prices, dtype=float)
            macd, signal, hist = talib.MACD(
                prices_array,
                fastperiod=fast_period,
                slowperiod=slow_period,
                signalperiod=signal_period
            )

            # Return the most recent values (last non-NaN values)
            for i in range(len(macd) - 1, -1, -1):
                if not np.isnan(macd[i]) and not np.isnan(signal[i]) and not np.isnan(hist[i]):
                    return float(macd[i]), float(signal[i]), float(hist[i])
            return None, None, None
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return None, None, None


class OrderBookAnalyzer:
    """
    Order book analysis utilities.

    Provides methods for analyzing order book data including
    bid/ask imbalance calculations.
    """

    @staticmethod
    def calculate_imbalance(bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]) -> float:
        """
        Calculate order book imbalance metric.

        Imbalance is calculated as the ratio of total bid volume to total ask volume
        in the top levels of the order book.

        Interpretation:
        - Imbalance > 1.0: More buying pressure (bullish)
        - Imbalance < 1.0: More selling pressure (bearish)
        - Imbalance ≈ 1.0: Balanced order book

        Args:
            bids: List of (price, quantity) tuples for bid side
            asks: List of (price, quantity) tuples for ask side

        Returns:
            Imbalance ratio (bid_volume / ask_volume)
            Returns 1.0 if order book is empty or error occurs
        """
        try:
            if not bids or not asks:
                logger.debug("Empty order book data")
                return 1.0

            # Calculate total volume for top 10 levels (or all available)
            bid_volume = sum(quantity for _, quantity in bids[:10])
            ask_volume = sum(quantity for _, quantity in asks[:10])

            if ask_volume == 0:
                logger.warning("Ask volume is zero, returning default imbalance")
                return 1.0

            imbalance = bid_volume / ask_volume
            logger.debug(f"Order book imbalance: {imbalance:.4f} (bid: {bid_volume:.2f}, ask: {ask_volume:.2f})")
            return imbalance

        except Exception as e:
            logger.error(f"Error calculating order book imbalance: {e}")
            return 1.0


class BinanceWebSocketClient:
    """
    Binance WebSocket client for real-time BTC/USDT price feed.

    Maintains a connection to Binance WebSocket API and stores historical
    price data for technical indicator calculation. Includes automatic
    reconnection logic.
    """

    def __init__(self, max_history: int = 200):
        """
        Initialize the WebSocket client.

        Args:
            max_history: Maximum number of price points to store in history
        """
        self.ws_url = "wss://stream.binance.com:9443/ws/btcusdt@trade"
        self.ws: Optional[WebSocketApp] = None
        self.thread: Optional[threading.Thread] = None

        # Price history storage
        self.max_history = max_history
        self.price_history: Deque[float] = deque(maxlen=max_history)
        self.current_price: Optional[float] = None

        # Order book data (from depth stream)
        self.order_book_bids: List[Tuple[float, float]] = []
        self.order_book_asks: List[Tuple[float, float]] = []

        # Connection state
        self.connected = False
        self.lock = threading.Lock()
        self.should_stop = False

        # Statistics
        self.last_update_time: Optional[datetime] = None
        self.update_count = 0

    def on_message(self, ws: WebSocketApp, message: str) -> None:
        """
        Handle incoming WebSocket messages.

        Args:
            ws: WebSocket application instance
            message: Raw message string
        """
        try:
            data = json.loads(message)

            # Parse trade message
            if 'p' in data:  # Trade price
                price = float(data['p'])

                with self.lock:
                    self.current_price = price
                    self.price_history.append(price)
                    self.last_update_time = datetime.utcnow()
                    self.update_count += 1

                if self.update_count % 100 == 0:
                    logger.debug(f"BTC/USDT price updated: ${price:.2f} (history size: {len(self.price_history)})")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")

    def on_error(self, ws: WebSocketApp, error: Exception) -> None:
        """
        Handle WebSocket errors.

        Args:
            ws: WebSocket application instance
            error: Error exception
        """
        logger.error(f"WebSocket error: {error}")

    def on_close(self, ws: WebSocketApp, close_status_code: Optional[int], close_msg: Optional[str]) -> None:
        """
        Handle WebSocket connection close.

        Args:
            ws: WebSocket application instance
            close_status_code: Close status code
            close_msg: Close message
        """
        with self.lock:
            self.connected = False
        logger.warning(f"WebSocket connection closed: {close_status_code} - {close_msg}")

        # Attempt reconnection if not intentionally stopped
        if not self.should_stop:
            logger.info("Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            self.connect()

    def on_open(self, ws: WebSocketApp) -> None:
        """
        Handle WebSocket connection open.

        Args:
            ws: WebSocket application instance
        """
        with self.lock:
            self.connected = True
        logger.info("WebSocket connection established")

    def connect(self) -> bool:
        """
        Establish WebSocket connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.ws = WebSocketApp(
                self.ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )

            self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.thread.start()

            # Wait for connection to establish (max 10 seconds)
            for _ in range(20):
                time.sleep(0.5)
                if self.connected:
                    logger.info("Successfully connected to Binance WebSocket")
                    return True

            logger.error("WebSocket connection timeout")
            return False

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from WebSocket and stop reconnection attempts."""
        self.should_stop = True
        if self.ws:
            self.ws.close()
        logger.info("WebSocket client disconnected")

    def get_current_price(self) -> Optional[float]:
        """
        Get the most recent BTC price.

        Returns:
            Current price, or None if no data available
        """
        with self.lock:
            return self.current_price

    def get_price_history(self, count: Optional[int] = None) -> List[float]:
        """
        Get historical price data.

        Args:
            count: Number of most recent prices to return (default: all)

        Returns:
            List of prices (oldest to newest)
        """
        with self.lock:
            history = list(self.price_history)
            if count is not None and count < len(history):
                return history[-count:]
            return history

    def get_rsi(self, period: int = 14) -> Optional[float]:
        """
        Calculate RSI from current price history.

        Args:
            period: RSI period (default: 14)

        Returns:
            Current RSI value, or None if insufficient data
        """
        prices = self.get_price_history()
        return TechnicalIndicators.calculate_rsi(prices, period)

    def get_macd(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Calculate MACD from current price history.

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        prices = self.get_price_history()
        return TechnicalIndicators.calculate_macd(prices)

    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        with self.lock:
            return self.connected

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get connection and data statistics.

        Returns:
            Dictionary with connection stats
        """
        with self.lock:
            return {
                "connected": self.connected,
                "current_price": self.current_price,
                "history_size": len(self.price_history),
                "max_history": self.max_history,
                "last_update": self.last_update_time.isoformat() if self.last_update_time else None,
                "update_count": self.update_count
            }


class MarketDataService:
    """
    Main market data service interface.

    Aggregates data from Binance WebSocket and provides a unified
    interface for accessing price data and technical indicators.
    """

    def __init__(self):
        """Initialize the market data service."""
        self.binance_client = BinanceWebSocketClient()
        self.order_book_analyzer = OrderBookAnalyzer()
        logger.info("Market data service initialized")

    def start(self) -> bool:
        """
        Start the market data service.

        Returns:
            True if started successfully, False otherwise
        """
        logger.info("Starting market data service...")
        success = self.binance_client.connect()

        if success:
            logger.info("Market data service started successfully")
        else:
            logger.error("Failed to start market data service")

        return success

    def stop(self) -> None:
        """Stop the market data service."""
        logger.info("Stopping market data service...")
        self.binance_client.disconnect()
        logger.info("Market data service stopped")

    def get_current_price(self) -> Optional[Decimal]:
        """
        Get current BTC price.

        Returns:
            Current price as Decimal, or None if unavailable
        """
        price = self.binance_client.get_current_price()
        return Decimal(str(price)) if price is not None else None

    def get_technical_indicators(self) -> Dict[str, Any]:
        """
        Get all technical indicators.

        Returns:
            Dictionary containing RSI, MACD, and other indicators
        """
        rsi = self.binance_client.get_rsi()
        macd_line, signal_line, histogram = self.binance_client.get_macd()

        # Get order book imbalance (placeholder - would need depth stream)
        imbalance = self.order_book_analyzer.calculate_imbalance(
            self.binance_client.order_book_bids,
            self.binance_client.order_book_asks
        )

        return {
            "rsi": rsi,
            "macd_line": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
            "order_book_imbalance": imbalance
        }

    def get_market_data(self) -> Dict[str, Any]:
        """
        Get aggregated market data including price and indicators.

        Returns:
            Complete market data snapshot
        """
        price = self.get_current_price()
        indicators = self.get_technical_indicators()
        stats = self.binance_client.get_statistics()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "btc_price": float(price) if price else None,
            "indicators": indicators,
            "connection_stats": stats
        }

    def is_ready(self) -> bool:
        """
        Check if service is ready to provide data.

        Returns:
            True if connected and has sufficient price history
        """
        if not self.binance_client.is_connected():
            return False

        history = self.binance_client.get_price_history()
        # Need at least 35 data points for MACD calculation (26 + 9)
        return len(history) >= 35
