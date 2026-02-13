"""
Tests for F1 data ingestion services.

This module contains comprehensive tests for race and qualifying data ingestion,
including API mocking, data validation, and error handling scenarios.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import date, timedelta
import json

from app.ingestion.race_ingestion import RaceIngestionService
from app.ingestion.qualifying_ingestion import QualifyingIngestionService
from app.ingestion.base import BaseIngestionService, IngestionError, APIError, DataValidationError
from app.models.race import Race
from app.models.race_result import RaceResult
from app.models.qualifying_result import QualifyingResult
from app.models.driver import Driver
from app.models.team import Team
from app.models.circuit import Circuit


class TestBaseIngestionService:
    """Test the base ingestion service functionality."""

    @pytest.fixture
    def base_service(self):
        """Create a concrete implementation of BaseIngestionService for testing."""
        class ConcreteIngestionService(BaseIngestionService):
            async def ingest_data(self, session, season, race_round=None, **kwargs):
                return {"test": "result"}

        return ConcreteIngestionService()

    @pytest.mark.asyncio
    async def test_http_client_setup(self, base_service):
        """Test that HTTP client is properly initialized."""
        assert base_service.http_client is not None
        assert "F1 Prediction Analytics" in base_service.http_client.headers.get("User-Agent", "")

    @pytest.mark.asyncio
    async def test_api_request_success(self, base_service):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = Mock()

        with patch.object(base_service.http_client, 'get', return_value=mock_response):
            result = await base_service._make_api_request("http://test.com")
            assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_api_request_retry_on_server_error(self, base_service):
        """Test API request retries on server error."""
        # First call fails with 500, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = Exception("Server Error")

        mock_response_success = Mock()
        mock_response_success.json.return_value = {"success": "data"}
        mock_response_success.raise_for_status = Mock()

        with patch.object(base_service.http_client, 'get', side_effect=[mock_response_fail, mock_response_success]):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await base_service._make_api_request("http://test.com", retries=1)
                assert result == {"success": "data"}

    @pytest.mark.asyncio
    async def test_api_request_failure_after_retries(self, base_service):
        """Test API request fails after exhausting retries."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Persistent Error")

        with patch.object(base_service.http_client, 'get', return_value=mock_response):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                with pytest.raises(APIError):
                    await base_service._make_api_request("http://test.com", retries=1)

    def test_validate_required_fields_success(self, base_service):
        """Test successful field validation."""
        data = {"field1": "value1", "field2": "value2"}
        # Should not raise any exception
        base_service._validate_required_fields(data, ["field1", "field2"])

    def test_validate_required_fields_missing(self, base_service):
        """Test validation failure on missing fields."""
        data = {"field1": "value1"}
        with pytest.raises(DataValidationError) as exc_info:
            base_service._validate_required_fields(data, ["field1", "field2"])
        assert "Missing required fields: ['field2']" in str(exc_info.value)

    def test_safe_get_success(self, base_service):
        """Test successful nested value retrieval."""
        data = {"level1": {"level2": {"level3": "value"}}}
        result = base_service._safe_get(data, "level1", "level2", "level3")
        assert result == "value"

    def test_safe_get_missing_key(self, base_service):
        """Test safe_get returns default for missing keys."""
        data = {"level1": {"level2": "value"}}
        result = base_service._safe_get(data, "level1", "missing", default="default")
        assert result == "default"

    def test_convert_time_string_minutes_seconds(self, base_service):
        """Test time conversion for format 'M:SS.mmm'."""
        result = base_service._convert_time_string("1:23.456")
        assert abs(result - 83.456) < 0.001

    def test_convert_time_string_seconds_only(self, base_service):
        """Test time conversion for format 'SS.mmm'."""
        result = base_service._convert_time_string("83.456")
        assert abs(result - 83.456) < 0.001

    def test_convert_time_string_invalid(self, base_service):
        """Test time conversion returns None for invalid input."""
        result = base_service._convert_time_string("invalid")
        assert result is None

    @pytest.mark.asyncio
    async def test_run_ingestion_success(self, base_service, db_session):
        """Test successful ingestion run."""
        result = await base_service.run_ingestion(season=2024)

        assert result["test"] == "result"
        assert "duration_seconds" in result
        assert "start_time" in result
        assert "end_time" in result

    @pytest.mark.asyncio
    async def test_close_http_client(self, base_service):
        """Test HTTP client cleanup."""
        base_service.http_client = Mock()
        base_service.http_client.aclose = AsyncMock()

        await base_service._close_http_client()
        base_service.http_client.aclose.assert_called_once()


