"""
Unit tests for Ergast API client.
"""

import pytest
import json
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from app.services.ergast_client import ErgastClient, ErgastAPIError
from app.config import ExternalAPIConfig


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = MagicMock(spec=ExternalAPIConfig)
    config.ergast_base_url = "https://ergast.com/api/f1"
    config.ergast_timeout = 30
    config.ergast_retry_attempts = 3
    return config


@pytest.fixture
def mock_session():
    """Mock HTTP session for testing."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def ergast_client(mock_config, mock_session):
    """Create Ergast client with mocked dependencies."""
    return ErgastClient(config=mock_config, session=mock_session)


@pytest.fixture
def sample_race_results():
    """Sample race results data from Ergast API."""
    return {
        "MRData": {
            "xmlns": "http://ergast.com/mrd/1.5",
            "series": "f1",
            "url": "http://ergast.com/api/f1/2023/1/results.json",
            "limit": "30",
            "offset": "0",
            "total": "20",
            "RaceTable": {
                "season": "2023",
                "round": "1",
                "Races": [
                    {
                        "season": "2023",
                        "round": "1",
                        "url": "http://en.wikipedia.org/wiki/2023_Bahrain_Grand_Prix",
                        "raceName": "Bahrain Grand Prix",
                        "Circuit": {
                            "circuitId": "bahrain",
                            "url": "http://en.wikipedia.org/wiki/Bahrain_International_Circuit",
                            "circuitName": "Bahrain International Circuit",
                            "Location": {
                                "lat": "26.0325",
                                "long": "50.5106",
                                "locality": "Sakhir",
                                "country": "Bahrain"
                            }
                        },
                        "date": "2023-03-05",
                        "time": "15:00:00Z",
                        "Results": [
                            {
                                "number": "1",
                                "position": "1",
                                "positionText": "1",
                                "points": "25",
                                "Driver": {
                                    "driverId": "max_verstappen",
                                    "permanentNumber": "1",
                                    "code": "VER",
                                    "url": "http://en.wikipedia.org/wiki/Max_Verstappen",
                                    "givenName": "Max",
                                    "familyName": "Verstappen",
                                    "dateOfBirth": "1997-09-30",
                                    "nationality": "Dutch"
                                },
                                "Constructor": {
                                    "constructorId": "red_bull",
                                    "url": "http://en.wikipedia.org/wiki/Red_Bull_Racing",
                                    "name": "Red Bull",
                                    "nationality": "Austrian"
                                },
                                "grid": "1",
                                "laps": "57",
                                "status": "Finished",
                                "Time": {
                                    "millis": "5266374",
                                    "time": "1:27:46.374"
                                },
                                "FastestLap": {
                                    "rank": "1",
                                    "lap": "49",
                                    "Time": {
                                        "time": "1:31.895"
                                    },
                                    "AverageSpeed": {
                                        "units": "kph",
                                        "speed": "204.478"
                                    }
                                }
                            }
                        ]
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_qualifying_results():
    """Sample qualifying results data from Ergast API."""
    return {
        "MRData": {
            "xmlns": "http://ergast.com/mrd/1.5",
            "series": "f1",
            "url": "http://ergast.com/api/f1/2023/1/qualifying.json",
            "limit": "30",
            "offset": "0",
            "total": "20",
            "RaceTable": {
                "season": "2023",
                "round": "1",
                "Races": [
                    {
                        "season": "2023",
                        "round": "1",
                        "QualifyingResults": [
                            {
                                "number": "1",
                                "position": "1",
                                "Driver": {
                                    "driverId": "max_verstappen",
                                    "code": "VER",
                                    "givenName": "Max",
                                    "familyName": "Verstappen"
                                },
                                "Constructor": {
                                    "constructorId": "red_bull",
                                    "name": "Red Bull"
                                },
                                "Q1": "1:29.708",
                                "Q2": "1:29.671",
                                "Q3": "1:29.708"
                            }
                        ]
                    }
                ]
            }
        }
    }


class TestErgastClient:
    """Test suite for ErgastClient."""

    @pytest.mark.asyncio
    async def test_init_default(self):
        """Test ErgastClient initialization with defaults."""
        client = ErgastClient()

        assert client.base_url == "https://ergast.com/api/f1"
        assert client.timeout == 30
        assert client.retry_attempts == 3
        assert client._own_session is True

    def test_init_with_config(self, mock_config, mock_session):
        """Test ErgastClient initialization with custom config."""
        client = ErgastClient(config=mock_config, session=mock_session)

        assert client.base_url == "https://ergast.com/api/f1"
        assert client.session == mock_session
        assert client._own_session is False

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_config, mock_session):
        """Test ErgastClient as async context manager."""
        mock_session.aclose = AsyncMock()

        async with ErgastClient(config=mock_config, session=mock_session) as client:
            assert isinstance(client, ErgastClient)

        mock_session.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_success(self, ergast_client, sample_race_results):
        """Test successful API request."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_race_results
        mock_response.raise_for_status = MagicMock()

        ergast_client.session.get.return_value = mock_response

        # Make request
        result = await ergast_client._make_request("2023/1/results.json")

        # Verify
        assert result == sample_race_results
        ergast_client.session.get.assert_called_once()

        # Check URL and params
        call_args = ergast_client.session.get.call_args
        assert "2023/1/results.json" in call_args[0][0]
        assert call_args[1]['params']['format'] == 'json'

    @pytest.mark.asyncio
    async def test_make_request_http_error(self, ergast_client):
        """Test HTTP error handling."""
        # Setup mock error response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        http_error = httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=mock_response)
        ergast_client.session.get.side_effect = http_error

        # Test error handling
        with pytest.raises(ErgastAPIError) as exc_info:
            await ergast_client._make_request("invalid/endpoint.json")

        assert exc_info.value.status_code == 404
        assert "HTTP error 404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_invalid_json(self, ergast_client):
        """Test invalid JSON response handling."""
        # Setup mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = MagicMock()

        ergast_client.session.get.return_value = mock_response

        # Test error handling
        with pytest.raises(ErgastAPIError) as exc_info:
            await ergast_client._make_request("test.json")

        assert "Invalid JSON response" in str(exc_info.value)

    def test_validate_season_valid(self, ergast_client):
        """Test valid season validation."""
        assert ergast_client._validate_season(2023) == "2023"
        assert ergast_client._validate_season("2023") == "2023"
        assert ergast_client._validate_season(1950) == "1950"

    def test_validate_season_invalid(self, ergast_client):
        """Test invalid season validation."""
        with pytest.raises(ValueError):
            ergast_client._validate_season(1949)  # Too early

        with pytest.raises(ValueError):
            ergast_client._validate_season(2040)  # Too late

        with pytest.raises(ValueError):
            ergast_client._validate_season("invalid")

    def test_validate_round_valid(self, ergast_client):
        """Test valid round validation."""
        assert ergast_client._validate_round(1) == "1"
        assert ergast_client._validate_round("15") == "15"
        assert ergast_client._validate_round(30) == "30"

    def test_validate_round_invalid(self, ergast_client):
        """Test invalid round validation."""
        with pytest.raises(ValueError):
            ergast_client._validate_round(0)  # Too low

        with pytest.raises(ValueError):
            ergast_client._validate_round(31)  # Too high

        with pytest.raises(ValueError):
            ergast_client._validate_round("invalid")

    @pytest.mark.asyncio
    async def test_fetch_race_results(self, ergast_client, sample_race_results):
        """Test fetching race results."""
        # Mock the _make_request method
        ergast_client._make_request = AsyncMock(return_value=sample_race_results)

        # Fetch results
        result = await ergast_client.fetch_race_results(2023, 1)

        # Verify
        assert result == sample_race_results
        ergast_client._make_request.assert_called_once_with("2023/1/results.json")

    @pytest.mark.asyncio
    async def test_fetch_qualifying_results(self, ergast_client, sample_qualifying_results):
        """Test fetching qualifying results."""
        # Mock the _make_request method
        ergast_client._make_request = AsyncMock(return_value=sample_qualifying_results)

        # Fetch results
        result = await ergast_client.fetch_qualifying_results(2023, 1)

        # Verify
        assert result == sample_qualifying_results
        ergast_client._make_request.assert_called_once_with("2023/1/qualifying.json")

    @pytest.mark.asyncio
    async def test_fetch_driver_standings_final(self, ergast_client):
        """Test fetching final driver standings."""
        mock_data = {"MRData": {"StandingsTable": {"StandingsLists": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_driver_standings(2023)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023/driverStandings.json")

    @pytest.mark.asyncio
    async def test_fetch_driver_standings_round(self, ergast_client):
        """Test fetching driver standings for specific round."""
        mock_data = {"MRData": {"StandingsTable": {"StandingsLists": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_driver_standings(2023, 10)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023/10/driverStandings.json")

    @pytest.mark.asyncio
    async def test_fetch_constructor_standings(self, ergast_client):
        """Test fetching constructor standings."""
        mock_data = {"MRData": {"StandingsTable": {"StandingsLists": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_constructor_standings(2023)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023/constructorStandings.json")

    @pytest.mark.asyncio
    async def test_fetch_race_schedule(self, ergast_client):
        """Test fetching race schedule."""
        mock_data = {"MRData": {"RaceTable": {"Races": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_race_schedule(2023)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023.json")

    @pytest.mark.asyncio
    async def test_fetch_circuits_all(self, ergast_client):
        """Test fetching all circuits."""
        mock_data = {"MRData": {"CircuitTable": {"Circuits": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_circuits()

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("circuits.json")

    @pytest.mark.asyncio
    async def test_fetch_circuits_season(self, ergast_client):
        """Test fetching circuits for specific season."""
        mock_data = {"MRData": {"CircuitTable": {"Circuits": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_circuits(2023)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023/circuits.json")

    @pytest.mark.asyncio
    async def test_fetch_drivers(self, ergast_client):
        """Test fetching drivers."""
        mock_data = {"MRData": {"DriverTable": {"Drivers": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_drivers(2023)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023/drivers.json")

    @pytest.mark.asyncio
    async def test_fetch_constructors(self, ergast_client):
        """Test fetching constructors."""
        mock_data = {"MRData": {"ConstructorTable": {"Constructors": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_constructors(2023)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023/constructors.json")

    @pytest.mark.asyncio
    async def test_fetch_lap_times_all(self, ergast_client):
        """Test fetching all lap times for a race."""
        mock_data = {"MRData": {"RaceTable": {"Races": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_lap_times(2023, 1)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023/1/laps.json")

    @pytest.mark.asyncio
    async def test_fetch_lap_times_specific(self, ergast_client):
        """Test fetching lap times for specific lap."""
        mock_data = {"MRData": {"RaceTable": {"Races": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        result = await ergast_client.fetch_lap_times(2023, 1, 10)

        assert result == mock_data
        ergast_client._make_request.assert_called_once_with("2023/1/laps/10.json")

    @pytest.mark.asyncio
    async def test_fetch_lap_times_invalid_lap(self, ergast_client):
        """Test fetching lap times with invalid lap number."""
        with pytest.raises(ValueError):
            await ergast_client.fetch_lap_times(2023, 1, 0)

    @pytest.mark.asyncio
    async def test_health_check_success(self, ergast_client):
        """Test successful health check."""
        mock_data = {"MRData": {"RaceTable": {"Races": []}}}
        ergast_client._make_request = AsyncMock(return_value=mock_data)

        with patch('app.services.ergast_client.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

            result = await ergast_client.health_check()

        assert result['status'] == 'healthy'
        assert 'response_time_seconds' in result
        assert result['api_url'] == ergast_client.base_url

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ergast_client):
        """Test health check with API failure."""
        ergast_client._make_request = AsyncMock(side_effect=ErgastAPIError("API Error"))

        with patch('app.services.ergast_client.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

            result = await ergast_client.health_check()

        assert result['status'] == 'unhealthy'
        assert 'error' in result
        assert 'API Error' in result['error']

    @pytest.mark.asyncio
    async def test_create_ergast_client(self):
        """Test factory function."""
        from app.services.ergast_client import create_ergast_client

        client = await create_ergast_client()
        assert isinstance(client, ErgastClient)