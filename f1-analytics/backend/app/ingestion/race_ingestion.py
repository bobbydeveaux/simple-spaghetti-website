"""
Race data ingestion service for F1 Prediction Analytics.

This module provides functionality to ingest race data from the Ergast API,
including race schedules, results, and metadata. The service handles both
scheduled and completed races with proper data validation.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.race import Race
from app.models.race_result import RaceResult
from app.models.driver import Driver
from app.models.team import Team
from app.models.circuit import Circuit
from app.config import settings
from .base import BaseIngestionService, DataValidationError, APIError


logger = logging.getLogger(__name__)


class RaceIngestionService(BaseIngestionService):
    """
    Service for ingesting race data from Ergast API.

    This service handles:
    - Race schedule ingestion (upcoming races)
    - Race result ingestion (completed races)
    - Circuit, driver, and team data dependencies
    - Data validation and conflict resolution
    """

    async def ingest_data(
        self,
        session: Session,
        season: int,
        race_round: Optional[int] = None,
        include_results: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ingest race data for the specified season and round.

        Args:
            session: Database session
            season: F1 season year
            race_round: Optional specific race round (if None, ingests all races)
            include_results: Whether to ingest race results for completed races

        Returns:
            dict: Summary of ingestion results
        """
        logger.info(f"Starting race ingestion for season {season}, round {race_round or 'all'}")

        results = {
            'season': season,
            'race_round': race_round,
            'races_processed': 0,
            'races_created': 0,
            'races_updated': 0,
            'results_processed': 0,
            'results_created': 0,
            'circuits_created': 0,
            'drivers_created': 0,
            'teams_created': 0,
            'errors': []
        }

        try:
            # First, ingest race schedule
            await self._ingest_race_schedule(session, season, race_round, results)

            # Then, ingest race results if requested
            if include_results:
                await self._ingest_race_results(session, season, race_round, results)

            logger.info(f"Race ingestion completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Race ingestion failed: {e}")
            results['errors'].append(str(e))
            raise

    async def _ingest_race_schedule(
        self,
        session: Session,
        season: int,
        race_round: Optional[int],
        results: Dict[str, Any]
    ) -> None:
        """Ingest race schedule (calendar) data."""
        logger.info(f"Ingesting race schedule for season {season}")

        # Build Ergast API URL
        if race_round:
            url = f"{settings.external_apis.ergast_base_url}/{season}/{race_round}.json"
        else:
            url = f"{settings.external_apis.ergast_base_url}/{season}.json"

        # Fetch data from Ergast API
        data = await self._make_api_request(url)
        race_table = self._safe_get(data, 'MRData', 'RaceTable')

        if not race_table or not race_table.get('Races'):
            logger.warning(f"No race data found for season {season}, round {race_round}")
            return

        races_data = race_table['Races']
        logger.info(f"Found {len(races_data)} races to process")

        for race_data in races_data:
            try:
                await self._process_race_schedule_entry(session, race_data, results)
                results['races_processed'] += 1
            except Exception as e:
                error_msg = f"Error processing race {race_data.get('round', 'unknown')}: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)

    async def _process_race_schedule_entry(
        self,
        session: Session,
        race_data: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Process a single race schedule entry."""
        # Validate required fields
        self._validate_required_fields(race_data, ['round', 'raceName', 'date', 'Circuit'])

        round_number = int(race_data['round'])
        race_name = race_data['raceName']
        race_date = datetime.strptime(race_data['date'], '%Y-%m-%d').date()
        circuit_data = race_data['Circuit']

        # Ensure circuit exists
        circuit = await self._ensure_circuit_exists(session, circuit_data, results)

        # Check if race already exists
        existing_race = session.query(Race).filter(
            and_(
                Race.season_year == int(race_data.get('season', datetime.now().year)),
                Race.round_number == round_number
            )
        ).first()

        season_year = int(race_data.get('season', datetime.now().year))

        if existing_race:
            # Update existing race
            updated = False
            if existing_race.race_name != race_name:
                existing_race.race_name = race_name
                updated = True
            if existing_race.race_date != race_date:
                existing_race.race_date = race_date
                updated = True
            if existing_race.circuit_id != circuit.circuit_id:
                existing_race.circuit_id = circuit.circuit_id
                updated = True

            if updated:
                existing_race.updated_at = datetime.utcnow()
                results['races_updated'] += 1
                logger.debug(f"Updated race: {race_name} (Round {round_number})")
        else:
            # Create new race
            new_race = Race(
                season_year=season_year,
                round_number=round_number,
                circuit_id=circuit.circuit_id,
                race_date=race_date,
                race_name=race_name,
                status='scheduled'
            )
            session.add(new_race)
            results['races_created'] += 1
            logger.debug(f"Created race: {race_name} (Round {round_number})")

        session.commit()

    async def _ingest_race_results(
        self,
        session: Session,
        season: int,
        race_round: Optional[int],
        results: Dict[str, Any]
    ) -> None:
        """Ingest race results for completed races."""
        logger.info(f"Ingesting race results for season {season}")

        # Get races that need results
        race_filter = Race.season_year == season
        if race_round:
            race_filter = and_(race_filter, Race.round_number == race_round)

        races = session.query(Race).filter(race_filter).all()

        for race in races:
            # Only try to get results for past races
            if race.race_date <= date.today():
                try:
                    await self._process_race_results(session, race, results)
                except Exception as e:
                    error_msg = f"Error processing results for race {race.race_id}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

    async def _process_race_results(
        self,
        session: Session,
        race: Race,
        results: Dict[str, Any]
    ) -> None:
        """Process race results for a specific race."""
        logger.debug(f"Processing results for race: {race.race_name}")

        # Build Ergast API URL for results
        url = f"{settings.external_apis.ergast_base_url}/{race.season_year}/{race.round_number}/results.json"

        # Fetch race results
        data = await self._make_api_request(url)
        race_table = self._safe_get(data, 'MRData', 'RaceTable')

        if not race_table or not race_table.get('Races'):
            logger.debug(f"No results available for race {race.race_id}")
            return

        race_data = race_table['Races'][0]  # Should be only one race
        race_results_data = race_data.get('Results', [])

        if not race_results_data:
            logger.debug(f"No result entries for race {race.race_id}")
            return

        logger.info(f"Processing {len(race_results_data)} results for {race.race_name}")

        for result_data in race_results_data:
            try:
                await self._process_race_result_entry(session, race, result_data, results)
                results['results_processed'] += 1
            except Exception as e:
                error_msg = f"Error processing result entry: {e}"
                logger.error(error_msg)
                results['errors'].append(error_msg)

        # Update race status to completed if we have results
        if race_results_data:
            race.status = 'completed'
            race.updated_at = datetime.utcnow()
            session.commit()

    async def _process_race_result_entry(
        self,
        session: Session,
        race: Race,
        result_data: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Process a single race result entry."""
        # Validate required fields
        self._validate_required_fields(result_data, ['Driver', 'Constructor', 'grid'])

        # Get or create driver and team
        driver = await self._ensure_driver_exists(session, result_data['Driver'], results)
        team = await self._ensure_team_exists(session, result_data['Constructor'], results)

        # Parse result data
        grid_position = int(result_data['grid']) if result_data['grid'] != '0' else None
        final_position = self._safe_get(result_data, 'position')
        final_position = int(final_position) if final_position else None

        points = self._safe_get(result_data, 'points', '0')
        points = float(points) if points else 0.0

        # Parse fastest lap
        fastest_lap_time = None
        fastest_lap_data = self._safe_get(result_data, 'FastestLap', 'Time', 'time')
        if fastest_lap_data:
            fastest_lap_seconds = self._convert_time_string(fastest_lap_data)
            if fastest_lap_seconds:
                from datetime import timedelta
                fastest_lap_time = timedelta(seconds=fastest_lap_seconds)

        # Determine race status
        status = self._safe_get(result_data, 'status', 'finished')
        if final_position:
            status = 'finished'
        elif 'Lap' in status.lower():
            status = 'finished'  # Finished but lapped
        elif any(term in status.lower() for term in ['retired', 'engine', 'accident', 'collision']):
            status = 'retired'
        elif 'disqualified' in status.lower():
            status = 'disqualified'
        else:
            status = 'dnf'

        # Check if result already exists
        existing_result = session.query(RaceResult).filter(
            and_(
                RaceResult.race_id == race.race_id,
                RaceResult.driver_id == driver.driver_id
            )
        ).first()

        if existing_result:
            # Update existing result
            existing_result.grid_position = grid_position
            existing_result.final_position = final_position
            existing_result.points = points
            existing_result.fastest_lap_time = fastest_lap_time
            existing_result.status = status
            existing_result.team_id = team.team_id
            logger.debug(f"Updated race result: {driver.driver_name} in {race.race_name}")
        else:
            # Create new result
            new_result = RaceResult(
                race_id=race.race_id,
                driver_id=driver.driver_id,
                team_id=team.team_id,
                grid_position=grid_position,
                final_position=final_position,
                points=points,
                fastest_lap_time=fastest_lap_time,
                status=status
            )
            session.add(new_result)
            results['results_created'] += 1
            logger.debug(f"Created race result: {driver.driver_name} in {race.race_name}")

        session.commit()

    async def _ensure_circuit_exists(
        self,
        session: Session,
        circuit_data: Dict[str, Any],
        results: Dict[str, Any]
    ) -> Circuit:
        """Ensure circuit exists in database, create if necessary."""
        self._validate_required_fields(circuit_data, ['circuitId', 'circuitName', 'Location'])

        circuit_id_external = circuit_data['circuitId']
        circuit_name = circuit_data['circuitName']
        location_data = circuit_data['Location']

        location = self._safe_get(location_data, 'locality', 'Unknown')
        country = self._safe_get(location_data, 'country', 'Unknown')

        # Look for existing circuit by name (Ergast IDs can change)
        existing_circuit = session.query(Circuit).filter(
            Circuit.circuit_name == circuit_name
        ).first()

        if existing_circuit:
            return existing_circuit

        # Create new circuit
        new_circuit = Circuit(
            circuit_name=circuit_name,
            location=location,
            country=country,
            track_type='permanent'  # Default, can be updated manually
        )
        session.add(new_circuit)
        session.commit()
        session.refresh(new_circuit)

        results['circuits_created'] += 1
        logger.debug(f"Created circuit: {circuit_name}")

        return new_circuit

    async def _ensure_driver_exists(
        self,
        session: Session,
        driver_data: Dict[str, Any],
        results: Dict[str, Any]
    ) -> Driver:
        """Ensure driver exists in database, create if necessary."""
        self._validate_required_fields(driver_data, ['driverId', 'familyName'])

        driver_id_external = driver_data['driverId']
        family_name = driver_data['familyName']
        given_name = self._safe_get(driver_data, 'givenName', '')
        driver_name = f"{given_name} {family_name}".strip()

        # Generate driver code (3 letters, usually last name + first letters of first name)
        driver_code = self._safe_get(driver_data, 'code')
        if not driver_code:
            # Generate a simple code if not provided
            if given_name:
                driver_code = (family_name[:2] + given_name[0]).upper()[:3]
            else:
                driver_code = family_name[:3].upper()

        # Look for existing driver by name or code
        existing_driver = session.query(Driver).filter(
            (Driver.driver_name == driver_name) | (Driver.driver_code == driver_code)
        ).first()

        if existing_driver:
            return existing_driver

        # Parse date of birth
        dob = None
        dob_str = self._safe_get(driver_data, 'dateOfBirth')
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"Invalid date format for driver {driver_name}: {dob_str}")

        # Create new driver
        new_driver = Driver(
            driver_code=driver_code,
            driver_name=driver_name,
            nationality=self._safe_get(driver_data, 'nationality'),
            date_of_birth=dob,
            current_elo_rating=1500  # Default ELO rating
        )
        session.add(new_driver)
        session.commit()
        session.refresh(new_driver)

        results['drivers_created'] += 1
        logger.debug(f"Created driver: {driver_name} ({driver_code})")

        return new_driver

    async def _ensure_team_exists(
        self,
        session: Session,
        team_data: Dict[str, Any],
        results: Dict[str, Any]
    ) -> Team:
        """Ensure team exists in database, create if necessary."""
        self._validate_required_fields(team_data, ['constructorId', 'name'])

        team_id_external = team_data['constructorId']
        team_name = team_data['name']

        # Look for existing team by name
        existing_team = session.query(Team).filter(Team.team_name == team_name).first()

        if existing_team:
            return existing_team

        # Create new team
        new_team = Team(
            team_name=team_name,
            nationality=self._safe_get(team_data, 'nationality'),
            current_elo_rating=1500  # Default ELO rating
        )
        session.add(new_team)
        session.commit()
        session.refresh(new_team)

        results['teams_created'] += 1
        logger.debug(f"Created team: {team_name}")

        return new_team