class TestRaceIngestionService:
    """Test the race data ingestion service."""

    @pytest.fixture
    def race_service(self):
        return RaceIngestionService()

    @pytest.fixture
    def mock_ergast_race_data(self):
        """Mock race schedule data from Ergast API."""
        return {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "raceName": "Bahrain Grand Prix",
                            "date": "2024-03-02",
                            "Circuit": {
                                "circuitId": "bahrain",
                                "circuitName": "Bahrain International Circuit",
                                "Location": {
                                    "locality": "Sakhir",
                                    "country": "Bahrain"
                                }
                            }
                        }
                    ]
                }
            }
        }

    @pytest.fixture
    def mock_ergast_results_data(self):
        """Mock race results data from Ergast API."""
        return {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "Results": [
                                {
                                    "position": "1",
                                    "Driver": {
                                        "driverId": "verstappen",
                                        "code": "VER",
                                        "givenName": "Max",
                                        "familyName": "Verstappen",
                                        "nationality": "Dutch",
                                        "dateOfBirth": "1997-09-30"
                                    },
                                    "Constructor": {
                                        "constructorId": "red_bull",
                                        "name": "Red Bull Racing Honda RBPT",
                                        "nationality": "Austrian"
                                    },
                                    "grid": "1",
                                    "points": "25",
                                    "status": "Finished",
                                    "FastestLap": {
                                        "Time": {
                                            "time": "1:31.447"
                                        }
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        }

    @pytest.mark.asyncio
    async def test_ingest_race_schedule(self, race_service, db_session, mock_ergast_race_data):
        """Test race schedule ingestion."""
        with patch.object(race_service, '_make_api_request', return_value=mock_ergast_race_data):
            results = await race_service.ingest_data(
                session=db_session,
                season=2024,
                include_results=False
            )

            assert results["races_processed"] == 1
            assert results["races_created"] == 1
            assert results["circuits_created"] == 1

            # Verify race was created
            race = db_session.query(Race).filter(Race.season_year == 2024).first()
            assert race is not None
            assert race.race_name == "Bahrain Grand Prix"
            assert race.round_number == 1

            # Verify circuit was created
            circuit = db_session.query(Circuit).filter(
                Circuit.circuit_name == "Bahrain International Circuit"
            ).first()
            assert circuit is not None
            assert circuit.location == "Sakhir"
            assert circuit.country == "Bahrain"

    @pytest.mark.asyncio
    async def test_ingest_race_results(self, race_service, db_session, test_race, mock_ergast_results_data):
        """Test race results ingestion."""
        # Set race date to past so results can be ingested
        test_race.race_date = date(2024, 3, 2)
        db_session.commit()

        with patch.object(race_service, '_make_api_request', return_value=mock_ergast_results_data):
            results = await race_service._ingest_race_results(
                session=db_session,
                season=test_race.season_year,
                race_round=None,
                results={"results_processed": 0, "results_created": 0, "drivers_created": 0, "teams_created": 0, "errors": []}
            )

            # Verify results were created
            race_result = db_session.query(RaceResult).filter(RaceResult.race_id == test_race.race_id).first()
            assert race_result is not None
            assert race_result.final_position == 1
            assert race_result.points == 25.0
            assert race_result.status == "finished"

            # Verify race status updated
            db_session.refresh(test_race)
            assert test_race.status == "completed"

    @pytest.mark.asyncio
    async def test_ensure_driver_exists_new_driver(self, race_service, db_session):
        """Test creating a new driver."""
        driver_data = {
            "driverId": "test_driver",
            "code": "TDR",
            "givenName": "Test",
            "familyName": "Driver",
            "nationality": "Test Country",
            "dateOfBirth": "1990-01-01"
        }

        results = {"drivers_created": 0}
        driver = await race_service._ensure_driver_exists(db_session, driver_data, results)

        assert driver is not None
        assert driver.driver_name == "Test Driver"
        assert driver.driver_code == "TDR"
        assert driver.nationality == "Test Country"
        assert results["drivers_created"] == 1

    @pytest.mark.asyncio
    async def test_ensure_driver_exists_existing_driver(self, race_service, db_session, test_driver):
        """Test finding an existing driver."""
        driver_data = {
            "driverId": "existing_driver",
            "code": test_driver.driver_code,
            "givenName": "Different",
            "familyName": "Name",
            "nationality": "Different Country"
        }

        results = {"drivers_created": 0}
        driver = await race_service._ensure_driver_exists(db_session, driver_data, results)

        assert driver.driver_id == test_driver.driver_id
        assert results["drivers_created"] == 0  # No new driver created

    @pytest.mark.asyncio
    async def test_ensure_team_exists_new_team(self, race_service, db_session):
        """Test creating a new team."""
        team_data = {
            "constructorId": "test_team",
            "name": "Test Racing Team",
            "nationality": "Test Country"
        }

        results = {"teams_created": 0}
        team = await race_service._ensure_team_exists(db_session, team_data, results)

        assert team is not None
        assert team.team_name == "Test Racing Team"
        assert team.nationality == "Test Country"
        assert results["teams_created"] == 1

    @pytest.mark.asyncio
    async def test_ensure_circuit_exists_new_circuit(self, race_service, db_session):
        """Test creating a new circuit."""
        circuit_data = {
            "circuitId": "test_circuit",
            "circuitName": "Test Racing Circuit",
            "Location": {
                "locality": "Test City",
                "country": "Test Country"
            }
        }

        results = {"circuits_created": 0}
        circuit = await race_service._ensure_circuit_exists(db_session, circuit_data, results)

        assert circuit is not None
        assert circuit.circuit_name == "Test Racing Circuit"
        assert circuit.location == "Test City"
        assert circuit.country == "Test Country"
        assert results["circuits_created"] == 1

    @pytest.mark.asyncio
    async def test_ingest_data_api_error(self, race_service, db_session):
        """Test handling of API errors during ingestion."""
        with patch.object(race_service, '_make_api_request', side_effect=APIError("API failed")):
            with pytest.raises(APIError):
                await race_service.ingest_data(session=db_session, season=2024)

    @pytest.mark.asyncio
    async def test_ingest_data_no_race_data(self, race_service, db_session):
        """Test handling when no race data is returned."""
        empty_response = {"MRData": {"RaceTable": {"Races": []}}}

        with patch.object(race_service, '_make_api_request', return_value=empty_response):
            results = await race_service.ingest_data(session=db_session, season=2024)

            assert results["races_processed"] == 0
            assert results["races_created"] == 0


class TestQualifyingIngestionService:
    """Test the qualifying data ingestion service."""

    @pytest.fixture
    def qualifying_service(self):
        return QualifyingIngestionService()

    @pytest.fixture
    def mock_ergast_qualifying_data(self):
        """Mock qualifying data from Ergast API."""
        return {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "QualifyingResults": [
                                {
                                    "position": "1",
                                    "Driver": {
                                        "driverId": "verstappen",
                                        "code": "VER",
                                        "givenName": "Max",
                                        "familyName": "Verstappen",
                                        "nationality": "Dutch"
                                    },
                                    "Q1": "1:29.708",
                                    "Q2": "1:29.542",
                                    "Q3": "1:29.179"
                                },
                                {
                                    "position": "2",
                                    "Driver": {
                                        "driverId": "russell",
                                        "code": "RUS",
                                        "givenName": "George",
                                        "familyName": "Russell",
                                        "nationality": "British"
                                    },
                                    "Q1": "1:30.123",
                                    "Q2": "1:29.889",
                                    "Q3": "1:29.456"
                                }
                            ]
                        }
                    ]
                }
            }
        }

    @pytest.mark.asyncio
    async def test_ingest_qualifying_data(self, qualifying_service, db_session, test_race, mock_ergast_qualifying_data):
        """Test qualifying data ingestion."""
        with patch.object(qualifying_service, '_make_api_request', return_value=mock_ergast_qualifying_data):
            results = await qualifying_service.ingest_data(
                session=db_session,
                season=test_race.season_year,
                race_round=test_race.round_number
            )

            assert results["qualifying_results_processed"] == 2
            assert results["qualifying_results_created"] == 2

            # Verify qualifying results were created
            qualifying_results = db_session.query(QualifyingResult).filter(
                QualifyingResult.race_id == test_race.race_id
            ).order_by(QualifyingResult.final_grid_position).all()

            assert len(qualifying_results) == 2

            # Check pole position driver
            pole_result = qualifying_results[0]
            assert pole_result.final_grid_position == 1
            assert pole_result.q1_time is not None
            assert pole_result.q2_time is not None
            assert pole_result.q3_time is not None
            assert pole_result.pole_position

            # Check second position driver
            second_result = qualifying_results[1]
            assert second_result.final_grid_position == 2
            assert second_result.top_10_start

    @pytest.mark.asyncio
    async def test_parse_qualifying_time(self, qualifying_service):
        """Test qualifying time parsing."""
        # Test valid time
        time_delta = qualifying_service._parse_qualifying_time("1:29.708")
        assert time_delta is not None
        total_seconds = time_delta.total_seconds()
        assert abs(total_seconds - 89.708) < 0.001

        # Test None input
        result = qualifying_service._parse_qualifying_time(None)
        assert result is None

        # Test invalid time
        result = qualifying_service._parse_qualifying_time("invalid")
        assert result is None

    @pytest.mark.asyncio
    async def test_qualifying_data_update(self, qualifying_service, db_session, test_race, mock_ergast_qualifying_data):
        """Test updating existing qualifying data."""
        # Create initial qualifying result
        from app.ingestion.race_ingestion import RaceIngestionService
        race_service = RaceIngestionService()
        driver_data = {
            "driverId": "verstappen",
            "code": "VER",
            "givenName": "Max",
            "familyName": "Verstappen"
        }
        driver = await race_service._ensure_driver_exists(db_session, driver_data, {"drivers_created": 0})

        initial_result = QualifyingResult(
            race_id=test_race.race_id,
            driver_id=driver.driver_id,
            q1_time=timedelta(seconds=90.0),
            final_grid_position=1
        )
        db_session.add(initial_result)
        db_session.commit()

        # Now run ingestion with updated data
        with patch.object(qualifying_service, '_make_api_request', return_value=mock_ergast_qualifying_data):
            results = await qualifying_service.ingest_data(
                session=db_session,
                season=test_race.season_year,
                race_round=test_race.round_number
            )

            assert results["qualifying_results_updated"] == 1

    @pytest.mark.asyncio
    async def test_validate_qualifying_data(self, qualifying_service, db_session, test_race, test_driver):
        """Test qualifying data validation."""
        # Create qualifying result with issues
        qualifying_result = QualifyingResult(
            race_id=test_race.race_id,
            driver_id=test_driver.driver_id,
            q1_time=None,  # Missing Q1 time - should be flagged
            final_grid_position=1
        )
        db_session.add(qualifying_result)
        db_session.commit()

        validation_results = await qualifying_service.validate_qualifying_data(
            session=db_session,
            season=test_race.season_year
        )

        assert validation_results["races_validated"] == 1
        assert len(validation_results["issues"]) == 1
        assert "missing Q1 time" in validation_results["issues"][0]["issues"][0]

    @pytest.mark.asyncio
    async def test_no_qualifying_data_available(self, qualifying_service, db_session, test_race):
        """Test handling when no qualifying data is available."""
        empty_response = {"MRData": {"RaceTable": {"Races": []}}}

        with patch.object(qualifying_service, '_make_api_request', return_value=empty_response):
            results = await qualifying_service.ingest_data(
                session=db_session,
                season=test_race.season_year,
                race_round=test_race.round_number
            )

            assert results["qualifying_results_processed"] == 0

    @pytest.mark.asyncio
    async def test_api_404_handling(self, qualifying_service, db_session, test_race):
        """Test handling of 404 errors (future races)."""
        with patch.object(qualifying_service, '_make_api_request', side_effect=APIError("404 Not Found")):
            # Should not raise exception for 404s (future races)
            results = await qualifying_service.ingest_data(
                session=db_session,
                season=test_race.season_year,
                race_round=test_race.round_number
            )

            assert results["qualifying_results_processed"] == 0


