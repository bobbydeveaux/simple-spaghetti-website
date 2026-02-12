"""
F1 Analytics Daily Data Ingestion DAG

This DAG orchestrates daily ingestion of Formula 1 data from various sources including:
- Ergast API for race data, driver standings, constructor standings
- Weather data for upcoming races
- ELO rating calculations
- Model predictions refresh

Author: F1 Analytics Team
Schedule: Daily at 6 AM UTC (configurable)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import os

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
from airflow.exceptions import AirflowSkipException
from airflow.hooks.base import BaseHook

import requests
import json
from datetime import timezone


# DAG configuration from environment
DAG_SCHEDULE = os.getenv("F1_DATA_INGESTION_SCHEDULE", "0 6 * * *")  # Daily at 6 AM UTC
DEFAULT_RETRIES = int(os.getenv("F1_DAG_DEFAULT_RETRIES", "3"))
RETRY_DELAY_MINUTES = int(os.getenv("F1_DAG_RETRY_DELAY", "5"))
EMAIL_ON_FAILURE = os.getenv("F1_DAG_EMAIL_ON_FAILURE", "").split(",") if os.getenv("F1_DAG_EMAIL_ON_FAILURE") else []

# API configuration
ERGAST_BASE_URL = os.getenv("F1_ERGAST_BASE_URL", "https://ergast.com/api/f1")
WEATHER_API_KEY = os.getenv("F1_WEATHER_API_KEY")
F1_API_BASE_URL = os.getenv("F1_API_BASE_URL", "http://api-gateway-service:8000/api/v1")

# Database connection
DB_CONN_ID = "f1_analytics_postgres"

logger = logging.getLogger(__name__)


def check_racing_season(**context) -> str:
    """
    Check if we're currently in a racing season.
    Returns task ID to execute next based on season status.
    """
    current_date = datetime.now(timezone.utc).date()
    current_year = current_date.year

    # F1 season typically runs from March to December
    season_start = datetime(current_year, 3, 1).date()
    season_end = datetime(current_year, 12, 31).date()

    if season_start <= current_date <= season_end:
        logger.info(f"In racing season {current_year}, proceeding with full ingestion")
        return "racing_season_tasks"
    else:
        logger.info(f"Outside racing season {current_year}, running limited ingestion")
        return "offseason_tasks"


def get_current_season_data(**context) -> Dict[str, Any]:
    """
    Fetch current F1 season data from Ergast API.
    """
    current_year = datetime.now(timezone.utc).year

    try:
        # Get race calendar for current season
        url = f"{ERGAST_BASE_URL}/{current_year}.json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])

        logger.info(f"Fetched {len(races)} races for {current_year} season")

        # Store in XCom for downstream tasks
        return {
            "season": current_year,
            "races": races,
            "total_races": len(races),
            "fetch_timestamp": datetime.now(timezone.utc).isoformat()
        }

    except requests.RequestException as e:
        logger.error(f"Failed to fetch season data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching season data: {e}")
        raise


def process_race_calendar(**context) -> None:
    """
    Process race calendar data and insert/update races in database.
    """
    # Get season data from XCom
    season_data = context["task_instance"].xcom_pull(task_ids="get_season_data")
    if not season_data:
        raise ValueError("No season data found in XCom")

    races = season_data.get("races", [])
    if not races:
        logger.warning("No races found in season data")
        return

    # Database connection
    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)

    races_processed = 0
    races_updated = 0
    races_inserted = 0

    for race in races:
        try:
            # Extract race data
            season = int(race.get("season"))
            round_number = int(race.get("round"))
            race_name = race.get("raceName")
            race_date = race.get("date")
            circuit = race.get("Circuit", {})
            circuit_name = circuit.get("circuitName")
            location = circuit.get("Location", {})

            # Process circuit first
            circuit_id = process_circuit(pg_hook, circuit, location)

            # Process race
            race_id = process_race(pg_hook, {
                "season": season,
                "round_number": round_number,
                "race_name": race_name,
                "race_date": race_date,
                "circuit_id": circuit_id
            })

            if race_id:
                races_processed += 1
                logger.info(f"Processed race: {race_name} ({season} R{round_number})")

        except Exception as e:
            logger.error(f"Error processing race {race.get('raceName', 'Unknown')}: {e}")
            continue

    logger.info(f"Race calendar processing complete: {races_processed} races processed")


def process_circuit(pg_hook: PostgresHook, circuit: Dict[str, Any], location: Dict[str, Any]) -> Optional[int]:
    """
    Process circuit data and return circuit_id.
    """
    circuit_name = circuit.get("circuitName")
    if not circuit_name:
        logger.warning("Circuit name missing, skipping")
        return None

    location_name = location.get("locality", "")
    country = location.get("country", "")

    # Check if circuit exists
    check_query = "SELECT circuit_id FROM circuits WHERE circuit_name = %s"
    result = pg_hook.get_first(check_query, parameters=[circuit_name])

    if result:
        return result[0]

    # Insert new circuit
    insert_query = """
        INSERT INTO circuits (circuit_name, location, country, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING circuit_id
    """
    result = pg_hook.get_first(
        insert_query,
        parameters=[circuit_name, location_name, country, datetime.now(timezone.utc)]
    )

    if result:
        logger.info(f"Inserted new circuit: {circuit_name}")
        return result[0]

    return None


def process_race(pg_hook: PostgresHook, race_data: Dict[str, Any]) -> Optional[int]:
    """
    Process race data and return race_id.
    """
    # Check if race exists
    check_query = "SELECT race_id FROM races WHERE season_year = %s AND round_number = %s"
    result = pg_hook.get_first(check_query, parameters=[race_data["season"], race_data["round_number"]])

    if result:
        # Update existing race if needed
        update_query = """
            UPDATE races SET
                race_name = %s,
                race_date = %s,
                circuit_id = %s,
                updated_at = %s
            WHERE race_id = %s
        """
        pg_hook.run(update_query, parameters=[
            race_data["race_name"],
            race_data["race_date"],
            race_data["circuit_id"],
            datetime.now(timezone.utc),
            result[0]
        ])
        return result[0]

    # Insert new race
    insert_query = """
        INSERT INTO races (season_year, round_number, race_name, race_date, circuit_id, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING race_id
    """
    result = pg_hook.get_first(insert_query, parameters=[
        race_data["season"],
        race_data["round_number"],
        race_data["race_name"],
        race_data["race_date"],
        race_data["circuit_id"],
        "scheduled",  # Default status
        datetime.now(timezone.utc)
    ])

    if result:
        logger.info(f"Inserted new race: {race_data['race_name']}")
        return result[0]

    return None


def get_completed_races(**context) -> List[Dict[str, Any]]:
    """
    Fetch data for completed races that need results processing.
    """
    current_year = datetime.now(timezone.utc).year

    try:
        # Get race results for completed races
        url = f"{ERGAST_BASE_URL}/{current_year}/results.json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])

        completed_races = []
        for race in races:
            if race.get("Results"):  # Only races with results
                completed_races.append({
                    "season": int(race.get("season")),
                    "round": int(race.get("round")),
                    "race_name": race.get("raceName"),
                    "results": race.get("Results", [])
                })

        logger.info(f"Found {len(completed_races)} completed races with results")
        return completed_races

    except requests.RequestException as e:
        logger.error(f"Failed to fetch race results: {e}")
        raise


def process_race_results(**context) -> None:
    """
    Process race results and insert into database.
    """
    completed_races = context["task_instance"].xcom_pull(task_ids="racing_season_tasks.get_completed_races")
    if not completed_races:
        logger.info("No completed races to process")
        return

    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)
    results_processed = 0

    for race in completed_races:
        try:
            # Get race_id from database
            race_query = "SELECT race_id FROM races WHERE season_year = %s AND round_number = %s"
            race_result = pg_hook.get_first(race_query, parameters=[race["season"], race["round"]])

            if not race_result:
                logger.warning(f"Race not found in database: {race['race_name']} ({race['season']} R{race['round']})")
                continue

            race_id = race_result[0]

            # Process each result
            for result in race["results"]:
                driver_id = process_driver_result(pg_hook, result)
                team_id = process_team_result(pg_hook, result)

                if driver_id and team_id:
                    process_single_result(pg_hook, race_id, driver_id, team_id, result)
                    results_processed += 1

            # Update race status to completed
            update_query = "UPDATE races SET status = 'completed' WHERE race_id = %s"
            pg_hook.run(update_query, parameters=[race_id])

            logger.info(f"Processed results for race: {race['race_name']}")

        except Exception as e:
            logger.error(f"Error processing results for race {race.get('race_name', 'Unknown')}: {e}")
            continue

    logger.info(f"Race results processing complete: {results_processed} results processed")


def process_driver_result(pg_hook: PostgresHook, result: Dict[str, Any]) -> Optional[int]:
    """
    Process driver from race result and return driver_id.
    """
    driver_info = result.get("Driver", {})
    driver_code = driver_info.get("code")
    driver_name = f"{driver_info.get('givenName', '')} {driver_info.get('familyName', '')}".strip()
    nationality = driver_info.get("nationality")
    date_of_birth = driver_info.get("dateOfBirth")

    if not driver_code or not driver_name:
        logger.warning("Driver information missing from result")
        return None

    # Check if driver exists
    check_query = "SELECT driver_id FROM drivers WHERE driver_code = %s"
    result = pg_hook.get_first(check_query, parameters=[driver_code])

    if result:
        return result[0]

    # Insert new driver
    insert_query = """
        INSERT INTO drivers (driver_code, driver_name, nationality, date_of_birth, created_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING driver_id
    """
    result = pg_hook.get_first(insert_query, parameters=[
        driver_code,
        driver_name,
        nationality,
        date_of_birth,
        datetime.now(timezone.utc)
    ])

    if result:
        logger.info(f"Inserted new driver: {driver_name} ({driver_code})")
        return result[0]

    return None


def process_team_result(pg_hook: PostgresHook, result: Dict[str, Any]) -> Optional[int]:
    """
    Process team from race result and return team_id.
    """
    constructor_info = result.get("Constructor", {})
    team_name = constructor_info.get("name")
    nationality = constructor_info.get("nationality")

    if not team_name:
        logger.warning("Team information missing from result")
        return None

    # Check if team exists
    check_query = "SELECT team_id FROM teams WHERE team_name = %s"
    result = pg_hook.get_first(check_query, parameters=[team_name])

    if result:
        return result[0]

    # Insert new team
    insert_query = """
        INSERT INTO teams (team_name, nationality, created_at)
        VALUES (%s, %s, %s)
        RETURNING team_id
    """
    result = pg_hook.get_first(insert_query, parameters=[
        team_name,
        nationality,
        datetime.now(timezone.utc)
    ])

    if result:
        logger.info(f"Inserted new team: {team_name}")
        return result[0]

    return None


def process_single_result(pg_hook: PostgresHook, race_id: int, driver_id: int, team_id: int, result: Dict[str, Any]) -> None:
    """
    Process a single race result entry.
    """
    grid_position = result.get("grid")
    final_position = result.get("position")
    points = result.get("points", "0")
    status = result.get("status", "").lower()
    fastest_lap = result.get("FastestLap", {})
    fastest_lap_time = fastest_lap.get("Time", {}).get("time") if fastest_lap else None

    # Convert position to integer, handle DNS/DNF
    try:
        grid_position = int(grid_position) if grid_position and grid_position.isdigit() else None
        final_position = int(final_position) if final_position and final_position.isdigit() else None
        points = float(points) if points else 0.0
    except (ValueError, TypeError):
        grid_position = None
        final_position = None
        points = 0.0

    # Determine result status
    result_status = "finished"
    if "retired" in status or "dnf" in status:
        result_status = "retired"
    elif "disqualified" in status:
        result_status = "disqualified"

    # Check if result already exists
    check_query = "SELECT result_id FROM race_results WHERE race_id = %s AND driver_id = %s"
    existing_result = pg_hook.get_first(check_query, parameters=[race_id, driver_id])

    if existing_result:
        # Update existing result
        update_query = """
            UPDATE race_results SET
                team_id = %s,
                grid_position = %s,
                final_position = %s,
                points = %s,
                fastest_lap_time = %s,
                status = %s
            WHERE result_id = %s
        """
        pg_hook.run(update_query, parameters=[
            team_id, grid_position, final_position, points, fastest_lap_time, result_status, existing_result[0]
        ])
    else:
        # Insert new result
        insert_query = """
            INSERT INTO race_results (race_id, driver_id, team_id, grid_position, final_position, points, fastest_lap_time, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        pg_hook.run(insert_query, parameters=[
            race_id, driver_id, team_id, grid_position, final_position, points, fastest_lap_time, result_status, datetime.now(timezone.utc)
        ])


def fetch_weather_data(**context) -> None:
    """
    Fetch weather data for upcoming races.
    """
    if not WEATHER_API_KEY:
        logger.warning("Weather API key not configured, skipping weather data fetch")
        return

    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)

    # Get upcoming races (next 2 weeks)
    upcoming_query = """
        SELECT r.race_id, r.race_name, r.race_date, c.location, c.country
        FROM races r
        JOIN circuits c ON r.circuit_id = c.circuit_id
        WHERE r.race_date >= CURRENT_DATE
        AND r.race_date <= CURRENT_DATE + INTERVAL '14 days'
        AND r.status = 'scheduled'
    """
    upcoming_races = pg_hook.get_records(upcoming_query)

    if not upcoming_races:
        logger.info("No upcoming races found for weather data fetch")
        return

    weather_records_processed = 0

    for race in upcoming_races:
        try:
            race_id, race_name, race_date, location, country = race

            # For simplicity, we'll use mock weather data in this implementation
            # In production, you would integrate with a real weather API
            mock_weather_data = {
                "temperature_celsius": 25.0,
                "precipitation_mm": 0.0,
                "wind_speed_kph": 15.0,
                "conditions": "dry"
            }

            # Check if weather data already exists
            check_query = "SELECT weather_id FROM weather_data WHERE race_id = %s"
            existing_weather = pg_hook.get_first(check_query, parameters=[race_id])

            if existing_weather:
                # Update existing weather data
                update_query = """
                    UPDATE weather_data SET
                        temperature_celsius = %s,
                        precipitation_mm = %s,
                        wind_speed_kph = %s,
                        conditions = %s
                    WHERE race_id = %s
                """
                pg_hook.run(update_query, parameters=[
                    mock_weather_data["temperature_celsius"],
                    mock_weather_data["precipitation_mm"],
                    mock_weather_data["wind_speed_kph"],
                    mock_weather_data["conditions"],
                    race_id
                ])
            else:
                # Insert new weather data
                insert_query = """
                    INSERT INTO weather_data (race_id, temperature_celsius, precipitation_mm, wind_speed_kph, conditions, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                pg_hook.run(insert_query, parameters=[
                    race_id,
                    mock_weather_data["temperature_celsius"],
                    mock_weather_data["precipitation_mm"],
                    mock_weather_data["wind_speed_kph"],
                    mock_weather_data["conditions"],
                    datetime.now(timezone.utc)
                ])

            weather_records_processed += 1
            logger.info(f"Processed weather data for race: {race_name}")

        except Exception as e:
            logger.error(f"Error processing weather data for race {race[1]}: {e}")
            continue

    logger.info(f"Weather data processing complete: {weather_records_processed} records processed")


def validate_data_quality(**context) -> None:
    """
    Validate data quality and completeness after ingestion.
    """
    pg_hook = PostgresHook(postgres_conn_id=DB_CONN_ID)
    current_year = datetime.now(timezone.utc).year

    validation_results = {}

    # Check race calendar completeness
    race_count_query = "SELECT COUNT(*) FROM races WHERE season_year = %s"
    race_count = pg_hook.get_first(race_count_query, parameters=[current_year])
    validation_results["races_count"] = race_count[0] if race_count else 0

    # Check completed races have results
    completed_races_query = "SELECT COUNT(*) FROM races WHERE season_year = %s AND status = 'completed'"
    completed_count = pg_hook.get_first(completed_races_query, parameters=[current_year])
    validation_results["completed_races"] = completed_count[0] if completed_count else 0

    # Check race results data
    results_query = """
        SELECT COUNT(*) FROM race_results rr
        JOIN races r ON rr.race_id = r.race_id
        WHERE r.season_year = %s
    """
    results_count = pg_hook.get_first(results_query, parameters=[current_year])
    validation_results["race_results"] = results_count[0] if results_count else 0

    # Check data consistency
    orphaned_results_query = """
        SELECT COUNT(*) FROM race_results rr
        LEFT JOIN races r ON rr.race_id = r.race_id
        WHERE r.race_id IS NULL
    """
    orphaned_count = pg_hook.get_first(orphaned_results_query)
    validation_results["orphaned_results"] = orphaned_count[0] if orphaned_count else 0

    # Log validation results
    logger.info(f"Data quality validation results: {validation_results}")

    # Check for critical issues
    if validation_results["orphaned_results"] > 0:
        logger.warning(f"Found {validation_results['orphaned_results']} orphaned race results!")

    if validation_results["races_count"] == 0:
        logger.error("No races found for current season!")
        raise ValueError("Critical data quality issue: No races found")

    logger.info("Data quality validation completed successfully")


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
    "f1_daily_data_ingestion",
    default_args=default_args,
    description="Daily F1 data ingestion from Ergast API and other sources",
    schedule_interval=DAG_SCHEDULE,
    start_date=days_ago(1),
    catchup=False,
    tags=["f1", "data-ingestion", "daily", "ergast"],
    doc_md=__doc__,
)

# Task definitions
check_season = BranchPythonOperator(
    task_id="check_racing_season",
    python_callable=check_racing_season,
    dag=dag,
)

# Racing season tasks group
with TaskGroup("racing_season_tasks", dag=dag) as racing_season_group:

    get_season_data = PythonOperator(
        task_id="get_season_data",
        python_callable=get_current_season_data,
        dag=dag,
    )

    process_calendar = PythonOperator(
        task_id="process_race_calendar",
        python_callable=process_race_calendar,
        dag=dag,
    )

    get_completed_races = PythonOperator(
        task_id="get_completed_races",
        python_callable=get_completed_races,
        dag=dag,
    )

    process_results = PythonOperator(
        task_id="process_race_results",
        python_callable=process_race_results,
        dag=dag,
    )

    fetch_weather = PythonOperator(
        task_id="fetch_weather_data",
        python_callable=fetch_weather_data,
        dag=dag,
    )

    # Task dependencies within racing season group
    get_season_data >> process_calendar
    get_season_data >> get_completed_races >> process_results
    process_calendar >> fetch_weather

# Offseason tasks group
with TaskGroup("offseason_tasks", dag=dag) as offseason_group:

    offseason_placeholder = DummyOperator(
        task_id="offseason_maintenance",
        dag=dag,
    )

# Final validation and cleanup
validate_data = PythonOperator(
    task_id="validate_data_quality",
    python_callable=validate_data_quality,
    dag=dag,
    trigger_rule="none_failed_or_skipped",  # Run even if some upstream tasks were skipped
)

# DAG structure
check_season >> [racing_season_group, offseason_group] >> validate_data