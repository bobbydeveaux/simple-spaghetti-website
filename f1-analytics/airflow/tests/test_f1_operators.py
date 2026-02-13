"""
Test suite for F1 Custom Operators

Tests custom Airflow operators for ELO ratings, predictions, and data validation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add the plugins directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plugins'))

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.exceptions import AirflowException

# Import custom operators
from f1_operators import EloRatingOperator, F1APIDataOperator, DataValidationOperator, PredictionModelOperator


class TestEloRatingOperator:
    """Test the ELO Rating Operator."""

    def test_operator_initialization(self):
        """Test operator can be initialized with correct parameters."""
        operator = EloRatingOperator(
            task_id="test_elo",
            postgres_conn_id="test_conn",
            k_factor=32,
            race_id=1,
            dag=None
        )

        assert operator.postgres_conn_id == "test_conn"
        assert operator.k_factor == 32
        assert operator.race_id == 1
        assert operator.process_all_recent is False

    def test_operator_initialization_process_all(self):
        """Test operator initialization for processing all recent races."""
        operator = EloRatingOperator(
            task_id="test_elo_all",
            process_all_recent=True,
            dag=None
        )

        assert operator.process_all_recent is True
        assert operator.race_id is None

    @patch('f1_operators.PostgresHook')
    def test_execute_specific_race(self, mock_pg_hook_class):
        """Test executing ELO calculation for a specific race."""
        # Mock PostgresHook
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock race results data
        mock_pg_hook.get_records.return_value = [
            (1, 1, 1, 1500, 1500),  # driver_id, team_id, position, driver_elo, team_elo
            (2, 1, 2, 1400, 1500),
            (3, 2, 3, 1600, 1400)
        ]

        operator = EloRatingOperator(
            task_id="test_elo",
            race_id=1,
            dag=None
        )

        context = {}
        operator.execute(context)

        # Verify database calls were made
        assert mock_pg_hook.get_records.called
        assert mock_pg_hook.run.call_count >= 3  # At least 3 updates (for 3 drivers/teams)

    @patch('f1_operators.PostgresHook')
    def test_execute_all_recent(self, mock_pg_hook_class):
        """Test executing ELO calculation for all recent races."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock recent races and results
        mock_pg_hook.get_records.side_effect = [
            [(1,), (2,)],  # Recent race IDs
            [(1, 1, 1, 1500, 1500)],  # Results for race 1
            [(2, 1, 1, 1400, 1500)]   # Results for race 2
        ]

        operator = EloRatingOperator(
            task_id="test_elo_all",
            process_all_recent=True,
            dag=None
        )

        context = {}
        operator.execute(context)

        # Verify database calls were made for multiple races
        assert mock_pg_hook.get_records.call_count == 3

    def test_execute_no_parameters(self):
        """Test execute fails when no race_id or process_all_recent specified."""
        operator = EloRatingOperator(
            task_id="test_elo_fail",
            dag=None
        )

        context = {}

        with pytest.raises(AirflowException, match="Either race_id or process_all_recent must be specified"):
            operator.execute(context)

    def test_elo_calculation_logic(self):
        """Test ELO calculation logic."""
        operator = EloRatingOperator(task_id="test", dag=None)

        # Test data: [(driver_id, team_id, position, driver_elo, team_elo)]
        results = [
            (1, 1, 1, 1500, 1500),  # Winner
            (2, 1, 2, 1500, 1500),  # Second
            (3, 2, 3, 1500, 1400)   # Third
        ]

        elo_updates = operator._calculate_elo_updates(results)

        assert len(elo_updates) == 3

        # Winner should gain ELO points
        winner_update = elo_updates[0]
        assert winner_update[2] > 1500  # New driver ELO should be higher

        # Lower finisher should lose ELO points
        third_update = elo_updates[2]
        assert third_update[2] < 1500  # New driver ELO should be lower


