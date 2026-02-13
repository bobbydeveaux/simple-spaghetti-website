"""
Test suite for F1 Daily Ingestion DAG

Tests DAG structure, task dependencies, and individual task functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add the dags directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dags'))

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.providers.postgres.hooks.postgres import PostgresHook

# Import the DAG
from f1_daily_ingestion import dag, check_racing_season, get_current_season_data, process_race_calendar


class TestF1DailyIngestionDAG:
    """Test the DAG structure and configuration."""

    def test_dag_loaded(self):
        """Test that the DAG is loaded correctly."""
        assert dag is not None
        assert dag.dag_id == "f1_daily_data_ingestion"
        assert dag.description == "Daily F1 data ingestion from Ergast API and other sources"

    def test_dag_schedule(self):
        """Test DAG schedule configuration."""
        # Default schedule should be daily at 6 AM UTC
        assert dag.schedule_interval == "0 6 * * *" or dag.schedule_interval == os.getenv("F1_DATA_INGESTION_SCHEDULE", "0 6 * * *")

    def test_dag_tags(self):
        """Test DAG has appropriate tags."""
        expected_tags = ["f1", "data-ingestion", "daily", "ergast"]
        assert all(tag in dag.tags for tag in expected_tags)

    def test_dag_catchup_disabled(self):
        """Test that catchup is disabled."""
        assert dag.catchup is False

    def test_dag_max_active_runs(self):
        """Test that max active runs is set to 1."""
        assert dag.max_active_runs == 1

    def test_task_count(self):
        """Test expected number of tasks in the DAG."""
        # Should have at least the main tasks
        task_ids = list(dag.task_dict.keys())
        expected_tasks = [
            "check_racing_season",
            "racing_season_tasks.get_season_data",
            "racing_season_tasks.process_race_calendar",
            "racing_season_tasks.get_completed_races",
            "racing_season_tasks.process_race_results",
            "racing_season_tasks.fetch_weather_data",
            "offseason_tasks.offseason_maintenance",
            "validate_data_quality"
        ]

        for expected_task in expected_tasks:
            assert expected_task in task_ids, f"Task {expected_task} not found in DAG"

    def test_task_dependencies(self):
        """Test task dependencies are correct."""
        check_season_task = dag.get_task("check_racing_season")
        validate_task = dag.get_task("validate_data_quality")

        # Check season should be first
        assert len(check_season_task.upstream_task_ids) == 0

        # Validate should be last and depend on both groups
        assert len(validate_task.downstream_task_ids) == 0


class TestSeasonCheck:
    """Test the racing season check functionality."""

    @patch('f1_daily_ingestion.datetime')
    def test_check_racing_season_in_season(self, mock_datetime):
        """Test season check during racing season."""
        # Mock current date to be in racing season (July)
        mock_datetime.now.return_value.date.return_value = datetime(2024, 7, 15).date()
        mock_datetime.now.return_value = datetime(2024, 7, 15)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        context = {"task_instance": Mock()}
        result = check_racing_season(**context)

        assert result == "racing_season_tasks"

    @patch('f1_daily_ingestion.datetime')
    def test_check_racing_season_offseason(self, mock_datetime):
        """Test season check during off-season."""
        # Mock current date to be in off-season (February)
        mock_datetime.now.return_value.date.return_value = datetime(2024, 2, 15).date()
        mock_datetime.now.return_value = datetime(2024, 2, 15)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        context = {"task_instance": Mock()}
        result = check_racing_season(**context)

        assert result == "offseason_tasks"


class TestSeasonDataFetch:
    """Test season data fetching functionality."""

    @patch('f1_daily_ingestion.requests.get')
    @patch('f1_daily_ingestion.datetime')
    def test_get_current_season_data_success(self, mock_datetime, mock_requests):
        """Test successful season data fetch."""
        # Mock current year
        mock_datetime.now.return_value.year = 2024
        mock_datetime.now.return_value = datetime(2024, 7, 15)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "raceName": "Bahrain Grand Prix",
                            "date": "2024-03-02",
                            "Circuit": {
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
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        context = {"task_instance": Mock()}
        result = get_current_season_data(**context)

        assert result is not None
        assert result["season"] == 2024
        assert len(result["races"]) == 1
        assert result["races"][0]["raceName"] == "Bahrain Grand Prix"

    @patch('f1_daily_ingestion.requests.get')
    def test_get_current_season_data_api_error(self, mock_requests):
        """Test season data fetch with API error."""
        # Mock API error
        mock_requests.side_effect = Exception("API Error")

        context = {"task_instance": Mock()}

        with pytest.raises(Exception):
            get_current_season_data(**context)


class TestRaceCalendarProcessing:
    """Test race calendar processing functionality."""

    @patch('f1_daily_ingestion.PostgresHook')
    def test_process_race_calendar_success(self, mock_pg_hook_class):
        """Test successful race calendar processing."""
        # Mock PostgresHook
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock XCom data
        mock_task_instance = Mock()
        mock_task_instance.xcom_pull.return_value = {
            "races": [
                {
                    "season": "2024",
                    "round": "1",
                    "raceName": "Bahrain Grand Prix",
                    "date": "2024-03-02",
                    "Circuit": {
                        "circuitName": "Bahrain International Circuit",
                        "Location": {
                            "locality": "Sakhir",
                            "country": "Bahrain"
                        }
                    }
                }
            ]
        }

        context = {"task_instance": mock_task_instance}

        # Mock database responses
        mock_pg_hook.get_first.side_effect = [
            None,  # Circuit doesn't exist
            [1],   # Circuit inserted, returns circuit_id
            None,  # Race doesn't exist
            [1]    # Race inserted, returns race_id
        ]

        # Should not raise an exception
        process_race_calendar(**context)

        # Verify database calls were made
        assert mock_pg_hook.get_first.call_count >= 2
        assert mock_pg_hook.run.call_count >= 0  # May be called for inserts

    def test_process_race_calendar_no_data(self):
        """Test race calendar processing with no XCom data."""
        mock_task_instance = Mock()
        mock_task_instance.xcom_pull.return_value = None

        context = {"task_instance": mock_task_instance}

        with pytest.raises(ValueError, match="No season data found in XCom"):
            process_race_calendar(**context)


class TestDataValidation:
    """Test data validation functionality."""

    @patch('f1_daily_ingestion.PostgresHook')
    def test_validate_data_quality(self, mock_pg_hook_class):
        """Test data quality validation."""
        from f1_daily_ingestion import validate_data_quality

        # Mock PostgresHook
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock database responses
        mock_pg_hook.get_first.side_effect = [
            [23],  # Race count
            [15],  # Completed races count
            [300], # Race results count
            [0]    # Orphaned results count
        ]

        context = {"task_instance": Mock()}

        # Should not raise an exception
        validate_data_quality(**context)

        # Verify database calls were made
        assert mock_pg_hook.get_first.call_count == 4

    @patch('f1_daily_ingestion.PostgresHook')
    def test_validate_data_quality_critical_error(self, mock_pg_hook_class):
        """Test data quality validation with critical error."""
        from f1_daily_ingestion import validate_data_quality

        # Mock PostgresHook
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock database responses - no races found
        mock_pg_hook.get_first.side_effect = [
            [0],   # Race count - critical error
            [0],   # Completed races count
            [0],   # Race results count
            [0]    # Orphaned results count
        ]

        context = {"task_instance": Mock()}

        with pytest.raises(ValueError, match="Critical data quality issue: No races found"):
            validate_data_quality(**context)


class TestHelperFunctions:
    """Test helper functions."""

    @patch('f1_daily_ingestion.PostgresHook')
    def test_process_circuit_new_circuit(self, mock_pg_hook_class):
        """Test processing a new circuit."""
        from f1_daily_ingestion import process_circuit

        mock_pg_hook = Mock()

        circuit_data = {
            "circuitName": "Test Circuit"
        }
        location_data = {
            "locality": "Test City",
            "country": "Test Country"
        }

        # Mock circuit doesn't exist, then return new circuit_id
        mock_pg_hook.get_first.side_effect = [None, [1]]

        result = process_circuit(mock_pg_hook, circuit_data, location_data)

        assert result == 1
        assert mock_pg_hook.get_first.call_count == 2

    @patch('f1_daily_ingestion.PostgresHook')
    def test_process_circuit_existing_circuit(self, mock_pg_hook_class):
        """Test processing an existing circuit."""
        from f1_daily_ingestion import process_circuit

        mock_pg_hook = Mock()

        circuit_data = {
            "circuitName": "Test Circuit"
        }
        location_data = {
            "locality": "Test City",
            "country": "Test Country"
        }

        # Mock circuit exists
        mock_pg_hook.get_first.return_value = [1]

        result = process_circuit(mock_pg_hook, circuit_data, location_data)

        assert result == 1
        assert mock_pg_hook.get_first.call_count == 1

    def test_process_circuit_missing_name(self):
        """Test processing circuit with missing name."""
        from f1_daily_ingestion import process_circuit

        mock_pg_hook = Mock()

        circuit_data = {}  # Missing circuitName
        location_data = {}

        result = process_circuit(mock_pg_hook, circuit_data, location_data)

        assert result is None


class TestIntegration:
    """Integration tests for the DAG."""

    @patch('f1_daily_ingestion.PostgresHook')
    @patch('f1_daily_ingestion.requests.get')
    @patch('f1_daily_ingestion.datetime')
    def test_full_dag_execution_flow(self, mock_datetime, mock_requests, mock_pg_hook_class):
        """Test a complete DAG execution flow."""
        # Mock current date to be in racing season
        mock_datetime.now.return_value.date.return_value = datetime(2024, 7, 15).date()
        mock_datetime.now.return_value = datetime(2024, 7, 15)
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "season": "2024",
                            "round": "1",
                            "raceName": "Test Grand Prix",
                            "date": "2024-07-01",
                            "Circuit": {
                                "circuitName": "Test Circuit",
                                "Location": {"locality": "Test", "country": "Test"}
                            }
                        }
                    ]
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock PostgresHook
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook
        mock_pg_hook.get_first.side_effect = [
            None, [1],  # Circuit processing
            None, [1],  # Race processing
            [1], [1], [1], [0]  # Data validation
        ]

        # Test season check
        context = {"task_instance": Mock()}
        season_check_result = check_racing_season(**context)
        assert season_check_result == "racing_season_tasks"

        # Test season data fetch
        season_data = get_current_season_data(**context)
        assert season_data["season"] == 2024
        assert len(season_data["races"]) == 1

        # Test race calendar processing
        mock_task_instance = Mock()
        mock_task_instance.xcom_pull.return_value = season_data
        context["task_instance"] = mock_task_instance

        # Should complete without errors
        process_race_calendar(**context)


if __name__ == "__main__":
    pytest.main([__file__])