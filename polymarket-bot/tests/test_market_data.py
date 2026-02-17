"""
Tests for Market Data Service

This module contains comprehensive tests for the Polymarket API integration,
including market discovery, odds fetching, filtering, and error handling.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import requests

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from market_data import (
    MarketDataService,
    PolymarketAPIError,
    get_active_btc_markets,
    get_market_odds_by_id
)
from models import MarketData, OutcomeType


class TestMarketDataService:
    """Tests for MarketDataService class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        with patch('market_data.get_config') as mock:
            config = Mock()
            config.polymarket_api_key = 'test_api_key'
            config.polymarket_api_secret = 'test_api_secret'
            config.polymarket_base_url = 'https://api.polymarket.com'
            mock.return_value = config
            yield config

    @pytest.fixture
    def service(self, mock_config):
        """Create a MarketDataService instance for testing."""
        return MarketDataService()

    @pytest.fixture
    def sample_market_response(self):
        """Sample market data response from API."""
        return {
            'id': 'market_123',
            'question': 'Will Bitcoin reach $100k in 2024?',
            'description': 'Bitcoin price prediction market',
            'yes_price': 0.65,
            'no_price': 0.35,
            'yes_volume': 150000.0,
            'no_volume': 85000.0,
            'liquidity': 50000.0,
            'active': True,
            'closed': False,
            'end_date': '2024-12-31T23:59:59Z',
            'created_date': '2024-01-01T00:00:00Z',
            'category': 'crypto',
            'tags': ['bitcoin', 'crypto', 'price']
        }

    def test_service_initialization(self, mock_config):
        """Test that service initializes correctly with config."""
        service = MarketDataService()

        assert service.api_key == 'test_api_key'
        assert service.api_secret == 'test_api_secret'
        assert service.base_url == 'https://api.polymarket.com'

    def test_service_initialization_with_custom_params(self):
        """Test service initialization with custom parameters."""
        service = MarketDataService(
            api_key='custom_key',
            api_secret='custom_secret',
            base_url='https://custom.api.com'
        )

        assert service.api_key == 'custom_key'
        assert service.api_secret == 'custom_secret'
        assert service.base_url == 'https://custom.api.com'

    def test_get_headers(self, service):
        """Test that headers are correctly formatted."""
        headers = service._get_headers()

        assert headers['Accept'] == 'application/json'
        assert headers['Content-Type'] == 'application/json'
        assert headers['X-API-Key'] == 'test_api_key'

    @patch('market_data.requests.get')
    def test_make_request_success(self, mock_get, service, sample_market_response):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = sample_market_response
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = service._make_request('/markets/market_123')

        assert result == sample_market_response
        mock_get.assert_called_once()
        assert '/markets/market_123' in mock_get.call_args[0][0]

    @patch('market_data.requests.get')
    def test_make_request_with_params(self, mock_get, service):
        """Test API request with query parameters."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        service._make_request('/markets', params={'limit': 10, 'query': 'BTC'})

        assert mock_get.call_args[1]['params'] == {'limit': 10, 'query': 'BTC'}

    @patch('market_data.requests.get')
    def test_make_request_http_error(self, mock_get, service):
        """Test API request with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'error': 'Not found'}
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        with pytest.raises(PolymarketAPIError) as exc_info:
            service._make_request('/markets/invalid')

        assert 'HTTP error' in str(exc_info.value)

    @patch('market_data.requests.get')
    def test_make_request_network_error(self, mock_get, service):
        """Test API request with network error."""
        mock_get.side_effect = requests.ConnectionError('Network error')

        with pytest.raises(requests.RequestException):
            service._make_request('/markets')

    @patch.object(MarketDataService, '_make_request')
    def test_discover_markets_success(self, mock_request, service, sample_market_response):
        """Test successful market discovery."""
        mock_request.return_value = [sample_market_response]

        markets = service.discover_markets(search_query='BTC', active_only=True, limit=50)

        assert len(markets) == 1
        assert isinstance(markets[0], MarketData)
        assert markets[0].market_id == 'market_123'
        assert markets[0].question == 'Will Bitcoin reach $100k in 2024?'
        assert float(markets[0].yes_price) == 0.65

    @patch.object(MarketDataService, '_make_request')
    def test_discover_markets_with_dict_response(self, mock_request, service, sample_market_response):
        """Test market discovery with dict response containing markets key."""
        mock_request.return_value = {'markets': [sample_market_response]}

        markets = service.discover_markets()

        assert len(markets) == 1
        assert markets[0].market_id == 'market_123'

    @patch.object(MarketDataService, '_make_request')
    def test_discover_markets_empty_response(self, mock_request, service):
        """Test market discovery with empty response."""
        mock_request.return_value = []

        markets = service.discover_markets()

        assert len(markets) == 0

    @patch.object(MarketDataService, '_make_request')
    def test_discover_markets_filters_invalid_data(self, mock_request, service, sample_market_response):
        """Test that invalid market data is filtered out."""
        invalid_market = {'id': 'bad_market'}  # Missing required fields
        mock_request.return_value = [sample_market_response, invalid_market]

        markets = service.discover_markets()

        assert len(markets) == 1
        assert markets[0].market_id == 'market_123'

    @patch.object(MarketDataService, '_make_request')
    def test_get_market_odds_success(self, mock_request, service, sample_market_response):
        """Test successful odds fetching."""
        mock_request.return_value = sample_market_response

        market = service.get_market_odds('market_123')

        assert isinstance(market, MarketData)
        assert market.market_id == 'market_123'
        assert float(market.yes_price) == 0.65
        assert float(market.no_price) == 0.35

    def test_get_market_odds_invalid_id(self, service):
        """Test odds fetching with invalid market ID."""
        with pytest.raises(Exception):  # ValidationError from utils
            service.get_market_odds('')

    @patch.object(MarketDataService, '_make_request')
    def test_get_market_odds_api_error(self, mock_request, service):
        """Test odds fetching with API error."""
        mock_request.side_effect = PolymarketAPIError('API error')

        with pytest.raises(PolymarketAPIError):
            service.get_market_odds('market_123')

    @patch.object(MarketDataService, 'get_market_odds')
    def test_get_market_by_id_success(self, mock_get_odds, service, sample_market_response):
        """Test get_market_by_id with valid market."""
        mock_market = MarketData(
            market_id='market_123',
            question='Test market',
            end_date=datetime.now() + timedelta(days=30),
            yes_price=Decimal('0.6'),
            no_price=Decimal('0.4')
        )
        mock_get_odds.return_value = mock_market

        market = service.get_market_by_id('market_123')

        assert market is not None
        assert market.market_id == 'market_123'

    @patch.object(MarketDataService, 'get_market_odds')
    def test_get_market_by_id_not_found(self, mock_get_odds, service):
        """Test get_market_by_id with non-existent market."""
        mock_get_odds.side_effect = PolymarketAPIError('Not found')

        market = service.get_market_by_id('invalid_id')

        assert market is None

    def test_filter_btc_markets_no_criteria(self, service):
        """Test filtering with no criteria filters only active markets."""
        markets = [
            MarketData(
                market_id='m1',
                question='BTC market 1',
                end_date=datetime.now() + timedelta(days=30),
                yes_price=Decimal('0.6'),
                no_price=Decimal('0.4'),
                is_active=True,
                is_closed=False
            ),
            MarketData(
                market_id='m2',
                question='BTC market 2',
                end_date=datetime.now() + timedelta(days=30),
                yes_price=Decimal('0.5'),
                no_price=Decimal('0.5'),
                is_active=False,  # Inactive market
                is_closed=False
            ),
        ]

        filtered = service.filter_btc_markets(markets)

        assert len(filtered) == 1
        assert filtered[0].market_id == 'm1'

    def test_filter_btc_markets_by_liquidity(self, service):
        """Test filtering markets by liquidity threshold."""
        markets = [
            MarketData(
                market_id='m1',
                question='High liquidity',
                end_date=datetime.now() + timedelta(days=30),
                yes_price=Decimal('0.6'),
                no_price=Decimal('0.4'),
                total_liquidity=Decimal('10000.0'),
                is_active=True
            ),
            MarketData(
                market_id='m2',
                question='Low liquidity',
                end_date=datetime.now() + timedelta(days=30),
                yes_price=Decimal('0.5'),
                no_price=Decimal('0.5'),
                total_liquidity=Decimal('500.0'),
                is_active=True
            ),
        ]

        filtered = service.filter_btc_markets(markets, min_liquidity=Decimal('1000'))

        assert len(filtered) == 1
        assert filtered[0].market_id == 'm1'

    def test_filter_btc_markets_by_volume(self, service):
        """Test filtering markets by volume threshold."""
        markets = [
            MarketData(
                market_id='m1',
                question='High volume',
                end_date=datetime.now() + timedelta(days=30),
                yes_price=Decimal('0.6'),
                no_price=Decimal('0.4'),
                yes_volume=Decimal('8000.0'),
                no_volume=Decimal('3000.0'),
                is_active=True
            ),
            MarketData(
                market_id='m2',
                question='Low volume',
                end_date=datetime.now() + timedelta(days=30),
                yes_price=Decimal('0.5'),
                no_price=Decimal('0.5'),
                yes_volume=Decimal('100.0'),
                no_volume=Decimal('50.0'),
                is_active=True
            ),
        ]

        filtered = service.filter_btc_markets(markets, min_volume=Decimal('1000'))

        assert len(filtered) == 1
        assert filtered[0].market_id == 'm1'

    def test_parse_market_data_complete(self, service, sample_market_response):
        """Test parsing complete market data."""
        market = service._parse_market_data(sample_market_response)

        assert market.market_id == 'market_123'
        assert market.question == 'Will Bitcoin reach $100k in 2024?'
        assert market.description == 'Bitcoin price prediction market'
        assert float(market.yes_price) == 0.65
        assert float(market.no_price) == 0.35
        assert market.is_active == True
        assert market.is_closed == False
        assert market.category == 'crypto'
        assert 'bitcoin' in market.tags

    def test_parse_market_data_missing_required_field(self, service):
        """Test parsing with missing required field."""
        incomplete_data = {'id': 'market_123'}  # Missing question

        with pytest.raises(ValueError):
            service._parse_market_data(incomplete_data)

    def test_parse_market_data_alternative_field_names(self, service):
        """Test parsing with alternative API field names."""
        alt_data = {
            'marketId': 'alt_123',  # Alternative ID field
            'title': 'Alternative market',  # Alternative question field
            'yesPrice': 0.7,  # Alternative price field
            'noPrice': 0.3,
            'endDate': '2024-12-31T23:59:59Z',
            'active': True
        }

        market = service._parse_market_data(alt_data)

        assert market.market_id == 'alt_123'
        assert market.question == 'Alternative market'
        assert float(market.yes_price) == 0.7

    def test_parse_market_data_with_resolution(self, service):
        """Test parsing market with resolution outcome."""
        resolved_data = {
            'id': 'resolved_123',
            'question': 'Resolved market',
            'yes_price': 1.0,
            'no_price': 0.0,
            'resolution': 'yes',
            'active': False,
            'closed': True,
            'end_date': '2024-01-01T00:00:00Z'
        }

        market = service._parse_market_data(resolved_data)

        assert market.resolution == OutcomeType.YES
        assert market.is_closed == True

    def test_extract_price_standard_format(self, service):
        """Test price extraction from standard format."""
        data = {'yes_price': 0.65}
        price = service._extract_price(data, 'yes')
        assert price == 0.65

    def test_extract_price_percentage_format(self, service):
        """Test price extraction with percentage (>1) format."""
        data = {'yes_price': 65.0}  # 65%
        price = service._extract_price(data, 'yes')
        assert price == 0.65

    def test_extract_price_from_outcomes_array(self, service):
        """Test price extraction from outcomes array."""
        data = {'outcomes': [0.7, 0.3]}
        yes_price = service._extract_price(data, 'yes')
        no_price = service._extract_price(data, 'no')
        assert yes_price == 0.7
        assert no_price == 0.3

    def test_extract_price_default_fallback(self, service):
        """Test price extraction falls back to 0.5 when not found."""
        data = {}
        price = service._extract_price(data, 'yes')
        assert price == 0.5

    def test_parse_date_iso_format(self, service):
        """Test date parsing from ISO format."""
        date_str = '2024-12-31T23:59:59Z'
        parsed = service._parse_date(date_str)
        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 12

    def test_parse_date_unix_timestamp(self, service):
        """Test date parsing from Unix timestamp."""
        timestamp = 1704067199  # 2024-01-01 00:00:00
        parsed = service._parse_date(timestamp)
        assert parsed is not None
        assert parsed.year == 2024

    def test_parse_date_datetime_object(self, service):
        """Test date parsing from datetime object."""
        dt = datetime(2024, 6, 15)
        parsed = service._parse_date(dt)
        assert parsed == dt

    def test_parse_date_invalid(self, service):
        """Test date parsing with invalid input."""
        parsed = service._parse_date('invalid')
        assert parsed is None

    def test_parse_date_none(self, service):
        """Test date parsing with None."""
        parsed = service._parse_date(None)
        assert parsed is None


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch('market_data.MarketDataService')
    def test_get_active_btc_markets_success(self, mock_service_class):
        """Test get_active_btc_markets convenience function."""
        mock_service = Mock()
        mock_markets = [
            MarketData(
                market_id='m1',
                question='BTC market',
                end_date=datetime.now() + timedelta(days=30),
                yes_price=Decimal('0.6'),
                no_price=Decimal('0.4'),
                is_active=True
            )
        ]
        mock_service.discover_markets.return_value = mock_markets
        mock_service.filter_btc_markets.return_value = mock_markets
        mock_service_class.return_value = mock_service

        markets = get_active_btc_markets(min_liquidity=Decimal('1000'))

        assert markets is not None
        assert len(markets) == 1
        mock_service.discover_markets.assert_called_once_with(
            search_query='BTC',
            active_only=True,
            limit=50
        )

    @patch('market_data.MarketDataService')
    def test_get_active_btc_markets_error_handling(self, mock_service_class):
        """Test get_active_btc_markets error handling."""
        mock_service = Mock()
        mock_service.discover_markets.side_effect = Exception('API error')
        mock_service_class.return_value = mock_service

        markets = get_active_btc_markets()

        # Should return None due to error handling
        assert markets is None

    @patch('market_data.MarketDataService')
    def test_get_market_odds_by_id_success(self, mock_service_class):
        """Test get_market_odds_by_id convenience function."""
        mock_service = Mock()
        mock_market = MarketData(
            market_id='market_123',
            question='Test market',
            end_date=datetime.now() + timedelta(days=30),
            yes_price=Decimal('0.65'),
            no_price=Decimal('0.35')
        )
        mock_service.get_market_odds.return_value = mock_market
        mock_service_class.return_value = mock_service

        market = get_market_odds_by_id('market_123')

        assert market is not None
        assert market.market_id == 'market_123'
        mock_service.get_market_odds.assert_called_once_with('market_123')

    @patch('market_data.MarketDataService')
    def test_get_market_odds_by_id_error_handling(self, mock_service_class):
        """Test get_market_odds_by_id error handling."""
        mock_service = Mock()
        mock_service.get_market_odds.side_effect = Exception('API error')
        mock_service_class.return_value = mock_service

        market = get_market_odds_by_id('market_123')

        # Should return None due to error handling
        assert market is None