class TestF1APIDataOperator:
    """Test the F1 API Data Operator."""

    def test_operator_initialization(self):
        """Test operator initialization."""
        operator = F1APIDataOperator(
            task_id="test_api",
            api_endpoint="current.json",
            season="2024",
            round_number="1",
            dag=None
        )

        assert operator.api_endpoint == "current.json"
        assert operator.season == "2024"
        assert operator.round_number == "1"
        assert operator.timeout == 30

    def test_build_url(self):
        """Test URL building logic."""
        operator = F1APIDataOperator(
            task_id="test_api",
            api_endpoint="results.json",
            api_base_url="https://ergast.com/api/f1",
            season="2024",
            round_number="1",
            dag=None
        )

        url = operator._build_url()
        expected_url = "https://ergast.com/api/f1/2024/1/results.json"
        assert url == expected_url

    def test_build_url_no_round(self):
        """Test URL building without round number."""
        operator = F1APIDataOperator(
            task_id="test_api",
            api_endpoint="races.json",
            season="2024",
            dag=None
        )

        url = operator._build_url()
        expected_url = "https://ergast.com/api/f1/2024/races.json"
        assert url == expected_url

    @patch('f1_operators.requests.get')
    def test_execute_success(self, mock_requests):
        """Test successful API execution."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {"MRData": {"RaceTable": {"Races": []}}}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        operator = F1APIDataOperator(
            task_id="test_api",
            api_endpoint="races.json",
            dag=None
        )

        context = {}
        result = operator.execute(context)

        assert result is not None
        assert "MRData" in result
        mock_requests.assert_called_once()

    @patch('f1_operators.requests.get')
    def test_execute_retry_logic(self, mock_requests):
        """Test retry logic on failure."""
        # Mock failed requests
        mock_requests.side_effect = Exception("API Error")

        operator = F1APIDataOperator(
            task_id="test_api",
            api_endpoint="races.json",
            retry_attempts=2,
            dag=None
        )

        context = {}

        with pytest.raises(AirflowException, match="Failed to fetch data after 2 attempts"):
            operator.execute(context)

        assert mock_requests.call_count == 2


class TestDataValidationOperator:
    """Test the Data Validation Operator."""

    def test_operator_initialization(self):
        """Test operator initialization."""
        validation_rules = {
            "test_rule": {
                "query": "SELECT COUNT(*) FROM test_table",
                "fail_threshold": 0
            }
        }

        operator = DataValidationOperator(
            task_id="test_validation",
            validation_rules=validation_rules,
            table_name="test_table",
            dag=None
        )

        assert operator.validation_rules == validation_rules
        assert operator.table_name == "test_table"
        assert operator.fail_on_validation_error is True

    @patch('f1_operators.PostgresHook')
    def test_execute_table_validation(self, mock_pg_hook_class):
        """Test table validation execution."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock database responses
        mock_pg_hook.get_first.side_effect = [
            [True],   # Table exists
            [100],    # Row count
            [],       # Primary key columns
        ]
        mock_pg_hook.get_records.return_value = []

        operator = DataValidationOperator(
            task_id="test_validation",
            table_name="test_table",
            dag=None
        )

        context = {}
        result = operator.execute(context)

        assert "table_exists" in result
        assert result["table_exists"] is True
        assert result["row_count"] == 100

    @patch('f1_operators.PostgresHook')
    def test_execute_custom_validation_rules(self, mock_pg_hook_class):
        """Test custom validation rules execution."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock rule query result
        mock_pg_hook.get_first.return_value = [5]  # Rule returns 5

        validation_rules = {
            "test_rule": {
                "query": "SELECT COUNT(*) FROM test_table WHERE status = 'invalid'",
                "fail_threshold": 10  # Should pass (5 <= 10)
            }
        }

        operator = DataValidationOperator(
            task_id="test_validation",
            validation_rules=validation_rules,
            dag=None
        )

        context = {}
        result = operator.execute(context)

        assert "test_rule" in result
        assert result["test_rule"]["count"] == 5
        assert result["test_rule"]["passed"] is True

    @patch('f1_operators.PostgresHook')
    def test_execute_validation_failure(self, mock_pg_hook_class):
        """Test validation failure handling."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock rule query result that exceeds threshold
        mock_pg_hook.get_first.return_value = [15]

        validation_rules = {
            "test_rule": {
                "query": "SELECT COUNT(*) FROM test_table WHERE status = 'invalid'",
                "fail_threshold": 10  # Should fail (15 > 10)
            }
        }

        operator = DataValidationOperator(
            task_id="test_validation",
            validation_rules=validation_rules,
            fail_on_validation_error=True,
            dag=None
        )

        context = {}

        with pytest.raises(AirflowException, match="Validation rule 'test_rule' failed"):
            operator.execute(context)


