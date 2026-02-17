"""
Unit tests for market_data module.

Tests cover:
- PolymarketClient API interactions
- BinanceWebSocketClient functionality
- Technical indicator calculations (RSI, MACD)
- Order book imbalance calculations
- Error handling and retry logic
- Data transformation and validation
"""

import pytest
import json
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data import (
    PolymarketClient,
    BinanceWebSocketClient,
    PolymarketAPIError,
    BinanceAPIError,
    calculate_rsi,
    calculate_macd,
    get_order_book_imbalance
)
from models import MarketData
from utils import RetryError


class TestPolymarketClient:
    """Test suite for PolymarketClient class."""

    @pytest.fixture
    def client(self):
        """Create a PolymarketClient instance for testing."""
        return PolymarketClient(
            api_key="test_api_key",
            api_secret="test_api_secret",
            base_url="https://api.polymarket.com"
        )

    def test_client_initialization(self, client):
        """Test that client initializes correctly with valid credentials."""
        assert client.api_key == "test_api_key"
        assert client.api_secret == "test_api_secret"
        assert client.base_url == "https://api.polymarket.com"
        assert "Content-Type" in client.session.headers
        assert client.session.headers["Content-Type"] == "application/json"

    def test_client_initialization_empty_api_key(self):
        """Test that client raises ValueError with empty API key."""
        with pytest.raises(Exception):  # ValidationError from utils
            PolymarketClient(api_key="", api_secret="secret")

    def test_client_initialization_empty_api_secret(self):
        """Test that client raises ValueError with empty API secret."""
        with pytest.raises(Exception):  # ValidationError from utils
            PolymarketClient(api_key="key", api_secret="")

    def test_generate_signature(self, client):
        """Test HMAC-SHA256 signature generation."""
        timestamp = "1234567890000"
        method = "GET"
        path = "/markets"
        body = ""

        signature = client._generate_signature(timestamp, method, path, body)

        # Signature should be a hexadecimal string
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 produces 64 hex characters
        assert all(c in '0123456789abcdef' for c in signature)

        # Same inputs should produce same signature (deterministic)
        signature2 = client._generate_signature(timestamp, method, path, body)
        assert signature == signature2

    def test_prepare_authenticated_headers(self, client):
        """Test authenticated headers preparation."""
        method = "GET"
        path = "/markets"
        body = ""

        headers = client._prepare_authenticated_headers(method, path, body)

        # Should contain required authentication headers
        assert "X-API-KEY" in headers
        assert "X-SIGNATURE" in headers
        assert "X-TIMESTAMP" in headers
        assert headers["X-API-KEY"] == "test_api_key"
        assert len(headers["X-SIGNATURE"]) == 64
        assert headers["X-TIMESTAMP"].isdigit()

    @patch('market_data.requests.Session.get')
    def test_find_active_market_success(self, mock_get, client):
        """Test successful market discovery."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "markets": [
                {"market_id": "market_123", "question": "Will BTC reach $100k?"},
                {"market_id": "market_456", "question": "Will BTC drop below $50k?"}
            ]
        }
        mock_get.return_value = mock_response

        market_id = client.find_active_market("BTC")

        assert market_id == "market_123"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "asset" in call_args[1]["params"]
        assert call_args[1]["params"]["asset"] == "BTC"

    @patch('market_data.requests.Session.get')
    def test_find_active_market_no_markets(self, mock_get, client):
        """Test market discovery when no markets are available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"markets": []}
        mock_get.return_value = mock_response

        market_id = client.find_active_market("BTC")

        assert market_id is None

    @patch('market_data.requests.Session.get')
    def test_find_active_market_404(self, mock_get, client):
        """Test market discovery when endpoint returns 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        market_id = client.find_active_market("BTC")

        assert market_id is None

    @patch('market_data.requests.Session.get')
    def test_find_active_market_rate_limit(self, mock_get, client):
        """Test market discovery when rate limited."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with pytest.raises(RetryError):
            client.find_active_market("BTC")

    @patch('market_data.requests.Session.get')
    def test_get_market_odds_success(self, mock_get, client):
        """Test successful odds retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "market_id": "market_123",
            "yes_price": 0.65,
            "no_price": 0.35
        }
        mock_get.return_value = mock_response

        yes_odds, no_odds = client.get_market_odds("market_123")

        assert yes_odds == Decimal("0.65")
        assert no_odds == Decimal("0.35")
        mock_get.assert_called_once()

    @patch('market_data.requests.Session.get')
    def test_get_market_odds_missing_price_data(self, mock_get, client):
        """Test odds retrieval with missing price data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "market_id": "market_123"
            # Missing yes_price and no_price
        }
        mock_get.return_value = mock_response

        with pytest.raises(RetryError):
            client.get_market_odds("market_123")

    @patch('market_data.requests.Session.get')
    def test_get_market_odds_invalid_probabilities(self, mock_get, client):
        """Test odds retrieval with invalid probability values."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "market_id": "market_123",
            "yes_price": 1.5,  # Invalid: > 1.0
            "no_price": 0.35
        }
        mock_get.return_value = mock_response

        with pytest.raises(RetryError):
            client.get_market_odds("market_123")

    @patch('market_data.requests.Session.get')
    def test_get_market_odds_empty_market_id(self, client):
        """Test odds retrieval with empty market ID."""
        with pytest.raises(Exception):  # ValidationError
            client.get_market_odds("")

    @patch('market_data.requests.Session.get')
    def test_get_market_details_success(self, mock_get, client):
        """Test successful market details retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        end_date = (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'
        mock_response.json.return_value = {
            "market_id": "market_123",
            "question": "Will BTC reach $100k in 2024?",
            "description": "Market resolves YES if BTC reaches $100k",
            "yes_price": 0.65,
            "no_price": 0.35,
            "yes_volume": 150000.0,
            "no_volume": 85000.0,
            "liquidity": 50000.0,
            "is_active": True,
            "is_closed": False,
            "end_date": end_date,
            "category": "Crypto",
            "tags": ["BTC", "price"]
        }
        mock_get.return_value = mock_response

        market_data = client.get_market_details("market_123")

        assert isinstance(market_data, MarketData)
        assert market_data.market_id == "market_123"
        assert market_data.question == "Will BTC reach $100k in 2024?"
        assert market_data.yes_price == Decimal("0.65")
        assert market_data.no_price == Decimal("0.35")
        assert market_data.is_active is True
        assert market_data.category == "Crypto"

    @patch('market_data.requests.Session.get')
    def test_get_market_details_404(self, mock_get, client):
        """Test market details retrieval for non-existent market."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with pytest.raises(RetryError):
            client.get_market_details("nonexistent_market")

    def test_transform_to_market_data_minimal(self, client):
        """Test transformation with minimal API response."""
        api_response = {
            "market_id": "market_123",
            "question": "Test question",
            "yes_price": 0.5,
            "no_price": 0.5
        }

        market_data = client._transform_to_market_data(api_response)

        assert market_data.market_id == "market_123"
        assert market_data.question == "Test question"
        assert market_data.yes_price == Decimal("0.5")
        assert market_data.no_price == Decimal("0.5")

    def test_transform_to_market_data_complete(self, client):
        """Test transformation with complete API response."""
        end_date = (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'
        api_response = {
            "market_id": "market_123",
            "question": "Will BTC reach $100k?",
            "description": "Full description",
            "yes_price": 0.65,
            "no_price": 0.35,
            "yes_volume": 100000,
            "no_volume": 50000,
            "liquidity": 25000,
            "is_active": True,
            "is_closed": False,
            "end_date": end_date,
            "category": "Crypto",
            "tags": ["BTC"],
            "metadata": {"source": "api"}
        }

        market_data = client._transform_to_market_data(api_response)

        assert market_data.description == "Full description"
        assert market_data.category == "Crypto"
        assert market_data.tags == ["BTC"]
        assert market_data.metadata == {"source": "api"}

    def test_client_close(self, client):
        """Test that client session closes properly."""
        with patch.object(client.session, 'close') as mock_close:
            client.close()
            mock_close.assert_called_once()


class TestBinanceWebSocketClient:
    """Test suite for BinanceWebSocketClient class."""

    @pytest.fixture
    def ws_client(self):
        """Create a BinanceWebSocketClient instance for testing."""
        return BinanceWebSocketClient(symbol="btcusdt", buffer_size=100)

    def test_ws_client_initialization(self, ws_client):
        """Test that WebSocket client initializes correctly."""
        assert ws_client.symbol == "btcusdt"
        assert ws_client.buffer_size == 100
        assert ws_client.price_buffer == []
        assert ws_client.is_connected is False

    def test_ws_on_open(self, ws_client):
        """Test WebSocket on_open callback."""
        ws_client._on_open(None)
        assert ws_client.is_connected is True

    def test_ws_on_message_valid(self, ws_client):
        """Test WebSocket message handling with valid data."""
        message = json.dumps({
            "k": {
                "c": "50000.50"  # Close price
            }
        })

        ws_client._on_message(None, message)

        assert len(ws_client.price_buffer) == 1
        assert ws_client.price_buffer[0] == 50000.50

    def test_ws_on_message_multiple_prices(self, ws_client):
        """Test WebSocket message handling with multiple prices."""
        for i in range(5):
            message = json.dumps({
                "k": {"c": f"{50000 + i}.00"}
            })
            ws_client._on_message(None, message)

        assert len(ws_client.price_buffer) == 5
        assert ws_client.price_buffer[-1] == 50004.0

    def test_ws_on_message_buffer_limit(self):
        """Test that price buffer respects size limit."""
        ws_client = BinanceWebSocketClient(buffer_size=3)

        for i in range(5):
            message = json.dumps({
                "k": {"c": f"{50000 + i}.00"}
            })
            ws_client._on_message(None, message)

        assert len(ws_client.price_buffer) == 3
        assert ws_client.price_buffer == [50002.0, 50003.0, 50004.0]

    def test_ws_on_message_invalid_json(self, ws_client):
        """Test WebSocket message handling with invalid JSON."""
        ws_client._on_message(None, "invalid json")
        assert len(ws_client.price_buffer) == 0

    def test_ws_on_error(self, ws_client):
        """Test WebSocket error callback."""
        ws_client.is_connected = True
        ws_client._on_error(None, "Test error")
        assert ws_client.is_connected is False

    def test_ws_on_close(self, ws_client):
        """Test WebSocket close callback."""
        ws_client.is_connected = True
        ws_client._on_close(None, 1000, "Normal closure")
        assert ws_client.is_connected is False

    def test_get_latest_prices_full_buffer(self, ws_client):
        """Test getting latest prices with full buffer."""
        for i in range(10):
            ws_client.price_buffer.append(50000.0 + i)

        prices = ws_client.get_latest_prices(5)

        assert len(prices) == 5
        assert prices == [50005.0, 50006.0, 50007.0, 50008.0, 50009.0]

    def test_get_latest_prices_partial_buffer(self, ws_client):
        """Test getting latest prices with partial buffer."""
        for i in range(3):
            ws_client.price_buffer.append(50000.0 + i)

        prices = ws_client.get_latest_prices(10)

        assert len(prices) == 3
        assert prices == [50000.0, 50001.0, 50002.0]

    def test_get_latest_prices_empty_buffer(self, ws_client):
        """Test getting latest prices from empty buffer."""
        prices = ws_client.get_latest_prices(10)
        assert prices == []

    def test_get_latest_price(self, ws_client):
        """Test getting single latest price."""
        ws_client.price_buffer = [50000.0, 50001.0, 50002.0]
        price = ws_client.get_latest_price()
        assert price == 50002.0

    def test_get_latest_price_empty_buffer(self, ws_client):
        """Test getting latest price from empty buffer."""
        price = ws_client.get_latest_price()
        assert price is None


class TestTechnicalIndicators:
    """Test suite for technical indicator calculations."""

    def test_calculate_rsi_valid(self):
        """Test RSI calculation with valid data."""
        # Create price series with upward trend
        prices = [100.0 + i * 0.5 for i in range(30)]
        rsi = calculate_rsi(prices, period=14)

        assert rsi is not None
        assert 0 <= rsi <= 100

    def test_calculate_rsi_insufficient_data(self):
        """Test RSI calculation with insufficient data."""
        prices = [100.0, 101.0, 102.0]  # Only 3 prices
        rsi = calculate_rsi(prices, period=14)

        assert rsi is None

    def test_calculate_rsi_extreme_values(self):
        """Test RSI with extreme market conditions."""
        # All gains (should approach 100)
        prices = [100.0 + i for i in range(30)]
        rsi = calculate_rsi(prices, period=14)

        assert rsi is not None
        assert rsi > 70  # Overbought condition

    def test_calculate_macd_valid(self):
        """Test MACD calculation with valid data."""
        # Create price series
        prices = [100.0 + i * 0.5 for i in range(50)]
        result = calculate_macd(prices)

        assert result is not None
        macd_line, signal_line = result
        assert isinstance(macd_line, float)
        assert isinstance(signal_line, float)

    def test_calculate_macd_insufficient_data(self):
        """Test MACD calculation with insufficient data."""
        prices = [100.0, 101.0, 102.0]
        result = calculate_macd(prices)

        assert result is None

    def test_calculate_macd_custom_periods(self):
        """Test MACD calculation with custom periods."""
        prices = [100.0 + i * 0.5 for i in range(50)]
        result = calculate_macd(
            prices,
            fast_period=8,
            slow_period=21,
            signal_period=5
        )

        assert result is not None

    def test_calculate_macd_trending_market(self):
        """Test MACD with trending market data."""
        # Strong uptrend
        prices = [100.0 + i for i in range(50)]
        result = calculate_macd(prices)

        assert result is not None
        macd_line, signal_line = result
        # In uptrend, MACD line should be positive
        assert macd_line > 0


class TestOrderBookImbalance:
    """Test suite for order book imbalance calculations."""

    @patch('market_data.requests.get')
    def test_get_order_book_imbalance_success(self, mock_get):
        """Test successful order book imbalance calculation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bids": [
                ["50000.00", "1.0"],
                ["49999.00", "2.0"]
            ],
            "asks": [
                ["50001.00", "1.5"],
                ["50002.00", "1.5"]
            ]
        }
        mock_get.return_value = mock_response

        imbalance = get_order_book_imbalance("BTCUSDT")

        assert imbalance is not None
        # bid_volume = 3.0, ask_volume = 3.0, imbalance = 1.0
        assert imbalance == 1.0

    @patch('market_data.requests.get')
    def test_get_order_book_imbalance_buying_pressure(self, mock_get):
        """Test order book with buying pressure (imbalance > 1)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bids": [
                ["50000.00", "3.0"],
                ["49999.00", "3.0"]
            ],
            "asks": [
                ["50001.00", "1.0"],
                ["50002.00", "1.0"]
            ]
        }
        mock_get.return_value = mock_response

        imbalance = get_order_book_imbalance("BTCUSDT")

        assert imbalance is not None
        # bid_volume = 6.0, ask_volume = 2.0, imbalance = 3.0
        assert imbalance == 3.0

    @patch('market_data.requests.get')
    def test_get_order_book_imbalance_selling_pressure(self, mock_get):
        """Test order book with selling pressure (imbalance < 1)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bids": [
                ["50000.00", "1.0"],
                ["49999.00", "1.0"]
            ],
            "asks": [
                ["50001.00", "4.0"],
                ["50002.00", "4.0"]
            ]
        }
        mock_get.return_value = mock_response

        imbalance = get_order_book_imbalance("BTCUSDT")

        assert imbalance is not None
        # bid_volume = 2.0, ask_volume = 8.0, imbalance = 0.25
        assert imbalance == 0.25

    @patch('market_data.requests.get')
    def test_get_order_book_imbalance_zero_asks(self, mock_get):
        """Test order book with zero ask volume."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bids": [["50000.00", "1.0"]],
            "asks": []
        }
        mock_get.return_value = mock_response

        imbalance = get_order_book_imbalance("BTCUSDT")

        assert imbalance is None

    @patch('market_data.requests.get')
    def test_get_order_book_imbalance_request_failure(self, mock_get):
        """Test order book imbalance when request fails."""
        mock_get.side_effect = requests.RequestException("Connection error")

        imbalance = get_order_book_imbalance("BTCUSDT")

        assert imbalance is None

    @patch('market_data.requests.get')
    def test_get_order_book_imbalance_invalid_response(self, mock_get):
        """Test order book imbalance with invalid response format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Missing bids and asks
        mock_get.return_value = mock_response

        imbalance = get_order_book_imbalance("BTCUSDT")

        # Should return None for invalid response
        assert imbalance is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
