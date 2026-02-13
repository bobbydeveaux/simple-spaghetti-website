"""
Base ingestion service for F1 Prediction Analytics.

This module provides the base class and common functionality for all
data ingestion services, including error handling, logging, and database
session management.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import asyncio
import httpx
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import db_manager
from app.config import settings


logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Base exception for data ingestion errors."""
    pass


class APIError(IngestionError):
    """Raised when external API calls fail."""
    pass


class DataValidationError(IngestionError):
    """Raised when ingested data fails validation."""
    pass


class BaseIngestionService(ABC):
    """
    Base service for data ingestion operations.

    This class provides common functionality for all ingestion services,
    including API client setup, error handling, and database operations.
    """

    def __init__(self):
        self.http_client = None
        self._setup_http_client()

    def _setup_http_client(self) -> None:
        """Setup HTTP client with appropriate timeouts and retries."""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=settings.external_apis.ergast_timeout,
                connect=10.0
            ),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={
                "User-Agent": f"{settings.app.app_name}/{settings.app.app_version}"
            }
        )

    async def _make_api_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to external API with retry logic.

        Args:
            url: The URL to request
            params: Query parameters for the request
            retries: Number of retry attempts (defaults to config value)

        Returns:
            dict: JSON response data

        Raises:
            APIError: If request fails after all retries
        """
        if retries is None:
            retries = settings.external_apis.ergast_retry_attempts

        last_exception = None

        for attempt in range(retries + 1):
            try:
                logger.debug(f"API request attempt {attempt + 1}: {url}")
                response = await self.http_client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                logger.debug(f"API request successful: {url}")
                return data

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code == 429:  # Rate limited
                    wait_time = min(2 ** attempt, 60)  # Exponential backoff, max 60s
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                elif 400 <= e.response.status_code < 500:
                    # Client error - don't retry
                    raise APIError(f"API request failed with {e.response.status_code}: {e}")
                else:
                    # Server error - retry
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(f"Server error {e.response.status_code}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                wait_time = min(2 ** attempt, 30)
                logger.warning(f"Request error: {e}, retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

        # All retries exhausted
        raise APIError(f"API request failed after {retries + 1} attempts: {last_exception}")

    def _validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validate that required fields are present in data.

        Args:
            data: Data dictionary to validate
            required_fields: List of required field names

        Raises:
            DataValidationError: If required fields are missing
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise DataValidationError(f"Missing required fields: {missing_fields}")

    def _safe_get(self, data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        """
        Safely get nested value from dictionary.

        Args:
            data: Dictionary to search
            keys: Nested keys to traverse
            default: Default value if key not found

        Returns:
            Value at the specified path or default
        """
        result = data
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        return result

    def _convert_time_string(self, time_str: str) -> Optional[float]:
        """
        Convert time string to seconds.

        Args:
            time_str: Time string in format "1:23.456" or "83.456"

        Returns:
            float: Time in seconds, or None if conversion fails
        """
        if not time_str:
            return None

        try:
            if ':' in time_str:
                # Format: "1:23.456"
                parts = time_str.split(':')
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                # Format: "83.456"
                return float(time_str)
        except (ValueError, IndexError):
            logger.warning(f"Failed to convert time string: {time_str}")
            return None

    async def _close_http_client(self) -> None:
        """Close the HTTP client connection."""
        if self.http_client:
            await self.http_client.aclose()

    @abstractmethod
    async def ingest_data(
        self,
        session: Session,
        season: int,
        race_round: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Abstract method for ingesting data.

        Args:
            session: Database session
            season: F1 season year
            race_round: Optional specific race round
            **kwargs: Additional parameters for specific ingestion types

        Returns:
            dict: Ingestion results summary
        """
        pass

    async def run_ingestion(
        self,
        season: int,
        race_round: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run the ingestion process with proper session management.

        Args:
            season: F1 season year
            race_round: Optional specific race round
            **kwargs: Additional parameters for specific ingestion types

        Returns:
            dict: Ingestion results summary
        """
        start_time = datetime.utcnow()

        try:
            with db_manager.get_session() as session:
                logger.info(f"Starting {self.__class__.__name__} for season {season}")

                result = await self.ingest_data(
                    session=session,
                    season=season,
                    race_round=race_round,
                    **kwargs
                )

                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Ingestion completed in {duration:.2f} seconds")

                return {
                    **result,
                    'duration_seconds': duration,
                    'start_time': start_time.isoformat(),
                    'end_time': datetime.utcnow().isoformat()
                }

        except SQLAlchemyError as e:
            logger.error(f"Database error during ingestion: {e}")
            raise IngestionError(f"Database error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during ingestion: {e}")
            raise IngestionError(f"Ingestion failed: {e}")
        finally:
            await self._close_http_client()