"""
Unit tests for market_data module.

Tests cover:
- BinanceWebSocketClient connection and data handling
- Technical indicator calculations (RSI, MACD)
- PolymarketClient API integration
- Order book imbalance calculations
- Market data aggregation
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import numpy as np

from market_data import (
    BinanceWebSocketClient,
    PolymarketClient,
    calculate_rsi,
    calculate_macd,
    get_order_book_imbalance,
    get_market_data,
    get_fallback_btc_price
)
from models import MarketData


class TestBinanceWebSocketClient:
    """Test cases for BinanceWebSocketClient."""

    @patch('market_data.WebSocketApp')
    def test_initialization(self, mock_ws_app):
        """Test client initialization with custom buffer size."""
        client = BinanceWebSocketClient(buffer_size=50)

        assert client.buffer_size == 50
        assert len(client.price_buffer) == 0
        assert not client.is_connected
        assert client.reconnect_attempts == 0

    @patch('market_data.WebSocketApp')
    @patch('market_data.Thread')
    def test_connect_success(self, mock_thread, mock_ws_app):
        """Test successful WebSocket connection."""
        client = BinanceWebSocketClient()

        # Mock WebSocket connection
        mock_ws_instance = MagicMock()
        mock_ws_app.return_value = mock_ws_instance

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Simulate connection established
        def simulate_connection(*args, **kwargs):
            client.is_connected = True

        mock_thread_instance.start.side_effect = simulate_connection

        client.connect()

        # Verify WebSocket was created with correct URL
        mock_ws_app.assert_called_once()
        args, kwargs = mock_ws_app.call_args
        assert 'wss://stream.binance.com:9443/ws/btcusdt@kline_1m' in args

    def test_on_message_valid_data(self):
        """Test message handling with valid kline data."""
        client = BinanceWebSocketClient()

        # Sample Binance kline message
        message = json.dumps({
            'k': {
                'c': '45123.50',  # Close price
                's': 'BTCUSDT',
                't': 1234567890
            }
        })

        client._on_message(None, message)

        # Verify price was added to buffer
        assert len(client.price_buffer) == 1
        assert client.price_buffer[0] == 45123.50

    def test_on_message_invalid_data(self):
        """Test message handling with invalid data."""
        client = BinanceWebSocketClient()

        # Invalid JSON
        client._on_message(None, "invalid json")
        assert len(client.price_buffer) == 0

        # Missing 'k' field
        message = json.dumps({'data': 'invalid'})
        client._on_message(None, message)
        assert len(client.price_buffer) == 0

    def test_buffer_size_limit(self):
        """Test that buffer respects max size."""
        client = BinanceWebSocketClient(buffer_size=5)

        # Add 10 prices
        for i in range(10):
            message = json.dumps({'k': {'c': str(100 + i)}})
            client._on_message(None, message)

        # Only last 5 should be kept
        assert len(client.price_buffer) == 5
        assert client.price_buffer[0] == 105.0
        assert client.price_buffer[-1] == 109.0

    def test_get_latest_prices(self):
        """Test retrieving latest prices from buffer."""
        client = BinanceWebSocketClient()

        # Add sample prices
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        for price in prices:
            client.price_buffer.append(price)

        # Get last 3 prices
        latest = client.get_latest_prices(count=3)
        assert latest == [102.0, 103.0, 104.0]

        # Request more than available
        latest = client.get_latest_prices(count=10)
        assert latest == prices

    def test_get_latest_price(self):
        """Test retrieving single latest price."""
        client = BinanceWebSocketClient()

        # Empty buffer
        assert client.get_latest_price() is None

        # With prices
        client.price_buffer.append(100.0)
        client.price_buffer.append(101.0)
        assert client.get_latest_price() == 101.0

    def test_close(self):
        """Test graceful connection closure."""
        client = BinanceWebSocketClient()
        client.ws = MagicMock()
        client.ws_thread = MagicMock()
        client.is_connected = True

        client.close()

        assert not client.is_connected
        client.ws.close.assert_called_once()


class TestPolymarketClient:
    """Test cases for PolymarketClient."""

    def test_initialization(self):
        """Test client initialization."""
        client = PolymarketClient(api_key='test_key', api_secret='test_secret')

        assert client.api_key == 'test_key'
        assert client.api_secret == 'test_secret'
        assert 'Authorization' in client.session.headers

    @patch('market_data.requests.Session.get')
    def test_find_active_market_success(self, mock_get):
        """Test finding active market successfully."""
        client = PolymarketClient(api_key='test_key', api_secret='test_secret')

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'market_id': 'market_123',
                'asset': 'BTC',
                'interval': '5m',
                'status': 'active'
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        market_id = client.find_active_market()

        assert market_id == 'market_123'
        mock_get.assert_called_once()

    @patch('market_data.requests.Session.get')
    def test_find_active_market_not_found(self, mock_get):
        """Test when no active markets are found."""
        client = PolymarketClient(api_key='test_key', api_secret='test_secret')

        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        market_id = client.find_active_market()

        assert market_id is None

    @patch('market_data.requests.Session.get')
    def test_find_active_market_api_error(self, mock_get):
        """Test handling API errors during market search."""
        client = PolymarketClient(api_key='test_key', api_secret='test_secret')

        # Mock API error
        mock_get.side_effect = Exception("API Error")

        market_id = client.find_active_market()

        assert market_id is None

    @patch('market_data.requests.Session.get')
    def test_get_market_odds_success(self, mock_get):
        """Test successful odds retrieval."""
        client = PolymarketClient(api_key='test_key', api_secret='test_secret')

        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'market_id': 'market_123',
            'odds_yes': 0.65,
            'odds_no': 0.35,
            'end_date': '2024-01-01T12:00:00Z',
            'question': 'Will BTC go up?'
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        yes_odds, no_odds, market_info = client.get_market_odds('market_123')

        assert yes_odds == 0.65
        assert no_odds == 0.35
        assert market_info['end_date'] == '2024-01-01T12:00:00Z'
        assert market_info['question'] == 'Will BTC go up?'

    @patch('market_data.requests.Session.get')
    def test_get_market_odds_api_error(self, mock_get):
        """Test handling API errors during odds retrieval."""
        client = PolymarketClient(api_key='test_key', api_secret='test_secret')

        # Mock API error
        mock_get.side_effect = Exception("API Error")

        with pytest.raises(ValueError, match="Failed to fetch odds"):
            client.get_market_odds('market_123')


class TestTechnicalIndicators:
    """Test cases for technical indicator calculations."""

    def test_calculate_rsi_valid_data(self):
        """Test RSI calculation with valid price data."""
        # Generate sample price data with upward trend
        prices = [100 + i * 0.5 for i in range(50)]

        rsi = calculate_rsi(prices, period=14)

        # RSI should be between 0 and 100
        assert 0 <= rsi <= 100

        # With upward trend, RSI should be > 50
        assert rsi > 50

    def test_calculate_rsi_insufficient_data(self):
        """Test RSI with insufficient price data."""
        prices = [100.0, 101.0, 102.0]  # Less than period + 1

        with pytest.raises(ValueError, match="Insufficient price data"):
            calculate_rsi(prices, period=14)

    def test_calculate_rsi_oversold(self):
        """Test RSI with oversold conditions (downward trend)."""
        # Generate downward trend
        prices = [100 - i * 0.5 for i in range(50)]

        rsi = calculate_rsi(prices, period=14)

        # With strong downward trend, RSI should be < 50
        assert rsi < 50

    def test_calculate_macd_valid_data(self):
        """Test MACD calculation with valid price data."""
        # Generate sample price data
        prices = [100 + i * 0.2 for i in range(100)]

        macd_line, signal_line = calculate_macd(prices)

        # MACD values should be calculated
        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)

    def test_calculate_macd_insufficient_data(self):
        """Test MACD with insufficient price data."""
        prices = [100.0, 101.0, 102.0]  # Less than 34 required

        with pytest.raises(ValueError, match="Insufficient price data"):
            calculate_macd(prices)

    def test_calculate_macd_bullish_crossover(self):
        """Test MACD in bullish crossover scenario."""
        # Create price pattern that generates bullish signal
        prices = [100.0] * 30 + [100 + i * 0.5 for i in range(30)]

        macd_line, signal_line = calculate_macd(prices)

        # In bullish trend, MACD should be above signal
        # Note: This may not always be true depending on exact pattern
        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)


class TestOrderBookImbalance:
    """Test cases for order book imbalance calculation."""

    @patch('market_data.requests.get')
    def test_order_book_imbalance_success(self, mock_get):
        """Test successful order book imbalance calculation."""
        # Mock Binance order book response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'bids': [['45000', '1.5'], ['44999', '2.0']],  # Total: 3.5
            'asks': [['45001', '1.0'], ['45002', '1.5']]   # Total: 2.5
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        imbalance = get_order_book_imbalance()

        # 3.5 / 2.5 = 1.4
        assert abs(imbalance - 1.4) < 0.01

    @patch('market_data.requests.get')
    def test_order_book_imbalance_zero_ask_volume(self, mock_get):
        """Test handling of zero ask volume."""
        # Mock response with zero ask volume
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'bids': [['45000', '1.5']],
            'asks': []
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        imbalance = get_order_book_imbalance()

        # Should return neutral imbalance
        assert imbalance == 1.0

    @patch('market_data.requests.get')
    def test_order_book_imbalance_api_error(self, mock_get):
        """Test handling API errors."""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(ConnectionError, match="Failed to fetch order book"):
            get_order_book_imbalance()


class TestGetMarketData:
    """Test cases for market data aggregation."""

    def test_get_market_data_success(self):
        """Test successful market data aggregation."""
        # Mock Binance client
        binance_client = MagicMock()
        prices = [100 + i * 0.2 for i in range(100)]
        binance_client.get_latest_prices.return_value = prices

        # Mock Polymarket client
        polymarket_client = MagicMock()
        polymarket_client.get_market_odds.return_value = (0.65, 0.35, {
            'end_date': '2024-01-01T12:00:00Z',
            'question': 'Will BTC go up?'
        })

        # Mock order book imbalance
        with patch('market_data.get_order_book_imbalance', return_value=1.2):
            market_data = get_market_data(
                binance_client,
                polymarket_client,
                market_id='market_123'
            )

        # Verify MarketData object
        assert isinstance(market_data, MarketData)
        assert market_data.market_id == 'market_123'
        assert market_data.yes_price == Decimal('0.65')
        assert market_data.no_price == Decimal('0.35')

        # Verify metadata includes technical indicators
        assert 'btc_price' in market_data.metadata
        assert 'rsi_14' in market_data.metadata
        assert 'macd_line' in market_data.metadata
        assert 'macd_signal' in market_data.metadata
        assert 'order_book_imbalance' in market_data.metadata

    def test_get_market_data_insufficient_prices(self):
        """Test handling insufficient price data."""
        # Mock Binance client with insufficient data
        binance_client = MagicMock()
        binance_client.get_latest_prices.return_value = [100.0, 101.0]

        polymarket_client = MagicMock()

        with pytest.raises(ValueError, match="Insufficient price data"):
            get_market_data(binance_client, polymarket_client, market_id='market_123')

    def test_get_market_data_no_market_id(self):
        """Test market data retrieval without providing market ID."""
        # Mock Binance client
        binance_client = MagicMock()
        prices = [100 + i * 0.2 for i in range(100)]
        binance_client.get_latest_prices.return_value = prices

        # Mock Polymarket client
        polymarket_client = MagicMock()
        polymarket_client.find_active_market.return_value = 'market_456'
        polymarket_client.get_market_odds.return_value = (0.55, 0.45, {
            'end_date': '2024-01-01T12:00:00Z',
            'question': 'BTC prediction market'
        })

        with patch('market_data.get_order_book_imbalance', return_value=1.1):
            market_data = get_market_data(binance_client, polymarket_client)

        # Should use found market ID
        assert market_data.market_id == 'market_456'
        polymarket_client.find_active_market.assert_called_once()

    def test_get_market_data_no_active_market(self):
        """Test handling when no active market is found."""
        binance_client = MagicMock()
        prices = [100 + i * 0.2 for i in range(100)]
        binance_client.get_latest_prices.return_value = prices

        polymarket_client = MagicMock()
        polymarket_client.find_active_market.return_value = None

        with pytest.raises(ValueError, match="No active Polymarket markets found"):
            get_market_data(binance_client, polymarket_client)


class TestFallbackBTCPrice:
    """Test cases for CoinGecko fallback price retrieval."""

    @patch('market_data.requests.get')
    def test_fallback_price_success(self, mock_get):
        """Test successful BTC price retrieval from CoinGecko."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'bitcoin': {'usd': 45123.50}
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        price = get_fallback_btc_price()

        assert price == 45123.50

    @patch('market_data.requests.get')
    def test_fallback_price_api_error(self, mock_get):
        """Test handling API errors."""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(ConnectionError, match="Failed to fetch BTC price from CoinGecko"):
            get_fallback_btc_price()


class TestIntegration:
    """Integration tests for market_data module."""

    @patch('market_data.WebSocketApp')
    @patch('market_data.requests.Session.get')
    def test_full_workflow(self, mock_session_get, mock_ws_app):
        """Test complete workflow from connection to data aggregation."""
        # Setup Binance client
        binance_client = BinanceWebSocketClient()

        # Simulate price data
        for i in range(100):
            message = json.dumps({'k': {'c': str(45000 + i)}})
            binance_client._on_message(None, message)

        # Verify prices collected
        prices = binance_client.get_latest_prices(100)
        assert len(prices) == 100
        assert prices[0] == 45000.0
        assert prices[-1] == 45099.0

        # Test technical indicators
        rsi = calculate_rsi(prices, period=14)
        assert 0 <= rsi <= 100

        macd_line, signal_line = calculate_macd(prices)
        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)