class TestIntegrationScenarios:
    """Integration-style tests for real-world scenarios."""

    @pytest.fixture
    def service_with_mock_api(self):
        """Service with mocked API responses."""
        with patch('market_data.get_config') as mock_config:
            config = Mock()
            config.polymarket_api_key = 'test_key'
            config.polymarket_api_secret = 'test_secret'
            config.polymarket_base_url = 'https://api.test.com'
            mock_config.return_value = config

            service = MarketDataService()
            return service

    @patch.object(MarketDataService, '_make_request')
    def test_discover_and_filter_workflow(self, mock_request, service_with_mock_api):
        """Test complete workflow: discover markets and filter them."""
        # Mock API response with multiple markets
        mock_request.return_value = [
            {
                'id': 'm1',
                'question': 'BTC $100k?',
                'yes_price': 0.6,
                'no_price': 0.4,
                'liquidity': 50000,
                'yes_volume': 80000,
                'no_volume': 40000,
                'active': True,
                'closed': False,
                'end_date': '2024-12-31T23:59:59Z'
            },
            {
                'id': 'm2',
                'question': 'BTC $50k?',
                'yes_price': 0.8,
                'no_price': 0.2,
                'liquidity': 500,
                'yes_volume': 1000,
                'no_volume': 500,
                'active': True,
                'closed': False,
                'end_date': '2024-12-31T23:59:59Z'
            }
        ]

        # Discover markets
        markets = service_with_mock_api.discover_markets('BTC')
        assert len(markets) == 2

        # Filter by liquidity
        filtered = service_with_mock_api.filter_btc_markets(
            markets,
            min_liquidity=Decimal('10000')
        )
        assert len(filtered) == 1
        assert filtered[0].market_id == 'm1'

        # Filter by volume
        filtered_by_volume = service_with_mock_api.filter_btc_markets(
            markets,
            min_volume=Decimal('10000')
        )
        assert len(filtered_by_volume) == 1
        assert filtered_by_volume[0].market_id == 'm1'
