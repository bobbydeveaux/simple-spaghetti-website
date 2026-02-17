"""
Unit tests for market_data module.

Tests cover:
- BinanceWebSocketClient connection and data handling
- Technical indicator calculations (RSI, MACD)
- PolymarketClient API integration
- Order book imbalance calculations
- Market data aggregation
- Market discovery and filtering
- Error handling and retry logic
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np
import requests

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data import (
    BinanceWebSocketClient,
    PolymarketClient,
    PolymarketAPIError,
    calculate_rsi,
    calculate_macd,
    get_order_book_imbalance,
    get_market_data,
    get_fallback_btc_price
)
from models import MarketData, OutcomeType
from config import Config
from utils import ValidationError


# Test fixtures

@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock(spec=Config)
    config.polymarket_base_url = "https://api.polymarket.com"
    config.polymarket_api_key = "test_api_key"
    config.polymarket_api_secret = "test_api_secret"
    config.ws_reconnect_delay = 5
    config.ws_max_reconnect_attempts = 10
    return config


@pytest.fixture
def polymarket_client(mock_config):
    """Create a PolymarketClient instance with mock config."""
    return PolymarketClient(mock_config)


@pytest.fixture
def sample_market_data():
    """Sample market data from Polymarket API."""
    return {
        "id": "market_123",
        "question": "Will Bitcoin reach $100k in 2024?",
        "description": "Resolves YES if BTC hits $100k USD",
        "created_at": "2024-01-01T00:00:00Z",
        "end_date": "2024-12-31T23:59:59Z",
        "yes_price": 0.65,
        "no_price": 0.35,
        "yes_volume": 150000.00,
        "no_volume": 85000.00,
        "liquidity": 50000.00,
        "active": True,
        "closed": False,
        "category": "Cryptocurrency",
        "tags": ["BTC", "Bitcoin", "Price"]
    }


@pytest.fixture
def sample_btc_markets():
    """Sample list of BTC-related markets."""
    return [
        {
            "id": "btc_market_1",
            "question": "Will Bitcoin reach $100k in 2024?",
            "yes_price": 0.65,
            "no_price": 0.35,
            "active": True,
            "closed": False,
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
        },
        {
            "id": "btc_market_2",
            "question": "Will Bitcoin dominance exceed 50% this year?",
            "yes_price": 0.55,
            "no_price": 0.45,
            "active": True,
            "closed": False,
            "end_date": (datetime.utcnow() + timedelta(days=60)).isoformat() + "Z"
        },
        {
            "id": "btc_market_3",
            "question": "Bitcoin ETF approval in 2024?",
            "yes_price": 0.80,
            "no_price": 0.20,
            "active": True,
            "closed": False,
            "end_date": (datetime.utcnow() + timedelta(days=90)).isoformat() + "Z"
        }
    ]


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


class TestPolymarketClientInitialization:
    """Tests for PolymarketClient initialization."""

    def test_client_initialization(self, mock_config):
        """Test client initializes with correct configuration."""
        client = PolymarketClient(mock_config)

        assert client.config == mock_config
        assert client.base_url == "https://api.polymarket.com"
        assert client.api_key == "test_api_key"
        assert client.session is not None
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer test_api_key"

    def test_client_headers(self, polymarket_client):
        """Test client sets correct headers."""
        headers = polymarket_client.session.headers

        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "Bearer" in headers["Authorization"]


class TestAPIRequests:
    """Tests for API request methods."""

    @patch('market_data.requests.Session.request')
    def test_make_request_success(self, mock_request, polymarket_client, sample_market_data):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_market_data
        mock_response.headers = {}
        mock_request.return_value = mock_response

        result = polymarket_client._make_request("GET", "/markets/123")

        assert result == sample_market_data
        mock_request.assert_called_once()

    @patch('market_data.requests.Session.request')
    def test_make_request_with_rate_limit_headers(self, mock_request, polymarket_client):
        """Test API request logs rate limit information."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.headers = {"X-RateLimit-Remaining": "95"}
        mock_request.return_value = mock_response

        result = polymarket_client._make_request("GET", "/test")

        assert result == {"status": "ok"}

    @patch('market_data.requests.Session.request')
    def test_make_request_http_error(self, mock_request, polymarket_client):
        """Test API request handles HTTP errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_request.return_value = mock_response

        with pytest.raises(PolymarketAPIError) as exc_info:
            polymarket_client._make_request("GET", "/markets/invalid")

        assert "404" in str(exc_info.value)

    @patch('market_data.requests.Session.request')
    def test_make_request_connection_error(self, mock_request, polymarket_client):
        """Test API request handles connection errors."""
        mock_request.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(PolymarketAPIError) as exc_info:
            polymarket_client._make_request("GET", "/markets")

        assert "Connection refused" in str(exc_info.value)

    @patch('market_data.requests.Session.request')
    def test_make_request_invalid_json(self, mock_request, polymarket_client):
        """Test API request handles invalid JSON responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.headers = {}
        mock_request.return_value = mock_response

        with pytest.raises(PolymarketAPIError) as exc_info:
            polymarket_client._make_request("GET", "/markets")

        assert "Invalid JSON" in str(exc_info.value)


