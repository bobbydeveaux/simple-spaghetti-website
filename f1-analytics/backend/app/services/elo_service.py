"""
ELO Rating Service for F1 analytics.

This service provides high-level functions to calculate and update ELO ratings
for drivers and teams based on race results.
"""

import math
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc

from ..models.f1_models import Driver, Team, RaceResult, Race, RaceStatus
from ..database import get_db
from ...ml.elo_calculator import ELOCalculator, ELORatingUpdate


class ELOService:
    """Service for managing ELO ratings calculation and persistence."""

    def __init__(self, db: Session, k_factor: int = 32):
        """
        Initialize ELO service.

        Args:
            db: Database session
            k_factor: K-factor for ELO calculations
        """
        self.db = db
        self.calculator = ELOCalculator(k_factor=k_factor)

    def get_current_driver_ratings(self) -> Dict[int, int]:
        """
        Get current ELO ratings for all drivers.

        Returns:
            Dictionary mapping driver_id to current ELO rating
        """
        drivers = self.db.query(Driver).all()
        return {driver.driver_id: driver.current_elo_rating for driver in drivers}

    def get_current_team_ratings(self) -> Dict[int, int]:
        """
        Get current ELO ratings for all teams.

        Returns:
            Dictionary mapping team_id to current ELO rating
        """
        teams = self.db.query(Team).all()
        return {team.team_id: team.current_elo_rating for team in teams}

    def get_race_results_for_race(self, race_id: int) -> List[RaceResult]:
        """
        Get all race results for a specific race.

        Args:
            race_id: ID of the race

        Returns:
            List of race results ordered by final position
        """
        return (
            self.db.query(RaceResult)
            .filter(RaceResult.race_id == race_id)
            .order_by(
                RaceResult.final_position.asc().nulls_last(),
                RaceResult.driver_id
            )
            .all()
        )

    def get_completed_races_chronologically(
        self,
        season_year: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Race]:
        """
        Get completed races in chronological order.

        Args:
            season_year: Filter by specific season (optional)
            limit: Maximum number of races to return (optional)

        Returns:
            List of completed races in chronological order
        """
        query = (
            self.db.query(Race)
            .filter(Race.status == RaceStatus.COMPLETED)
            .order_by(asc(Race.race_date), asc(Race.round_number))
        )

        if season_year:
            query = query.filter(Race.season_year == season_year)

        if limit:
            query = query.limit(limit)

        return query.all()

    def update_ratings_for_race(self, race_id: int) -> Tuple[Dict[int, ELORatingUpdate], Dict[int, ELORatingUpdate]]:
        """
        Calculate and apply ELO rating updates for a single race.

        Args:
            race_id: ID of the race to process

        Returns:
            Tuple of (driver_updates, team_updates)
        """
        # Get race results
        race_results = self.get_race_results_for_race(race_id)
        if not race_results:
            return {}, {}

        # Get current ratings
        driver_ratings = self.get_current_driver_ratings()
        team_ratings = self.get_current_team_ratings()

        # Calculate updates
        driver_updates = self.calculator.update_driver_ratings(race_results, driver_ratings)
        team_updates = self.calculator.update_team_ratings(race_results, team_ratings)

        # Apply updates to database
        self._apply_driver_updates(driver_updates)
        self._apply_team_updates(team_updates)

        return driver_updates, team_updates

    def _apply_driver_updates(self, updates: Dict[int, ELORatingUpdate]) -> None:
        """Apply driver rating updates to database."""
        for driver_id, update in updates.items():
            driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
            if driver:
                driver.current_elo_rating = update.new_rating

    def _apply_team_updates(self, updates: Dict[int, ELORatingUpdate]) -> None:
        """Apply team rating updates to database."""
        for team_id, update in updates.items():
            team = self.db.query(Team).filter(Team.team_id == team_id).first()
            if team:
                team.current_elo_rating = update.new_rating

    def recalculate_all_ratings(
        self,
        season_year: Optional[int] = None,
        reset_to_base: bool = True
    ) -> Tuple[Dict[int, int], Dict[int, int]]:
        """
        Recalculate all ELO ratings from scratch.

        Args:
            season_year: Process only specific season (None for all)
            reset_to_base: Whether to reset all ratings to base rating first

        Returns:
            Tuple of (final_driver_ratings, final_team_ratings)
        """
        # Reset all ratings to base if requested
        if reset_to_base:
            self._reset_all_ratings_to_base()

        # Get initial ratings
        initial_driver_ratings = self.get_current_driver_ratings()
        initial_team_ratings = self.get_current_team_ratings()

        # Get all completed races in order
        completed_races = self.get_completed_races_chronologically(season_year)

        # Collect race results for batch processing
        all_race_results = []
        for race in completed_races:
            race_results = self.get_race_results_for_race(race.race_id)
            if race_results:
                all_race_results.append(race_results)

        # Batch process all races
        final_driver_ratings, final_team_ratings, all_updates = self.calculator.batch_update_ratings(
            all_race_results,
            initial_driver_ratings,
            initial_team_ratings
        )

        # Apply final ratings to database
        self._apply_final_ratings(final_driver_ratings, final_team_ratings)

        return final_driver_ratings, final_team_ratings

    def _reset_all_ratings_to_base(self) -> None:
        """Reset all driver and team ratings to base rating."""
        # Reset driver ratings
        self.db.query(Driver).update(
            {Driver.current_elo_rating: self.calculator.base_rating}
        )

        # Reset team ratings
        self.db.query(Team).update(
            {Team.current_elo_rating: self.calculator.base_rating}
        )

    def _apply_final_ratings(
        self,
        driver_ratings: Dict[int, int],
        team_ratings: Dict[int, int]
    ) -> None:
        """Apply final calculated ratings to database."""
        # Update driver ratings
        for driver_id, rating in driver_ratings.items():
            driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
            if driver:
                driver.current_elo_rating = rating

        # Update team ratings
        for team_id, rating in team_ratings.items():
            team = self.db.query(Team).filter(Team.team_id == team_id).first()
            if team:
                team.current_elo_rating = rating

    def get_driver_rankings(self, limit: int = 20) -> List[Driver]:
        """
        Get drivers ranked by ELO rating.

        Args:
            limit: Maximum number of drivers to return

        Returns:
            List of drivers ordered by ELO rating (descending)
        """
        return (
            self.db.query(Driver)
            .order_by(desc(Driver.current_elo_rating))
            .limit(limit)
            .all()
        )

    def get_team_rankings(self, limit: int = 10) -> List[Team]:
        """
        Get teams ranked by ELO rating.

        Args:
            limit: Maximum number of teams to return

        Returns:
            List of teams ordered by ELO rating (descending)
        """
        return (
            self.db.query(Team)
            .order_by(desc(Team.current_elo_rating))
            .limit(limit)
            .all()
        )

    def get_driver_rating_history(self, driver_id: int, limit: int = 20) -> List[Dict]:
        """
        Get rating history for a specific driver.

        Note: This is a placeholder for future implementation.
        Would require a separate rating_history table to track changes over time.

        Args:
            driver_id: Driver ID
            limit: Maximum number of historical entries

        Returns:
            List of rating history entries (placeholder implementation)
        """
        # TODO: Implement rating history tracking
        driver = self.db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if driver:
            return [{
                "driver_id": driver.driver_id,
                "current_rating": driver.current_elo_rating,
                "note": "Historical tracking not yet implemented"
            }]
        return []

    def predict_race_outcome(
        self,
        race_id: int,
        participating_driver_ids: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Predict race outcome based on current ELO ratings.

        Args:
            race_id: Race ID for prediction
            participating_driver_ids: List of participating driver IDs (optional)

        Returns:
            List of drivers with win probabilities ordered by rating
        """
        if participating_driver_ids:
            drivers = (
                self.db.query(Driver)
                .filter(Driver.driver_id.in_(participating_driver_ids))
                .all()
            )
        else:
            # Get all drivers (fallback)
            drivers = self.db.query(Driver).all()

        if not drivers:
            return []

        # Sort by ELO rating (descending)
        drivers.sort(key=lambda d: d.current_elo_rating, reverse=True)

        # Calculate simple probability based on rating differences
        total_rating_weight = sum(
            math.exp(driver.current_elo_rating / 400.0) for driver in drivers
        )

        predictions = []
        for driver in drivers:
            rating_weight = math.exp(driver.current_elo_rating / 400.0)
            win_probability = (rating_weight / total_rating_weight) * 100

            predictions.append({
                "driver_id": driver.driver_id,
                "driver_name": driver.driver_name,
                "current_elo_rating": driver.current_elo_rating,
                "win_probability": round(win_probability, 2)
            })

        return predictions


def get_elo_service(db: Session, k_factor: int = 32) -> ELOService:
    """
    Factory function to create ELO service instance.

    Args:
        db: Database session
        k_factor: K-factor for ELO calculations

    Returns:
        ELO service instance
    """
    return ELOService(db, k_factor)