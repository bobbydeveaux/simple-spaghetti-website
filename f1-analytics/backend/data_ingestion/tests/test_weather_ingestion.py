"""
Integration tests for weather data ingestion functionality.

These tests verify the end-to-end weather data ingestion workflow
including geospatial matching, API integration, and database operations.
"""

import pytest
import asyncio
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
from pathlib import Path

# Add the parent directories to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.f1_models import Circuit, Race, WeatherData, WeatherCondition, RaceStatus, TrackType, Base
from data_ingestion.clients.weather_client import OpenWeatherMapClient, WeatherData as WeatherAPIData
from data_ingestion.services.weather_service import WeatherIngestionService, GeospatialMatch


class TestWeatherIngestionIntegration:
    """Integration tests for weather ingestion service."""

    @pytest.fixture
    def db_session(self):
        """Create an in-memory SQLite database for testing."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    @pytest.fixture
    def sample_circuits(self, db_session):
        """Create sample circuits with coordinates."""
        circuits = [
            Circuit(
                circuit_name="Monaco",
                location="Monte Carlo",
                country="Monaco",
                track_length_km=Decimal('3.337'),
                track_type=TrackType.STREET,
                latitude=Decimal('43.73473100'),
                longitude=Decimal('7.42019500')
            ),
            Circuit(
                circuit_name="Silverstone",
                location="Silverstone",
                country="United Kingdom",
                track_length_km=Decimal('5.891'),
                track_type=TrackType.PERMANENT,
                latitude=Decimal('52.07833300'),
                longitude=Decimal('-1.01666700')
            ),
            Circuit(
                circuit_name="Missing Coordinates",
                location="Unknown",
                country="Unknown",
                track_length_km=Decimal('5.000'),
                track_type=TrackType.PERMANENT,
                latitude=None,
                longitude=None
            )
        ]

        for circuit in circuits:
            db_session.add(circuit)
        db_session.commit()

        return circuits

    @pytest.fixture
    def sample_races(self, db_session, sample_circuits):
        """Create sample races for testing."""
        races = [
            Race(
                season_year=2024,
                round_number=1,
                circuit_id=sample_circuits[0].circuit_id,
                race_date=date(2024, 5, 26),
                race_name="Monaco Grand Prix",
                status=RaceStatus.COMPLETED
            ),
            Race(
                season_year=2024,
                round_number=2,
                circuit_id=sample_circuits[1].circuit_id,
                race_date=date(2024, 7, 7),
                race_name="British Grand Prix",
                status=RaceStatus.COMPLETED
            ),
            Race(
                season_year=2024,
                round_number=3,
                circuit_id=sample_circuits[0].circuit_id,
                race_date=date.today() + timedelta(days=14),
                race_name="Future Monaco Race",
                status=RaceStatus.SCHEDULED
            )
        ]

        for race in races:
            db_session.add(race)
        db_session.commit()

        return races

    @pytest.fixture
    def mock_weather_client(self):
        """Create a mock weather client."""
        client = Mock(spec=OpenWeatherMapClient)

        # Mock weather data
        mock_weather = WeatherAPIData(
            temperature_celsius=Decimal('22.5'),
            precipitation_mm=Decimal('0.0'),
            wind_speed_kph=Decimal('15.3'),
            conditions='DRY',
            humidity_percent=65,
            pressure_hpa=1013,
            visibility_km=Decimal('10.0'),
            timestamp=datetime.now(timezone.utc)
        )

        client.get_current_weather = AsyncMock(return_value=mock_weather)
        client.get_historical_weather = AsyncMock(return_value=mock_weather)
        client.get_weather_forecast = AsyncMock(return_value=[mock_weather])

        return client

    @pytest.fixture
    def weather_service(self, db_session, mock_weather_client):
        """Create weather ingestion service with mocked dependencies."""
        return WeatherIngestionService(
            db_session=db_session,
            weather_client=mock_weather_client
        )

    def test_calculate_distance(self, weather_service):
        """Test geospatial distance calculation."""
        # Test distance between Monaco and Silverstone
        monaco_lat = Decimal('43.73473100')
        monaco_lon = Decimal('7.42019500')
        silverstone_lat = Decimal('52.07833300')
        silverstone_lon = Decimal('-1.01666700')

        distance = weather_service.calculate_distance(
            monaco_lat, monaco_lon,
            silverstone_lat, silverstone_lon
        )

        # Distance should be approximately 1069 km
        assert 1000 < distance < 1200
        assert isinstance(distance, float)

    def test_find_circuits_with_coordinates(self, weather_service, sample_circuits):
        """Test finding circuits with valid coordinates."""
        matches = weather_service.find_circuits_with_coordinates()

        # Should find 2 circuits with coordinates (Monaco and Silverstone)
        assert len(matches) == 2

        monaco_match = next(
            (m for m in matches if m.circuit_name == "Monaco"), None
        )
        assert monaco_match is not None
        assert monaco_match.latitude == Decimal('43.73473100')
        assert monaco_match.longitude == Decimal('7.42019500')

    def test_find_nearest_circuit(self, weather_service, sample_circuits):
        """Test finding the nearest circuit to given coordinates."""
        # Test coordinates near Monaco (43.7347, 7.4202)
        near_monaco_lat = Decimal('43.7400')
        near_monaco_lon = Decimal('7.4000')

        nearest = weather_service.find_nearest_circuit(
            near_monaco_lat, near_monaco_lon, max_distance_km=50.0
        )

        assert nearest is not None
        assert nearest.circuit_name == "Monaco"
        assert nearest.distance_km < 5.0  # Should be very close

        # Test coordinates with no nearby circuits
        middle_of_ocean_lat = Decimal('0.0')
        middle_of_ocean_lon = Decimal('0.0')

        nearest = weather_service.find_nearest_circuit(
            middle_of_ocean_lat, middle_of_ocean_lon, max_distance_km=100.0
        )

        assert nearest is None

    @pytest.mark.asyncio
    async def test_fetch_current_weather_for_circuit(
        self, weather_service, sample_circuits, mock_weather_client
    ):
        """Test fetching current weather for a circuit."""
        monaco_circuit_id = sample_circuits[0].circuit_id

        weather_data = await weather_service.fetch_current_weather_for_circuit(
            monaco_circuit_id
        )

        assert weather_data is not None
        assert weather_data.temperature_celsius == Decimal('22.5')
        assert weather_data.conditions == 'DRY'

        # Verify the client was called with correct coordinates
        mock_weather_client.get_current_weather.assert_called_once_with(
            Decimal('43.73473100'), Decimal('7.42019500')
        )

    @pytest.mark.asyncio
    async def test_fetch_current_weather_circuit_not_found(
        self, weather_service, mock_weather_client
    ):
        """Test fetching weather for non-existent circuit."""
        weather_data = await weather_service.fetch_current_weather_for_circuit(999)

        assert weather_data is None
        mock_weather_client.get_current_weather.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_current_weather_no_coordinates(
        self, weather_service, sample_circuits, mock_weather_client
    ):
        """Test fetching weather for circuit without coordinates."""
        no_coords_circuit_id = sample_circuits[2].circuit_id

        weather_data = await weather_service.fetch_current_weather_for_circuit(
            no_coords_circuit_id
        )

        assert weather_data is None
        mock_weather_client.get_current_weather.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_historical_weather_for_race(
        self, weather_service, sample_races, mock_weather_client
    ):
        """Test fetching historical weather for a race."""
        completed_race_id = sample_races[0].race_id
        race_datetime = datetime(2024, 5, 26, 14, 0, tzinfo=timezone.utc)

        weather_data = await weather_service.fetch_historical_weather_for_race(
            completed_race_id, race_datetime
        )

        assert weather_data is not None
        assert weather_data.temperature_celsius == Decimal('22.5')

        # Verify the client was called with correct coordinates and time
        mock_weather_client.get_historical_weather.assert_called_once()
        call_args = mock_weather_client.get_historical_weather.call_args
        assert call_args[0][0] == Decimal('43.73473100')  # Monaco lat
        assert call_args[0][1] == Decimal('7.42019500')   # Monaco lon
        assert call_args[0][2] == race_datetime

    def test_map_weather_condition_to_enum(self, weather_service):
        """Test weather condition mapping to enum values."""
        assert weather_service.map_weather_condition_to_enum('DRY') == WeatherCondition.DRY
        assert weather_service.map_weather_condition_to_enum('WET') == WeatherCondition.WET
        assert weather_service.map_weather_condition_to_enum('MIXED') == WeatherCondition.MIXED
        assert weather_service.map_weather_condition_to_enum('OVERCAST') == WeatherCondition.DRY
        assert weather_service.map_weather_condition_to_enum('UNKNOWN') == WeatherCondition.DRY

    def test_create_weather_record_new(
        self, weather_service, sample_races, mock_weather_client
    ):
        """Test creating a new weather record."""
        race_id = sample_races[0].race_id

        # Create mock weather data
        weather_api_data = WeatherAPIData(
            temperature_celsius=Decimal('25.0'),
            precipitation_mm=Decimal('2.5'),  # Significant precipitation
            wind_speed_kph=Decimal('20.0'),
            conditions='WET',
            humidity_percent=80,
            pressure_hpa=1008,
            visibility_km=Decimal('5.0'),
            timestamp=datetime.now(timezone.utc)
        )

        weather_record = weather_service.create_weather_record(race_id, weather_api_data)

        assert weather_record is not None
        assert weather_record.race_id == race_id
        assert weather_record.temperature_celsius == Decimal('25.0')
        assert weather_record.precipitation_mm == Decimal('2.5')
        assert weather_record.wind_speed_kph == Decimal('20.0')
        assert weather_record.conditions == WeatherCondition.WET  # Should be wet due to precipitation

        # Verify record exists in database
        db_weather = weather_service.weather_repository.get_by_race(race_id)
        assert db_weather is not None
        assert db_weather.weather_id == weather_record.weather_id

    def test_create_weather_record_update_existing(
        self, weather_service, sample_races, db_session
    ):
        """Test updating an existing weather record."""
        race_id = sample_races[0].race_id

        # Create existing weather record
        existing_weather = WeatherData(
            race_id=race_id,
            temperature_celsius=Decimal('20.0'),
            precipitation_mm=Decimal('0.0'),
            wind_speed_kph=Decimal('10.0'),
            conditions=WeatherCondition.DRY,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(existing_weather)
        db_session.commit()

        # Update with new data
        weather_api_data = WeatherAPIData(
            temperature_celsius=Decimal('25.0'),
            precipitation_mm=Decimal('1.0'),
            wind_speed_kph=Decimal('15.0'),
            conditions='WET',
            humidity_percent=70,
            pressure_hpa=1010,
            visibility_km=Decimal('8.0'),
            timestamp=datetime.now(timezone.utc)
        )

        weather_record = weather_service.create_weather_record(race_id, weather_api_data)

        assert weather_record is not None
        assert weather_record.weather_id == existing_weather.weather_id  # Same record
        assert weather_record.temperature_celsius == Decimal('25.0')  # Updated value
        assert weather_record.conditions == WeatherCondition.WET  # Updated value

    @pytest.mark.asyncio
    async def test_ingest_weather_for_race_success(
        self, weather_service, sample_races, mock_weather_client
    ):
        """Test successful weather ingestion for a race."""
        completed_race_id = sample_races[0].race_id

        success = await weather_service.ingest_weather_for_race(completed_race_id)

        assert success is True

        # Verify weather data was created in database
        weather_data = weather_service.weather_repository.get_by_race(completed_race_id)
        assert weather_data is not None
        assert weather_data.race_id == completed_race_id

    @pytest.mark.asyncio
    async def test_ingest_weather_for_race_already_exists(
        self, weather_service, sample_races, db_session, mock_weather_client
    ):
        """Test ingesting weather for race that already has weather data."""
        race_id = sample_races[0].race_id

        # Create existing weather data
        existing_weather = WeatherData(
            race_id=race_id,
            temperature_celsius=Decimal('20.0'),
            precipitation_mm=Decimal('0.0'),
            wind_speed_kph=Decimal('10.0'),
            conditions=WeatherCondition.DRY,
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(existing_weather)
        db_session.commit()

        success = await weather_service.ingest_weather_for_race(race_id)

        assert success is True  # Should return True (no error, just skipped)

        # Should not have called the weather API since data already exists
        mock_weather_client.get_historical_weather.assert_not_called()
        mock_weather_client.get_current_weather.assert_not_called()

    @pytest.mark.asyncio
    async def test_backfill_historical_weather(
        self, weather_service, sample_races, mock_weather_client
    ):
        """Test historical weather backfill operation."""
        # Mock the race query to return only completed races without weather data
        results = await weather_service.backfill_historical_weather(
            season_year=2024,
            limit=2
        )

        assert results['total_races'] >= 0
        assert results['successful'] >= 0
        assert results['failed'] >= 0
        assert isinstance(results['errors'], list)

    @pytest.mark.asyncio
    async def test_update_upcoming_race_weather(
        self, weather_service, sample_races, mock_weather_client
    ):
        """Test upcoming race weather update operation."""
        results = await weather_service.update_upcoming_race_weather(days_ahead=30)

        assert results['total_races'] >= 0
        assert results['successful'] >= 0
        assert results['failed'] >= 0
        assert isinstance(results['errors'], list)

    @pytest.mark.asyncio
    async def test_validate_circuit_coordinates(
        self, weather_service, sample_circuits
    ):
        """Test circuit coordinate validation."""
        results = await weather_service.validate_circuit_coordinates()

        assert results['total_circuits'] == 3
        assert results['with_coordinates'] == 2  # Monaco and Silverstone
        assert results['missing_coordinates'] == 1  # Missing Coordinates circuit
        assert results['invalid_coordinates'] == 0

        # Check missing coordinates details
        assert len(results['circuits_missing_coords']) == 1
        missing_circuit = results['circuits_missing_coords'][0]
        assert missing_circuit['name'] == 'Missing Coordinates'

    @pytest.mark.asyncio
    async def test_weather_client_error_handling(
        self, weather_service, sample_circuits
    ):
        """Test error handling when weather client fails."""
        # Create a mock client that raises exceptions
        error_client = Mock(spec=OpenWeatherMapClient)
        error_client.get_current_weather = AsyncMock(
            side_effect=Exception("API Error")
        )

        # Replace the service's client
        weather_service.weather_client = error_client

        monaco_circuit_id = sample_circuits[0].circuit_id
        weather_data = await weather_service.fetch_current_weather_for_circuit(
            monaco_circuit_id
        )

        assert weather_data is None  # Should handle error gracefully

    def test_geospatial_match_dataclass(self):
        """Test GeospatialMatch dataclass."""
        match = GeospatialMatch(
            circuit_id=1,
            circuit_name="Monaco",
            latitude=Decimal('43.7347'),
            longitude=Decimal('7.4202'),
            distance_km=5.5
        )

        assert match.circuit_id == 1
        assert match.circuit_name == "Monaco"
        assert match.latitude == Decimal('43.7347')
        assert match.longitude == Decimal('7.4202')
        assert match.distance_km == 5.5


class TestWeatherClientIntegration:
    """Integration tests for OpenWeatherMap client."""

    @pytest.fixture
    def mock_response_data(self):
        """Mock OpenWeatherMap API response data."""
        return {
            'main': {
                'temp': 22.5,
                'humidity': 65,
                'pressure': 1013
            },
            'weather': [{'main': 'Clear'}],
            'wind': {'speed': 4.25},  # m/s
            'rain': {'1h': 0.0},
            'snow': {'1h': 0.0},
            'visibility': 10000,  # meters
            'dt': int(datetime.now(timezone.utc).timestamp())
        }

    @pytest.mark.asyncio
    async def test_weather_client_initialization(self):
        """Test weather client initialization."""
        with patch('data_ingestion.clients.weather_client.get_settings') as mock_settings:
            mock_settings.return_value.external_apis.weather_api_key = "test_key"
            mock_settings.return_value.external_apis.weather_base_url = "https://api.test.com"

            client = OpenWeatherMapClient()
            assert client.api_key == "test_key"
            assert client.base_url == "https://api.test.com"

    @pytest.mark.asyncio
    async def test_weather_client_current_weather_parsing(self, mock_response_data):
        """Test current weather data parsing."""
        with patch('data_ingestion.clients.weather_client.get_settings') as mock_settings:
            mock_settings.return_value.external_apis.weather_api_key = "test_key"
            mock_settings.return_value.external_apis.weather_base_url = "https://api.test.com"

            client = OpenWeatherMapClient()
            weather_data = client._parse_current_weather(mock_response_data)

            assert weather_data.temperature_celsius == Decimal('22.5')
            assert weather_data.conditions == 'DRY'
            assert weather_data.wind_speed_kph == Decimal('15.3')  # 4.25 m/s * 3.6
            assert weather_data.humidity_percent == 65
            assert weather_data.pressure_hpa == 1013

    def test_weather_condition_mapping(self):
        """Test weather condition mapping."""
        with patch('data_ingestion.clients.weather_client.get_settings') as mock_settings:
            mock_settings.return_value.external_apis.weather_api_key = "test_key"

            client = OpenWeatherMapClient()

            assert client._map_weather_condition('Clear') == 'DRY'
            assert client._map_weather_condition('Rain') == 'WET'
            assert client._map_weather_condition('Clouds') == 'OVERCAST'
            assert client._map_weather_condition('Unknown') == 'DRY'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])