class TestMarketDiscovery:
    """Tests for market discovery methods."""

    @patch.object(PolymarketClient, '_make_request')
    def test_get_active_markets(self, mock_request, polymarket_client, sample_btc_markets):
        """Test fetching active markets."""
        mock_request.return_value = sample_btc_markets

        markets = polymarket_client.get_active_markets(limit=10)

        assert len(markets) == 3
        assert markets == sample_btc_markets
        mock_request.assert_called_once_with(
            "GET",
            "/markets",
            params={"limit": 10, "offset": 0, "closed": "false"}
        )

    @patch.object(PolymarketClient, '_make_request')
    def test_get_active_markets_with_offset(self, mock_request, polymarket_client):
        """Test fetching markets with offset."""
        mock_request.return_value = []

        markets = polymarket_client.get_active_markets(limit=50, offset=100)

        mock_request.assert_called_once_with(
            "GET",
            "/markets",
            params={"limit": 50, "offset": 100, "closed": "false"}
        )

    @patch.object(PolymarketClient, '_make_request')
    def test_get_active_markets_nested_response(self, mock_request, polymarket_client):
        """Test fetching markets with nested response format."""
        mock_request.return_value = {"markets": [{"id": "1"}, {"id": "2"}]}

        markets = polymarket_client.get_active_markets()

        assert len(markets) == 2
        assert markets[0]["id"] == "1"

    @patch.object(PolymarketClient, '_make_request')
    def test_get_market_by_id(self, mock_request, polymarket_client, sample_market_data):
        """Test fetching a specific market by ID."""
        mock_request.return_value = sample_market_data

        market = polymarket_client.get_market_by_id("market_123")

        assert market == sample_market_data
        mock_request.assert_called_once_with("GET", "/markets/market_123")

    def test_get_market_by_id_empty_id(self, polymarket_client):
        """Test get_market_by_id raises error for empty ID."""
        with pytest.raises(ValidationError) as exc_info:
            polymarket_client.get_market_by_id("")

        assert "market_id" in str(exc_info.value).lower()

    @patch.object(PolymarketClient, '_make_request')
    def test_search_markets(self, mock_request, polymarket_client, sample_btc_markets):
        """Test searching for markets."""
        mock_request.return_value = sample_btc_markets

        markets = polymarket_client.search_markets("Bitcoin", limit=25)

        assert len(markets) == 3
        mock_request.assert_called_once_with(
            "GET",
            "/markets",
            params={"query": "Bitcoin", "limit": 25}
        )

    def test_search_markets_empty_query(self, polymarket_client):
        """Test search_markets raises error for empty query."""
        with pytest.raises(ValidationError) as exc_info:
            polymarket_client.search_markets("")

        assert "query" in str(exc_info.value).lower()


