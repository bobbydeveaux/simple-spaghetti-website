"""
Qualifying data ingestion service for F1 Prediction Analytics.

This module provides functionality to ingest qualifying session results
from the Ergast API, including Q1, Q2, and Q3 lap times and grid positions.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.race import Race
from app.models.qualifying_result import QualifyingResult
from app.models.driver import Driver
from app.models.team import Team
from app.config import settings
from .base import BaseIngestionService, DataValidationError, APIError


logger = logging.getLogger(__name__)


class QualifyingIngestionService(BaseIngestionService):
    """
    Service for ingesting qualifying data from Ergast API.

    This service handles:
    - Qualifying session results (Q1, Q2, Q3)
    - Grid position determination
    - Lap time conversion and validation
    - Driver and team data dependencies
    """

    async def ingest_data(
        self,
        session: Session,
        season: int,
        race_round: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ingest qualifying data for the specified season and round.

        Args:
            session: Database session
            season: F1 season year
            race_round: Optional specific race round (if None, ingests all races)

        Returns:
            dict: Summary of ingestion results
        """
        logger.info(f"Starting qualifying ingestion for season {season}, round {race_round or 'all'}")

        results = {
            'season': season,
            'race_round': race_round,
            'races_processed': 0,
            'qualifying_results_processed': 0,
            'qualifying_results_created': 0,
            'qualifying_results_updated': 0,
            'drivers_created': 0,
            'errors': []
        }

        try:
            # Get races for the specified season/round
            race_filter = Race.season_year == season
            if race_round:
                race_filter = and_(race_filter, Race.round_number == race_round)

            races = session.query(Race).filter(race_filter).all()

            if not races:
                logger.warning(f"No races found for season {season}, round {race_round}")
                return results

            logger.info(f"Processing qualifying data for {len(races)} races")

            for race in races:
                try:
                    await self._process_race_qualifying(session, race, results)
                    results['races_processed'] += 1
                except Exception as e:
                    error_msg = f"Error processing qualifying for race {race.race_id}: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

            logger.info(f"Qualifying ingestion completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Qualifying ingestion failed: {e}")
            results['errors'].append(str(e))
            raise

    async def _process_race_qualifying(
        self,
        session: Session,
        race: Race,
        results: Dict[str, Any]
    ) -> None:
        """Process qualifying results for a specific race."""
        logger.debug(f"Processing qualifying for race: {race.race_name}")

        # Build Ergast API URL for qualifying results
        url = f"{settings.external_apis.ergast_base_url}/{race.season_year}/{race.round_number}/qualifying.json"

        try:
            # Fetch qualifying data
            data = await self._make_api_request(url)
            race_table = self._safe_get(data, 'MRData', 'RaceTable')

            if not race_table or not race_table.get('Races'):
                logger.debug(f"No qualifying data available for race {race.race_id}")
                return

            race_data = race_table['Races'][0]  # Should be only one race
            qualifying_data = race_data.get('QualifyingResults', [])

            if not qualifying_data:
                logger.debug(f"No qualifying entries for race {race.race_id}")
                return

            logger.info(f"Processing {len(qualifying_data)} qualifying results for {race.race_name}")

            for qualifying_entry in qualifying_data:
                try:
                    await self._process_qualifying_entry(session, race, qualifying_entry, results)
                    results['qualifying_results_processed'] += 1
                except Exception as e:
                    error_msg = f"Error processing qualifying entry: {e}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

        except APIError as e:
            if "404" in str(e):
                logger.debug(f"No qualifying data found for {race.race_name} (likely future race)")
            else:
                raise

    async def _process_qualifying_entry(
        self,
        session: Session,
        race: Race,
        qualifying_data: Dict[str, Any],
        results: Dict[str, Any]
    ) -> None:
        """Process a single qualifying result entry."""
        # Validate required fields
        self._validate_required_fields(qualifying_data, ['Driver', 'position'])

        # Get or create driver (using the same method from race ingestion)
        from .race_ingestion import RaceIngestionService
        race_service = RaceIngestionService()
        driver = await race_service._ensure_driver_exists(
            session, qualifying_data['Driver'], results
        )

        # Parse qualifying position
        grid_position = int(qualifying_data['position'])

        # Parse qualifying times
        q1_time = self._parse_qualifying_time(self._safe_get(qualifying_data, 'Q1'))
        q2_time = self._parse_qualifying_time(self._safe_get(qualifying_data, 'Q2'))
        q3_time = self._parse_qualifying_time(self._safe_get(qualifying_data, 'Q3'))

        # Check if qualifying result already exists
        existing_result = session.query(QualifyingResult).filter(
            and_(
                QualifyingResult.race_id == race.race_id,
                QualifyingResult.driver_id == driver.driver_id
            )
        ).first()

        if existing_result:
            # Update existing qualifying result
            updated = False
            if existing_result.q1_time != q1_time:
                existing_result.q1_time = q1_time
                updated = True
            if existing_result.q2_time != q2_time:
                existing_result.q2_time = q2_time
                updated = True
            if existing_result.q3_time != q3_time:
                existing_result.q3_time = q3_time
                updated = True
            if existing_result.final_grid_position != grid_position:
                existing_result.final_grid_position = grid_position
                updated = True

            if updated:
                results['qualifying_results_updated'] += 1
                logger.debug(f"Updated qualifying result: {driver.driver_name} in {race.race_name}")
        else:
            # Create new qualifying result
            new_result = QualifyingResult(
                race_id=race.race_id,
                driver_id=driver.driver_id,
                q1_time=q1_time,
                q2_time=q2_time,
                q3_time=q3_time,
                final_grid_position=grid_position
            )
            session.add(new_result)
            results['qualifying_results_created'] += 1
            logger.debug(f"Created qualifying result: {driver.driver_name} in {race.race_name} - P{grid_position}")

        session.commit()

    def _parse_qualifying_time(self, time_str: Optional[str]) -> Optional[timedelta]:
        """
        Parse qualifying time string to timedelta object.

        Args:
            time_str: Time string in format "1:23.456" or None

        Returns:
            timedelta: Parsed time as timedelta object, or None if parsing fails
        """
        if not time_str:
            return None

        try:
            # Convert time string to seconds
            time_seconds = self._convert_time_string(time_str)
            if time_seconds is not None:
                return timedelta(seconds=time_seconds)
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse qualifying time '{time_str}': {e}")

        return None

    async def ingest_qualifying_for_race(
        self,
        session: Session,
        race: Race
    ) -> Dict[str, Any]:
        """
        Convenience method to ingest qualifying data for a specific race.

        Args:
            session: Database session
            race: Race object to ingest qualifying data for

        Returns:
            dict: Summary of ingestion results
        """
        return await self.ingest_data(
            session=session,
            season=race.season_year,
            race_round=race.round_number
        )

    async def validate_qualifying_data(
        self,
        session: Session,
        season: int,
        race_round: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate qualifying data integrity.

        Args:
            session: Database session
            season: F1 season year
            race_round: Optional specific race round

        Returns:
            dict: Validation results and any issues found
        """
        logger.info(f"Validating qualifying data for season {season}")

        validation_results = {
            'season': season,
            'race_round': race_round,
            'races_validated': 0,
            'issues': [],
            'warnings': []
        }

        # Get races to validate
        race_filter = Race.season_year == season
        if race_round:
            race_filter = and_(race_filter, Race.round_number == race_round)

        races = session.query(Race).filter(race_filter).all()

        for race in races:
            race_issues = []

            # Get qualifying results for this race
            qualifying_results = session.query(QualifyingResult).filter(
                QualifyingResult.race_id == race.race_id
            ).order_by(QualifyingResult.final_grid_position).all()

            if not qualifying_results:
                race_issues.append(f"No qualifying data found")
            else:
                # Check grid position sequence
                expected_positions = list(range(1, len(qualifying_results) + 1))
                actual_positions = [qr.final_grid_position for qr in qualifying_results]

                if actual_positions != expected_positions:
                    race_issues.append(f"Grid positions not sequential: {actual_positions}")

                # Check Q1/Q2/Q3 progression logic
                for qr in qualifying_results:
                    if qr.q1_time is None:
                        race_issues.append(f"Driver {qr.driver_id} missing Q1 time")

                    # Drivers in top 15 should have Q2 times
                    if qr.final_grid_position <= 15 and qr.q2_time is None:
                        validation_results['warnings'].append(
                            f"Driver {qr.driver_id} in P{qr.final_grid_position} missing Q2 time"
                        )

                    # Drivers in top 10 should have Q3 times
                    if qr.final_grid_position <= 10 and qr.q3_time is None:
                        validation_results['warnings'].append(
                            f"Driver {qr.driver_id} in P{qr.final_grid_position} missing Q3 time"
                        )

            if race_issues:
                validation_results['issues'].append({
                    'race_name': race.race_name,
                    'race_id': race.race_id,
                    'issues': race_issues
                })

            validation_results['races_validated'] += 1

        logger.info(f"Qualifying validation completed: {len(validation_results['issues'])} races with issues")
        return validation_results