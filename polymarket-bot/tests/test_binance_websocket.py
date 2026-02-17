"""
Tests for Binance WebSocket BTC Price Feed

This module tests the Binance WebSocket client including:
- WebSocket connection and message handling
- Price data parsing and storage
- Reconnection logic
- Historical price data management
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from decimal import Decimal
from datetime import datetime
import json
import time

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data import BinanceWebSocket, BinanceWebSocketError
from models import BTCPriceData
from utils import ValidationError


# Test fixtures

@pytest.fixture
def sample_binance_ticker():
    """Sample Binance 24hr ticker data."""
    return {
        "e": "24hrTicker",
        "E": 1705318800000,  # Event time (timestamp in ms)
        "s": "BTCUSDT",
        "p": "678.90",  # Price change
        "P": "1.51",  # Price change percent
        "w": "45500.00",  # Weighted average price
        "x": "45000.00",  # First trade price
        "c": "45678.90",  # Last price
        "Q": "0.5",  # Last quantity
        "b": "45678.50",  # Best bid price
        "B": "1.2",  # Best bid quantity
        "a": "45679.00",  # Best ask price
        "A": "0.8",  # Best ask quantity
        "o": "45000.00",  # Open price
        "h": "46000.00",  # High price
        "l": "45000.00",  # Low price
        "v": "12345.67",  # Total traded base asset volume
        "q": "123456789.50",  # Total traded quote asset volume
        "O": 1705232400000,  # Statistics open time
        "C": 1705318800000,  # Statistics close time
        "F": 100000,  # First trade ID
        "L": 200000,  # Last trade ID
        "n": 100001  # Total number of trades
    }


@pytest.fixture
def binance_ws():
    """Create a BinanceWebSocket instance for testing."""
    return BinanceWebSocket(history_size=50)


# Test BinanceWebSocket initialization

class TestBinanceWebSocketInitialization:
    """Tests for BinanceWebSocket initialization."""

    def test_initialization_default(self):
        """Test WebSocket initializes with default settings."""
        ws = BinanceWebSocket()

        assert ws.history_size == 200
        assert ws.latest_price is None
        assert len(ws.price_history) == 0
        assert ws.is_connected is False
        assert ws.should_reconnect is True
        assert ws.on_price_update is None

    def test_initialization_with_callback(self):
        """Test WebSocket initializes with callback function."""
        callback = Mock()
        ws = BinanceWebSocket(on_price_update=callback, history_size=100)

        assert ws.on_price_update == callback
        assert ws.history_size == 100

    def test_initialization_with_custom_history_size(self):
        """Test WebSocket initializes with custom history size."""
        ws = BinanceWebSocket(history_size=500)

        assert ws.price_history.maxlen == 500


# Test ticker data parsing

class TestTickerDataParsing:
    """Tests for Binance ticker data parsing."""

    def test_parse_ticker_data_complete(self, binance_ws, sample_binance_ticker):
        """Test parsing complete ticker data."""
        price_data = binance_ws._parse_ticker_data(sample_binance_ticker)

        assert isinstance(price_data, BTCPriceData)
        assert price_data.symbol == "BTCUSDT"
        assert price_data.price == Decimal("45678.90")
        assert price_data.volume_24h == Decimal("123456789.50")
        assert price_data.high_24h == Decimal("46000.00")
        assert price_data.low_24h == Decimal("45000.00")
        assert price_data.price_change_24h == Decimal("678.90")
        assert price_data.price_change_percent_24h == Decimal("1.51")
        assert isinstance(price_data.timestamp, datetime)

    def test_parse_ticker_data_minimal(self, binance_ws):
        """Test parsing minimal ticker data."""
        minimal_data = {
            "s": "BTCUSDT",
            "c": "50000.00",
            "E": 1705318800000
        }

        price_data = binance_ws._parse_ticker_data(minimal_data)

        assert price_data.symbol == "BTCUSDT"
        assert price_data.price == Decimal("50000.00")
        assert price_data.volume_24h is None
        assert price_data.high_24h is None
        assert price_data.low_24h is None

    def test_parse_ticker_data_alternate_field_names(self, binance_ws):
        """Test parsing with alternate field names."""
        alt_data = {
            "s": "BTCUSDT",
            "lastPrice": "48000.00",
            "highPrice": "49000.00",
            "lowPrice": "47000.00",
            "quoteVolume": "100000000.00",
            "priceChange": "500.00",
            "priceChangePercent": "1.05",
            "E": 1705318800000
        }

        price_data = binance_ws._parse_ticker_data(alt_data)

        assert price_data.price == Decimal("48000.00")
        assert price_data.high_24h == Decimal("49000.00")
        assert price_data.low_24h == Decimal("47000.00")
        assert price_data.volume_24h == Decimal("100000000.00")

    def test_parse_ticker_data_invalid_format(self, binance_ws):
        """Test parsing fails for invalid ticker data."""
        invalid_data = {"invalid": "data"}

        with pytest.raises(ValidationError) as exc_info:
            binance_ws._parse_ticker_data(invalid_data)

        assert "Failed to parse" in str(exc_info.value)

    def test_parse_ticker_data_stores_metadata(self, binance_ws, sample_binance_ticker):
        """Test that raw ticker data is stored in metadata."""
        price_data = binance_ws._parse_ticker_data(sample_binance_ticker)

        assert price_data.metadata == sample_binance_ticker


# Test WebSocket message handling

class TestWebSocketMessageHandling:
    """Tests for WebSocket message handling."""

    def test_on_message_updates_latest_price(self, binance_ws, sample_binance_ticker):
        """Test message handler updates latest price."""
        message = json.dumps(sample_binance_ticker)

        binance_ws._on_message(None, message)

        assert binance_ws.latest_price is not None
        assert binance_ws.latest_price.price == Decimal("45678.90")
        assert binance_ws.last_message_time is not None

    def test_on_message_adds_to_history(self, binance_ws, sample_binance_ticker):
        """Test message handler adds to price history."""
        message = json.dumps(sample_binance_ticker)

        binance_ws._on_message(None, message)

        assert len(binance_ws.price_history) == 1
        assert binance_ws.price_history[0].price == Decimal("45678.90")

    def test_on_message_calls_callback(self, sample_binance_ticker):
        """Test message handler calls user callback."""
        callback = Mock()
        ws = BinanceWebSocket(on_price_update=callback)

        message = json.dumps(sample_binance_ticker)
        ws._on_message(None, message)

        callback.assert_called_once()
        assert isinstance(callback.call_args[0][0], BTCPriceData)

    def test_on_message_handles_callback_error(self, sample_binance_ticker):
        """Test message handler gracefully handles callback errors."""
        callback = Mock(side_effect=Exception("Callback error"))
        ws = BinanceWebSocket(on_price_update=callback)

        message = json.dumps(sample_binance_ticker)

        # Should not raise exception
        ws._on_message(None, message)

        # Price should still be updated
        assert ws.latest_price is not None

    def test_on_message_handles_invalid_json(self, binance_ws):
        """Test message handler handles invalid JSON."""
        invalid_message = "{ invalid json }"

        # Should not raise exception
        binance_ws._on_message(None, invalid_message)

        # Latest price should remain None
        assert binance_ws.latest_price is None

    def test_on_message_multiple_updates(self, binance_ws):
        """Test multiple message updates."""
        for i in range(10):
            ticker_data = {
                "s": "BTCUSDT",
                "c": str(45000 + i * 100),
                "E": 1705318800000 + i * 1000
            }
            message = json.dumps(ticker_data)
            binance_ws._on_message(None, message)

        assert len(binance_ws.price_history) == 10
        assert binance_ws.latest_price.price == Decimal("45900")


# Test connection state management

class TestConnectionStateManagement:
    """Tests for WebSocket connection state management."""

    def test_on_open_sets_connected(self, binance_ws):
        """Test on_open sets connection state."""
        binance_ws._on_open(None)

        assert binance_ws.is_connected is True
        assert binance_ws.connection_errors == 0

    def test_on_close_sets_disconnected(self, binance_ws):
        """Test on_close sets disconnection state."""
        binance_ws.is_connected = True
        binance_ws._on_close(None, 1000, "Normal close")

        assert binance_ws.is_connected is False

    def test_on_error_sets_disconnected(self, binance_ws):
        """Test on_error sets disconnection state."""
        binance_ws.is_connected = True
        binance_ws._on_error(None, "Connection error")

        assert binance_ws.is_connected is False


# Test price data retrieval

class TestPriceDataRetrieval:
    """Tests for price data retrieval methods."""

    def test_get_latest_price_none_when_no_data(self, binance_ws):
        """Test get_latest_price returns None when no data."""
        assert binance_ws.get_latest_price() is None

    def test_get_latest_price_returns_latest(self, binance_ws, sample_binance_ticker):
        """Test get_latest_price returns most recent price."""
        message = json.dumps(sample_binance_ticker)
        binance_ws._on_message(None, message)

        latest = binance_ws.get_latest_price()

        assert latest is not None
        assert latest.price == Decimal("45678.90")

    def test_get_price_history_empty(self, binance_ws):
        """Test get_price_history returns empty list when no data."""
        history = binance_ws.get_price_history()

        assert history == []

    def test_get_price_history_returns_all(self, binance_ws):
        """Test get_price_history returns all price data."""
        for i in range(5):
            ticker_data = {"s": "BTCUSDT", "c": str(45000 + i), "E": 1705318800000}
            message = json.dumps(ticker_data)
            binance_ws._on_message(None, message)

        history = binance_ws.get_price_history()

        assert len(history) == 5
        assert all(isinstance(item, BTCPriceData) for item in history)

    def test_get_price_history_with_limit(self, binance_ws):
        """Test get_price_history respects limit parameter."""
        for i in range(10):
            ticker_data = {"s": "BTCUSDT", "c": str(45000 + i), "E": 1705318800000}
            message = json.dumps(ticker_data)
            binance_ws._on_message(None, message)

        history = binance_ws.get_price_history(limit=5)

        assert len(history) == 5
        # Should return the 5 most recent prices
        assert history[-1].price == Decimal("45009")

    def test_get_price_series(self, binance_ws):
        """Test get_price_series returns list of prices."""
        for i in range(5):
            ticker_data = {"s": "BTCUSDT", "c": str(45000 + i), "E": 1705318800000}
            message = json.dumps(ticker_data)
            binance_ws._on_message(None, message)

        series = binance_ws.get_price_series()

        assert len(series) == 5
        assert all(isinstance(price, Decimal) for price in series)
        assert series == [Decimal("45000"), Decimal("45001"), Decimal("45002"), Decimal("45003"), Decimal("45004")]

    def test_get_price_series_with_limit(self, binance_ws):
        """Test get_price_series respects limit parameter."""
        for i in range(10):
            ticker_data = {"s": "BTCUSDT", "c": str(45000 + i), "E": 1705318800000}
            message = json.dumps(ticker_data)
            binance_ws._on_message(None, message)

        series = binance_ws.get_price_series(limit=3)

        assert len(series) == 3
        assert series[-1] == Decimal("45009")


# Test price history size management

class TestPriceHistorySizeManagement:
    """Tests for price history size management."""

    def test_history_respects_maxlen(self):
        """Test history respects maximum length."""
        ws = BinanceWebSocket(history_size=5)

        for i in range(10):
            ticker_data = {"s": "BTCUSDT", "c": str(45000 + i), "E": 1705318800000}
            message = json.dumps(ticker_data)
            ws._on_message(None, message)

        # Should only keep the 5 most recent
        assert len(ws.price_history) == 5
        assert ws.price_history[0].price == Decimal("45005")
        assert ws.price_history[-1].price == Decimal("45009")


# Test health check

class TestHealthCheck:
    """Tests for WebSocket health check."""

    def test_is_healthy_false_when_not_connected(self, binance_ws):
        """Test is_healthy returns False when not connected."""
        assert binance_ws.is_healthy() is False

    def test_is_healthy_false_when_no_messages(self, binance_ws):
        """Test is_healthy returns False when no messages received."""
        binance_ws.is_connected = True
        binance_ws.last_message_time = None

        assert binance_ws.is_healthy() is False

    def test_is_healthy_true_when_recent_message(self, binance_ws):
        """Test is_healthy returns True when recent message received."""
        binance_ws.is_connected = True
        binance_ws.last_message_time = datetime.now(timezone.utc)

        assert binance_ws.is_healthy() is True

    @patch('market_data.datetime')
    def test_is_healthy_false_when_message_old(self, mock_datetime, binance_ws):
        """Test is_healthy returns False when message is old."""
        old_time = datetime(2024, 1, 1, 10, 0, 0)
        current_time = datetime(2024, 1, 1, 10, 2, 0)  # 2 minutes later

        binance_ws.is_connected = True
        binance_ws.last_message_time = old_time

        mock_datetime.utcnow.return_value = current_time

        # Should be unhealthy with default 60s max age
        assert binance_ws.is_healthy(max_message_age_seconds=60) is False

    @patch('market_data.datetime')
    def test_is_healthy_true_with_custom_max_age(self, mock_datetime, binance_ws):
        """Test is_healthy with custom max message age."""
        old_time = datetime(2024, 1, 1, 10, 0, 0)
        current_time = datetime(2024, 1, 1, 10, 2, 0)  # 2 minutes later

        binance_ws.is_connected = True
        binance_ws.last_message_time = old_time

        mock_datetime.utcnow.return_value = current_time

        # Should be healthy with 180s max age
        assert binance_ws.is_healthy(max_message_age_seconds=180) is True


# Test disconnect

class TestDisconnect:
    """Tests for WebSocket disconnection."""

    @patch('websocket.WebSocketApp')
    def test_disconnect_stops_reconnection(self, mock_ws_app, binance_ws):
        """Test disconnect stops reconnection attempts."""
        binance_ws.ws = Mock()
        binance_ws.is_connected = True
        binance_ws.should_reconnect = True

        binance_ws.disconnect()

        assert binance_ws.should_reconnect is False
        assert binance_ws.is_connected is False
        binance_ws.ws.close.assert_called_once()

    @patch('websocket.WebSocketApp')
    def test_disconnect_waits_for_thread(self, mock_ws_app, binance_ws):
        """Test disconnect waits for thread to finish."""
        binance_ws.ws = Mock()
        binance_ws.ws_thread = Mock()
        binance_ws.ws_thread.is_alive.return_value = True

        binance_ws.disconnect()

        binance_ws.ws_thread.join.assert_called_once_with(timeout=5)


# Test context manager

class TestContextManager:
    """Tests for context manager functionality."""

    @patch.object(BinanceWebSocket, 'connect')
    @patch.object(BinanceWebSocket, 'disconnect')
    def test_context_manager(self, mock_disconnect, mock_connect):
        """Test WebSocket works as context manager."""
        with BinanceWebSocket() as ws:
            assert ws is not None

        mock_connect.assert_called_once()
        mock_disconnect.assert_called_once()


# Test BTCPriceData model methods

class TestBTCPriceDataModel:
    """Tests for BTCPriceData model methods."""

    def test_btc_price_data_to_dict(self):
        """Test BTCPriceData to_dict method."""
        price_data = BTCPriceData(
            symbol="BTCUSDT",
            price=Decimal("45678.90"),
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            volume_24h=Decimal("123456789.50"),
            high_24h=Decimal("46000.00"),
            low_24h=Decimal("45000.00"),
            price_change_24h=Decimal("678.90"),
            price_change_percent_24h=Decimal("1.51")
        )

        data_dict = price_data.to_dict()

        assert data_dict["symbol"] == "BTCUSDT"
        assert data_dict["price"] == 45678.90
        assert data_dict["volume_24h"] == 123456789.50
        assert data_dict["high_24h"] == 46000.00
        assert data_dict["low_24h"] == 45000.00
        assert isinstance(data_dict["timestamp"], str)

    def test_btc_price_data_get_mid_range_price(self):
        """Test BTCPriceData get_mid_range_price method."""
        price_data = BTCPriceData(
            symbol="BTCUSDT",
            price=Decimal("45500.00"),
            timestamp=datetime.now(timezone.utc),
            high_24h=Decimal("46000.00"),
            low_24h=Decimal("45000.00")
        )

        mid_range = price_data.get_mid_range_price()

        assert mid_range == Decimal("45500.00")

    def test_btc_price_data_get_mid_range_price_none(self):
        """Test get_mid_range_price returns None when data missing."""
        price_data = BTCPriceData(
            symbol="BTCUSDT",
            price=Decimal("45500.00"),
            timestamp=datetime.now(timezone.utc)
        )

        mid_range = price_data.get_mid_range_price()

        assert mid_range is None

    def test_btc_price_data_get_volatility_percent(self):
        """Test BTCPriceData get_volatility_percent method."""
        price_data = BTCPriceData(
            symbol="BTCUSDT",
            price=Decimal("45500.00"),
            timestamp=datetime.now(timezone.utc),
            high_24h=Decimal("46000.00"),
            low_24h=Decimal("45000.00")
        )

        volatility = price_data.get_volatility_percent()

        # Range = 1000, Price = 45500, Volatility = (1000 / 45500) * 100 ≈ 2.20%
        assert volatility is not None
        assert abs(volatility - Decimal("2.20")) < Decimal("0.01")

    def test_btc_price_data_get_volatility_percent_none(self):
        """Test get_volatility_percent returns None when data missing."""
        price_data = BTCPriceData(
            symbol="BTCUSDT",
            price=Decimal("45500.00"),
            timestamp=datetime.now(timezone.utc)
        )

        volatility = price_data.get_volatility_percent()

        assert volatility is None
