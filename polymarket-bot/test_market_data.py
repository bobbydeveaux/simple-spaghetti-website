"""
Integration tests for Market Data Service.

Tests verify the complete data flow from sources (Binance, Polymarket)
to the unified MarketDataService interface.
"""

import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from market_data import (
    BinanceWebSocketClient,
    PolymarketClient,
    MarketDataService,
    calculate_rsi,
    calculate_macd,
    get_order_book_imbalance,
    _calculate_ema
)
from models import MarketData
from utils import ValidationError


class TestCalculateRSI:
    """Test RSI calculation function."""

    def test_rsi_with_sufficient_data(self):
        """Test RSI calculation with sufficient price data."""
        # Create price data with known trend
        prices = [
            100.0, 101.0, 102.0, 103.0, 104.0,
            105.0, 106.0, 107.0, 108.0, 109.0,
            110.0, 111.0, 112.0, 113.0, 114.0,
            115.0  # 16 prices (need 15 for period=14)
        ]

        rsi = calculate_rsi(prices, period=14)

        # RSI should be high (>50) for uptrend
        assert 50 < rsi <= 100
        assert isinstance(rsi, float)

    def test_rsi_with_downtrend(self):
        """Test RSI calculation with downtrend data."""
        prices = [
            100.0, 99.0, 98.0, 97.0, 96.0,
            95.0, 94.0, 93.0, 92.0, 91.0,
            90.0, 89.0, 88.0, 87.0, 86.0,
            85.0
        ]

        rsi = calculate_rsi(prices, period=14)

        # RSI should be low (<50) for downtrend
        assert 0 <= rsi < 50

    def test_rsi_with_insufficient_data(self):
        """Test RSI calculation with insufficient data raises error."""
        prices = [100.0, 101.0, 102.0]  # Only 3 prices

        with pytest.raises(ValidationError) as exc_info:
            calculate_rsi(prices, period=14)

        assert "Insufficient data" in str(exc_info.value)

    def test_rsi_boundary_values(self):
        """Test RSI handles extreme cases."""
        # All gains
        prices = [float(i) for i in range(1, 30)]
        rsi = calculate_rsi(prices, period=14)
        assert 80 < rsi <= 100

        # All losses
        prices = [float(30 - i) for i in range(1, 30)]
        rsi = calculate_rsi(prices, period=14)
        assert 0 <= rsi < 20


class TestCalculateMACD:
    """Test MACD calculation function."""

    def test_macd_with_sufficient_data(self):
        """Test MACD calculation with sufficient price data."""
        # Need at least 26 + 9 = 35 prices
        prices = [100.0 + i * 0.5 for i in range(50)]

        macd_line, signal_line = calculate_macd(prices)

        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)
        # In an uptrend, MACD line should be positive
        assert macd_line > 0

    def test_macd_with_downtrend(self):
        """Test MACD calculation with downtrend data."""
        prices = [100.0 - i * 0.5 for i in range(50)]

        macd_line, signal_line = calculate_macd(prices)

        # In a downtrend, MACD line should be negative
        assert macd_line < 0

    def test_macd_with_insufficient_data(self):
        """Test MACD calculation with insufficient data raises error."""
        prices = [100.0 + i for i in range(20)]  # Only 20 prices

        with pytest.raises(ValidationError) as exc_info:
            calculate_macd(prices)

        assert "Insufficient data" in str(exc_info.value)

    def test_macd_custom_periods(self):
        """Test MACD calculation with custom period values."""
        prices = [100.0 + i * 0.5 for i in range(50)]

        macd_line, signal_line = calculate_macd(
            prices,
            fast_period=8,
            slow_period=17,
            signal_period=9
        )

        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)


class TestCalculateEMA:
    """Test EMA helper function."""

    def test_ema_calculation(self):
        """Test EMA calculation produces correct values."""
        prices = [100.0, 102.0, 104.0, 103.0, 105.0, 107.0, 106.0, 108.0]

        ema = _calculate_ema(prices, period=5)

        assert len(ema) == 4  # 8 prices - 5 period + 1
        assert all(isinstance(val, float) for val in ema)

    def test_ema_with_insufficient_data(self):
        """Test EMA returns empty list with insufficient data."""
        prices = [100.0, 101.0]

        ema = _calculate_ema(prices, period=5)

        assert ema == []