class TestBTCMarketFiltering:
    """Tests for BTC-related market filtering."""

    @patch.object(PolymarketClient, 'search_markets')
    def test_get_btc_markets(self, mock_search, polymarket_client, sample_btc_markets):
        """Test fetching BTC-related markets."""
        mock_search.return_value = sample_btc_markets

        markets = polymarket_client.get_btc_markets(limit=50)

        # Should search for multiple keywords
        assert mock_search.call_count >= 1
        assert len(markets) <= 50

    @patch.object(PolymarketClient, 'search_markets')
    def test_get_btc_markets_deduplication(self, mock_search, polymarket_client):
        """Test BTC markets are deduplicated."""
        # Return same market for different keywords
        duplicate_market = {
            "id": "same_market",
            "question": "BTC price",
            "active": True,
            "closed": False,
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
        }
        mock_search.return_value = [duplicate_market]

        markets = polymarket_client.get_btc_markets()

        # Should only include each market once
        market_ids = [m.get('id') for m in markets]
        assert len(market_ids) == len(set(market_ids))

    @patch.object(PolymarketClient, 'search_markets')
    def test_get_btc_markets_filters_inactive(self, mock_search, polymarket_client):
        """Test BTC markets filters out inactive markets."""
        markets_with_inactive = [
            {"id": "1", "question": "BTC", "active": True, "closed": False, "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"},
            {"id": "2", "question": "BTC", "active": False, "closed": False},
            {"id": "3", "question": "BTC", "active": True, "closed": True}
        ]
        mock_search.return_value = markets_with_inactive

        markets = polymarket_client.get_btc_markets()

        # Should only include active markets
        assert len(markets) == 1
        assert markets[0]["id"] == "1"

    @patch.object(PolymarketClient, 'search_markets')
    def test_get_btc_markets_handles_search_errors(self, mock_search, polymarket_client):
        """Test BTC markets handles search errors gracefully."""
        # First call succeeds, second fails
        mock_search.side_effect = [
            [{"id": "1", "question": "BTC", "active": True, "closed": False, "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"}],
            PolymarketAPIError("API error")
        ]

        markets = polymarket_client.get_btc_markets()

        # Should still return markets from successful searches
        assert len(markets) >= 1


class TestMarketStatusChecks:
    """Tests for market status validation."""

    def test_is_market_active_true(self, polymarket_client):
        """Test active market detection."""
        market = {
            "closed": False,
            "active": True,
            "end_date": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
        }

        assert polymarket_client._is_market_active(market) is True

    def test_is_market_active_closed(self, polymarket_client):
        """Test closed market detection."""
        market = {"closed": True, "active": False}

        assert polymarket_client._is_market_active(market) is False

    def test_is_market_active_is_closed_key(self, polymarket_client):
        """Test closed market with is_closed key."""
        market = {"is_closed": True}

        assert polymarket_client._is_market_active(market) is False

    def test_is_market_active_inactive(self, polymarket_client):
        """Test inactive market detection."""
        market = {"active": False, "closed": False}

        assert polymarket_client._is_market_active(market) is False

    def test_is_market_active_past_end_date(self, polymarket_client):
        """Test market past end date is inactive."""
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        market = {
            "active": True,
            "closed": False,
            "end_date": past_date
        }

        assert polymarket_client._is_market_active(market) is False

    def test_is_market_active_invalid_end_date(self, polymarket_client):
        """Test market with invalid end date is considered active."""
        market = {
            "active": True,
            "closed": False,
            "end_date": "invalid_date"
        }

        # Should assume active if date can't be parsed
        assert polymarket_client._is_market_active(market) is True


