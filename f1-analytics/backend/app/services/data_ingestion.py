"""
Data ingestion services for F1 analytics.

This module provides services for ingesting data from external APIs
(Ergast F1 API, OpenWeatherMap) and storing it in the database.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .ergast_client import ErgastClient, ErgastAPIError
from .weather_client import WeatherClient, WeatherAPIError
from .data_transformer import DataTransformer, DataTransformationError
from ..repositories.f1_repositories import (
    DriverRepository, TeamRepository, CircuitRepository, RaceRepository,
    RaceResultRepository, QualifyingResultRepository, WeatherDataRepository
)
from ..database import get_session
from ..config import ExternalAPIConfig

logger = logging.getLogger(__name__)


class DataIngestionError(Exception):
    """Exception raised for data ingestion errors."""
    pass


class F1DataIngestionService:
    """
    Service for ingesting F1 data from external APIs into the database.

    Handles the complete ETL pipeline from API data to database storage,
    including data validation, transformation, and error handling.
    """

    def __init__(
        self,
        ergast_client: Optional[ErgastClient] = None,
        weather_client: Optional[WeatherClient] = None,
        transformer: Optional[DataTransformer] = None,
        config: Optional[ExternalAPIConfig] = None
    ):
        """
        Initialize the data ingestion service.

        Args:
            ergast_client: Ergast API client
            weather_client: Weather API client
            transformer: Data transformation utility
            config: External API configuration
        """
        self.config = config or ExternalAPIConfig()
        self.transformer = transformer or DataTransformer()

        # Initialize API clients if not provided
        self.ergast_client = ergast_client
        self.weather_client = weather_client

        self.logger = logging.getLogger(__name__)

    async def __aenter__(self):
        """Async context manager entry."""
        # Initialize clients if not provided
        if self.ergast_client is None:
            self.ergast_client = ErgastClient(self.config)

        if self.weather_client is None:
            try:
                self.weather_client = WeatherClient(self.config)
            except ValueError as e:
                self.logger.warning(f"Weather client not available: {e}")
                self.weather_client = None

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.ergast_client:
            await self.ergast_client.close()
        if self.weather_client:
            await self.weather_client.close()

    def _get_repositories(self, db_session: Session) -> Dict[str, Any]:
        """Get all required repositories for the session."""
        return {
            'driver': DriverRepository(db_session),
            'team': TeamRepository(db_session),
            'circuit': CircuitRepository(db_session),
            'race': RaceRepository(db_session),
            'race_result': RaceResultRepository(db_session),
            'qualifying': QualifyingResultRepository(db_session),
            'weather': WeatherDataRepository(db_session)
        }

    async def ingest_season_data(self, season: int, include_weather: bool = True) -> Dict[str, Any]:
        """
        Ingest complete season data including races, results, and weather.

        Args:
            season: Season year to ingest
            include_weather: Whether to include weather data

        Returns:
            Ingestion statistics and results

        Raises:
            DataIngestionError: If ingestion fails
        """
        start_time = datetime.now()
        stats = {
            'season': season,
            'drivers_created': 0,
            'teams_created': 0,
            'circuits_created': 0,
            'races_created': 0,
            'race_results_created': 0,
            'qualifying_results_created': 0,
            'weather_records_created': 0,
            'errors': []
        }

        try:
            self.logger.info(f"Starting season {season} data ingestion")

            # Get race schedule for the season
            schedule_data = await self.ergast_client.fetch_race_schedule(season)
            races = schedule_data.get('MRData', {}).get('RaceTable', {}).get('Races', [])

            if not races:
                raise DataIngestionError(f"No races found for season {season}")

            # Process each race
            with get_session() as db_session:
                repos = self._get_repositories(db_session)

                for race_data in races:
                    try:
                        round_number = int(race_data.get('round', 0))
                        race_name = race_data.get('raceName', '')

                        self.logger.info(f"Processing {race_name} (Round {round_number})")

                        # Ingest race and dependencies
                        race_stats = await self._ingest_race_data(
                            race_data, season, repos, include_weather
                        )

                        # Update stats
                        for key, value in race_stats.items():
                            if key in stats:
                                stats[key] += value

                    except Exception as e:
                        error_msg = f"Failed to process race {race_name}: {str(e)}"
                        self.logger.error(error_msg)
                        stats['errors'].append(error_msg)

                # Commit all changes
                db_session.commit()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.logger.info(f"Season {season} ingestion completed in {duration:.2f} seconds")
            self.logger.info(f"Created: {stats['races_created']} races, "
                           f"{stats['race_results_created']} results, "
                           f"{stats['weather_records_created']} weather records")

            stats['duration_seconds'] = duration
            stats['timestamp'] = datetime.now().isoformat()

            return stats

        except Exception as e:
            raise DataIngestionError(f"Season {season} ingestion failed: {str(e)}")

    async def ingest_race_results(self, season: int, round_number: int) -> Dict[str, Any]:
        """
        Ingest race results for a specific race.

        Args:
            season: Season year
            round_number: Race round number

        Returns:
            Ingestion statistics

        Raises:
            DataIngestionError: If ingestion fails
        """
        start_time = datetime.now()
        stats = {
            'season': season,
            'round': round_number,
            'results_created': 0,
            'results_updated': 0,
            'errors': []
        }

        try:
            self.logger.info(f"Ingesting race results for {season} Round {round_number}")

            # Fetch race results from Ergast API
            results_data = await self.ergast_client.fetch_race_results(season, round_number)
            race_results = results_data.get('MRData', {}).get('RaceTable', {}).get('Races', [])

            if not race_results:
                raise DataIngestionError(f"No race results found for {season} Round {round_number}")

            race_data = race_results[0]
            results = race_data.get('Results', [])

            with get_session() as db_session:
                repos = self._get_repositories(db_session)

                # Find or create race record
                race = await self._ensure_race_exists(race_data, season, repos)

                # Process each result
                for result_data in results:
                    try:
                        # Transform and store result
                        result_stats = await self._ingest_single_race_result(
                            result_data, race.race_id, repos
                        )

                        stats['results_created'] += result_stats.get('created', 0)
                        stats['results_updated'] += result_stats.get('updated', 0)

                    except Exception as e:
                        error_msg = f"Failed to process result: {str(e)}"
                        self.logger.error(error_msg)
                        stats['errors'].append(error_msg)

                db_session.commit()

            end_time = datetime.now()
            stats['duration_seconds'] = (end_time - start_time).total_seconds()
            stats['timestamp'] = datetime.now().isoformat()

            self.logger.info(f"Race results ingestion completed: "
                           f"{stats['results_created']} created, "
                           f"{stats['results_updated']} updated")

            return stats

        except Exception as e:
            raise DataIngestionError(f"Race results ingestion failed: {str(e)}")

    async def ingest_qualifying_results(self, season: int, round_number: int) -> Dict[str, Any]:
        """
        Ingest qualifying results for a specific race.

        Args:
            season: Season year
            round_number: Race round number

        Returns:
            Ingestion statistics

        Raises:
            DataIngestionError: If ingestion fails
        """
        start_time = datetime.now()
        stats = {
            'season': season,
            'round': round_number,
            'qualifying_created': 0,
            'qualifying_updated': 0,
            'errors': []
        }

        try:
            self.logger.info(f"Ingesting qualifying results for {season} Round {round_number}")

            # Fetch qualifying results from Ergast API
            quali_data = await self.ergast_client.fetch_qualifying_results(season, round_number)
            qualifying_results = quali_data.get('MRData', {}).get('RaceTable', {}).get('Races', [])

            if not qualifying_results:
                raise DataIngestionError(f"No qualifying results found for {season} Round {round_number}")

            race_data = qualifying_results[0]
            results = race_data.get('QualifyingResults', [])

            with get_session() as db_session:
                repos = self._get_repositories(db_session)

                # Find race record
                race = await self._ensure_race_exists(race_data, season, repos)

                # Process each qualifying result
                for quali_result in results:
                    try:
                        # Transform and store result
                        result_stats = await self._ingest_single_qualifying_result(
                            quali_result, race.race_id, repos
                        )

                        stats['qualifying_created'] += result_stats.get('created', 0)
                        stats['qualifying_updated'] += result_stats.get('updated', 0)

                    except Exception as e:
                        error_msg = f"Failed to process qualifying result: {str(e)}"
                        self.logger.error(error_msg)
                        stats['errors'].append(error_msg)

                db_session.commit()

            end_time = datetime.now()
            stats['duration_seconds'] = (end_time - start_time).total_seconds()
            stats['timestamp'] = datetime.now().isoformat()

            self.logger.info(f"Qualifying results ingestion completed: "
                           f"{stats['qualifying_created']} created, "
                           f"{stats['qualifying_updated']} updated")

            return stats

        except Exception as e:
            raise DataIngestionError(f"Qualifying results ingestion failed: {str(e)}")

    async def ingest_weather_data(self, season: int, round_number: int, circuit_id: str) -> Dict[str, Any]:
        """
        Ingest weather data for a specific race.

        Args:
            season: Season year
            round_number: Race round number
            circuit_id: Circuit identifier for weather lookup

        Returns:
            Ingestion statistics

        Raises:
            DataIngestionError: If ingestion fails
        """
        if not self.weather_client:
            raise DataIngestionError("Weather client not available")

        start_time = datetime.now()
        stats = {
            'season': season,
            'round': round_number,
            'circuit_id': circuit_id,
            'weather_created': 0,
            'weather_updated': 0,
            'errors': []
        }

        try:
            self.logger.info(f"Ingesting weather data for {season} Round {round_number} ({circuit_id})")

            with get_session() as db_session:
                repos = self._get_repositories(db_session)

                # Find race record
                race = repos['race'].get_by_season_and_round(season, round_number)
                if not race:
                    raise DataIngestionError(f"Race not found for {season} Round {round_number}")

                # Fetch weather data
                weather_data = await self.weather_client.get_weather_for_circuit(
                    circuit_id, race.race_date
                )

                # Transform and store weather data
                if 'error' not in weather_data:
                    weather_record = self.transformer.transform_weather_from_openweather(
                        weather_data, race.race_id
                    )

                    # Check if weather data already exists
                    existing_weather = repos['weather'].get_by_race_id(race.race_id)

                    if existing_weather:
                        # Update existing record
                        updated_weather = repos['weather'].update(
                            existing_weather.weather_id,
                            weather_record.dict(exclude_unset=True)
                        )
                        if updated_weather:
                            stats['weather_updated'] = 1
                    else:
                        # Create new record
                        new_weather = repos['weather'].create(weather_record)
                        if new_weather:
                            stats['weather_created'] = 1

                    db_session.commit()

                else:
                    stats['errors'].append(weather_data.get('message', 'Unknown weather API error'))

            end_time = datetime.now()
            stats['duration_seconds'] = (end_time - start_time).total_seconds()
            stats['timestamp'] = datetime.now().isoformat()

            self.logger.info(f"Weather data ingestion completed: "
                           f"{stats['weather_created']} created, "
                           f"{stats['weather_updated']} updated")

            return stats

        except Exception as e:
            raise DataIngestionError(f"Weather data ingestion failed: {str(e)}")

    async def _ingest_race_data(
        self,
        race_data: Dict[str, Any],
        season: int,
        repos: Dict[str, Any],
        include_weather: bool = True
    ) -> Dict[str, Any]:
        """Ingest complete race data including results and weather."""
        stats = {
            'drivers_created': 0,
            'teams_created': 0,
            'circuits_created': 0,
            'races_created': 0,
            'race_results_created': 0,
            'qualifying_results_created': 0,
            'weather_records_created': 0
        }

        round_number = int(race_data.get('round', 0))

        # Ensure race exists
        race = await self._ensure_race_exists(race_data, season, repos)
        if race:
            stats['races_created'] = 1

        # Fetch and ingest race results
        try:
            results_data = await self.ergast_client.fetch_race_results(season, round_number)
            race_results = results_data.get('MRData', {}).get('RaceTable', {}).get('Races', [])

            if race_results:
                results = race_results[0].get('Results', [])
                for result_data in results:
                    result_stats = await self._ingest_single_race_result(
                        result_data, race.race_id, repos
                    )
                    stats['race_results_created'] += result_stats.get('created', 0)

        except Exception as e:
            self.logger.warning(f"Failed to ingest race results for Round {round_number}: {e}")

        # Fetch and ingest qualifying results
        try:
            quali_data = await self.ergast_client.fetch_qualifying_results(season, round_number)
            qualifying_results = quali_data.get('MRData', {}).get('RaceTable', {}).get('Races', [])

            if qualifying_results:
                results = qualifying_results[0].get('QualifyingResults', [])
                for quali_result in results:
                    result_stats = await self._ingest_single_qualifying_result(
                        quali_result, race.race_id, repos
                    )
                    stats['qualifying_results_created'] += result_stats.get('created', 0)

        except Exception as e:
            self.logger.warning(f"Failed to ingest qualifying results for Round {round_number}: {e}")

        # Ingest weather data if requested and client available
        if include_weather and self.weather_client:
            try:
                circuit_data = race_data.get('Circuit', {})
                circuit_id = circuit_data.get('circuitId', '')

                if circuit_id:
                    weather_data = await self.weather_client.get_weather_for_circuit(
                        circuit_id, race.race_date
                    )

                    if 'error' not in weather_data:
                        weather_record = self.transformer.transform_weather_from_openweather(
                            weather_data, race.race_id
                        )
                        new_weather = repos['weather'].create(weather_record)
                        if new_weather:
                            stats['weather_records_created'] = 1

            except Exception as e:
                self.logger.warning(f"Failed to ingest weather data for Round {round_number}: {e}")

        return stats

    async def _ensure_race_exists(self, race_data: Dict[str, Any], season: int, repos: Dict[str, Any]):
        """Ensure race and its dependencies exist in the database."""
        round_number = int(race_data.get('round', 0))

        # Check if race already exists
        existing_race = repos['race'].get_by_season_and_round(season, round_number)
        if existing_race:
            return existing_race

        # Ensure circuit exists
        circuit_data = race_data.get('Circuit', {})
        circuit = await self._ensure_circuit_exists(circuit_data, repos)

        # Transform and create race
        race_create = self.transformer.transform_race_from_ergast(race_data, season)
        race_create.circuit_id = circuit.circuit_id

        return repos['race'].create(race_create)

    async def _ensure_circuit_exists(self, circuit_data: Dict[str, Any], repos: Dict[str, Any]):
        """Ensure circuit exists in the database."""
        circuit_name = circuit_data.get('circuitName', '')

        # Check if circuit already exists
        existing_circuit = repos['circuit'].get_by_name(circuit_name)
        if existing_circuit:
            return existing_circuit

        # Transform and create circuit
        circuit_create = self.transformer.transform_circuit_from_ergast(circuit_data)
        return repos['circuit'].create(circuit_create)

    async def _ingest_single_race_result(
        self,
        result_data: Dict[str, Any],
        race_id: int,
        repos: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ingest a single race result."""
        stats = {'created': 0, 'updated': 0}

        # Ensure driver and team exist
        driver_data = result_data.get('Driver', {})
        constructor_data = result_data.get('Constructor', {})

        driver = await self._ensure_driver_exists(driver_data, repos)
        team = await self._ensure_team_exists(constructor_data, repos)

        # Transform race result
        result_create = self.transformer.transform_race_result_from_ergast(result_data, race_id)
        result_create.driver_id = driver.driver_id
        result_create.team_id = team.team_id

        # Check if result already exists
        existing_result = repos['race_result'].get_by_race_and_driver(race_id, driver.driver_id)

        if existing_result:
            # Update existing result
            updated_result = repos['race_result'].update(
                existing_result.result_id,
                result_create.dict(exclude_unset=True)
            )
            if updated_result:
                stats['updated'] = 1
        else:
            # Create new result
            new_result = repos['race_result'].create(result_create)
            if new_result:
                stats['created'] = 1

        return stats

    async def _ingest_single_qualifying_result(
        self,
        quali_data: Dict[str, Any],
        race_id: int,
        repos: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Ingest a single qualifying result."""
        stats = {'created': 0, 'updated': 0}

        # Ensure driver and team exist
        driver_data = quali_data.get('Driver', {})
        constructor_data = quali_data.get('Constructor', {})

        driver = await self._ensure_driver_exists(driver_data, repos)
        team = await self._ensure_team_exists(constructor_data, repos)

        # Transform qualifying result
        quali_create = self.transformer.transform_qualifying_result_from_ergast(quali_data, race_id)
        quali_create.driver_id = driver.driver_id
        quali_create.team_id = team.team_id

        # Check if result already exists
        existing_quali = repos['qualifying'].get_by_race_and_driver(race_id, driver.driver_id)

        if existing_quali:
            # Update existing result
            updated_quali = repos['qualifying'].update(
                existing_quali.qualifying_id,
                quali_create.dict(exclude_unset=True)
            )
            if updated_quali:
                stats['updated'] = 1
        else:
            # Create new result
            new_quali = repos['qualifying'].create(quali_create)
            if new_quali:
                stats['created'] = 1

        return stats

    async def _ensure_driver_exists(self, driver_data: Dict[str, Any], repos: Dict[str, Any]):
        """Ensure driver exists in the database."""
        driver_id = driver_data.get('driverId', '')

        # Try to find by driver code first
        driver_create = self.transformer.transform_driver_from_ergast(driver_data)
        existing_driver = repos['driver'].get_by_code(driver_create.driver_code)

        if existing_driver:
            return existing_driver

        # Create new driver
        return repos['driver'].create(driver_create)

    async def _ensure_team_exists(self, constructor_data: Dict[str, Any], repos: Dict[str, Any]):
        """Ensure team exists in the database."""
        team_name = constructor_data.get('name', '')

        # Check if team already exists
        existing_team = repos['team'].get_by_name(team_name)
        if existing_team:
            return existing_team

        # Transform and create team
        team_create = self.transformer.transform_constructor_from_ergast(constructor_data)
        return repos['team'].create(team_create)

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on data ingestion services.

        Returns:
            Health check results for all components
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {}
        }

        # Check Ergast API
        try:
            if self.ergast_client:
                ergast_health = await self.ergast_client.health_check()
                results['components']['ergast_api'] = ergast_health
            else:
                results['components']['ergast_api'] = {
                    'status': 'not_initialized',
                    'message': 'Ergast client not initialized'
                }
        except Exception as e:
            results['components']['ergast_api'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            results['overall_status'] = 'degraded'

        # Check Weather API
        try:
            if self.weather_client:
                weather_health = await self.weather_client.health_check()
                results['components']['weather_api'] = weather_health
            else:
                results['components']['weather_api'] = {
                    'status': 'not_available',
                    'message': 'Weather client not configured (API key missing)'
                }
        except Exception as e:
            results['components']['weather_api'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            # Weather API failure is not critical
            if results['overall_status'] == 'healthy':
                results['overall_status'] = 'degraded'

        # Check database connectivity
        try:
            with get_session() as db_session:
                db_session.execute('SELECT 1')
                results['components']['database'] = {
                    'status': 'healthy',
                    'message': 'Database connection successful'
                }
        except Exception as e:
            results['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            results['overall_status'] = 'unhealthy'

        return results