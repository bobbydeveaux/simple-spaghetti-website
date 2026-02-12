"""
Ergast Formula 1 API client.

This module provides a client for the Ergast Developer API to fetch F1 data
including race results, qualifying times, driver standings, and constructor standings.

API Documentation: http://ergast.com/mrd/
Rate Limit: Respectful use - 1 request per minute for regular updates.
"""

import asyncio
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import ExternalAPIConfig

logger = logging.getLogger(__name__)


class ErgastAPIError(Exception):
    """Exception raised for Ergast API related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message)


class ErgastClient:
    """
    Async client for Ergast Formula 1 API.

    Provides methods to fetch F1 data including:
    - Race results and standings
    - Qualifying results
    - Driver and constructor championships
    - Race schedules and circuit information
    """

    def __init__(self, config: Optional[ExternalAPIConfig] = None, session: Optional[httpx.AsyncClient] = None):
        """
        Initialize the Ergast API client.

        Args:
            config: External API configuration object
            session: Optional HTTP session, will create default if not provided
        """
        self.config = config or ExternalAPIConfig()
        self.base_url = self.config.ergast_base_url.rstrip('/')
        self.timeout = self.config.ergast_timeout
        self.retry_attempts = self.config.ergast_retry_attempts

        # Create HTTP client with reasonable defaults
        if session is None:
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    'User-Agent': 'F1-Analytics/1.0 (Educational/Analytics)',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate'
                },
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            self._own_session = True
        else:
            self.session = session
            self._own_session = False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP session if owned by this client."""
        if self._own_session and self.session:
            await self.session.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make an HTTP request to the Ergast API with retry logic.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            ErgastAPIError: If the request fails after retries
        """
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))

        try:
            # Add default JSON format parameter
            request_params = params or {}
            if 'format' not in request_params:
                request_params['format'] = 'json'

            logger.debug(f"Making request to Ergast API: {url} with params: {request_params}")

            response = await self.session.get(url, params=request_params)
            response.raise_for_status()

            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise ErgastAPIError(f"Invalid JSON response: {str(e)}", response.status_code, None)

            logger.debug(f"Ergast API response received: {len(str(data))} characters")
            return data

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(f"Ergast API HTTP error: {error_msg}")
            raise ErgastAPIError(error_msg, e.response.status_code, None)

        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(f"Ergast API request error: {error_msg}")
            raise ErgastAPIError(error_msg, None, None)

    def _validate_season(self, season: Union[int, str]) -> str:
        """
        Validate and convert season to string format.

        Args:
            season: Season year (int or str)

        Returns:
            Season as string

        Raises:
            ValueError: If season is invalid
        """
        try:
            season_int = int(season)
            if season_int < 1950 or season_int > datetime.now().year + 1:
                raise ValueError(f"Invalid season: {season_int}. Must be between 1950 and {datetime.now().year + 1}")
            return str(season_int)
        except (ValueError, TypeError):
            raise ValueError(f"Season must be a valid year: {season}")

    def _validate_round(self, round_num: Union[int, str]) -> str:
        """
        Validate and convert round number to string format.

        Args:
            round_num: Round number (int or str)

        Returns:
            Round as string

        Raises:
            ValueError: If round is invalid
        """
        try:
            round_int = int(round_num)
            if round_int < 1 or round_int > 30:  # Reasonable upper bound for F1 seasons
                raise ValueError(f"Invalid round: {round_int}. Must be between 1 and 30")
            return str(round_int)
        except (ValueError, TypeError):
            raise ValueError(f"Round must be a valid number: {round_num}")

    async def fetch_race_results(self, season: Union[int, str], round_num: Union[int, str]) -> Dict[str, Any]:
        """
        Fetch race results for a specific season and round.

        Args:
            season: F1 season year (e.g., 2023)
            round_num: Race round number (e.g., 1 for first race)

        Returns:
            Race results data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If season or round parameters are invalid
        """
        season_str = self._validate_season(season)
        round_str = self._validate_round(round_num)

        endpoint = f"{season_str}/{round_str}/results.json"
        logger.info(f"Fetching race results for season {season_str}, round {round_str}")

        data = await self._make_request(endpoint)
        return data

    async def fetch_qualifying_results(self, season: Union[int, str], round_num: Union[int, str]) -> Dict[str, Any]:
        """
        Fetch qualifying results for a specific season and round.

        Args:
            season: F1 season year (e.g., 2023)
            round_num: Race round number (e.g., 1 for first race)

        Returns:
            Qualifying results data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If season or round parameters are invalid
        """
        season_str = self._validate_season(season)
        round_str = self._validate_round(round_num)

        endpoint = f"{season_str}/{round_str}/qualifying.json"
        logger.info(f"Fetching qualifying results for season {season_str}, round {round_str}")

        data = await self._make_request(endpoint)
        return data

    async def fetch_driver_standings(self, season: Union[int, str], round_num: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        """
        Fetch driver championship standings for a season.

        Args:
            season: F1 season year (e.g., 2023)
            round_num: Optional specific round (defaults to final standings)

        Returns:
            Driver standings data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If season parameter is invalid
        """
        season_str = self._validate_season(season)

        if round_num is not None:
            round_str = self._validate_round(round_num)
            endpoint = f"{season_str}/{round_str}/driverStandings.json"
            logger.info(f"Fetching driver standings for season {season_str}, round {round_str}")
        else:
            endpoint = f"{season_str}/driverStandings.json"
            logger.info(f"Fetching final driver standings for season {season_str}")

        data = await self._make_request(endpoint)
        return data

    async def fetch_constructor_standings(self, season: Union[int, str], round_num: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        """
        Fetch constructor championship standings for a season.

        Args:
            season: F1 season year (e.g., 2023)
            round_num: Optional specific round (defaults to final standings)

        Returns:
            Constructor standings data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If season parameter is invalid
        """
        season_str = self._validate_season(season)

        if round_num is not None:
            round_str = self._validate_round(round_num)
            endpoint = f"{season_str}/{round_str}/constructorStandings.json"
            logger.info(f"Fetching constructor standings for season {season_str}, round {round_str}")
        else:
            endpoint = f"{season_str}/constructorStandings.json"
            logger.info(f"Fetching final constructor standings for season {season_str}")

        data = await self._make_request(endpoint)
        return data

    async def fetch_race_schedule(self, season: Union[int, str]) -> Dict[str, Any]:
        """
        Fetch race schedule for a season.

        Args:
            season: F1 season year (e.g., 2023)

        Returns:
            Race schedule data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If season parameter is invalid
        """
        season_str = self._validate_season(season)

        endpoint = f"{season_str}.json"
        logger.info(f"Fetching race schedule for season {season_str}")

        data = await self._make_request(endpoint)
        return data

    async def fetch_circuits(self, season: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        """
        Fetch circuit information.

        Args:
            season: Optional season year to get circuits for that season only

        Returns:
            Circuits data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If season parameter is invalid
        """
        if season is not None:
            season_str = self._validate_season(season)
            endpoint = f"{season_str}/circuits.json"
            logger.info(f"Fetching circuits for season {season_str}")
        else:
            endpoint = "circuits.json"
            logger.info("Fetching all circuits")

        data = await self._make_request(endpoint)
        return data

    async def fetch_drivers(self, season: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        """
        Fetch driver information.

        Args:
            season: Optional season year to get drivers for that season only

        Returns:
            Drivers data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If season parameter is invalid
        """
        if season is not None:
            season_str = self._validate_season(season)
            endpoint = f"{season_str}/drivers.json"
            logger.info(f"Fetching drivers for season {season_str}")
        else:
            endpoint = "drivers.json"
            logger.info("Fetching all drivers")

        data = await self._make_request(endpoint)
        return data

    async def fetch_constructors(self, season: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        """
        Fetch constructor (team) information.

        Args:
            season: Optional season year to get constructors for that season only

        Returns:
            Constructors data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If season parameter is invalid
        """
        if season is not None:
            season_str = self._validate_season(season)
            endpoint = f"{season_str}/constructors.json"
            logger.info(f"Fetching constructors for season {season_str}")
        else:
            endpoint = "constructors.json"
            logger.info("Fetching all constructors")

        data = await self._make_request(endpoint)
        return data

    async def fetch_lap_times(self, season: Union[int, str], round_num: Union[int, str], lap: Optional[Union[int, str]] = None) -> Dict[str, Any]:
        """
        Fetch lap times for a specific race.

        Args:
            season: F1 season year (e.g., 2023)
            round_num: Race round number (e.g., 1 for first race)
            lap: Optional specific lap number (defaults to all laps)

        Returns:
            Lap times data from Ergast API

        Raises:
            ErgastAPIError: If the request fails
            ValueError: If parameters are invalid
        """
        season_str = self._validate_season(season)
        round_str = self._validate_round(round_num)

        if lap is not None:
            try:
                lap_int = int(lap)
                if lap_int < 1:
                    raise ValueError(f"Invalid lap number: {lap_int}. Must be >= 1")
                lap_str = str(lap_int)
                endpoint = f"{season_str}/{round_str}/laps/{lap_str}.json"
                logger.info(f"Fetching lap times for season {season_str}, round {round_str}, lap {lap_str}")
            except (ValueError, TypeError):
                raise ValueError(f"Lap must be a valid number: {lap}")
        else:
            endpoint = f"{season_str}/{round_str}/laps.json"
            logger.info(f"Fetching all lap times for season {season_str}, round {round_str}")

        data = await self._make_request(endpoint)
        return data

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check against the Ergast API.

        Returns:
            Health check result with status and response time
        """
        start_time = datetime.now()

        try:
            # Simple request to check API availability
            data = await self._make_request("current.json", {"limit": "1"})
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            return {
                "status": "healthy",
                "response_time_seconds": response_time,
                "api_url": self.base_url,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            return {
                "status": "unhealthy",
                "error": str(e),
                "response_time_seconds": response_time,
                "api_url": self.base_url,
                "timestamp": datetime.now().isoformat()
            }


# Factory function for easy client creation
async def create_ergast_client(config: Optional[ExternalAPIConfig] = None) -> ErgastClient:
    """
    Factory function to create an Ergast API client.

    Args:
        config: Optional configuration object

    Returns:
        Configured ErgastClient instance
    """
    return ErgastClient(config)