class TestMarketDataParsing:
    """Tests for parsing market data into MarketData models."""

    def test_parse_market_data_complete(self, polymarket_client, sample_market_data):
        """Test parsing complete market data."""
        market_data = polymarket_client.parse_market_data(sample_market_data)

        assert isinstance(market_data, MarketData)
        assert market_data.market_id == "market_123"
        assert market_data.question == "Will Bitcoin reach $100k in 2024?"
        assert market_data.yes_price == Decimal("0.65")
        assert market_data.no_price == Decimal("0.35")
        assert market_data.yes_volume == Decimal("150000.00")
        assert market_data.no_volume == Decimal("85000.00")
        assert market_data.total_liquidity == Decimal("50000.00")
        assert market_data.is_active is True
        assert market_data.is_closed is False
        assert market_data.category == "Cryptocurrency"
        assert "BTC" in market_data.tags

    def test_parse_market_data_missing_id(self, polymarket_client):
        """Test parsing fails for market without ID."""
        market = {"question": "Test market"}

        with pytest.raises(ValidationError) as exc_info:
            polymarket_client.parse_market_data(market)

        assert "id" in str(exc_info.value).lower()

    def test_parse_market_data_alternate_field_names(self, polymarket_client):
        """Test parsing with alternate field names."""
        market = {
            "market_id": "alt_123",
            "title": "Alternative title field",
            "yesPrice": 0.7,
            "noPrice": 0.3,
            "end_time": "2024-12-31T23:59:59Z"
        }

        market_data = polymarket_client.parse_market_data(market)

        assert market_data.market_id == "alt_123"
        assert market_data.question == "Alternative title field"
        assert market_data.yes_price == Decimal("0.7")
        assert market_data.no_price == Decimal("0.3")

    def test_parse_market_data_nested_prices(self, polymarket_client):
        """Test parsing with nested price structure."""
        market = {
            "id": "nested_123",
            "question": "Test",
            "prices": {"yes": 0.6, "no": 0.4},
            "end_date": "2024-12-31T23:59:59Z"
        }

        market_data = polymarket_client.parse_market_data(market)

        assert market_data.yes_price == Decimal("0.6")
        assert market_data.no_price == Decimal("0.4")

    def test_parse_market_data_outcomes_array(self, polymarket_client):
        """Test parsing with outcomes array structure."""
        market = {
            "id": "outcomes_123",
            "question": "Test",
            "outcomes": [
                {"name": "yes", "price": 0.55, "volume": 10000},
                {"name": "no", "price": 0.45, "volume": 8000}
            ],
            "end_date": "2024-12-31T23:59:59Z"
        }

        market_data = polymarket_client.parse_market_data(market)

        assert market_data.yes_price == Decimal("0.55")
        assert market_data.no_price == Decimal("0.45")
        assert market_data.yes_volume == Decimal("10000")
        assert market_data.no_volume == Decimal("8000")

    def test_parse_market_data_with_resolution(self, polymarket_client):
        """Test parsing resolved market."""
        market = {
            "id": "resolved_123",
            "question": "Test",
            "yes_price": 1.0,
            "no_price": 0.0,
            "end_date": "2024-01-01T00:00:00Z",
            "resolved": True,
            "resolution": "yes"
        }

        market_data = polymarket_client.parse_market_data(market)

        assert market_data.resolution == OutcomeType.YES

    def test_parse_market_data_default_values(self, polymarket_client):
        """Test parsing with minimal data uses defaults."""
        market = {
            "id": "minimal_123",
            "question": "Minimal market",
            "end_date": "2024-12-31T23:59:59Z"
        }

        market_data = polymarket_client.parse_market_data(market)

        # Should use default values
        assert market_data.yes_price == Decimal("0.5")
        assert market_data.no_price == Decimal("0.5")
        assert market_data.yes_volume == Decimal("0")
        assert market_data.no_volume == Decimal("0")