class TestBinanceWebSocketClient:
    """Test Binance WebSocket client."""

    def test_initialization(self):
        """Test client initializes with correct parameters."""
        client = BinanceWebSocketClient(
            symbol="btcusdt",
            interval="1m",
            buffer_size=100
        )

        assert client.symbol == "btcusdt"
        assert client.interval == "1m"
        assert client.buffer_size == 100
        assert len(client.price_buffer) == 0
        assert client.latest_price is None
        assert not client.is_connected

    def test_on_message_parsing(self):
        """Test WebSocket message parsing."""
        client = BinanceWebSocketClient()

        # Simulate WebSocket message
        message = '''
        {
            "e": "kline",
            "E": 1638747660000,
            "s": "BTCUSDT",
            "k": {
                "t": 1638747600000,
                "T": 1638747659999,
                "s": "BTCUSDT",
                "i": "1m",
                "f": 100,
                "L": 200,
                "o": "50000.00",
                "c": "50100.00",
                "h": "50200.00",
                "l": "49900.00",
                "v": "100",
                "n": 100,
                "x": true,
                "q": "5000000",
                "V": "50",
                "Q": "2500000"
            }
        }
        '''

        client._on_message(None, message)

        assert client.latest_price == 50100.00
        assert len(client.price_buffer) == 1
        assert client.price_buffer[0] == 50100.00

    def test_on_message_partial_kline(self):
        """Test WebSocket message with unclosed kline."""
        client = BinanceWebSocketClient()

        # Kline not closed (x: false)
        message = '''
        {
            "k": {
                "c": "50100.00",
                "x": false
            }
        }
        '''

        client._on_message(None, message)

        # Latest price should be updated
        assert client.latest_price == 50100.00
        # But buffer should not be updated (kline not closed)
        assert len(client.price_buffer) == 0

    def test_get_latest_price(self):
        """Test getting latest price."""
        client = BinanceWebSocketClient()

        # Initially None
        assert client.get_latest_price() is None

        # Set a price
        client.latest_price = 50000.0

        assert client.get_latest_price() == 50000.0

    def test_get_price_history(self):
        """Test getting price history."""
        client = BinanceWebSocketClient(buffer_size=10)

        # Add some prices
        for i in range(15):
            client.price_buffer.append(float(50000 + i * 100))

        # Should only have last 10 (buffer_size)
        history = client.get_price_history()
        assert len(history) == 10

        # Get last 5 prices
        history = client.get_price_history(count=5)
        assert len(history) == 5
        assert history[-1] == 51400.0  # Last price


class TestPolymarketClient:
    """Test Polymarket API client."""

    def test_initialization(self):
        """Test client initializes with credentials."""
        client = PolymarketClient(
            api_key="test_key",
            api_secret="test_secret",
            base_url="https://api.test.com"
        )

        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert client.base_url == "https://api.test.com"
        assert "Bearer test_key" in client.headers["Authorization"]

    @patch('market_data.requests.get')
    def test_find_active_btc_market_success(self, mock_get):
        """Test finding active BTC market."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "market_id": "market_123",
                "question": "Will BTC reach $100k?",
                "category": "crypto",
                "status": "active"
            }
        ]
        mock_get.return_value = mock_response

        client = PolymarketClient("key", "secret")
        market = client.find_active_btc_market()

        assert market is not None
        assert market["market_id"] == "market_123"
        assert "BTC" in market["question"] or market["category"] == "crypto"

    @patch('market_data.requests.get')
    def test_find_active_btc_market_no_markets(self, mock_get):
        """Test finding market when none available."""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        client = PolymarketClient("key", "secret")
        market = client.find_active_btc_market()

        assert market is None

    @patch('market_data.requests.get')
    def test_get_market_odds_success(self, mock_get):
        """Test getting market odds."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "market_id": "market_123",
            "yes_price": 0.65,
            "no_price": 0.35
        }
        mock_get.return_value = mock_response

        client = PolymarketClient("key", "secret")
        yes_odds, no_odds = client.get_market_odds("market_123")

        assert yes_odds == Decimal("0.65")
        assert no_odds == Decimal("0.35")

    @patch('market_data.requests.get')
    def test_get_market_odds_invalid(self, mock_get):
        """Test getting invalid market odds raises error."""
        # Mock response with invalid odds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "yes_price": 1.5,  # Invalid (> 1)
            "no_price": 0.35
        }
        mock_get.return_value = mock_response

        client = PolymarketClient("key", "secret")

        with pytest.raises(ValidationError) as exc_info:
            client.get_market_odds("market_123")

        assert "Invalid odds" in str(exc_info.value)