class TestPredictionModelOperator:
    """Test the Prediction Model Operator."""

    def test_operator_initialization(self):
        """Test operator initialization."""
        operator = PredictionModelOperator(
            task_id="test_predictions",
            model_version="v2",
            race_ids=[1, 2, 3],
            dag=None
        )

        assert operator.model_version == "v2"
        assert operator.race_ids == [1, 2, 3]
        assert operator.update_all_upcoming is False

    @patch('f1_operators.PostgresHook')
    def test_get_upcoming_races(self, mock_pg_hook_class):
        """Test getting upcoming races."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock upcoming races
        mock_pg_hook.get_records.return_value = [(1,), (2,), (3,)]

        operator = PredictionModelOperator(
            task_id="test_predictions",
            dag=None
        )

        upcoming_races = operator._get_upcoming_races(mock_pg_hook)

        assert upcoming_races == [1, 2, 3]
        assert mock_pg_hook.get_records.called

    @patch('f1_operators.PostgresHook')
    def test_generate_predictions(self, mock_pg_hook_class):
        """Test prediction generation."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock driver data
        mock_pg_hook.get_records.return_value = [
            (1, "Driver One", 1600),
            (2, "Driver Two", 1500),
            (3, "Driver Three", 1400)
        ]

        operator = PredictionModelOperator(
            task_id="test_predictions",
            model_version="v1",
            dag=None
        )

        predictions = operator._generate_predictions(mock_pg_hook, race_id=1)

        assert len(predictions) == 3
        assert all("driver_id" in pred for pred in predictions)
        assert all("predicted_win_probability" in pred for pred in predictions)
        assert all(pred["model_version"] == "v1" for pred in predictions)

        # Probabilities should sum to 100%
        total_prob = sum(pred["predicted_win_probability"] for pred in predictions)
        assert abs(total_prob - 100.0) < 0.1  # Allow small rounding error

    @patch('f1_operators.PostgresHook')
    def test_execute_specific_races(self, mock_pg_hook_class):
        """Test execution for specific race IDs."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock driver data
        mock_pg_hook.get_records.return_value = [
            (1, "Driver One", 1600)
        ]

        # Mock existing prediction check
        mock_pg_hook.get_first.return_value = None  # No existing predictions

        operator = PredictionModelOperator(
            task_id="test_predictions",
            race_ids=[1, 2],
            dag=None
        )

        context = {}
        result = operator.execute(context)

        assert result["predictions_updated"] == 2
        assert result["races_processed"] == 2

    @patch('f1_operators.PostgresHook')
    def test_execute_update_all_upcoming(self, mock_pg_hook_class):
        """Test execution for all upcoming races."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock upcoming races query
        mock_pg_hook.get_records.side_effect = [
            [(1,), (2,)],  # Upcoming races
            [(1, "Driver One", 1600)],  # Driver data for race 1
            [(1, "Driver One", 1600)]   # Driver data for race 2
        ]

        # Mock existing prediction checks
        mock_pg_hook.get_first.return_value = None

        operator = PredictionModelOperator(
            task_id="test_predictions",
            update_all_upcoming=True,
            dag=None
        )

        context = {}
        result = operator.execute(context)

        assert result["predictions_updated"] == 2
        assert result["races_processed"] == 2


class TestIntegration:
    """Integration tests for operators."""

    @patch('f1_operators.PostgresHook')
    def test_operator_chain_execution(self, mock_pg_hook_class):
        """Test chaining multiple operators together."""
        mock_pg_hook = Mock()
        mock_pg_hook_class.return_value = mock_pg_hook

        # Mock database responses for validation
        mock_pg_hook.get_first.side_effect = [
            [True],   # Table exists
            [100],    # Row count
            [0],      # Validation rule result
        ]

        # Test data validation operator
        validation_op = DataValidationOperator(
            task_id="validate",
            table_name="races",
            validation_rules={
                "race_count": {
                    "query": "SELECT COUNT(*) FROM races WHERE status = 'invalid'",
                    "fail_threshold": 0
                }
            },
            dag=None
        )

        context = {}
        validation_result = validation_op.execute(context)

        assert validation_result["table_exists"] is True
        assert validation_result["race_count"]["passed"] is True

        # Test ELO operator after validation
        mock_pg_hook.get_records.return_value = [
            (1, 1, 1, 1500, 1500)
        ]

        elo_op = EloRatingOperator(
            task_id="elo_update",
            race_id=1,
            dag=None
        )

        elo_op.execute(context)

        # Verify both operators executed successfully
        assert mock_pg_hook.get_first.called
        assert mock_pg_hook.get_records.called


if __name__ == "__main__":
    pytest.main([__file__])