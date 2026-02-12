"""
Unit tests for Data Transformer.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal

from app.services.data_transformer import DataTransformer, DataTransformationError
from app.schemas.f1_schemas import (
    DriverCreate, TeamCreate, CircuitCreate, RaceCreate,
    RaceResultCreate, QualifyingResultCreate, WeatherDataCreate
)


@pytest.fixture
def transformer():
    """Create DataTransformer instance."""
    return DataTransformer()


@pytest.fixture
def sample_ergast_driver():
    """Sample driver data from Ergast API."""
    return {
        "driverId": "max_verstappen",
        "permanentNumber": "1",
        "code": "VER",
        "url": "http://en.wikipedia.org/wiki/Max_Verstappen",
        "givenName": "Max",
        "familyName": "Verstappen",
        "dateOfBirth": "1997-09-30",
        "nationality": "Dutch"
    }


@pytest.fixture
def sample_ergast_constructor():
    """Sample constructor data from Ergast API."""
    return {
        "constructorId": "red_bull",
        "url": "http://en.wikipedia.org/wiki/Red_Bull_Racing",
        "name": "Red Bull",
        "nationality": "Austrian"
    }


@pytest.fixture
def sample_ergast_circuit():
    """Sample circuit data from Ergast API."""
    return {
        "circuitId": "monaco",
        "url": "http://en.wikipedia.org/wiki/Circuit_de_Monaco",
        "circuitName": "Circuit de Monaco",
        "Location": {
            "lat": "43.7347",
            "long": "7.4197",
            "locality": "Monte-Carlo",
            "country": "Monaco"
        }
    }


@pytest.fixture
def sample_ergast_race():
    """Sample race data from Ergast API."""
    return {
        "season": "2023",
        "round": "6",
        "url": "http://en.wikipedia.org/wiki/2023_Monaco_Grand_Prix",
        "raceName": "Monaco Grand Prix",
        "Circuit": {
            "circuitId": "monaco",
            "circuitName": "Circuit de Monaco"
        },
        "date": "2023-05-28",
        "time": "13:00:00Z"
    }


@pytest.fixture
def sample_ergast_race_result():
    """Sample race result data from Ergast API."""
    return {
        "number": "1",
        "position": "1",
        "positionText": "1",
        "points": "25",
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
        "grid": "1",
        "laps": "78",
        "status": "Finished",
        "Time": {
            "millis": "6445445",
            "time": "1:47:25.445"
        },
        "FastestLap": {
            "rank": "1",
            "lap": "65",
            "Time": {
                "time": "1:12.909"
            }
        }
    }


@pytest.fixture
def sample_ergast_qualifying():
    """Sample qualifying result data from Ergast API."""
    return {
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
        "Q1": "1:11.365",
        "Q2": "1:10.270",
        "Q3": "1:10.166"
    }


@pytest.fixture
def sample_weather_data():
    """Sample weather data from OpenWeatherMap."""
    return {
        "weather_summary": {
            "temperature_celsius": 22.5,
            "humidity_percent": 65,
            "precipitation_mm": 0.0,
            "wind_speed_kph": 12.5,
            "conditions": "dry"
        }
    }


class TestDataTransformer:
    """Test suite for DataTransformer."""

    def test_init(self):
        """Test DataTransformer initialization."""
        transformer = DataTransformer()
        assert isinstance(transformer, DataTransformer)

    def test_transform_driver_from_ergast(self, transformer, sample_ergast_driver):
        """Test transforming driver data from Ergast API."""
        result = transformer.transform_driver_from_ergast(sample_ergast_driver)

        assert isinstance(result, DriverCreate)
        assert result.driver_code == "VER"
        assert result.driver_name == "Max Verstappen"
        assert result.nationality == "Dutch"
        assert result.date_of_birth == date(1997, 9, 30)
        assert result.current_elo_rating == 1500

    def test_transform_driver_missing_code(self, transformer):
        """Test transforming driver data with missing driver code."""
        driver_data = {
            "driverId": "ab",  # Too short
            "givenName": "John",
            "familyName": "Doe",
            "nationality": "American"
        }

        result = transformer.transform_driver_from_ergast(driver_data)
        assert result.driver_code == "DOE"  # Generated from family name

    def test_transform_driver_invalid_birth_date(self, transformer, sample_ergast_driver):
        """Test transforming driver data with invalid birth date."""
        sample_ergast_driver["dateOfBirth"] = "invalid-date"

        result = transformer.transform_driver_from_ergast(sample_ergast_driver)
        assert result.date_of_birth is None

    def test_transform_driver_error(self, transformer):
        """Test driver transformation error handling."""
        with pytest.raises(DataTransformationError):
            transformer.transform_driver_from_ergast({})  # Empty data

    def test_transform_constructor_from_ergast(self, transformer, sample_ergast_constructor):
        """Test transforming constructor data from Ergast API."""
        result = transformer.transform_constructor_from_ergast(sample_ergast_constructor)

        assert isinstance(result, TeamCreate)
        assert result.team_name == "Red Bull"
        assert result.nationality == "Austrian"
        assert result.current_elo_rating == 1500

    def test_transform_constructor_with_color(self, transformer):
        """Test transforming constructor with known team color."""
        constructor_data = {
            "name": "Ferrari",
            "nationality": "Italian"
        }

        result = transformer.transform_constructor_from_ergast(constructor_data)
        assert result.team_color == "#DC143C"

    def test_transform_circuit_from_ergast(self, transformer, sample_ergast_circuit):
        """Test transforming circuit data from Ergast API."""
        result = transformer.transform_circuit_from_ergast(sample_ergast_circuit)

        assert isinstance(result, CircuitCreate)
        assert result.circuit_name == "Circuit de Monaco"
        assert result.location == "Monte-Carlo"
        assert result.country == "Monaco"
        assert result.track_type == "street"  # Monaco is a street circuit

    def test_transform_circuit_permanent(self, transformer):
        """Test transforming permanent circuit."""
        circuit_data = {
            "circuitName": "Silverstone Circuit",
            "Location": {
                "locality": "Silverstone",
                "country": "UK"
            }
        }

        result = transformer.transform_circuit_from_ergast(circuit_data)
        assert result.track_type == "permanent"

    def test_transform_race_from_ergast(self, transformer, sample_ergast_race):
        """Test transforming race data from Ergast API."""
        result = transformer.transform_race_from_ergast(sample_ergast_race, 2023)

        assert isinstance(result, RaceCreate)
        assert result.season_year == 2023
        assert result.round_number == 6
        assert result.race_name == "Monaco Grand Prix"
        assert result.race_date == date(2023, 5, 28)
        assert result.status == "completed"  # Past date

    def test_transform_race_future_date(self, transformer):
        """Test transforming race with future date."""
        race_data = {
            "round": "1",
            "raceName": "Future Grand Prix",
            "date": "2030-01-01"  # Future date
        }

        result = transformer.transform_race_from_ergast(race_data, 2030)
        assert result.status == "scheduled"

    def test_transform_race_result_from_ergast(self, transformer, sample_ergast_race_result):
        """Test transforming race result data from Ergast API."""
        result = transformer.transform_race_result_from_ergast(sample_ergast_race_result, 1)

        assert isinstance(result, RaceResultCreate)
        assert result.race_id == 1
        assert result.grid_position == 1
        assert result.final_position == 1
        assert result.points == Decimal("25")
        assert result.fastest_lap_time == "1:12.909"
        assert result.status == "finished"

    def test_transform_race_result_retired(self, transformer):
        """Test transforming retired race result."""
        result_data = {
            "position": "\\N",  # Not classified
            "points": "0",
            "status": "Engine",
            "grid": "5",
            "Driver": {"driverId": "test", "givenName": "Test", "familyName": "Driver"},
            "Constructor": {"name": "Test Team"}
        }

        result = transformer.transform_race_result_from_ergast(result_data, 1)
        assert result.status == "retired"
        assert result.final_position is None

    def test_transform_qualifying_result_from_ergast(self, transformer, sample_ergast_qualifying):
        """Test transforming qualifying result data from Ergast API."""
        result = transformer.transform_qualifying_result_from_ergast(sample_ergast_qualifying, 1)

        assert isinstance(result, QualifyingResultCreate)
        assert result.race_id == 1
        assert result.q1_time == "1:11.365"
        assert result.q2_time == "1:10.270"
        assert result.q3_time == "1:10.166"
        assert result.final_grid_position == 1

    def test_transform_weather_from_openweather(self, transformer, sample_weather_data):
        """Test transforming weather data from OpenWeatherMap API."""
        result = transformer.transform_weather_from_openweather(sample_weather_data, 1)

        assert isinstance(result, WeatherDataCreate)
        assert result.race_id == 1
        assert result.temperature_celsius == Decimal("22.5")
        assert result.precipitation_mm == Decimal("0.0")
        assert result.wind_speed_kph == Decimal("12.5")
        assert result.conditions == "dry"

    def test_transform_weather_direct_api_response(self, transformer):
        """Test transforming direct OpenWeatherMap API response."""
        weather_data = {
            "main": {"temp": 20.0},
            "weather": [{"main": "Rain", "description": "light rain"}],
            "wind": {"speed": 5.0},
            "rain": {"1h": 2.5}
        }

        result = transformer.transform_weather_from_openweather(weather_data, 1)
        assert result.conditions == "wet"  # Rain condition
        assert result.precipitation_mm == Decimal("2.5")

    def test_normalize_driver_name_basic(self, transformer):
        """Test basic driver name normalization."""
        assert transformer.normalize_driver_name("Max Verstappen") == "Max Verstappen"
        assert transformer.normalize_driver_name("  Lewis  Hamilton  ") == "Lewis Hamilton"
        assert transformer.normalize_driver_name("") == ""

    def test_normalize_driver_name_patterns(self, transformer):
        """Test driver name normalization patterns."""
        # Remove periods
        assert transformer.normalize_driver_name("Jr.") == "Jr"

        # Reverse comma format
        assert transformer.normalize_driver_name("Hamilton, Lewis") == "Lewis Hamilton"

        # Multiple spaces
        assert transformer.normalize_driver_name("Max    Verstappen") == "Max Verstappen"

    def test_convert_lap_time_mmss_format(self, transformer):
        """Test converting lap time in MM:SS.mmm format."""
        assert transformer.convert_lap_time("1:23.456") == 83.456
        assert transformer.convert_lap_time("2:05.123") == 125.123

    def test_convert_lap_time_ss_format(self, transformer):
        """Test converting lap time in SS.mmm format."""
        assert transformer.convert_lap_time("83.456") == 83.456
        assert transformer.convert_lap_time("125.123") == 125.123

    def test_convert_lap_time_invalid(self, transformer):
        """Test converting invalid lap time."""
        assert transformer.convert_lap_time("invalid") is None
        assert transformer.convert_lap_time("") is None
        assert transformer.convert_lap_time(None) is None

    def test_validate_race_result_valid(self, transformer, sample_ergast_race_result):
        """Test validating valid race result data."""
        assert transformer.validate_race_result(sample_ergast_race_result) is True

    def test_validate_race_result_missing_position(self, transformer):
        """Test validating race result with missing position."""
        result_data = {
            "Driver": {"driverId": "test"}
        }
        assert transformer.validate_race_result(result_data) is False

    def test_validate_race_result_missing_driver(self, transformer):
        """Test validating race result with missing driver."""
        result_data = {"position": "1"}
        assert transformer.validate_race_result(result_data) is False

    def test_validate_race_result_incomplete_driver(self, transformer):
        """Test validating race result with incomplete driver data."""
        result_data = {
            "position": "1",
            "Driver": {}  # No driverId or names
        }
        assert transformer.validate_race_result(result_data) is False

    def test_generate_driver_code_from_family_name(self, transformer):
        """Test generating driver code from family name."""
        code = transformer._generate_driver_code("Lewis", "Hamilton")
        assert code == "HAM"

    def test_generate_driver_code_short_names(self, transformer):
        """Test generating driver code from short names."""
        code = transformer._generate_driver_code("A", "B")
        assert code == "ABX"  # Padded with X

    def test_generate_driver_code_no_names(self, transformer):
        """Test generating driver code with no names."""
        code = transformer._generate_driver_code("", "")
        assert code == "UNK"

    def test_get_team_color_known_team(self, transformer):
        """Test getting color for known team."""
        assert transformer._get_team_color("Ferrari") == "#DC143C"
        assert transformer._get_team_color("Mercedes") == "#00D2BE"

    def test_get_team_color_unknown_team(self, transformer):
        """Test getting color for unknown team."""
        assert transformer._get_team_color("Unknown Team") is None

    def test_determine_track_type_street(self, transformer):
        """Test determining street circuit type."""
        assert transformer._determine_track_type("Monaco", "Monte-Carlo") == "street"
        assert transformer._determine_track_type("Singapore Street Circuit", "Singapore") == "street"

    def test_determine_track_type_permanent(self, transformer):
        """Test determining permanent circuit type."""
        assert transformer._determine_track_type("Silverstone", "Silverstone") == "permanent"
        assert transformer._determine_track_type("Spa-Francorchamps", "Spa") == "permanent"

    def test_normalize_result_status(self, transformer):
        """Test normalizing race result status."""
        assert transformer._normalize_result_status("Finished") == "finished"
        assert transformer._normalize_result_status("Engine") == "retired"
        assert transformer._normalize_result_status("Disqualified") == "disqualified"
        assert transformer._normalize_result_status("Unknown") == "dnf"

    def test_safe_int_valid(self, transformer):
        """Test safe integer conversion with valid values."""
        assert transformer._safe_int("123") == 123
        assert transformer._safe_int(456) == 456
        assert transformer._safe_int("0") == 0

    def test_safe_int_invalid(self, transformer):
        """Test safe integer conversion with invalid values."""
        assert transformer._safe_int("invalid") == 0
        assert transformer._safe_int(None) == 0
        assert transformer._safe_int("") == 0

    def test_batch_validate_race_results(self, transformer, sample_ergast_race_result):
        """Test batch validation of race results."""
        valid_result = sample_ergast_race_result
        invalid_result = {"invalid": "data"}

        results = [valid_result, invalid_result, valid_result]
        valid_results, errors = transformer.batch_validate_race_results(results)

        assert len(valid_results) == 2
        assert len(errors) == 1
        assert "Missing required fields" in errors[0]

    def test_batch_validate_empty_list(self, transformer):
        """Test batch validation with empty list."""
        valid_results, errors = transformer.batch_validate_race_results([])
        assert len(valid_results) == 0
        assert len(errors) == 0