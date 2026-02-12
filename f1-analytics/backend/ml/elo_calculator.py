"""
ELO Rating Calculator for Formula 1 predictions.

This module implements an ELO rating system for F1 drivers and teams based on race results.
The ELO system provides a dynamic rating that updates based on performance relative to expectations.
"""

import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

from ..app.models.f1_models import RaceResult, Driver, Team, ResultStatus


@dataclass
class ELORatingUpdate:
    """Data class representing an ELO rating update."""
    entity_id: int
    entity_type: str  # "driver" or "team"
    old_rating: int
    new_rating: int
    rating_change: int
    race_id: int
    final_position: Optional[int]
    expected_position: float


class ELOCalculator:
    """
    ELO rating calculator for Formula 1 drivers and teams.

    The ELO system calculates expected performance based on current ratings
    and updates ratings based on actual performance in races.

    Algorithm:
    - Expected score = 1 / (1 + 10^((Rb - Ra) / 400))
    - New rating = Old rating + K * (Actual score - Expected score)

    K-factor: Default 32 (configurable)
    Base rating: 1500 (standard ELO starting point)
    """

    def __init__(self, k_factor: int = 32, base_rating: int = 1500):
        """
        Initialize ELO calculator.

        Args:
            k_factor: K-factor for rating changes (default 32)
            base_rating: Starting rating for new drivers/teams (default 1500)
        """
        self.k_factor = k_factor
        self.base_rating = base_rating

    def calculate_expected_score(self, rating_a: int, rating_b: int) -> float:
        """
        Calculate expected score for entity A against entity B.

        Args:
            rating_a: Current ELO rating of entity A
            rating_b: Current ELO rating of entity B

        Returns:
            Expected score between 0 and 1
        """
        return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / 400.0))

    def calculate_position_score(self, position: int, total_participants: int) -> float:
        """
        Convert race position to a score between 0 and 1.

        Position 1 (winner) = 1.0
        Last position = 0.0
        Linear interpolation for positions in between

        Args:
            position: Final position in race (1-based)
            total_participants: Total number of participants

        Returns:
            Score between 0 and 1
        """
        if position is None or position < 1 or total_participants < 1:
            return 0.0

        if total_participants == 1:
            return 1.0

        # Linear score: (total - position) / (total - 1)
        return (total_participants - position) / (total_participants - 1)

    def calculate_expected_position(self, entity_rating: int, all_ratings: List[int]) -> float:
        """
        Calculate expected position based on ratings.

        Args:
            entity_rating: Rating of the entity
            all_ratings: List of all participant ratings

        Returns:
            Expected position (1-based float)
        """
        if not all_ratings or entity_rating not in all_ratings:
            return len(all_ratings) / 2.0  # Middle position if rating not found

        # Count how many participants are expected to finish ahead
        better_count = 0
        for other_rating in all_ratings:
            if other_rating != entity_rating:
                expected_score = self.calculate_expected_score(entity_rating, other_rating)
                # If expected to lose (score < 0.5), other is expected to finish ahead
                if expected_score < 0.5:
                    better_count += 1

        return better_count + 1  # Position is 1-based

    def get_rating_change(
        self,
        actual_position: Optional[int],
        expected_position: float,
        total_participants: int,
        result_status: ResultStatus
    ) -> int:
        """
        Calculate ELO rating change based on actual vs expected performance.

        Args:
            actual_position: Actual finishing position (None for DNF/Retired)
            expected_position: Expected position based on ratings
            total_participants: Total participants in race
            result_status: Race result status

        Returns:
            Rating change (positive for better than expected, negative for worse)
        """
        # Handle DNF/Retired - treated as worst position with penalty
        if result_status in [ResultStatus.DNF, ResultStatus.RETIRED, ResultStatus.DISQUALIFIED]:
            actual_score = 0.0  # Worst possible score
        elif actual_position is None:
            actual_score = 0.0  # Default to worst score for unknown position
        else:
            actual_score = self.calculate_position_score(actual_position, total_participants)

        expected_score = self.calculate_position_score(int(expected_position), total_participants)

        # Calculate rating change
        rating_change = self.k_factor * (actual_score - expected_score)

        return int(round(rating_change))

    def update_driver_ratings(
        self,
        race_results: List[RaceResult],
        current_ratings: Dict[int, int]
    ) -> Dict[int, ELORatingUpdate]:
        """
        Update driver ELO ratings based on race results.

        Args:
            race_results: List of race results for a single race
            current_ratings: Current ELO ratings for all drivers {driver_id: rating}

        Returns:
            Dictionary of rating updates {driver_id: ELORatingUpdate}
        """
        if not race_results:
            return {}

        # Get race info
        race_id = race_results[0].race_id
        total_participants = len(race_results)

        # Collect all driver ratings for this race
        participant_ratings = []
        driver_results = {}

        for result in race_results:
            driver_id = result.driver_id
            current_rating = current_ratings.get(driver_id, self.base_rating)
            participant_ratings.append(current_rating)
            driver_results[driver_id] = result

        # Calculate rating updates
        updates = {}

        for driver_id, result in driver_results.items():
            old_rating = current_ratings.get(driver_id, self.base_rating)
            expected_position = self.calculate_expected_position(old_rating, participant_ratings)

            rating_change = self.get_rating_change(
                actual_position=result.final_position,
                expected_position=expected_position,
                total_participants=total_participants,
                result_status=result.status
            )

            new_rating = old_rating + rating_change

            # Ensure rating doesn't go below reasonable minimum
            new_rating = max(new_rating, 500)  # Minimum rating floor

            updates[driver_id] = ELORatingUpdate(
                entity_id=driver_id,
                entity_type="driver",
                old_rating=old_rating,
                new_rating=new_rating,
                rating_change=rating_change,
                race_id=race_id,
                final_position=result.final_position,
                expected_position=expected_position
            )

        return updates

    def update_team_ratings(
        self,
        race_results: List[RaceResult],
        current_ratings: Dict[int, int]
    ) -> Dict[int, ELORatingUpdate]:
        """
        Update team ELO ratings based on race results.

        For teams, we aggregate the performance of both drivers.
        Team rating is based on the better-performing driver's result.

        Args:
            race_results: List of race results for a single race
            current_ratings: Current ELO ratings for all teams {team_id: rating}

        Returns:
            Dictionary of rating updates {team_id: ELORatingUpdate}
        """
        if not race_results:
            return {}

        # Group results by team
        team_results = {}
        for result in race_results:
            team_id = result.team_id
            if team_id not in team_results:
                team_results[team_id] = []
            team_results[team_id].append(result)

        # Get race info
        race_id = race_results[0].race_id
        total_teams = len(team_results)

        # Use best result per team for team rating calculation
        team_best_results = {}
        team_participant_ratings = []

        for team_id, results in team_results.items():
            # Find best result (lowest position number, handling DNFs)
            best_result = min(results, key=lambda r: r.final_position if r.final_position else 99)
            team_best_results[team_id] = best_result

            current_rating = current_ratings.get(team_id, self.base_rating)
            team_participant_ratings.append(current_rating)

        # Calculate team position based on best driver result
        sorted_teams = sorted(
            team_best_results.items(),
            key=lambda x: (
                x[1].final_position is None,  # DNFs go to end
                x[1].final_position if x[1].final_position else 99
            )
        )

        # Calculate rating updates
        updates = {}

        for team_position, (team_id, best_result) in enumerate(sorted_teams, 1):
            old_rating = current_ratings.get(team_id, self.base_rating)

            # Calculate expected team position
            expected_position = self.calculate_expected_position(old_rating, team_participant_ratings)

            rating_change = self.get_rating_change(
                actual_position=team_position,
                expected_position=expected_position,
                total_participants=total_teams,
                result_status=best_result.status
            )

            new_rating = old_rating + rating_change

            # Ensure rating doesn't go below reasonable minimum
            new_rating = max(new_rating, 500)  # Minimum rating floor

            updates[team_id] = ELORatingUpdate(
                entity_id=team_id,
                entity_type="team",
                old_rating=old_rating,
                new_rating=new_rating,
                rating_change=rating_change,
                race_id=race_id,
                final_position=team_position,
                expected_position=expected_position
            )

        return updates

    def batch_update_ratings(
        self,
        race_results_list: List[List[RaceResult]],
        initial_driver_ratings: Optional[Dict[int, int]] = None,
        initial_team_ratings: Optional[Dict[int, int]] = None
    ) -> Tuple[Dict[int, int], Dict[int, int], List[Dict[int, ELORatingUpdate]]]:
        """
        Process multiple races in chronological order to update ratings.

        Args:
            race_results_list: List of race results, each containing results for one race
            initial_driver_ratings: Initial driver ratings (defaults to base_rating)
            initial_team_ratings: Initial team ratings (defaults to base_rating)

        Returns:
            Tuple of (final_driver_ratings, final_team_ratings, all_updates)
        """
        # Initialize ratings
        driver_ratings = initial_driver_ratings.copy() if initial_driver_ratings else {}
        team_ratings = initial_team_ratings.copy() if initial_team_ratings else {}

        all_updates = []

        # Process each race in order
        for race_results in race_results_list:
            if not race_results:
                continue

            # Ensure all participants have ratings
            for result in race_results:
                if result.driver_id not in driver_ratings:
                    driver_ratings[result.driver_id] = self.base_rating
                if result.team_id not in team_ratings:
                    team_ratings[result.team_id] = self.base_rating

            # Calculate updates
            driver_updates = self.update_driver_ratings(race_results, driver_ratings)
            team_updates = self.update_team_ratings(race_results, team_ratings)

            # Apply updates
            for driver_id, update in driver_updates.items():
                driver_ratings[driver_id] = update.new_rating

            for team_id, update in team_updates.items():
                team_ratings[team_id] = update.new_rating

            # Store updates
            race_updates = {**driver_updates, **{f"team_{k}": v for k, v in team_updates.items()}}
            all_updates.append(race_updates)

        return driver_ratings, team_ratings, all_updates


def get_elo_calculator(k_factor: int = 32) -> ELOCalculator:
    """
    Factory function to create ELO calculator instance.

    Args:
        k_factor: K-factor for rating calculations

    Returns:
        ELO calculator instance
    """
    return ELOCalculator(k_factor=k_factor)