class TestMarketDataService:
    """Test unified MarketDataService."""

    def test_initialization(self):
        """Test service initializes with clients."""
        binance_client = BinanceWebSocketClient()
        polymarket_client = PolymarketClient("key", "secret")

        service = MarketDataService(binance_client, polymarket_client)

        assert service.binance_ws == binance_client
        assert service.polymarket == polymarket_client
        assert service.active_market_id is None

    @patch.object(BinanceWebSocketClient, 'connect')
    @patch.object(BinanceWebSocketClient, 'get_latest_price')
    def test_start(self, mock_get_price, mock_connect):
        """Test service start connects to Binance."""
        mock_get_price.return_value = 50000.0

        binance_client = BinanceWebSocketClient()
        polymarket_client = PolymarketClient("key", "secret")
        service = MarketDataService(binance_client, polymarket_client)

        service.start()

        mock_connect.assert_called_once()

    @patch.object(BinanceWebSocketClient, 'close')
    def test_stop(self, mock_close):
        """Test service stop closes connections."""
        binance_client = BinanceWebSocketClient()
        polymarket_client = PolymarketClient("key", "secret")
        service = MarketDataService(binance_client, polymarket_client)

        service.stop()

        mock_close.assert_called_once()

    @patch.object(BinanceWebSocketClient, 'get_latest_price')
    @patch.object(BinanceWebSocketClient, 'get_price_history')
    @patch.object(PolymarketClient, 'find_active_btc_market')
    @patch.object(PolymarketClient, 'get_market_odds')
    def test_get_market_data_success(
        self,
        mock_get_odds,
        mock_find_market,
        mock_get_history,
        mock_get_price
    ):
        """Test getting complete market data."""
        # Setup mocks
        mock_get_price.return_value = 50000.0
        mock_get_history.return_value = [float(50000 + i * 10) for i in range(50)]
        mock_find_market.return_value = {
            "market_id": "market_123",
            "question": "Will BTC reach $100k?"
        }
        mock_get_odds.return_value = (Decimal("0.65"), Decimal("0.35"))

        # Create service
        binance_client = BinanceWebSocketClient()
        polymarket_client = PolymarketClient("key", "secret")
        service = MarketDataService(binance_client, polymarket_client)

        # Get market data
        data = service.get_market_data()

        # Verify data
        assert isinstance(data, MarketData)
        assert data.market_id == "market_123"
        assert data.yes_price == Decimal("0.65")
        assert data.no_price == Decimal("0.35")
        assert "btc_price" in data.metadata
        assert data.metadata["btc_price"] == 50000.0
        assert "rsi_14" in data.metadata
        assert "macd_line" in data.metadata
        assert "macd_signal" in data.metadata

    @patch.object(BinanceWebSocketClient, 'get_latest_price')
    def test_get_market_data_no_price(self, mock_get_price):
        """Test getting market data without price raises error."""
        mock_get_price.return_value = None

        binance_client = BinanceWebSocketClient()
        polymarket_client = PolymarketClient("key", "secret")
        service = MarketDataService(binance_client, polymarket_client)

        with pytest.raises(ValidationError) as exc_info:
            service.get_market_data()

        assert "No BTC price data" in str(exc_info.value)

    @patch.object(BinanceWebSocketClient, 'get_latest_price')
    @patch.object(BinanceWebSocketClient, 'get_price_history')
    @patch.object(PolymarketClient, 'find_active_btc_market')
    def test_get_market_data_insufficient_history(
        self,
        mock_find_market,
        mock_get_history,
        mock_get_price
    ):
        """Test getting market data with insufficient price history."""
        mock_get_price.return_value = 50000.0
        mock_get_history.return_value = [50000.0, 50100.0]  # Only 2 prices
        mock_find_market.return_value = None

        binance_client = BinanceWebSocketClient()
        polymarket_client = PolymarketClient("key", "secret")
        service = MarketDataService(binance_client, polymarket_client)

        # Should use default values instead of raising error
        data = service.get_market_data()

        assert isinstance(data, MarketData)
        # Should have default indicator values
        assert data.metadata["rsi_14"] == 50.0
        assert data.metadata["macd_line"] == 0.0
        assert data.metadata["macd_signal"] == 0.0

    @patch.object(BinanceWebSocketClient, 'get_latest_price')
    @patch.object(BinanceWebSocketClient, 'get_price_history')
    @patch.object(PolymarketClient, 'find_active_btc_market')
    @patch.object(PolymarketClient, 'get_market_odds')
    def test_get_market_data_odds_failure(
        self,
        mock_get_odds,
        mock_find_market,
        mock_get_history,
        mock_get_price
    ):
        """Test getting market data when odds retrieval fails."""
        mock_get_price.return_value = 50000.0
        mock_get_history.return_value = [float(50000 + i * 10) for i in range(50)]
        mock_find_market.return_value = {"market_id": "market_123"}
        mock_get_odds.side_effect = Exception("API error")

        binance_client = BinanceWebSocketClient()
        polymarket_client = PolymarketClient("key", "secret")
        service = MarketDataService(binance_client, polymarket_client)

        # Should use default odds instead of raising error
        data = service.get_market_data()

        assert isinstance(data, MarketData)
        assert data.yes_price == Decimal("0.5")
        assert data.no_price == Decimal("0.5")


