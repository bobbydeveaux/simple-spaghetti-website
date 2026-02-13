"""
Weather Data Ingestion Service

This module provides the main service for ingesting weather data with geospatial
matching to associate weather data with F1 circuits and races.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from math import radians, cos, sin, asin, sqrt
from typing import List, Optional, Dict, Tuple, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.database import get_db_session
from app.models.f1_models import Circuit, Race, WeatherData, WeatherCondition, RaceStatus
from app.repositories.f1_repositories import CircuitRepository, RaceRepository, WeatherDataRepository

from ..clients.weather_client import OpenWeatherMapClient, create_weather_client, WeatherData as WeatherAPIData


logger = logging.getLogger(__name__)


@dataclass
class GeospatialMatch:
    """Represents a geospatial match between circuit and weather station."""
    circuit_id: int
    circuit_name: str
    latitude: Decimal
    longitude: Decimal
    distance_km: float


class WeatherIngestionService:
    """Service for weather data ingestion with geospatial matching."""

    def __init__(
        self,
        db_session: Optional[Session] = None,
        weather_client: Optional[OpenWeatherMapClient] = None
    ):
        """Initialize the weather ingestion service.

        Args:
            db_session: Database session. If None, will create a new session.
            weather_client: OpenWeatherMap client. If None, will create a default client.
        """
        self.db_session = db_session or next(get_db_session())
        self.weather_client = weather_client or create_weather_client()

        # Initialize repositories
        self.circuit_repository = CircuitRepository(self.db_session)
        self.race_repository = RaceRepository(self.db_session)
        self.weather_repository = WeatherDataRepository(self.db_session)

    def calculate_distance(
        self,
        lat1: Decimal,
        lon1: Decimal,
        lat2: Decimal,
        lon2: Decimal
    ) -> float:
        """Calculate the great circle distance between two points on Earth.

        Args:
            lat1: Latitude of first point
            lon1: Longitude of first point
            lat2: Latitude of second point
            lon2: Longitude of second point

        Returns:
            Distance in kilometers
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(lambda x: radians(float(x)), [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))

        # Radius of Earth in kilometers
        r = 6371

        return c * r

    def find_circuits_with_coordinates(self) -> List[GeospatialMatch]:
        """Find all circuits that have geospatial coordinates.

        Returns:
            List of circuits with coordinates for geospatial matching
        """
        circuits = self.circuit_repository.db.query(Circuit).filter(
            and_(
                Circuit.latitude.isnot(None),
                Circuit.longitude.isnot(None)
            )
        ).all()

        matches = []
        for circuit in circuits:
            match = GeospatialMatch(
                circuit_id=circuit.circuit_id,
                circuit_name=circuit.circuit_name,
                latitude=circuit.latitude,
                longitude=circuit.longitude,
                distance_km=0.0  # Distance from itself
            )
            matches.append(match)

        return matches

    def find_nearest_circuit(
        self,
        target_lat: Decimal,
        target_lon: Decimal,
        max_distance_km: float = 100.0
    ) -> Optional[GeospatialMatch]:
        """Find the nearest circuit to given coordinates.

        Args:
            target_lat: Target latitude
            target_lon: Target longitude
            max_distance_km: Maximum distance to search within

        Returns:
            Nearest circuit match or None if no circuit within range
        """
        circuits = self.find_circuits_with_coordinates()

        if not circuits:
            logger.warning("No circuits with coordinates found in database")
            return None

        # Calculate distances and find nearest
        nearest_circuit = None
        min_distance = float('inf')

        for circuit in circuits:
            distance = self.calculate_distance(
                target_lat, target_lon,
                circuit.latitude, circuit.longitude
            )

            if distance < min_distance and distance <= max_distance_km:
                min_distance = distance
                nearest_circuit = circuit
                nearest_circuit.distance_km = distance

        if nearest_circuit:
            logger.info(f"Found nearest circuit: {nearest_circuit.circuit_name} "
                       f"({nearest_circuit.distance_km:.2f} km away)")

        return nearest_circuit

    async def fetch_current_weather_for_circuit(
        self,
        circuit_id: int
    ) -> Optional[WeatherAPIData]:
        """Fetch current weather data for a specific circuit.

        Args:
            circuit_id: Circuit ID to fetch weather for

        Returns:
            Weather data or None if circuit not found or no coordinates
        """
        circuit = self.circuit_repository.get_by_id(circuit_id)
        if not circuit:
            logger.error(f"Circuit not found: {circuit_id}")
            return None

        if not circuit.latitude or not circuit.longitude:
            logger.warning(f"Circuit {circuit.circuit_name} has no coordinates")
            return None

        try:
            weather_data = await self.weather_client.get_current_weather(
                circuit.latitude, circuit.longitude
            )
            logger.info(f"Fetched current weather for {circuit.circuit_name}")
            return weather_data

        except Exception as e:
            logger.error(f"Failed to fetch current weather for {circuit.circuit_name}: {e}")
            return None

    async def fetch_historical_weather_for_race(
        self,
        race_id: int,
        race_datetime: Optional[datetime] = None
    ) -> Optional[WeatherAPIData]:
        """Fetch historical weather data for a specific race.

        Args:
            race_id: Race ID to fetch weather for
            race_datetime: Specific datetime for race (if None, uses race date)

        Returns:
            Weather data or None if race/circuit not found
        """
        race = self.race_repository.get_by_id(race_id)
        if not race:
            logger.error(f"Race not found: {race_id}")
            return None

        circuit = race.circuit
        if not circuit or not circuit.latitude or not circuit.longitude:
            logger.warning(f"Race {race.race_name} circuit has no coordinates")
            return None

        # Use provided datetime or race date at noon local time
        target_datetime = race_datetime or datetime.combine(
            race.race_date, datetime.min.time().replace(hour=12)
        ).replace(tzinfo=timezone.utc)

        try:
            weather_data = await self.weather_client.get_historical_weather(
                circuit.latitude, circuit.longitude, target_datetime
            )
            logger.info(f"Fetched historical weather for {race.race_name} on {target_datetime}")
            return weather_data

        except Exception as e:
            logger.error(f"Failed to fetch historical weather for {race.race_name}: {e}")
            return None

    def map_weather_condition_to_enum(self, condition_str: str) -> WeatherCondition:
        """Map weather condition string to database enum.

        Args:
            condition_str: Weather condition string from API

        Returns:
            WeatherCondition enum value
        """
        condition_mapping = {
            'DRY': WeatherCondition.DRY,
            'WET': WeatherCondition.WET,
            'MIXED': WeatherCondition.MIXED,
            'OVERCAST': WeatherCondition.DRY,  # Map overcast to dry unless precipitating
            'SUNNY': WeatherCondition.DRY
        }

        return condition_mapping.get(condition_str, WeatherCondition.DRY)

    def create_weather_record(
        self,
        race_id: int,
        weather_api_data: WeatherAPIData
    ) -> Optional[WeatherData]:
        """Create or update weather data record in database.

        Args:
            race_id: Race ID to associate weather with
            weather_api_data: Weather data from API

        Returns:
            Created or updated WeatherData record
        """
        try:
            # Check if weather data already exists for this race
            existing_weather = self.weather_repository.get_by_race(race_id)

            # Determine weather condition based on precipitation and condition string
            weather_condition = self.map_weather_condition_to_enum(weather_api_data.conditions)

            # If there's significant precipitation, classify as wet
            if weather_api_data.precipitation_mm > Decimal('0.5'):
                weather_condition = WeatherCondition.WET

            weather_data = {
                'race_id': race_id,
                'temperature_celsius': weather_api_data.temperature_celsius,
                'precipitation_mm': weather_api_data.precipitation_mm,
                'wind_speed_kph': weather_api_data.wind_speed_kph,
                'conditions': weather_condition,
                'created_at': datetime.now(timezone.utc)
            }

            if existing_weather:
                # Update existing record
                for key, value in weather_data.items():
                    if key != 'race_id':  # Don't update the primary relationship
                        setattr(existing_weather, key, value)

                self.db_session.commit()
                logger.info(f"Updated weather data for race {race_id}")
                return existing_weather

            else:
                # Create new record
                new_weather = WeatherData(**weather_data)
                self.db_session.add(new_weather)
                self.db_session.commit()
                logger.info(f"Created weather data for race {race_id}")
                return new_weather

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create weather record for race {race_id}: {e}")
            return None

    async def ingest_weather_for_race(self, race_id: int) -> bool:
        """Ingest weather data for a specific race.

        Args:
            race_id: Race ID to ingest weather for

        Returns:
            True if successful, False otherwise
        """
        try:
            race = self.race_repository.get_by_id(race_id)
            if not race:
                logger.error(f"Race not found: {race_id}")
                return False

            # Check if weather data already exists
            existing_weather = self.weather_repository.get_by_race(race_id)
            if existing_weather:
                logger.info(f"Weather data already exists for race {race_id}, skipping")
                return True

            # Determine if this is historical or current/future weather
            now = datetime.now(timezone.utc)
            race_datetime = datetime.combine(race.race_date, datetime.min.time()).replace(tzinfo=timezone.utc)

            if race_datetime <= now - timedelta(days=1):
                # Historical race - use historical weather API
                weather_api_data = await self.fetch_historical_weather_for_race(race_id, race_datetime)
            else:
                # Current or future race - use current weather API
                weather_api_data = await self.fetch_current_weather_for_circuit(race.circuit_id)

            if not weather_api_data:
                logger.warning(f"Could not fetch weather data for race {race_id}")
                return False

            # Create weather record
            weather_record = self.create_weather_record(race_id, weather_api_data)
            return weather_record is not None

        except Exception as e:
            logger.error(f"Failed to ingest weather for race {race_id}: {e}")
            return False

    async def backfill_historical_weather(
        self,
        season_year: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Backfill historical weather data for races without weather data.

        Args:
            season_year: Specific season year to backfill (if None, all seasons)
            limit: Maximum number of races to process (if None, process all)

        Returns:
            Dictionary with backfill results and statistics
        """
        try:
            logger.info(f"Starting historical weather backfill for season {season_year or 'all'}")

            # Query races without weather data
            query = self.db_session.query(Race).outerjoin(WeatherData).filter(
                WeatherData.weather_id.is_(None),
                Race.status == RaceStatus.COMPLETED
            )

            if season_year:
                query = query.filter(Race.season_year == season_year)

            if limit:
                query = query.limit(limit)

            races_without_weather = query.all()

            logger.info(f"Found {len(races_without_weather)} races without weather data")

            results = {
                'total_races': len(races_without_weather),
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': []
            }

            # Process races in batches to avoid overwhelming the API
            batch_size = 10
            for i in range(0, len(races_without_weather), batch_size):
                batch = races_without_weather[i:i + batch_size]

                # Process batch concurrently
                tasks = [self.ingest_weather_for_race(race.race_id) for race in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for j, result in enumerate(batch_results):
                    race = batch[j]
                    if isinstance(result, Exception):
                        results['failed'] += 1
                        results['errors'].append(f"Race {race.race_id}: {str(result)}")
                        logger.error(f"Failed to process race {race.race_id}: {result}")
                    elif result:
                        results['successful'] += 1
                    else:
                        results['failed'] += 1

                # Rate limiting - wait between batches
                if i + batch_size < len(races_without_weather):
                    await asyncio.sleep(2)  # 2-second delay between batches

            logger.info(f"Backfill completed: {results['successful']} successful, "
                       f"{results['failed']} failed out of {results['total_races']} total")

            return results

        except Exception as e:
            logger.error(f"Error during historical weather backfill: {e}")
            return {
                'total_races': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': [str(e)]
            }

    async def update_upcoming_race_weather(
        self,
        days_ahead: int = 7
    ) -> Dict[str, Any]:
        """Update weather data for upcoming races.

        Args:
            days_ahead: Number of days ahead to look for upcoming races

        Returns:
            Dictionary with update results and statistics
        """
        try:
            logger.info(f"Updating weather for races in next {days_ahead} days")

            # Query upcoming races
            start_date = datetime.now(timezone.utc).date()
            end_date = start_date + timedelta(days=days_ahead)

            upcoming_races = self.race_repository.db.query(Race).filter(
                and_(
                    Race.race_date >= start_date,
                    Race.race_date <= end_date,
                    Race.status == RaceStatus.SCHEDULED
                )
            ).all()

            logger.info(f"Found {len(upcoming_races)} upcoming races")

            results = {
                'total_races': len(upcoming_races),
                'successful': 0,
                'failed': 0,
                'errors': []
            }

            # Process races concurrently
            tasks = [self.ingest_weather_for_race(race.race_id) for race in upcoming_races]
            race_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(race_results):
                race = upcoming_races[i]
                if isinstance(result, Exception):
                    results['failed'] += 1
                    results['errors'].append(f"Race {race.race_id}: {str(result)}")
                    logger.error(f"Failed to process upcoming race {race.race_id}: {result}")
                elif result:
                    results['successful'] += 1
                else:
                    results['failed'] += 1

            logger.info(f"Upcoming weather update completed: {results['successful']} successful, "
                       f"{results['failed']} failed out of {results['total_races']} total")

            return results

        except Exception as e:
            logger.error(f"Error during upcoming race weather update: {e}")
            return {
                'total_races': 0,
                'successful': 0,
                'failed': 0,
                'errors': [str(e)]
            }

    async def validate_circuit_coordinates(self) -> Dict[str, Any]:
        """Validate that all active circuits have proper coordinates.

        Returns:
            Dictionary with validation results
        """
        try:
            logger.info("Validating circuit coordinates")

            all_circuits = self.circuit_repository.get_all()

            results = {
                'total_circuits': len(all_circuits),
                'with_coordinates': 0,
                'missing_coordinates': 0,
                'invalid_coordinates': 0,
                'circuits_missing_coords': [],
                'circuits_invalid_coords': []
            }

            for circuit in all_circuits:
                has_coords = circuit.latitude is not None and circuit.longitude is not None

                if not has_coords:
                    results['missing_coordinates'] += 1
                    results['circuits_missing_coords'].append({
                        'circuit_id': circuit.circuit_id,
                        'name': circuit.circuit_name,
                        'country': circuit.country
                    })
                else:
                    # Validate coordinate ranges
                    lat = float(circuit.latitude)
                    lon = float(circuit.longitude)

                    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                        results['invalid_coordinates'] += 1
                        results['circuits_invalid_coords'].append({
                            'circuit_id': circuit.circuit_id,
                            'name': circuit.circuit_name,
                            'latitude': lat,
                            'longitude': lon
                        })
                    else:
                        results['with_coordinates'] += 1

            logger.info(f"Circuit validation completed: {results['with_coordinates']} valid, "
                       f"{results['missing_coordinates']} missing, "
                       f"{results['invalid_coordinates']} invalid coordinates")

            return results

        except Exception as e:
            logger.error(f"Error during circuit coordinate validation: {e}")
            return {
                'total_circuits': 0,
                'with_coordinates': 0,
                'missing_coordinates': 0,
                'invalid_coordinates': 0,
                'circuits_missing_coords': [],
                'circuits_invalid_coords': [],
                'errors': [str(e)]
            }


# Convenience function for creating a service instance
def create_weather_service(
    db_session: Optional[Session] = None,
    weather_client: Optional[OpenWeatherMapClient] = None
) -> WeatherIngestionService:
    """Create a configured weather ingestion service instance.

    Args:
        db_session: Database session. If None, will create a new session.
        weather_client: OpenWeatherMap client. If None, will create a default client.

    Returns:
        Configured WeatherIngestionService instance
    """
    return WeatherIngestionService(db_session=db_session, weather_client=weather_client)