"""
F1 Analytics Custom Airflow Operators

Custom operators for F1-specific data processing tasks including
ELO rating calculations, prediction model updates, and data validation.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging
import json

from airflow.models import BaseOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowException

import requests
import pandas as pd
from decimal import Decimal


class EloRatingOperator(BaseOperator):
    """
    Custom operator for calculating and updating ELO ratings for drivers and teams.
    """

    template_fields = ["race_id", "k_factor"]

    @apply_defaults
    def __init__(
        self,
        postgres_conn_id: str = "f1_analytics_postgres",
        k_factor: int = 32,
        race_id: Optional[int] = None,
        process_all_recent: bool = False,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.postgres_conn_id = postgres_conn_id
        self.k_factor = k_factor
        self.race_id = race_id
        self.process_all_recent = process_all_recent

    def execute(self, context):
        """Execute ELO rating calculations."""
        pg_hook = PostgresHook(postgres_conn_id=self.postgres_conn_id)

        if self.race_id:
            self._process_race_elo(pg_hook, self.race_id)
        elif self.process_all_recent:
            self._process_recent_races_elo(pg_hook)
        else:
            raise AirflowException("Either race_id or process_all_recent must be specified")

        self.log.info("ELO rating calculation completed successfully")

    def _process_race_elo(self, pg_hook: PostgresHook, race_id: int):
        """Process ELO ratings for a specific race."""
        # Get race results ordered by position
        results_query = """
            SELECT rr.driver_id, rr.team_id, rr.final_position, d.current_elo_rating as driver_elo,
                   t.current_elo_rating as team_elo
            FROM race_results rr
            JOIN drivers d ON rr.driver_id = d.driver_id
            JOIN teams t ON rr.team_id = t.team_id
            WHERE rr.race_id = %s AND rr.final_position IS NOT NULL
            ORDER BY rr.final_position
        """

        results = pg_hook.get_records(results_query, parameters=[race_id])

        if not results:
            self.log.warning(f"No results found for race {race_id}")
            return

        # Calculate ELO updates
        elo_updates = self._calculate_elo_updates(results)

        # Apply updates to database
        for driver_id, team_id, new_driver_elo, new_team_elo in elo_updates:
            # Update driver ELO
            pg_hook.run(
                "UPDATE drivers SET current_elo_rating = %s, updated_at = %s WHERE driver_id = %s",
                parameters=[new_driver_elo, datetime.now(timezone.utc), driver_id]
            )

            # Update team ELO
            pg_hook.run(
                "UPDATE teams SET current_elo_rating = %s, updated_at = %s WHERE team_id = %s",
                parameters=[new_team_elo, datetime.now(timezone.utc), team_id]
            )

        self.log.info(f"Updated ELO ratings for {len(elo_updates)} driver/team combinations")

    def _process_recent_races_elo(self, pg_hook: PostgresHook):
        """Process ELO ratings for races without ELO updates in the last 7 days."""
        # Get races that need ELO processing
        recent_races_query = """
            SELECT DISTINCT r.race_id
            FROM races r
            JOIN race_results rr ON r.race_id = rr.race_id
            WHERE r.status = 'completed'
            AND r.race_date >= CURRENT_DATE - INTERVAL '7 days'
            ORDER BY r.race_date
        """

        races = pg_hook.get_records(recent_races_query)

        for race in races:
            self._process_race_elo(pg_hook, race[0])

    def _calculate_elo_updates(self, results: List[tuple]) -> List[tuple]:
        """
        Calculate ELO rating updates based on race results.
        Uses pairwise comparisons between all drivers.
        """
        updates = []

        for i, (driver_id_a, team_id_a, pos_a, elo_a, team_elo_a) in enumerate(results):
            driver_elo_change = 0
            team_elo_change = 0

            for j, (driver_id_b, team_id_b, pos_b, elo_b, team_elo_b) in enumerate(results):
                if i == j:
                    continue

                # Driver finished better than driver B
                actual_score = 1 if pos_a < pos_b else 0

                # Expected score based on current ELO
                expected_score = 1 / (1 + 10**((elo_b - elo_a) / 400))

                # ELO update
                driver_change = self.k_factor * (actual_score - expected_score)
                driver_elo_change += driver_change

                # Team ELO calculation
                team_expected = 1 / (1 + 10**((team_elo_b - team_elo_a) / 400))
                team_change = self.k_factor * (actual_score - team_expected)
                team_elo_change += team_change

            # Normalize by number of comparisons
            num_comparisons = len(results) - 1
            if num_comparisons > 0:
                driver_elo_change /= num_comparisons
                team_elo_change /= num_comparisons

            new_driver_elo = max(1000, int(elo_a + driver_elo_change))  # Minimum ELO of 1000
            new_team_elo = max(1000, int(team_elo_a + team_elo_change))

            updates.append((driver_id_a, team_id_a, new_driver_elo, new_team_elo))

        return updates


class F1APIDataOperator(BaseOperator):
    """
    Custom operator for fetching data from external F1 APIs with retry logic and error handling.
    """

    template_fields = ["api_endpoint", "season", "round_number"]

    @apply_defaults
    def __init__(
        self,
        api_endpoint: str,
        api_base_url: str = "https://ergast.com/api/f1",
        timeout: int = 30,
        retry_attempts: int = 3,
        season: Optional[str] = None,
        round_number: Optional[str] = None,
        output_format: str = "json",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.api_endpoint = api_endpoint
        self.api_base_url = api_base_url
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.season = season
        self.round_number = round_number
        self.output_format = output_format

    def execute(self, context) -> Dict[str, Any]:
        """Execute API data fetch with retry logic."""
        url = self._build_url()

        for attempt in range(self.retry_attempts):
            try:
                self.log.info(f"Fetching data from {url} (attempt {attempt + 1}/{self.retry_attempts})")

                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()

                if self.output_format.lower() == "json":
                    data = response.json()
                else:
                    data = {"content": response.text}

                self.log.info(f"Successfully fetched data from {url}")
                return data

            except requests.RequestException as e:
                self.log.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.retry_attempts - 1:
                    raise AirflowException(f"Failed to fetch data after {self.retry_attempts} attempts: {e}")

        raise AirflowException("Unexpected error in API data fetch")

    def _build_url(self) -> str:
        """Build the complete API URL."""
        url_parts = [self.api_base_url.rstrip("/")]

        if self.season:
            url_parts.append(str(self.season))

        if self.round_number:
            url_parts.append(str(self.round_number))

        url_parts.append(self.api_endpoint.lstrip("/"))

        return "/".join(url_parts)


class DataValidationOperator(BaseOperator):
    """
    Custom operator for validating F1 data quality and completeness.
    """

    template_fields = ["validation_rules", "table_name"]

    @apply_defaults
    def __init__(
        self,
        postgres_conn_id: str = "f1_analytics_postgres",
        validation_rules: Dict[str, Any] = None,
        table_name: Optional[str] = None,
        fail_on_validation_error: bool = True,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.postgres_conn_id = postgres_conn_id
        self.validation_rules = validation_rules or {}
        self.table_name = table_name
        self.fail_on_validation_error = fail_on_validation_error

    def execute(self, context) -> Dict[str, Any]:
        """Execute data validation checks."""
        pg_hook = PostgresHook(postgres_conn_id=self.postgres_conn_id)
        validation_results = {}

        if self.table_name:
            validation_results.update(self._validate_table(pg_hook, self.table_name))

        # Run custom validation rules
        for rule_name, rule_config in self.validation_rules.items():
            try:
                result = self._execute_validation_rule(pg_hook, rule_name, rule_config)
                validation_results[rule_name] = result

                # Check if validation passed
                if rule_config.get("fail_threshold") and result.get("count", 0) > rule_config["fail_threshold"]:
                    error_msg = f"Validation rule '{rule_name}' failed: {result}"
                    if self.fail_on_validation_error:
                        raise AirflowException(error_msg)
                    else:
                        self.log.warning(error_msg)

            except Exception as e:
                error_msg = f"Error executing validation rule '{rule_name}': {e}"
                if self.fail_on_validation_error:
                    raise AirflowException(error_msg)
                else:
                    self.log.error(error_msg)
                    validation_results[rule_name] = {"error": str(e)}

        self.log.info(f"Validation completed: {validation_results}")
        return validation_results

    def _validate_table(self, pg_hook: PostgresHook, table_name: str) -> Dict[str, Any]:
        """Validate basic table properties."""
        results = {}

        # Check if table exists
        exists_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            )
        """
        table_exists = pg_hook.get_first(exists_query, parameters=[table_name])
        results["table_exists"] = table_exists[0] if table_exists else False

        if not results["table_exists"]:
            return results

        # Get row count
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        row_count = pg_hook.get_first(count_query)
        results["row_count"] = row_count[0] if row_count else 0

        # Check for duplicate primary keys (if applicable)
        try:
            # Get primary key columns
            pk_query = """
                SELECT column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY'
            """
            pk_columns = pg_hook.get_records(pk_query, parameters=[table_name])

            if pk_columns:
                pk_column_list = [col[0] for col in pk_columns]
                pk_columns_str = ", ".join(pk_column_list)

                duplicate_query = f"""
                    SELECT COUNT(*) FROM (
                        SELECT {pk_columns_str}, COUNT(*) as cnt
                        FROM {table_name}
                        GROUP BY {pk_columns_str}
                        HAVING COUNT(*) > 1
                    ) duplicates
                """
                duplicate_count = pg_hook.get_first(duplicate_query)
                results["duplicate_primary_keys"] = duplicate_count[0] if duplicate_count else 0

        except Exception as e:
            self.log.warning(f"Could not check for duplicate primary keys in {table_name}: {e}")
            results["duplicate_primary_keys"] = "check_failed"

        return results

    def _execute_validation_rule(self, pg_hook: PostgresHook, rule_name: str, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a custom validation rule."""
        query = rule_config.get("query")
        if not query:
            raise AirflowException(f"Validation rule '{rule_name}' missing required 'query' field")

        result = pg_hook.get_first(query)

        return {
            "rule": rule_name,
            "query": query,
            "count": result[0] if result else 0,
            "passed": True if not rule_config.get("fail_threshold") else (result[0] if result else 0) <= rule_config["fail_threshold"]
        }


class PredictionModelOperator(BaseOperator):
    """
    Custom operator for triggering ML model predictions and updates.
    """

    template_fields = ["model_version", "race_ids"]

    @apply_defaults
    def __init__(
        self,
        postgres_conn_id: str = "f1_analytics_postgres",
        model_api_endpoint: str = "",
        model_version: str = "v1",
        race_ids: Optional[List[int]] = None,
        update_all_upcoming: bool = False,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.postgres_conn_id = postgres_conn_id
        self.model_api_endpoint = model_api_endpoint
        self.model_version = model_version
        self.race_ids = race_ids or []
        self.update_all_upcoming = update_all_upcoming

    def execute(self, context) -> Dict[str, Any]:
        """Execute prediction model updates."""
        pg_hook = PostgresHook(postgres_conn_id=self.postgres_conn_id)

        # Get races to process
        if self.update_all_upcoming:
            races_to_process = self._get_upcoming_races(pg_hook)
        else:
            races_to_process = self.race_ids

        predictions_updated = 0

        for race_id in races_to_process:
            try:
                # Generate predictions for this race
                predictions = self._generate_predictions(pg_hook, race_id)

                # Save predictions to database
                self._save_predictions(pg_hook, race_id, predictions)
                predictions_updated += 1

                self.log.info(f"Updated predictions for race {race_id}")

            except Exception as e:
                self.log.error(f"Failed to update predictions for race {race_id}: {e}")
                continue

        return {
            "predictions_updated": predictions_updated,
            "model_version": self.model_version,
            "races_processed": len(races_to_process)
        }

    def _get_upcoming_races(self, pg_hook: PostgresHook) -> List[int]:
        """Get upcoming race IDs."""
        query = """
            SELECT race_id FROM races
            WHERE race_date >= CURRENT_DATE
            AND status = 'scheduled'
            ORDER BY race_date
            LIMIT 10
        """

        results = pg_hook.get_records(query)
        return [race[0] for race in results]

    def _generate_predictions(self, pg_hook: PostgresHook, race_id: int) -> List[Dict[str, Any]]:
        """
        Generate predictions for a race.
        This is a simplified implementation - in practice, this would call
        your ML model service or load a trained model.
        """
        # Get drivers for the race (simplified - would use actual entry list)
        drivers_query = """
            SELECT d.driver_id, d.driver_name, d.current_elo_rating
            FROM drivers d
            WHERE d.current_elo_rating > 0
            ORDER BY d.current_elo_rating DESC
            LIMIT 20
        """

        drivers = pg_hook.get_records(drivers_query)

        # Simple prediction based on ELO rating
        predictions = []
        total_elo = sum(driver[2] for driver in drivers)

        for driver_id, driver_name, elo_rating in drivers:
            # Simple probability calculation based on ELO
            win_probability = (elo_rating / total_elo) * 100

            predictions.append({
                "driver_id": driver_id,
                "predicted_win_probability": round(win_probability, 2),
                "model_version": self.model_version
            })

        return predictions

    def _save_predictions(self, pg_hook: PostgresHook, race_id: int, predictions: List[Dict[str, Any]]):
        """Save predictions to database."""
        for prediction in predictions:
            # Check if prediction exists
            check_query = """
                SELECT prediction_id FROM predictions
                WHERE race_id = %s AND driver_id = %s AND model_version = %s
            """
            existing = pg_hook.get_first(check_query, parameters=[
                race_id, prediction["driver_id"], prediction["model_version"]
            ])

            if existing:
                # Update existing prediction
                update_query = """
                    UPDATE predictions SET
                        predicted_win_probability = %s,
                        prediction_timestamp = %s
                    WHERE prediction_id = %s
                """
                pg_hook.run(update_query, parameters=[
                    prediction["predicted_win_probability"],
                    datetime.now(timezone.utc),
                    existing[0]
                ])
            else:
                # Insert new prediction
                insert_query = """
                    INSERT INTO predictions (race_id, driver_id, predicted_win_probability, model_version, prediction_timestamp, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                pg_hook.run(insert_query, parameters=[
                    race_id,
                    prediction["driver_id"],
                    prediction["predicted_win_probability"],
                    prediction["model_version"],
                    datetime.now(timezone.utc),
                    datetime.now(timezone.utc)
                ])