@pytest.mark.asyncio
async def test_integration_race_and_qualifying(db_session, test_data_builder):
    """Integration test for both race and qualifying ingestion."""
    # Create test season data
    season_data = test_data_builder.create_season_data(season_year=2024, num_races=1)
    race = season_data["races"][0]

    # Mock race data
    mock_race_data = {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "Results": [
                            {
                                "position": "1",
                                "Driver": {
                                    "driverId": "test_driver",
                                    "code": "TD1",
                                    "givenName": "Test",
                                    "familyName": "Driver",
                                    "nationality": "Test Country"
                                },
                                "Constructor": {
                                    "constructorId": "test_team",
                                    "name": "Test Team 1",
                                    "nationality": "Test Country"
                                },
                                "grid": "1",
                                "points": "25",
                                "status": "Finished"
                            }
                        ]
                    }
                ]
            }
        }
    }

    # Mock qualifying data
    mock_qualifying_data = {
        "MRData": {
            "RaceTable": {
                "Races": [
                    {
                        "QualifyingResults": [
                            {
                                "position": "1",
                                "Driver": {
                                    "driverId": "test_driver",
                                    "code": "TD1",
                                    "givenName": "Test",
                                    "familyName": "Driver"
                                },
                                "Q1": "1:30.123",
                                "Q2": "1:29.889",
                                "Q3": "1:29.456"
                            }
                        ]
                    }
                ]
            }
        }
    }

    # Set race to past date
    race.race_date = date(2024, 3, 15)
    db_session.commit()

    # Run race ingestion
    race_service = RaceIngestionService()
    with patch.object(race_service, '_make_api_request', return_value=mock_race_data):
        race_results = await race_service._ingest_race_results(
            session=db_session,
            season=2024,
            race_round=None,
            results={"results_processed": 0, "results_created": 0, "drivers_created": 0, "teams_created": 0, "errors": []}
        )

    # Run qualifying ingestion
    qualifying_service = QualifyingIngestionService()
    with patch.object(qualifying_service, '_make_api_request', return_value=mock_qualifying_data):
        qualifying_results = await qualifying_service.ingest_data(
            session=db_session,
            season=2024,
            race_round=1
        )

    # Verify both results exist for the same driver
    race_result = db_session.query(RaceResult).filter(RaceResult.race_id == race.race_id).first()
    qualifying_result = db_session.query(QualifyingResult).filter(
        QualifyingResult.race_id == race.race_id
    ).first()

    assert race_result is not None
    assert qualifying_result is not None
    assert race_result.driver_id == qualifying_result.driver_id
    assert race_result.grid_position == qualifying_result.final_grid_position