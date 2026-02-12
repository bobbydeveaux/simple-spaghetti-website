"""
Unit tests for Weather API client.
"""

import pytest
import json
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from app.services.weather_client import WeatherClient, WeatherAPIError, CircuitCoordinates
from app.config import ExternalAPIConfig


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = MagicMock(spec=ExternalAPIConfig)
    config.weather_api_key = "test_api_key_12345"
    config.weather_base_url = "https://api.openweathermap.org/data/2.5"
    return config


@pytest.fixture
def mock_session():
    """Mock HTTP session for testing."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def weather_client(mock_config, mock_session):
    """Create Weather client with mocked dependencies."""
    return WeatherClient(config=mock_config, session=mock_session)


@pytest.fixture
def sample_current_weather():
    """Sample current weather data from OpenWeatherMap API."""
    return {
        "coord": {"lon": 7.4197, "lat": 43.7347},
        "weather": [
            {
                "id": 800,
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d"
            }
        ],
        "base": "stations",
        "main": {
            "temp": 22.5,
            "feels_like": 21.8,
            "temp_min": 20.2,
            "temp_max": 25.1,
            "pressure": 1013,
            "humidity": 64
        },
        "visibility": 10000,
        "wind": {
            "speed": 3.1,
            "deg": 120
        },
        "clouds": {"all": 0},
        "dt": 1646318698,
        "sys": {
            "type": 2,
            "id": 2012516,
            "country": "MC",
            "sunrise": 1646295687,
            "sunset": 1646337441
        },
        "timezone": 3600,
        "id": 2993458,
        "name": "Monaco",
        "cod": 200
    }


@pytest.fixture
def sample_forecast():
    """Sample forecast data from OpenWeatherMap API."""
    return {
        "cod": "200",
        "message": 0,
        "cnt": 40,
        "list": [
            {
                "dt": 1646323200,
                "main": {
                    "temp": 22.5,
                    "feels_like": 21.8,
                    "temp_min": 20.2,
                    "temp_max": 25.1,
                    "pressure": 1013,
                    "humidity": 64
                },
                "weather": [
                    {
                        "id": 500,
                        "main": "Rain",
                        "description": "light rain",
                        "icon": "10d"
                    }
                ],
                "clouds": {"all": 75},
                "wind": {
                    "speed": 4.2,
                    "deg": 140
                },
                "visibility": 10000,
                "pop": 0.8,
                "rain": {"3h": 2.5},
                "sys": {"pod": "d"},
                "dt_txt": "2023-03-05 15:00:00"
            }
        ],
        "city": {
            "id": 2993458,
            "name": "Monaco",
            "coord": {"lat": 43.7347, "lon": 7.4197},
            "country": "MC",
            "population": 38400,
            "timezone": 3600,
            "sunrise": 1646295687,
            "sunset": 1646337441
        }
    }


class TestCircuitCoordinates:
    """Test suite for CircuitCoordinates."""

    def test_get_coordinates_valid(self):
        """Test getting coordinates for valid circuit."""
        coords = CircuitCoordinates.get_coordinates('monaco')
        assert coords == (43.7347, 7.4197)

    def test_get_coordinates_case_insensitive(self):
        """Test case insensitive circuit lookup."""
        coords = CircuitCoordinates.get_coordinates('MONACO')
        assert coords == (43.7347, 7.4197)

    def test_get_coordinates_invalid(self):
        """Test getting coordinates for invalid circuit."""
        coords = CircuitCoordinates.get_coordinates('invalid_circuit')
        assert coords is None

    def test_get_all_circuits(self):
        """Test getting all circuit IDs."""
        circuits = CircuitCoordinates.get_all_circuits()
        assert isinstance(circuits, list)
        assert len(circuits) > 0
        assert 'monaco' in circuits
        assert 'silverstone' in circuits


class TestWeatherClient:
    """Test suite for WeatherClient."""

    def test_init_without_api_key(self, mock_session):
        """Test WeatherClient initialization without API key."""
        config = MagicMock(spec=ExternalAPIConfig)
        config.weather_api_key = None
        config.weather_base_url = "https://api.openweathermap.org/data/2.5"

        with pytest.raises(ValueError, match="Weather API key is required"):
            WeatherClient(config=config, session=mock_session)

    def test_init_with_config(self, mock_config, mock_session):
        """Test WeatherClient initialization with config."""
        client = WeatherClient(config=mock_config, session=mock_session)

        assert client.api_key == "test_api_key_12345"
        assert client.base_url == "https://api.openweathermap.org/data/2.5"
        assert client.session == mock_session
        assert client._own_session is False

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config, mock_session):
        """Test WeatherClient as async context manager."""
        mock_session.aclose = AsyncMock()

        async with WeatherClient(config=mock_config, session=mock_session) as client:
            assert isinstance(client, WeatherClient)

        mock_session.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_success(self, weather_client, sample_current_weather):
        """Test successful API request."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_current_weather
        mock_response.raise_for_status = MagicMock()

        weather_client.session.get.return_value = mock_response

        # Make request
        result = await weather_client._make_request("weather", {"lat": 43.7347, "lon": 7.4197})

        # Verify
        assert result == sample_current_weather
        weather_client.session.get.assert_called_once()

        # Check params include API key
        call_args = weather_client.session.get.call_args
        assert call_args[1]['params']['appid'] == "test_api_key_12345"
        assert call_args[1]['params']['units'] == 'metric'

    @pytest.mark.asyncio
    async def test_make_request_401_error(self, weather_client):
        """Test 401 Unauthorized error handling."""
        # Setup mock error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"

        http_error = httpx.HTTPStatusError("401 Unauthorized", request=MagicMock(), response=mock_response)
        weather_client.session.get.side_effect = http_error

        # Test error handling
        with pytest.raises(WeatherAPIError) as exc_info:
            await weather_client._make_request("weather")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_404_error(self, weather_client):
        """Test 404 Not Found error handling."""
        # Setup mock error response
        mock_response = MagicMock()
        mock_response.status_code = 404

        http_error = httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=mock_response)
        weather_client.session.get.side_effect = http_error

        # Test error handling
        with pytest.raises(WeatherAPIError) as exc_info:
            await weather_client._make_request("weather")

        assert exc_info.value.status_code == 404
        assert "Location not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_429_error(self, weather_client):
        """Test 429 Rate Limit error handling."""
        # Setup mock error response
        mock_response = MagicMock()
        mock_response.status_code = 429

        http_error = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=mock_response)
        weather_client.session.get.side_effect = http_error

        # Test error handling
        with pytest.raises(WeatherAPIError) as exc_info:
            await weather_client._make_request("weather")

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value)

    def test_validate_coordinates_valid(self, weather_client):
        """Test valid coordinate validation."""
        lat, lon = weather_client._validate_coordinates(43.7347, 7.4197)
        assert lat == 43.7347
        assert lon == 7.4197

    def test_validate_coordinates_edge_cases(self, weather_client):
        """Test edge case coordinate validation."""
        # Test boundary values
        lat, lon = weather_client._validate_coordinates(90.0, 180.0)
        assert lat == 90.0
        assert lon == 180.0

        lat, lon = weather_client._validate_coordinates(-90.0, -180.0)
        assert lat == -90.0
        assert lon == -180.0

    def test_validate_coordinates_invalid_lat(self, weather_client):
        """Test invalid latitude validation."""
        with pytest.raises(ValueError, match="Invalid latitude"):
            weather_client._validate_coordinates(91.0, 0.0)

        with pytest.raises(ValueError, match="Invalid latitude"):
            weather_client._validate_coordinates(-91.0, 0.0)

    def test_validate_coordinates_invalid_lon(self, weather_client):
        """Test invalid longitude validation."""
        with pytest.raises(ValueError, match="Invalid longitude"):
            weather_client._validate_coordinates(0.0, 181.0)

        with pytest.raises(ValueError, match="Invalid longitude"):
            weather_client._validate_coordinates(0.0, -181.0)

    def test_validate_coordinates_non_numeric(self, weather_client):
        """Test non-numeric coordinate validation."""
        with pytest.raises(ValueError, match="Coordinates must be numeric"):
            weather_client._validate_coordinates("invalid", 0.0)

        with pytest.raises(ValueError, match="Coordinates must be numeric"):
            weather_client._validate_coordinates(0.0, "invalid")

    @pytest.mark.asyncio
    async def test_get_current_weather(self, weather_client, sample_current_weather):
        """Test getting current weather."""
        weather_client._make_request = AsyncMock(return_value=sample_current_weather)

        result = await weather_client.get_current_weather(43.7347, 7.4197)

        assert result == sample_current_weather
        weather_client._make_request.assert_called_once_with(
            'weather',
            {'lat': 43.7347, 'lon': 7.4197, 'lang': 'en'}
        )

    @pytest.mark.asyncio
    async def test_get_forecast(self, weather_client, sample_forecast):
        """Test getting weather forecast."""
        weather_client._make_request = AsyncMock(return_value=sample_forecast)

        result = await weather_client.get_forecast(43.7347, 7.4197)

        assert result == sample_forecast
        weather_client._make_request.assert_called_once_with(
            'forecast',
            {'lat': 43.7347, 'lon': 7.4197, 'lang': 'en'}
        )

    @pytest.mark.asyncio
    async def test_get_historical_weather_datetime(self, weather_client):
        """Test getting historical weather with datetime."""
        mock_data = {"current": {"temp": 20.0}}
        weather_client._make_request = AsyncMock(return_value=mock_data)

        test_date = datetime(2023, 3, 5, 14, 0, 0)
        result = await weather_client.get_historical_weather(43.7347, 7.4197, test_date)

        assert result == mock_data
        expected_timestamp = int(test_date.timestamp())
        weather_client._make_request.assert_called_once_with(
            'onecall/timemachine',
            {'lat': 43.7347, 'lon': 7.4197, 'dt': expected_timestamp}
        )

    @pytest.mark.asyncio
    async def test_get_historical_weather_date(self, weather_client):
        """Test getting historical weather with date."""
        mock_data = {"current": {"temp": 20.0}}
        weather_client._make_request = AsyncMock(return_value=mock_data)

        test_date = date(2023, 3, 5)
        result = await weather_client.get_historical_weather(43.7347, 7.4197, test_date)

        assert result == mock_data

    @pytest.mark.asyncio
    async def test_get_historical_weather_unauthorized(self, weather_client):
        """Test historical weather with unauthorized error."""
        weather_client._make_request = AsyncMock(
            side_effect=WeatherAPIError("Unauthorized", 401)
        )

        with pytest.raises(WeatherAPIError, match="Historical weather data requires"):
            await weather_client.get_historical_weather(43.7347, 7.4197, datetime.now())

    @pytest.mark.asyncio
    async def test_get_weather_for_circuit_current(self, weather_client, sample_current_weather):
        """Test getting weather for circuit (current day)."""
        with patch('app.services.weather_client.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 3, 5, 12, 0, 0)

            weather_client.get_current_weather = AsyncMock(return_value=sample_current_weather)

            race_date = date(2023, 3, 5)  # Today
            result = await weather_client.get_weather_for_circuit('monaco', race_date)

            assert result['circuit_id'] == 'monaco'
            assert result['data_type'] == 'current'
            assert result['weather_data'] == sample_current_weather

    @pytest.mark.asyncio
    async def test_get_weather_for_circuit_forecast(self, weather_client, sample_forecast):
        """Test getting weather for circuit (future)."""
        with patch('app.services.weather_client.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 3, 1, 12, 0, 0)

            weather_client.get_forecast = AsyncMock(return_value=sample_forecast)

            race_date = date(2023, 3, 5)  # 4 days in future
            result = await weather_client.get_weather_for_circuit('monaco', race_date)

            assert result['circuit_id'] == 'monaco'
            assert result['data_type'] == 'forecast'
            assert result['weather_data'] == sample_forecast

    @pytest.mark.asyncio
    async def test_get_weather_for_circuit_too_far_future(self, weather_client):
        """Test getting weather for circuit too far in future."""
        with patch('app.services.weather_client.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 3, 1, 12, 0, 0)

            race_date = date(2023, 3, 15)  # 14 days in future (too far)

            with pytest.raises(WeatherAPIError, match="Weather forecast only available for next 5 days"):
                await weather_client.get_weather_for_circuit('monaco', race_date)

    @pytest.mark.asyncio
    async def test_get_weather_for_circuit_invalid_circuit(self, weather_client):
        """Test getting weather for invalid circuit."""
        race_date = date(2023, 3, 5)

        with pytest.raises(ValueError, match="Unknown circuit"):
            await weather_client.get_weather_for_circuit('invalid_circuit', race_date)

    @pytest.mark.asyncio
    async def test_get_weather_for_circuit_historical_no_subscription(self, weather_client):
        """Test getting historical weather without subscription."""
        with patch('app.services.weather_client.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 3, 10, 12, 0, 0)

            weather_client.get_historical_weather = AsyncMock(
                side_effect=WeatherAPIError("subscription required", 401)
            )

            race_date = date(2023, 3, 5)  # Past date
            result = await weather_client.get_weather_for_circuit('monaco', race_date)

            assert 'error' in result
            assert result['error'] == "Historical weather data unavailable"

    @pytest.mark.asyncio
    async def test_get_weather_summary_current(self, weather_client, sample_current_weather):
        """Test getting weather summary from current weather."""
        circuit_weather = {
            'circuit_id': 'monaco',
            'coordinates': {'lat': 43.7347, 'lon': 7.4197},
            'race_date': '2023-03-05T14:00:00',
            'data_type': 'current',
            'weather_data': sample_current_weather,
            'timestamp': '2023-03-05T12:00:00'
        }

        weather_client.get_weather_for_circuit = AsyncMock(return_value=circuit_weather)

        result = await weather_client.get_weather_summary('monaco', date(2023, 3, 5))

        assert result['circuit_id'] == 'monaco'
        assert result['data_type'] == 'current'

        summary = result['weather_summary']
        assert summary['temperature_celsius'] == 22.5
        assert summary['humidity_percent'] == 64
        assert summary['wind_speed_kph'] == 3.1 * 3.6  # Converted from m/s to km/h
        assert summary['weather_condition'] == 'Clear'

    @pytest.mark.asyncio
    async def test_get_weather_summary_forecast(self, weather_client, sample_forecast):
        """Test getting weather summary from forecast."""
        circuit_weather = {
            'circuit_id': 'monaco',
            'coordinates': {'lat': 43.7347, 'lon': 7.4197},
            'race_date': '2023-03-05T14:00:00',
            'data_type': 'forecast',
            'weather_data': sample_forecast,
            'timestamp': '2023-03-05T12:00:00'
        }

        weather_client.get_weather_for_circuit = AsyncMock(return_value=circuit_weather)

        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.fromisoformat.return_value.timestamp.return_value = 1646323200

            result = await weather_client.get_weather_summary('monaco', date(2023, 3, 5))

            assert result['circuit_id'] == 'monaco'
            assert result['data_type'] == 'forecast'

            summary = result['weather_summary']
            assert summary['temperature_celsius'] == 22.5
            assert summary['precipitation_mm'] == 2.5  # From 3h rain data

    @pytest.mark.asyncio
    async def test_get_weather_summary_error(self, weather_client):
        """Test getting weather summary with error."""
        error_response = {
            'error': 'Historical weather data unavailable',
            'message': 'Historical weather requires paid OpenWeatherMap subscription'
        }

        weather_client.get_weather_for_circuit = AsyncMock(return_value=error_response)

        result = await weather_client.get_weather_summary('monaco', date(2023, 3, 5))

        assert result == error_response

    @pytest.mark.asyncio
    async def test_health_check_success(self, weather_client, sample_current_weather):
        """Test successful health check."""
        weather_client.get_current_weather = AsyncMock(return_value=sample_current_weather)

        with patch('app.services.weather_client.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

            result = await weather_client.health_check()

        assert result['status'] == 'healthy'
        assert result['api_key_status'] == 'valid'
        assert 'response_time_seconds' in result

    @pytest.mark.asyncio
    async def test_health_check_api_key_invalid(self, weather_client):
        """Test health check with invalid API key."""
        weather_client.get_current_weather = AsyncMock(
            side_effect=WeatherAPIError("Invalid API key", 401)
        )

        with patch('app.services.weather_client.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

            result = await weather_client.health_check()

        assert result['status'] == 'unhealthy'
        assert result['api_key_status'] == 'invalid'
        assert 'error' in result

    @pytest.mark.asyncio
    async def test_create_weather_client(self):
        """Test factory function."""
        from app.services.weather_client import create_weather_client

        # Mock config to provide API key
        with patch('app.services.weather_client.ExternalAPIConfig') as mock_config_class:
            mock_config = MagicMock()
            mock_config.weather_api_key = "test_key"
            mock_config.weather_base_url = "https://api.openweathermap.org/data/2.5"
            mock_config_class.return_value = mock_config

            client = await create_weather_client()
            assert isinstance(client, WeatherClient)