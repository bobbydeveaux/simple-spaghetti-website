"""
Tests for Market Data Module (Polymarket API Integration)

This module tests the Polymarket API client including:
- Market discovery and search
- BTC market filtering
- Odds retrieval and parsing
- Error handling and retry logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
import requests

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data import PolymarketClient, PolymarketAPIError
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
            "closed": False
        },
        {
            "id": "btc_market_2",
            "question": "Will Bitcoin dominance exceed 50% this year?",
            "yes_price": 0.55,
            "no_price": 0.45,
            "active": True,
            "closed": False
        },
        {
            "id": "btc_market_3",
            "question": "Bitcoin ETF approval in 2024?",
            "yes_price": 0.80,
            "no_price": 0.20,
            "active": True,
            "closed": False
        }
    ]


# Test PolymarketClient initialization

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


# Test API request methods

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


# Test market discovery methods

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


# Test BTC market filtering

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
        duplicate_market = {"id": "same_market", "question": "BTC price", "active": True}
        mock_search.return_value = [duplicate_market]

        markets = polymarket_client.get_btc_markets()

        # Should only include each market once
        market_ids = [m.get('id') for m in markets]
        assert len(market_ids) == len(set(market_ids))

    @patch.object(PolymarketClient, 'search_markets')
    def test_get_btc_markets_filters_inactive(self, mock_search, polymarket_client):
        """Test BTC markets filters out inactive markets."""
        markets_with_inactive = [
            {"id": "1", "question": "BTC", "active": True, "closed": False},
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
            [{"id": "1", "question": "BTC", "active": True}],
            PolymarketAPIError("API error")
        ]

        markets = polymarket_client.get_btc_markets()

        # Should still return markets from successful searches
        assert len(markets) >= 1


# Test market status checks

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


# Test market data parsing

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


# Test odds retrieval

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


# Test utility methods

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


# Test context manager

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
