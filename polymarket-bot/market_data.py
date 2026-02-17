"""
Market Data Module for Polymarket Bot.

This module provides functionality for:
- Polymarket API client for market discovery and odds retrieval
- BTC-related market filtering
- Real-time market data fetching with retry logic
- Market metadata and pricing data management
"""

import logging
import requests
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime

from .config import Config
from .models import MarketData, OutcomeType
from .utils import (
    retry_with_backoff,
    validate_non_empty,
    validate_probability,
    ValidationError,
    RetryError
)


# Configure module logger
logger = logging.getLogger(__name__)


class PolymarketAPIError(Exception):
    """Exception raised for Polymarket API errors."""
    pass


class PolymarketClient:
    """
    Client for interacting with the Polymarket API.

    Provides methods for discovering active markets, fetching market odds,
    and filtering BTC-related prediction markets.
    """

    def __init__(self, config: Config):
        """
        Initialize the Polymarket API client.

        Args:
            config: Configuration object containing API credentials and base URL
        """
        self.config = config
        self.base_url = config.polymarket_base_url
        self.api_key = config.polymarket_api_key
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        logger.info(f"Initialized PolymarketClient with base URL: {self.base_url}")

    @retry_with_backoff(max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,))
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Polymarket API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data

        Returns:
            JSON response from the API

        Raises:
            PolymarketAPIError: If the API request fails
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )

            # Log rate limit information if available
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = response.headers['X-RateLimit-Remaining']
                logger.debug(f"API rate limit remaining: {remaining}")

            response.raise_for_status()

            return response.json()

        except requests.HTTPError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise PolymarketAPIError(error_msg) from e

        except requests.RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            raise PolymarketAPIError(error_msg) from e

        except ValueError as e:
            error_msg = f"Invalid JSON response: {str(e)}"
            logger.error(error_msg)
            raise PolymarketAPIError(error_msg) from e

    def get_active_markets(
        self,
        limit: int = 100,
        offset: int = 0,
        closed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetch active markets from Polymarket.

        Args:
            limit: Maximum number of markets to retrieve (default: 100)
            offset: Number of markets to skip (default: 0)
            closed: Whether to include closed markets (default: False)

        Returns:
            List of market data dictionaries

        Raises:
            PolymarketAPIError: If the API request fails
        """
        endpoint = "/markets"
        params = {
            "limit": limit,
            "offset": offset,
            "closed": "true" if closed else "false"
        }

        logger.info(f"Fetching active markets (limit={limit}, offset={offset})")

        response = self._make_request("GET", endpoint, params=params)

        # Handle different response formats
        markets = response if isinstance(response, list) else response.get('markets', [])

        logger.info(f"Retrieved {len(markets)} markets from Polymarket")

        return markets

    def get_market_by_id(self, market_id: str) -> Dict[str, Any]:
        """
        Fetch a specific market by ID.

        Args:
            market_id: Unique market identifier

        Returns:
            Market data dictionary

        Raises:
            PolymarketAPIError: If the API request fails
            ValidationError: If market_id is invalid
        """
        validate_non_empty(market_id, "market_id")

        endpoint = f"/markets/{market_id}"

        logger.info(f"Fetching market {market_id}")

        return self._make_request("GET", endpoint)

    def search_markets(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for markets matching a query string.

        Args:
            query: Search query string
            limit: Maximum number of results (default: 50)

        Returns:
            List of matching market data dictionaries

        Raises:
            PolymarketAPIError: If the API request fails
            ValidationError: If query is empty
        """
        validate_non_empty(query, "query")

        endpoint = "/markets"
        params = {
            "query": query,
            "limit": limit
        }

        logger.info(f"Searching markets with query: '{query}'")

        response = self._make_request("GET", endpoint, params=params)

        markets = response if isinstance(response, list) else response.get('markets', [])

        logger.info(f"Found {len(markets)} markets matching '{query}'")

        return markets

    def get_btc_markets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch BTC-related prediction markets.

        Searches for markets containing Bitcoin-related keywords and filters
        for active markets with sufficient liquidity.

        Args:
            limit: Maximum number of markets to retrieve (default: 50)

        Returns:
            List of BTC-related market data dictionaries

        Raises:
            PolymarketAPIError: If the API request fails
        """
        # Search terms for BTC-related markets
        btc_keywords = ["BTC", "Bitcoin", "bitcoin"]

        all_markets = []
        seen_ids = set()

        for keyword in btc_keywords:
            try:
                markets = self.search_markets(keyword, limit=limit)

                # Add unique markets
                for market in markets:
                    market_id = market.get('id') or market.get('market_id')
                    if market_id and market_id not in seen_ids:
                        all_markets.append(market)
                        seen_ids.add(market_id)

            except PolymarketAPIError as e:
                logger.warning(f"Failed to search for '{keyword}': {e}")
                continue

        # Filter for active markets
        active_btc_markets = [
            market for market in all_markets
            if self._is_market_active(market)
        ]

        logger.info(f"Found {len(active_btc_markets)} active BTC-related markets")

        return active_btc_markets[:limit]

    def _is_market_active(self, market: Dict[str, Any]) -> bool:
        """
        Check if a market is active for trading.

        Args:
            market: Market data dictionary

        Returns:
            True if market is active, False otherwise
        """
        # Check if market is explicitly closed
        if market.get('closed') or market.get('is_closed'):
            return False

        # Check if market is active
        if not market.get('active', True) and not market.get('is_active', True):
            return False

        # Check if market has ended
        end_date_str = market.get('end_date') or market.get('end_time')
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                if end_date < datetime.now(end_date.tzinfo):
                    return False
            except (ValueError, AttributeError):
                # If we can't parse the date, assume it's active
                pass

        return True

    def parse_market_data(self, market: Dict[str, Any]) -> MarketData:
        """
        Parse raw market data from API into MarketData model.

        Args:
            market: Raw market data dictionary from API

        Returns:
            MarketData model instance

        Raises:
            ValidationError: If required fields are missing or invalid
        """
        # Extract market ID
        market_id = market.get('id') or market.get('market_id') or market.get('marketId')
        if not market_id:
            raise ValidationError("Market data missing 'id' field")

        # Extract question/title
        question = (
            market.get('question') or
            market.get('title') or
            market.get('description', 'Unknown Market')
        )

        # Extract prices (probabilities)
        yes_price = self._extract_price(market, 'yes')
        no_price = self._extract_price(market, 'no')

        # Ensure prices sum to approximately 1.0
        if yes_price and no_price:
            total = yes_price + no_price
            if abs(total - Decimal("1.0")) > Decimal("0.05"):
                logger.warning(
                    f"Market {market_id} prices don't sum to 1.0: "
                    f"yes={yes_price}, no={no_price}, total={total}"
                )

        # Extract volumes
        yes_volume = self._extract_volume(market, 'yes')
        no_volume = self._extract_volume(market, 'no')

        # Extract liquidity
        liquidity = Decimal(str(market.get('liquidity', 0)))

        # Extract dates
        created_date = self._parse_datetime(
            market.get('created_at') or market.get('creation_date'),
            datetime.utcnow()
        )

        end_date = self._parse_datetime(
            market.get('end_date') or market.get('end_time'),
            datetime.utcnow()
        )

        # Extract market status
        is_active = self._is_market_active(market)
        is_closed = market.get('closed', False) or market.get('is_closed', False)

        # Extract resolution if available
        resolution = None
        if market.get('resolved'):
            resolution_str = market.get('resolution') or market.get('winning_outcome')
            if resolution_str:
                resolution = (
                    OutcomeType.YES if resolution_str.lower() == 'yes'
                    else OutcomeType.NO if resolution_str.lower() == 'no'
                    else None
                )

        # Extract metadata
        category = market.get('category')
        tags = market.get('tags', [])
        if isinstance(tags, str):
            tags = [tags]

        description = market.get('description')

        return MarketData(
            market_id=str(market_id),
            question=question,
            description=description,
            created_date=created_date,
            end_date=end_date,
            yes_price=yes_price,
            no_price=no_price,
            yes_volume=yes_volume,
            no_volume=no_volume,
            total_liquidity=liquidity,
            is_active=is_active,
            is_closed=is_closed,
            resolution=resolution,
            category=category,
            tags=tags,
            metadata=market
        )

    def _extract_price(self, market: Dict[str, Any], outcome: str) -> Decimal:
        """Extract price for a specific outcome from market data."""
        price_key = f"{outcome}_price"
        price = market.get(price_key) or market.get(f"{outcome}Price")

        # Try nested structure
        if price is None and 'prices' in market:
            price = market['prices'].get(outcome)

        # Try outcomes array
        if price is None and 'outcomes' in market:
            for outcome_data in market['outcomes']:
                if outcome_data.get('name', '').lower() == outcome.lower():
                    price = outcome_data.get('price')
                    break

        if price is None:
            # Default to 0.5 if not found
            logger.warning(f"Could not find {outcome} price in market data, defaulting to 0.5")
            price = 0.5

        return Decimal(str(price))

    def _extract_volume(self, market: Dict[str, Any], outcome: str) -> Decimal:
        """Extract volume for a specific outcome from market data."""
        volume_key = f"{outcome}_volume"
        volume = market.get(volume_key) or market.get(f"{outcome}Volume")

        # Try nested structure
        if volume is None and 'volumes' in market:
            volume = market['volumes'].get(outcome)

        # Try outcomes array
        if volume is None and 'outcomes' in market:
            for outcome_data in market['outcomes']:
                if outcome_data.get('name', '').lower() == outcome.lower():
                    volume = outcome_data.get('volume')
                    break

        if volume is None:
            volume = 0

        return Decimal(str(volume))

    def _parse_datetime(self, date_str: Optional[str], default: datetime) -> datetime:
        """Parse datetime string from API response."""
        if not date_str:
            return default

        try:
            # Try ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try timestamp
                return datetime.fromtimestamp(float(date_str))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse datetime: {date_str}")
                return default

    def get_market_odds(self, market_id: str) -> tuple[Decimal, Decimal]:
        """
        Get current YES/NO odds for a specific market.

        Args:
            market_id: Unique market identifier

        Returns:
            Tuple of (yes_price, no_price) as Decimal values

        Raises:
            PolymarketAPIError: If the API request fails
            ValidationError: If market_id is invalid
        """
        market = self.get_market_by_id(market_id)
        market_data = self.parse_market_data(market)

        return (market_data.yes_price, market_data.no_price)

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.info("Closed PolymarketClient session")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
