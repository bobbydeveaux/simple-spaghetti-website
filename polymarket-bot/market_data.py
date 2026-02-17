"""
Market Data Service for Polymarket Bot.

This module provides integration with the Polymarket API for:
- Discovering active BTC-related prediction markets
- Fetching current market odds (Yes/No prices)
- Retrieving market metadata and status

The service includes retry logic, error handling, and rate limit management.
"""

import logging
import requests
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime

from models import MarketData, OutcomeType
from config import get_config
from utils import retry_with_backoff, validate_non_empty, validate_probability, handle_errors

# Configure module logger
logger = logging.getLogger(__name__)


class PolymarketAPIError(Exception):
    """Exception raised for Polymarket API errors."""
    pass


class MarketDataService:
    """
    Service for fetching and managing Polymarket market data.

    Provides methods for discovering active markets, fetching odds,
    and managing market metadata with built-in retry logic and error handling.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 base_url: Optional[str] = None):
        """
        Initialize the Market Data Service.

        Args:
            api_key: Polymarket API key (defaults to config if not provided)
            api_secret: Polymarket API secret (defaults to config if not provided)
            base_url: Polymarket API base URL (defaults to config if not provided)
        """
        config = get_config()

        self.api_key = api_key or config.polymarket_api_key
        self.api_secret = api_secret or config.polymarket_api_secret
        self.base_url = base_url or config.polymarket_base_url

        # Rate limiting configuration
        self.rate_limit_delay = 0.1  # 100ms between requests
        self.last_request_time = None

        logger.info(f"MarketDataService initialized with base_url: {self.base_url}")

    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for API requests.

        Returns:
            Dictionary of HTTP headers including authentication
        """
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key
        }

    @retry_with_backoff(max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,))
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an HTTP GET request to the Polymarket API with retry logic.

        Args:
            endpoint: API endpoint path (e.g., '/markets')
            params: Optional query parameters

        Returns:
            JSON response as dictionary

        Raises:
            PolymarketAPIError: If the API returns an error response
            requests.RequestException: For network-related errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        logger.debug(f"Making API request to {url} with params: {params}")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.debug(f"API request successful: {url}")

            return data

        except requests.HTTPError as e:
            error_msg = f"HTTP error from Polymarket API: {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg += f" - {error_data.get('error', error_data)}"
            except:
                pass

            logger.error(error_msg)
            raise PolymarketAPIError(error_msg) from e

        except requests.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise

    def discover_markets(self, search_query: Optional[str] = "BTC",
                        active_only: bool = True,
                        limit: int = 50) -> List[MarketData]:
        """
        Discover active markets matching search criteria.

        Args:
            search_query: Search term for markets (default: "BTC" for Bitcoin-related markets)
            active_only: Only return active markets for trading (default: True)
            limit: Maximum number of markets to return (default: 50)

        Returns:
            List of MarketData objects representing discovered markets

        Raises:
            PolymarketAPIError: If the API request fails
        """
        logger.info(f"Discovering markets with query: '{search_query}', active_only={active_only}, limit={limit}")

        params = {
            'limit': limit,
            'offset': 0
        }

        if search_query:
            params['query'] = search_query

        if active_only:
            params['active'] = 'true'

        try:
            response_data = self._make_request('/markets', params=params)

            markets = []
            market_list = response_data if isinstance(response_data, list) else response_data.get('markets', [])

            for market_data in market_list:
                try:
                    market = self._parse_market_data(market_data)
                    markets.append(market)
                except Exception as e:
                    logger.warning(f"Failed to parse market data: {e}. Skipping market.")
                    continue

            logger.info(f"Discovered {len(markets)} markets")
            return markets

        except Exception as e:
            logger.error(f"Failed to discover markets: {str(e)}")
            raise PolymarketAPIError(f"Market discovery failed: {str(e)}") from e

    def get_market_odds(self, market_id: str) -> MarketData:
        """
        Fetch current odds for a specific market.

        Args:
            market_id: Unique Polymarket market identifier

        Returns:
            MarketData object with current odds and market information

        Raises:
            PolymarketAPIError: If the API request fails
            ValueError: If market_id is invalid
        """
        validate_non_empty(market_id, "market_id")

        logger.info(f"Fetching odds for market: {market_id}")

        try:
            response_data = self._make_request(f'/markets/{market_id}')
            market = self._parse_market_data(response_data)

            logger.info(
                f"Fetched odds for market {market_id}: "
                f"YES={float(market.yes_price):.4f}, NO={float(market.no_price):.4f}"
            )

            return market

        except Exception as e:
            logger.error(f"Failed to fetch market odds for {market_id}: {str(e)}")
            raise PolymarketAPIError(f"Failed to fetch market odds: {str(e)}") from e

    def get_market_by_id(self, market_id: str) -> Optional[MarketData]:
        """
        Get complete market information by ID.

        Args:
            market_id: Unique Polymarket market identifier

        Returns:
            MarketData object or None if market not found
        """
        try:
            return self.get_market_odds(market_id)
        except PolymarketAPIError:
            logger.warning(f"Market not found: {market_id}")
            return None

    def filter_btc_markets(self, markets: List[MarketData],
                           min_liquidity: Optional[Decimal] = None,
                           min_volume: Optional[Decimal] = None) -> List[MarketData]:
        """
        Filter BTC-related markets based on liquidity and volume criteria.

        Args:
            markets: List of MarketData objects to filter
            min_liquidity: Minimum required liquidity in USD (optional)
            min_volume: Minimum required volume in USD (optional)

        Returns:
            Filtered list of MarketData objects
        """
        logger.info(
            f"Filtering {len(markets)} markets with "
            f"min_liquidity={min_liquidity}, min_volume={min_volume}"
        )

        filtered = []

        for market in markets:
            # Check if market is active
            if not market.is_active or market.is_closed:
                continue

            # Check liquidity threshold
            if min_liquidity and market.total_liquidity < min_liquidity:
                continue

            # Check volume threshold
            if min_volume:
                total_volume = market.get_total_volume()
                if total_volume < min_volume:
                    continue

            filtered.append(market)

        logger.info(f"Filtered to {len(filtered)} markets meeting criteria")
        return filtered

    def _parse_market_data(self, data: Dict[str, Any]) -> MarketData:
        """
        Parse raw API response data into a MarketData model.

        Args:
            data: Raw market data from API response

        Returns:
            MarketData object

        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Extract required fields
            market_id = data.get('id') or data.get('market_id') or data.get('marketId')
            question = data.get('question') or data.get('title') or data.get('description', '')

            validate_non_empty(market_id, "market_id")
            validate_non_empty(question, "question")

            # Extract pricing data (may be in different formats depending on API version)
            yes_price = self._extract_price(data, 'yes')
            no_price = self._extract_price(data, 'no')

            # Validate prices
            validate_probability(yes_price, "yes_price")
            validate_probability(no_price, "no_price")

            # Extract volume and liquidity data
            yes_volume = Decimal(str(data.get('yes_volume', 0) or data.get('yesVolume', 0)))
            no_volume = Decimal(str(data.get('no_volume', 0) or data.get('noVolume', 0)))
            total_liquidity = Decimal(str(data.get('liquidity', 0) or data.get('total_liquidity', 0)))

            # Extract market status
            is_active = data.get('active', True) and not data.get('closed', False)
            is_closed = data.get('closed', False)

            # Parse resolution if available
            resolution = None
            resolution_data = data.get('resolution') or data.get('outcome')
            if resolution_data:
                resolution_str = str(resolution_data).lower()
                if resolution_str in ['yes', 'true', '1']:
                    resolution = OutcomeType.YES
                elif resolution_str in ['no', 'false', '0']:
                    resolution = OutcomeType.NO

            # Parse dates
            end_date = self._parse_date(data.get('end_date') or data.get('endDate') or data.get('end_time'))
            if not end_date:
                # Default to far future if no end date specified
                end_date = datetime(2099, 12, 31)

            created_date = self._parse_date(data.get('created_date') or data.get('createdDate') or data.get('created_at'))
            if not created_date:
                created_date = datetime.utcnow()

            # Create MarketData object
            market = MarketData(
                market_id=str(market_id),
                question=question,
                description=data.get('description'),
                created_date=created_date,
                end_date=end_date,
                yes_price=Decimal(str(yes_price)),
                no_price=Decimal(str(no_price)),
                yes_volume=yes_volume,
                no_volume=no_volume,
                total_liquidity=total_liquidity,
                is_active=is_active,
                is_closed=is_closed,
                resolution=resolution,
                category=data.get('category'),
                tags=data.get('tags', []),
                metadata=data,
                last_updated=datetime.utcnow()
            )

            return market

        except Exception as e:
            logger.error(f"Failed to parse market data: {str(e)}")
            raise ValueError(f"Invalid market data format: {str(e)}") from e

    def _extract_price(self, data: Dict[str, Any], outcome: str) -> float:
        """
        Extract price for a specific outcome from various API response formats.

        Args:
            data: Raw market data
            outcome: 'yes' or 'no'

        Returns:
            Price as float between 0 and 1
        """
        # Try different possible field names
        price_fields = [
            f'{outcome}_price',
            f'{outcome}Price',
            outcome,
            f'{outcome}_bid',
            f'{outcome}Bid'
        ]

        for field in price_fields:
            if field in data and data[field] is not None:
                price = float(data[field])
                # Normalize price to 0-1 range if needed
                if price > 1:
                    price = price / 100.0
                return price

        # Try to extract from outcomes array
        outcomes = data.get('outcomes') or data.get('prices')
        if outcomes and isinstance(outcomes, list) and len(outcomes) >= 2:
            idx = 0 if outcome == 'yes' else 1
            if idx < len(outcomes):
                price = float(outcomes[idx])
                if price > 1:
                    price = price / 100.0
                return price

        # Default to 0.5 if price not found (50/50 odds)
        logger.warning(f"Could not find {outcome} price in data, defaulting to 0.5")
        return 0.5

    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """
        Parse a date value from various formats.

        Args:
            date_value: Date as string, timestamp, or datetime

        Returns:
            datetime object or None if parsing fails
        """
        if not date_value:
            return None

        if isinstance(date_value, datetime):
            return date_value

        try:
            # Try parsing as ISO format string
            if isinstance(date_value, str):
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))

            # Try parsing as Unix timestamp
            if isinstance(date_value, (int, float)):
                return datetime.fromtimestamp(date_value)

        except Exception as e:
            logger.warning(f"Failed to parse date '{date_value}': {e}")

        return None


@handle_errors(default_return=None, log_level=logging.WARNING)
def get_active_btc_markets(min_liquidity: Optional[Decimal] = None,
                           min_volume: Optional[Decimal] = None,
                           limit: int = 50) -> Optional[List[MarketData]]:
    """
    Convenience function to get active BTC markets with filtering.

    Args:
        min_liquidity: Minimum required liquidity in USD (optional)
        min_volume: Minimum required volume in USD (optional)
        limit: Maximum number of markets to fetch (default: 50)

    Returns:
        List of filtered MarketData objects, or None if an error occurs

    Example:
        # Get BTC markets with at least $1000 liquidity
        markets = get_active_btc_markets(min_liquidity=Decimal("1000"))
    """
    service = MarketDataService()
    markets = service.discover_markets(search_query="BTC", active_only=True, limit=limit)

    if min_liquidity or min_volume:
        markets = service.filter_btc_markets(markets, min_liquidity, min_volume)

    return markets


@handle_errors(default_return=None, log_level=logging.WARNING)
def get_market_odds_by_id(market_id: str) -> Optional[MarketData]:
    """
    Convenience function to fetch odds for a specific market.

    Args:
        market_id: Unique Polymarket market identifier

    Returns:
        MarketData object with current odds, or None if an error occurs

    Example:
        market = get_market_odds_by_id("0x123abc...")
        if market:
            print(f"YES: {market.yes_price}, NO: {market.no_price}")
    """
    service = MarketDataService()
    return service.get_market_odds(market_id)
