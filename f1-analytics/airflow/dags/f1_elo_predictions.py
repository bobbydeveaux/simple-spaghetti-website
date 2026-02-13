"""
F1 Analytics ELO Rating and Prediction Update DAG

This DAG handles:
- ELO rating calculations after race completions
- ML model prediction updates for upcoming races
- Prediction accuracy evaluation for completed races

Author: F1 Analytics Team
Schedule: Every 6 hours (configurable)
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import logging
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup

# Import custom operators
import sys
sys.path.append('/opt/airflow/plugins')
from f1_operators import EloRatingOperator, PredictionModelOperator, DataValidationOperator

# DAG configuration from environment
DAG_SCHEDULE = os.getenv("ELO_UPDATE_SCHEDULE", "0 */6 * * *")  # Every 6 hours
PREDICTION_SCHEDULE = os.getenv("PREDICTION_REFRESH_SCHEDULE", "0 */2 * * *")  # Every 2 hours
DEFAULT_RETRIES = int(os.getenv("F1_DAG_DEFAULT_RETRIES", "2"))
RETRY_DELAY_MINUTES = int(os.getenv("F1_DAG_RETRY_DELAY", "10"))
EMAIL_ON_FAILURE = os.getenv("F1_DAG_EMAIL_ON_FAILURE", "").split(",") if os.getenv("F1_DAG_EMAIL_ON_FAILURE") else []

# Database connection
DB_CONN_ID = "f1_analytics_postgres"

logger = logging.getLogger(__name__)


def check_completed_races(**context) -> Dict[str, Any]:
    """
    Check for races completed since last ELO update.
    """
    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)

    # Get completed races without recent ELO updates
    # We'll check for races completed in the last 7 days
    query = """
        SELECT r.race_id, r.race_name, r.race_date, r.season_year
        FROM races r
        WHERE r.status = 'completed'
        AND r.race_date >= CURRENT_DATE - INTERVAL '7 days'
        AND EXISTS (
            SELECT 1 FROM race_results rr
            WHERE rr.race_id = r.race_id
            AND rr.final_position IS NOT NULL
        )
        ORDER BY r.race_date DESC
    """

    completed_races = pg_hook.get_records(query)

    race_data = []
    for race in completed_races:
        race_data.append({
            "race_id": race[0],
            "race_name": race[1],
            "race_date": race[2].isoformat() if race[2] else None,
            "season_year": race[3]
        })

    logger.info(f"Found {len(race_data)} completed races for ELO processing")

    return {
        "completed_races": race_data,
        "count": len(race_data),
        "check_timestamp": datetime.now().isoformat()
    }


def get_upcoming_races(**context) -> Dict[str, Any]:
    """
    Get upcoming races that need prediction updates.
    """
    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)

    # Get upcoming races in the next 30 days
    query = """
        SELECT r.race_id, r.race_name, r.race_date, r.season_year, c.circuit_name
        FROM races r
        JOIN circuits c ON r.circuit_id = c.circuit_id
        WHERE r.status = 'scheduled'
        AND r.race_date >= CURRENT_DATE
        AND r.race_date <= CURRENT_DATE + INTERVAL '30 days'
        ORDER BY r.race_date ASC
    """

    upcoming_races = pg_hook.get_records(query)

    race_data = []
    for race in upcoming_races:
        race_data.append({
            "race_id": race[0],
            "race_name": race[1],
            "race_date": race[2].isoformat() if race[2] else None,
            "season_year": race[3],
            "circuit_name": race[4]
        })

    logger.info(f"Found {len(race_data)} upcoming races for prediction updates")

    return {
        "upcoming_races": race_data,
        "count": len(race_data),
        "check_timestamp": datetime.now().isoformat()
    }


def evaluate_prediction_accuracy(**context) -> Dict[str, Any]:
    """
    Evaluate prediction accuracy for recently completed races.
    """
    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)

    # Get completed races from the last 30 days that have predictions
    query = """
        SELECT DISTINCT r.race_id, r.race_name, r.race_date
        FROM races r
        JOIN predictions p ON r.race_id = p.race_id
        JOIN race_results rr ON r.race_id = rr.race_id
        WHERE r.status = 'completed'
        AND r.race_date >= CURRENT_DATE - INTERVAL '30 days'
        AND NOT EXISTS (
            SELECT 1 FROM prediction_accuracy pa
            WHERE pa.race_id = r.race_id
        )
        ORDER BY r.race_date DESC
    """

    races_to_evaluate = pg_hook.get_records(query)

    if not races_to_evaluate:
        logger.info("No races need prediction accuracy evaluation")
        return {"races_evaluated": 0, "evaluations": []}

    evaluations = []

    for race in races_to_evaluate:
        race_id, race_name, race_date = race

        try:
            # Calculate accuracy metrics for this race
            accuracy_metrics = calculate_race_prediction_accuracy(pg_hook, race_id)

            # Insert accuracy record
            insert_query = """
                INSERT INTO prediction_accuracy (
                    race_id, brier_score, log_loss, correct_winner, top_3_accuracy, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """

            pg_hook.run(insert_query, parameters=[
                race_id,
                accuracy_metrics.get("brier_score"),
                accuracy_metrics.get("log_loss"),
                accuracy_metrics.get("correct_winner"),
                accuracy_metrics.get("top_3_accuracy"),
                datetime.now()
            ])

            evaluations.append({
                "race_id": race_id,
                "race_name": race_name,
                "accuracy_metrics": accuracy_metrics
            })

            logger.info(f"Evaluated prediction accuracy for race: {race_name}")

        except Exception as e:
            logger.error(f"Error evaluating accuracy for race {race_name}: {e}")
            continue

    return {
        "races_evaluated": len(evaluations),
        "evaluations": evaluations
    }


def calculate_race_prediction_accuracy(pg_hook: PostgresHook, race_id: int) -> Dict[str, Any]:
    """
    Calculate prediction accuracy metrics for a completed race.
    """
    # Get predictions and actual results
    query = """
        SELECT p.driver_id, p.predicted_win_probability, rr.final_position
        FROM predictions p
        JOIN race_results rr ON p.race_id = rr.race_id AND p.driver_id = rr.driver_id
        WHERE p.race_id = %s
        AND rr.final_position IS NOT NULL
        AND rr.status = 'finished'
        ORDER BY rr.final_position
    """

    results = pg_hook.get_records(query, parameters=[race_id])

    if not results:
        raise ValueError(f"No prediction/result data found for race {race_id}")

    # Calculate metrics
    predictions = []
    actual_results = []
    winner_predicted_correctly = False
    top_3_drivers = []

    for i, (driver_id, pred_prob, final_pos) in enumerate(results):
        # Convert probability to 0-1 range
        prob = float(pred_prob) / 100.0
        predictions.append(prob)

        # Actual outcome (1 if won, 0 if not)
        actual = 1.0 if final_pos == 1 else 0.0
        actual_results.append(actual)

        # Check winner prediction
        if final_pos == 1 and i == 0:  # If winner had highest predicted probability
            winner_predicted_correctly = True

        # Track top 3 finishers
        if final_pos <= 3:
            top_3_drivers.append(i)  # Index in the sorted predictions list

    # Calculate Brier Score
    brier_score = sum((p - a) ** 2 for p, a in zip(predictions, actual_results)) / len(predictions)

    # Calculate Log Loss
    log_loss = 0
    for p, a in zip(predictions, actual_results):
        # Clip probabilities to avoid log(0)
        p_clipped = max(min(p, 0.9999), 0.0001)
        log_loss -= a * math.log(p_clipped) + (1 - a) * math.log(1 - p_clipped)
    log_loss /= len(predictions)

    # Check top 3 accuracy
    # Sort drivers by predicted probability (descending)
    driver_prob_pairs = [(i, predictions[i]) for i in range(len(predictions))]
    driver_prob_pairs.sort(key=lambda x: x[1], reverse=True)

    predicted_top_3 = [pair[0] for pair in driver_prob_pairs[:3]]
    top_3_accuracy = len(set(predicted_top_3) & set(top_3_drivers)) >= 2  # At least 2 out of 3 correct

    return {
        "brier_score": round(brier_score, 4),
        "log_loss": round(log_loss, 4),
        "correct_winner": winner_predicted_correctly,
        "top_3_accuracy": top_3_accuracy
    }


def cleanup_old_predictions(**context) -> Dict[str, Any]:
    """
    Clean up old prediction data to prevent database bloat.
    """
    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)

    # Delete predictions for races older than 1 year
    cleanup_query = """
        DELETE FROM predictions
        WHERE race_id IN (
            SELECT race_id FROM races
            WHERE race_date < CURRENT_DATE - INTERVAL '1 year'
        )
    """

    deleted_count = pg_hook.run(cleanup_query)

    logger.info(f"Cleaned up old predictions, deleted records: {deleted_count}")

    return {
        "deleted_predictions": deleted_count,
        "cleanup_timestamp": datetime.now().isoformat()
    }


# DAG Definition
default_args = {
    "owner": "f1-analytics",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": bool(EMAIL_ON_FAILURE),
    "email_on_retry": False,
    "email": EMAIL_ON_FAILURE,
    "retries": DEFAULT_RETRIES,
    "retry_delay": timedelta(minutes=RETRY_DELAY_MINUTES),
    "max_active_runs": 1,
}

dag = DAG(
    "f1_elo_and_predictions",
    default_args=default_args,
    description="F1 ELO rating updates and prediction model refresh",
    schedule_interval=DAG_SCHEDULE,
    start_date=days_ago(1),
    catchup=False,
    tags=["f1", "elo", "predictions", "ml"],
    doc_md=__doc__,
)

# Task definitions

# Check for data to process
check_completed = PythonOperator(
    task_id="check_completed_races",
    python_callable=check_completed_races,
    dag=dag,
)

check_upcoming = PythonOperator(
    task_id="check_upcoming_races",
    python_callable=get_upcoming_races,
    dag=dag,
)

# ELO Rating Tasks
with TaskGroup("elo_processing", dag=dag) as elo_group:

    update_elo_ratings = EloRatingOperator(
        task_id="update_elo_ratings",
        postgres_conn_id=DB_CONN_ID,
        process_all_recent=True,
        k_factor=32,
        dag=dag,
    )

    validate_elo_updates = DataValidationOperator(
        task_id="validate_elo_updates",
        postgres_conn_id=DB_CONN_ID,
        validation_rules={
            "negative_elo_check": {
                "query": "SELECT COUNT(*) FROM drivers WHERE current_elo_rating < 1000",
                "fail_threshold": 0
            },
            "extreme_elo_check": {
                "query": "SELECT COUNT(*) FROM drivers WHERE current_elo_rating > 3000",
                "fail_threshold": 5  # Allow up to 5 drivers with very high ELO
            }
        },
        fail_on_validation_error=False,
        dag=dag,
    )

    update_elo_ratings >> validate_elo_updates

# Prediction Tasks
with TaskGroup("prediction_processing", dag=dag) as prediction_group:

    update_predictions = PredictionModelOperator(
        task_id="update_predictions",
        postgres_conn_id=DB_CONN_ID,
        model_version="v1",
        update_all_upcoming=True,
        dag=dag,
    )

    validate_predictions = DataValidationOperator(
        task_id="validate_predictions",
        postgres_conn_id=DB_CONN_ID,
        validation_rules={
            "prediction_probability_range": {
                "query": "SELECT COUNT(*) FROM predictions WHERE predicted_win_probability < 0 OR predicted_win_probability > 100",
                "fail_threshold": 0
            },
            "recent_predictions_exist": {
                "query": """
                    SELECT COUNT(*) FROM predictions p
                    JOIN races r ON p.race_id = r.race_id
                    WHERE r.race_date >= CURRENT_DATE
                    AND p.prediction_timestamp >= CURRENT_DATE - INTERVAL '1 day'
                """,
                "fail_threshold": None  # Just log the count
            }
        },
        fail_on_validation_error=False,
        dag=dag,
    )

    update_predictions >> validate_predictions

# Accuracy Evaluation
evaluate_accuracy = PythonOperator(
    task_id="evaluate_prediction_accuracy",
    python_callable=evaluate_prediction_accuracy,
    dag=dag,
)

# Cleanup Tasks
cleanup_task = PythonOperator(
    task_id="cleanup_old_predictions",
    python_callable=cleanup_old_predictions,
    dag=dag,
)

# Final summary
summary_task = DummyOperator(
    task_id="processing_complete",
    dag=dag,
    trigger_rule="none_failed_or_skipped",
)

# DAG structure
[check_completed, check_upcoming] >> elo_group
check_upcoming >> prediction_group
[elo_group, prediction_group] >> evaluate_accuracy >> cleanup_task >> summary_task

# Import math for log calculations
import math