class TestGetOrderBookImbalance:
    """Test order book imbalance calculation."""

    @patch('market_data.requests.get')
    def test_order_book_imbalance_success(self, mock_get):
        """Test calculating order book imbalance."""
        # Mock order book response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bids": [
                ["50000", "1.0"],
                ["49990", "2.0"],
                ["49980", "3.0"]
            ],
            "asks": [
                ["50010", "1.5"],
                ["50020", "2.5"],
                ["50030", "1.0"]
            ]
        }
        mock_get.return_value = mock_response

        imbalance = get_order_book_imbalance("key", "secret")

        # Bid volume = 1 + 2 + 3 = 6
        # Ask volume = 1.5 + 2.5 + 1 = 5
        # Imbalance = 6 / 5 = 1.2
        assert abs(imbalance - 1.2) < 0.001

    @patch('market_data.requests.get')
    def test_order_book_imbalance_zero_ask_volume(self, mock_get):
        """Test order book with zero ask volume raises error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bids": [["50000", "1.0"]],
            "asks": []
        }
        mock_get.return_value = mock_response

        with pytest.raises(ValidationError) as exc_info:
            get_order_book_imbalance("key", "secret")

        assert "Ask volume is zero" in str(exc_info.value)


class TestIntegrationFlow:
    """Integration tests for complete data flow."""

    @patch('market_data.requests.get')
    @patch.object(BinanceWebSocketClient, 'get_latest_price')
    @patch.object(BinanceWebSocketClient, 'get_price_history')
    def test_complete_market_data_flow(
        self,
        mock_get_history,
        mock_get_price,
        mock_requests_get
    ):
        """Test complete flow from data sources to MarketData model."""
        # Setup Binance mocks
        mock_get_price.return_value = 50000.0
        mock_get_history.return_value = [float(50000 + i * 10) for i in range(50)]

        # Setup Polymarket mocks
        def mock_api_response(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200

            if "/markets" in url:
                mock_response.json.return_value = [{
                    "market_id": "market_xyz",
                    "question": "Will BTC moon?"
                }]
            elif "/odds" in url:
                mock_response.json.return_value = {
                    "yes_price": 0.72,
                    "no_price": 0.28
                }

            return mock_response

        mock_requests_get.side_effect = mock_api_response

        # Create service
        binance_client = BinanceWebSocketClient()
        polymarket_client = PolymarketClient("test_key", "test_secret")
        service = MarketDataService(binance_client, polymarket_client)

        # Get market data
        market_data = service.get_market_data()

        # Verify complete data
        assert isinstance(market_data, MarketData)
        assert market_data.market_id == "market_xyz"
        assert market_data.yes_price == Decimal("0.72")
        assert market_data.no_price == Decimal("0.28")
        assert market_data.metadata["btc_price"] == 50000.0
        assert "rsi_14" in market_data.metadata
        assert "macd_line" in market_data.metadata
        assert market_data.metadata["price_history_length"] == 50