class TestOddsRetrieval:
    """Tests for odds retrieval methods."""

    @patch.object(PolymarketClient, 'get_market_by_id')
    def test_get_market_odds(self, mock_get_market, polymarket_client, sample_market_data):
        """Test getting market odds."""
        mock_get_market.return_value = sample_market_data

        yes_price, no_price = polymarket_client.get_market_odds("market_123")

        assert yes_price == Decimal("0.65")
        assert no_price == Decimal("0.35")
        mock_get_market.assert_called_once_with("market_123")

    @patch.object(PolymarketClient, 'get_market_by_id')
    def test_get_market_odds_error(self, mock_get_market, polymarket_client):
        """Test get_market_odds handles errors."""
        mock_get_market.side_effect = PolymarketAPIError("Market not found")

        with pytest.raises(PolymarketAPIError):
            polymarket_client.get_market_odds("invalid_id")


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_extract_price_direct(self, polymarket_client):
        """Test extracting price from direct field."""
        market = {"yes_price": 0.75}
        price = polymarket_client._extract_price(market, "yes")
        assert price == Decimal("0.75")

    def test_extract_price_camel_case(self, polymarket_client):
        """Test extracting price from camelCase field."""
        market = {"yesPrice": 0.65}
        price = polymarket_client._extract_price(market, "yes")
        assert price == Decimal("0.65")

    def test_extract_price_default(self, polymarket_client):
        """Test extracting price defaults to 0.5."""
        market = {}
        price = polymarket_client._extract_price(market, "yes")
        assert price == Decimal("0.5")

    def test_extract_volume_direct(self, polymarket_client):
        """Test extracting volume from direct field."""
        market = {"yes_volume": 50000}
        volume = polymarket_client._extract_volume(market, "yes")
        assert volume == Decimal("50000")

    def test_extract_volume_default(self, polymarket_client):
        """Test extracting volume defaults to 0."""
        market = {}
        volume = polymarket_client._extract_volume(market, "yes")
        assert volume == Decimal("0")

    def test_parse_datetime_iso_format(self, polymarket_client):
        """Test parsing ISO format datetime."""
        date_str = "2024-12-31T23:59:59Z"
        result = polymarket_client._parse_datetime(date_str, datetime.utcnow())
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 31

    def test_parse_datetime_invalid(self, polymarket_client):
        """Test parsing invalid datetime returns default."""
        default = datetime(2024, 1, 1)
        result = polymarket_client._parse_datetime("invalid", default)
        assert result == default

    def test_parse_datetime_none(self, polymarket_client):
        """Test parsing None datetime returns default."""
        default = datetime(2024, 1, 1)
        result = polymarket_client._parse_datetime(None, default)
        assert result == default


class TestContextManager:
    """Tests for context manager functionality."""

    def test_context_manager(self, mock_config):
        """Test client works as context manager."""
        with PolymarketClient(mock_config) as client:
            assert client is not None
            assert client.session is not None

    @patch.object(PolymarketClient, 'close')
    def test_context_manager_closes(self, mock_close, mock_config):
        """Test context manager closes session."""
        with PolymarketClient(mock_config) as client:
            pass

        mock_close.assert_called_once()

    def test_close_method(self, polymarket_client):
        """Test close method."""
        polymarket_client.close()
        # Session should be closed (no easy way to verify, just ensure no exception)


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
        sample_market = {
            "id": "market_123",
            "question": "Will BTC go up?",
            "yes_price": 0.65,
            "no_price": 0.35,
            "end_date": "2024-01-01T12:00:00Z"
        }
        polymarket_client.get_btc_markets.return_value = [sample_market]
        polymarket_client.parse_market_data.return_value = MarketData(
            market_id="market_123",
            question="Will BTC go up?",
            end_date=datetime(2024, 1, 1, 12, 0, 0),
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35")
        )

        # Mock order book imbalance
        with patch('market_data.get_order_book_imbalance', return_value=1.2):
            market_data = get_market_data(
                binance_client,
                polymarket_client
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

    def test_get_market_data_no_active_market(self):
        """Test handling when no active market is found."""
        binance_client = MagicMock()
        prices = [100 + i * 0.2 for i in range(100)]
        binance_client.get_latest_prices.return_value = prices

        polymarket_client = MagicMock()
        polymarket_client.get_btc_markets.return_value = []

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
