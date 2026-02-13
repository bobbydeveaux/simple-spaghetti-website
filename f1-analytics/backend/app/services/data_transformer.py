"""
Data transformation utilities for F1 API data.

This module provides utilities to transform data from external APIs
(Ergast, OpenWeatherMap) into validated database models.
"""

import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union, Tuple

from ..schemas.f1_schemas import (
    DriverCreate, TeamCreate, CircuitCreate, RaceCreate,
    RaceResultCreate, QualifyingResultCreate, WeatherDataCreate,
    WeatherSummary
)

logger = logging.getLogger(__name__)


class DataTransformationError(Exception):
    """Exception raised for data transformation errors."""
    pass


class DataTransformer:
    """
    Utility class for transforming external API data into database models.

    Handles data validation, normalization, and conversion from Ergast API
    and OpenWeatherMap API formats to our internal schemas.
    """

    # Points system mapping (modern F1 points system)
    POINTS_SYSTEM = {
        1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
        6: 8, 7: 6, 8: 4, 9: 2, 10: 1
    }

    # Driver name normalization patterns
    DRIVER_NAME_PATTERNS = [
        # Handle common name variations
        (r'\.', ''),  # Remove periods
        (r'\s+', ' '),  # Normalize spaces
        (r'^(.+),\s*(.+)$', r'\2 \1'),  # "Lastname, Firstname" -> "Firstname Lastname"
    ]

    def __init__(self):
        """Initialize the data transformer."""
        self.logger = logging.getLogger(__name__)

    def transform_driver_from_ergast(self, driver_data: Dict[str, Any]) -> DriverCreate:
        """
        Transform driver data from Ergast API to DriverCreate schema.

        Args:
            driver_data: Raw driver data from Ergast API

        Returns:
            Validated DriverCreate object

        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            # Extract data with fallbacks
            driver_id = driver_data.get('driverId', '')
            given_name = driver_data.get('givenName', '')
            family_name = driver_data.get('familyName', '')
            nationality = driver_data.get('nationality')
            birth_date_str = driver_data.get('dateOfBirth')

            # Create driver code from driverId or names
            if len(driver_id) >= 3:
                driver_code = driver_id[:3].upper()
            else:
                # Fallback: create code from names
                driver_code = self._generate_driver_code(given_name, family_name)

            # Normalize driver name
            full_name = f"{given_name} {family_name}".strip()
            normalized_name = self.normalize_driver_name(full_name)

            # Parse birth date
            birth_date = None
            if birth_date_str:
                try:
                    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
                except ValueError:
                    self.logger.warning(f"Invalid birth date format for driver {normalized_name}: {birth_date_str}")

            driver = DriverCreate(
                driver_code=driver_code,
                driver_name=normalized_name,
                nationality=nationality,
                date_of_birth=birth_date,
                current_elo_rating=1500  # Default ELO rating
            )

            self.logger.debug(f"Transformed driver: {normalized_name} ({driver_code})")
            return driver

        except Exception as e:
            raise DataTransformationError(f"Failed to transform driver data: {str(e)}")

    def transform_constructor_from_ergast(self, constructor_data: Dict[str, Any]) -> TeamCreate:
        """
        Transform constructor data from Ergast API to TeamCreate schema.

        Args:
            constructor_data: Raw constructor data from Ergast API

        Returns:
            Validated TeamCreate object

        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            team_name = constructor_data.get('name', constructor_data.get('constructorId', ''))
            nationality = constructor_data.get('nationality')

            # Try to determine team color (this would ideally come from a separate mapping)
            team_color = self._get_team_color(team_name)

            team = TeamCreate(
                team_name=team_name,
                nationality=nationality,
                team_color=team_color,
                current_elo_rating=1500  # Default ELO rating
            )

            self.logger.debug(f"Transformed team: {team_name}")
            return team

        except Exception as e:
            raise DataTransformationError(f"Failed to transform constructor data: {str(e)}")

    def transform_circuit_from_ergast(self, circuit_data: Dict[str, Any]) -> CircuitCreate:
        """
        Transform circuit data from Ergast API to CircuitCreate schema.

        Args:
            circuit_data: Raw circuit data from Ergast API

        Returns:
            Validated CircuitCreate object

        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            circuit_name = circuit_data.get('circuitName', '')
            location_data = circuit_data.get('Location', {})
            location = location_data.get('locality', '')
            country = location_data.get('country', '')

            # Determine track type (this would ideally come from a separate mapping)
            track_type = self._determine_track_type(circuit_name, location)

            circuit = CircuitCreate(
                circuit_name=circuit_name,
                location=location,
                country=country,
                track_type=track_type
            )

            self.logger.debug(f"Transformed circuit: {circuit_name}")
            return circuit

        except Exception as e:
            raise DataTransformationError(f"Failed to transform circuit data: {str(e)}")

    def transform_race_from_ergast(self, race_data: Dict[str, Any], season: int) -> RaceCreate:
        """
        Transform race data from Ergast API to RaceCreate schema.

        Args:
            race_data: Raw race data from Ergast API
            season: Season year

        Returns:
            Validated RaceCreate object

        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            race_name = race_data.get('raceName', '')
            round_number = int(race_data.get('round', 0))
            race_date_str = race_data.get('date', '')

            # Parse race date
            race_date = datetime.strptime(race_date_str, '%Y-%m-%d').date()

            # Determine race status based on date
            today = date.today()
            if race_date < today:
                status = 'completed'
            elif race_date == today:
                # Could be completed or in progress - would need additional logic
                status = 'scheduled'
            else:
                status = 'scheduled'

            # Note: circuit_id would need to be resolved separately
            # This is a placeholder - the ingestion service would handle the mapping
            race = RaceCreate(
                season_year=season,
                round_number=round_number,
                circuit_id=0,  # Placeholder - needs circuit lookup
                race_name=race_name,
                race_date=race_date,
                status=status
            )

            self.logger.debug(f"Transformed race: {race_name} ({season} Round {round_number})")
            return race

        except Exception as e:
            raise DataTransformationError(f"Failed to transform race data: {str(e)}")

    def transform_race_result_from_ergast(self, result_data: Dict[str, Any], race_id: int) -> RaceResultCreate:
        """
        Transform race result data from Ergast API to RaceResultCreate schema.

        Args:
            result_data: Raw race result data from Ergast API
            race_id: Database race ID

        Returns:
            Validated RaceResultCreate object

        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            grid_position = self._safe_int(result_data.get('grid', '0'))
            final_position = self._safe_int(result_data.get('position', '0'))
            points = Decimal(str(result_data.get('points', '0')))

            # Extract fastest lap time
            fastest_lap = result_data.get('FastestLap', {})
            fastest_lap_time = fastest_lap.get('Time', {}).get('time')

            # Determine result status
            status_data = result_data.get('status', 'Finished')
            status = self._normalize_result_status(status_data)

            # Note: driver_id and team_id would need to be resolved separately
            result = RaceResultCreate(
                race_id=race_id,
                driver_id=0,  # Placeholder - needs driver lookup
                team_id=0,    # Placeholder - needs team lookup
                grid_position=grid_position if grid_position > 0 else None,
                final_position=final_position if final_position > 0 else None,
                points=points,
                fastest_lap_time=fastest_lap_time,
                status=status
            )

            self.logger.debug(f"Transformed race result: Position {final_position}, {points} points")
            return result

        except Exception as e:
            raise DataTransformationError(f"Failed to transform race result data: {str(e)}")

    def transform_qualifying_result_from_ergast(self, quali_data: Dict[str, Any], race_id: int) -> QualifyingResultCreate:
        """
        Transform qualifying result data from Ergast API to QualifyingResultCreate schema.

        Args:
            quali_data: Raw qualifying result data from Ergast API
            race_id: Database race ID

        Returns:
            Validated QualifyingResultCreate object

        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            grid_position = int(quali_data.get('position', 0))

            # Extract qualifying times
            q1_time = quali_data.get('Q1')
            q2_time = quali_data.get('Q2')
            q3_time = quali_data.get('Q3')

            # Note: driver_id and team_id would need to be resolved separately
            result = QualifyingResultCreate(
                race_id=race_id,
                driver_id=0,  # Placeholder - needs driver lookup
                team_id=0,    # Placeholder - needs team lookup
                q1_time=q1_time,
                q2_time=q2_time,
                q3_time=q3_time,
                final_grid_position=grid_position
            )

            self.logger.debug(f"Transformed qualifying result: Grid position {grid_position}")
            return result

        except Exception as e:
            raise DataTransformationError(f"Failed to transform qualifying result data: {str(e)}")

    def transform_weather_from_openweather(self, weather_data: Dict[str, Any], race_id: int) -> WeatherDataCreate:
        """
        Transform weather data from OpenWeatherMap API to WeatherDataCreate schema.

        Args:
            weather_data: Raw weather data from OpenWeatherMap API
            race_id: Database race ID

        Returns:
            Validated WeatherDataCreate object

        Raises:
            DataTransformationError: If transformation fails
        """
        try:
            # Handle different response formats from weather API
            if 'weather_summary' in weather_data:
                # From weather summary response
                summary = weather_data['weather_summary']
                temperature = summary.get('temperature_celsius')
                precipitation = summary.get('precipitation_mm', 0)
                wind_speed = summary.get('wind_speed_kph')
                conditions = summary.get('conditions', 'dry')
            else:
                # Direct OpenWeatherMap API response
                main = weather_data.get('main', {})
                weather_desc = weather_data.get('weather', [{}])[0]
                wind = weather_data.get('wind', {})
                rain = weather_data.get('rain', {})
                snow = weather_data.get('snow', {})

                temperature = main.get('temp')
                precipitation = rain.get('1h', 0) + snow.get('1h', 0)
                wind_speed = wind.get('speed', 0) * 3.6 if wind.get('speed') else None  # m/s to km/h

                # Classify conditions
                weather_main = weather_desc.get('main', '').lower()
                if precipitation > 1.0 or 'rain' in weather_main or 'storm' in weather_main:
                    conditions = 'wet'
                elif precipitation > 0.1 or 'drizzle' in weather_main:
                    conditions = 'mixed'
                else:
                    conditions = 'dry'

            weather = WeatherDataCreate(
                race_id=race_id,
                temperature_celsius=Decimal(str(temperature)) if temperature is not None else None,
                precipitation_mm=Decimal(str(precipitation)) if precipitation else None,
                wind_speed_kph=Decimal(str(wind_speed)) if wind_speed is not None else None,
                conditions=conditions
            )

            self.logger.debug(f"Transformed weather: {temperature}°C, {precipitation}mm, {conditions}")
            return weather

        except Exception as e:
            raise DataTransformationError(f"Failed to transform weather data: {str(e)}")

    def normalize_driver_name(self, driver_name: str) -> str:
        """
        Standardize driver name format.

        Args:
            driver_name: Raw driver name

        Returns:
            Normalized driver name
        """
        if not driver_name:
            return ""

        normalized = driver_name.strip()

        # Apply normalization patterns
        for pattern, replacement in self.DRIVER_NAME_PATTERNS:
            normalized = re.sub(pattern, replacement, normalized)

        return normalized.strip()

    def convert_lap_time(self, lap_time_str: str) -> Optional[float]:
        """
        Convert lap time string to seconds.

        Args:
            lap_time_str: Lap time in format "MM:SS.mmm" or "SS.mmm"

        Returns:
            Lap time in seconds, or None if invalid

        Examples:
            "1:23.456" -> 83.456
            "83.456" -> 83.456
        """
        if not lap_time_str:
            return None

        try:
            # Handle MM:SS.mmm format
            if ':' in lap_time_str:
                parts = lap_time_str.split(':')
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds

            # Handle SS.mmm format
            return float(lap_time_str)

        except (ValueError, IndexError):
            self.logger.warning(f"Failed to convert lap time: {lap_time_str}")
            return None

    def validate_race_result(self, raw_data: Dict[str, Any]) -> bool:
        """
        Validate race result data before transformation.

        Args:
            raw_data: Raw race result data

        Returns:
            True if data is valid for transformation
        """
        required_fields = ['position', 'Driver']

        for field in required_fields:
            if field not in raw_data:
                return False

        # Check driver data
        driver_data = raw_data.get('Driver', {})
        if not driver_data.get('driverId') and not (driver_data.get('givenName') and driver_data.get('familyName')):
            return False

        return True

    def _generate_driver_code(self, given_name: str, family_name: str) -> str:
        """Generate a 3-letter driver code from names."""
        if not given_name and not family_name:
            return "UNK"

        # Try family name first 3 letters
        if len(family_name) >= 3:
            return family_name[:3].upper()

        # Fallback: first letter of given name + family name
        code = (given_name[:1] + family_name[:2]).upper()
        return code.ljust(3, 'X')

    def _get_team_color(self, team_name: str) -> Optional[str]:
        """Get team color based on team name (would ideally be in a database)."""
        team_colors = {
            'Ferrari': '#DC143C',
            'Mercedes': '#00D2BE',
            'Red Bull': '#0600EF',
            'McLaren': '#FF8700',
            'Alpine': '#0090FF',
            'AlphaTauri': '#2B4562',
            'Aston Martin': '#006F62',
            'Williams': '#005AFF',
            'Alfa Romeo': '#900000',
            'Haas': '#FFFFFF'
        }

        for team, color in team_colors.items():
            if team.lower() in team_name.lower():
                return color

        return None

    def _determine_track_type(self, circuit_name: str, location: str) -> str:
        """Determine track type based on circuit name and location."""
        street_circuits = [
            'monaco', 'singapore', 'baku', 'jeddah', 'miami', 'las vegas',
            'detroit', 'phoenix', 'adelaide', 'valencia'
        ]

        circuit_lower = circuit_name.lower()
        location_lower = location.lower()

        for street in street_circuits:
            if street in circuit_lower or street in location_lower:
                return 'street'

        return 'permanent'

    def _normalize_result_status(self, status: str) -> str:
        """Normalize race result status."""
        status_lower = status.lower()

        if status_lower in ['finished', 'classified']:
            return 'finished'
        elif status_lower in ['retired', 'engine', 'gearbox', 'hydraulics', 'electrical']:
            return 'retired'
        elif 'disqualified' in status_lower:
            return 'disqualified'
        else:
            return 'dnf'

    def _safe_int(self, value: Union[str, int, None]) -> int:
        """Safely convert value to integer."""
        if value is None:
            return 0

        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def batch_validate_race_results(self, results_data: List[Dict[str, Any]]) -> Tuple[List[Dict], List[str]]:
        """
        Validate a batch of race results and return valid/invalid lists.

        Args:
            results_data: List of raw race result data

        Returns:
            Tuple of (valid_results, error_messages)
        """
        valid_results = []
        errors = []

        for i, result_data in enumerate(results_data):
            try:
                if self.validate_race_result(result_data):
                    valid_results.append(result_data)
                else:
                    errors.append(f"Result {i+1}: Missing required fields")
            except Exception as e:
                errors.append(f"Result {i+1}: Validation error - {str(e)}")

        return valid_results, errors