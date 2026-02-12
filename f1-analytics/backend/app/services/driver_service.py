"""
Driver service for data transformation and business logic.

This module handles all driver-related operations including CRUD,
statistics calculation, and ranking management.
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from ..models.f1_models import Driver, Team, RaceResult
from ..schemas.driver import (
    DriverCreate, DriverUpdate, DriverResponse, DriverBasic,
    DriverRanking, DriverStatistics
)
from .base import BaseService, DataValidator, DataTransformer


class DriverService(BaseService[Driver, DriverCreate, DriverUpdate, DriverResponse]):
    """Service for driver data operations and transformations."""

    def __init__(self):
        super().__init__(
            model=Driver,
            create_schema=DriverCreate,
            update_schema=DriverUpdate,
            response_schema=DriverResponse
        )

    def create_driver(
        self,
        db: Session,
        driver_data: DriverCreate
    ) -> DriverResponse:
        """Create a new driver with validation and transformation."""
        # Validate driver code uniqueness
        existing_driver = db.query(Driver).filter(
            Driver.driver_code == driver_data.driver_code.upper()
        ).first()

        if existing_driver:
            from .base import ValidationError
            raise ValidationError(
                f"Driver code {driver_data.driver_code} already exists",
                "driver_code",
                driver_data.driver_code
            )

        # Transform data
        normalized_name = DataTransformer.normalize_driver_name(driver_data.driver_name)
        validated_code = DataValidator.validate_driver_code(driver_data.driver_code)

        # Validate ELO rating if provided
        elo_rating = driver_data.current_elo_rating or 1500
        validated_elo = DataValidator.validate_elo_rating(elo_rating)

        # Create driver
        return self.create(
            db=db,
            obj_in=driver_data,
            driver_name=normalized_name,
            driver_code=validated_code,
            current_elo_rating=validated_elo
        )

    def get_driver_by_code(self, db: Session, driver_code: str) -> Optional[DriverResponse]:
        """Get driver by three-letter code."""
        driver = db.query(Driver).filter(
            Driver.driver_code == driver_code.upper()
        ).first()

        if driver:
            return self._to_response_schema(driver)
        return None

    def get_drivers_rankings(
        self,
        db: Session,
        season: Optional[int] = None,
        limit: int = 20
    ) -> List[DriverRanking]:
        """Get driver rankings based on ELO rating and season performance."""
        current_year = datetime.now().year
        season = season or current_year

        # Query drivers with their current season stats
        query = db.query(Driver).join(Driver.current_team, isouter=True)

        # Order by ELO rating (highest first)
        drivers = query.order_by(desc(Driver.current_elo_rating)).limit(limit).all()

        rankings = []
        for position, driver in enumerate(drivers, 1):
            # Calculate season statistics
            season_stats = self._get_driver_season_stats(db, driver.driver_id, season)

            ranking = DriverRanking(
                position=position,
                driver_id=driver.driver_id,
                driver_code=driver.driver_code,
                driver_name=driver.driver_name,
                current_team_id=driver.current_team_id,
                team_name=driver.current_team.team_name if driver.current_team else None,
                current_elo_rating=driver.current_elo_rating,
                season_wins=season_stats['wins'],
                season_points=season_stats['points'],
                championship_position=season_stats['championship_position']
            )
            rankings.append(ranking)

        return rankings

    def get_driver_statistics(
        self,
        db: Session,
        driver_id: int,
        season: Optional[int] = None
    ) -> DriverStatistics:
        """Get comprehensive driver statistics."""
        driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if not driver:
            from .base import DataTransformationError
            raise DataTransformationError(f"Driver with ID {driver_id} not found")

        # Base query for race results
        results_query = db.query(RaceResult).filter(RaceResult.driver_id == driver_id)

        # Filter by season if specified
        if season:
            from ..models.f1_models import Race
            results_query = results_query.join(Race).filter(Race.season_year == season)

        results = results_query.all()

        # Calculate statistics
        total_races = len(results)
        total_wins = sum(1 for r in results if r.final_position == 1)
        total_podiums = sum(1 for r in results if r.final_position and r.final_position <= 3)
        total_points = sum(float(r.points or 0) for r in results)

        # Calculate rates
        win_rate = DataTransformer.safe_divide(total_wins, total_races)
        podium_rate = DataTransformer.safe_divide(total_podiums, total_races)

        # Calculate average finish position (only for finished races)
        finished_positions = [r.final_position for r in results
                             if r.final_position and r.status.value == 'finished']
        avg_position = (sum(finished_positions) / len(finished_positions)
                       if finished_positions else None)

        # Calculate current streak (wins or podiums)
        current_streak = self._calculate_current_streak(results)

        return DriverStatistics(
            driver_id=driver_id,
            total_races=total_races,
            total_wins=total_wins,
            total_podiums=total_podiums,
            total_points=total_points,
            win_rate=win_rate,
            podium_rate=podium_rate,
            average_finish_position=avg_position,
            current_streak=current_streak
        )

    def update_elo_rating(
        self,
        db: Session,
        driver_id: int,
        new_rating: int
    ) -> DriverResponse:
        """Update driver ELO rating with validation."""
        driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
        if not driver:
            from .base import DataTransformationError
            raise DataTransformationError(f"Driver with ID {driver_id} not found")

        validated_elo = DataValidator.validate_elo_rating(new_rating)

        driver.current_elo_rating = validated_elo
        driver.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(driver)

        return self._to_response_schema(driver)

    def search_drivers(
        self,
        db: Session,
        query: str,
        limit: int = 10
    ) -> List[DriverBasic]:
        """Search drivers by name or code."""
        search_term = f"%{query.strip()}%"

        drivers = db.query(Driver).filter(
            (Driver.driver_name.ilike(search_term)) |
            (Driver.driver_code.ilike(search_term))
        ).limit(limit).all()

        return [
            DriverBasic(
                driver_id=d.driver_id,
                driver_code=d.driver_code,
                driver_name=d.driver_name,
                current_elo_rating=d.current_elo_rating
            )
            for d in drivers
        ]

    def get_drivers_by_team(
        self,
        db: Session,
        team_id: int
    ) -> List[DriverResponse]:
        """Get all drivers for a specific team."""
        drivers = db.query(Driver).filter(Driver.current_team_id == team_id).all()
        return [self._to_response_schema(driver) for driver in drivers]

    def _get_driver_season_stats(
        self,
        db: Session,
        driver_id: int,
        season: int
    ) -> Dict[str, Any]:
        """Get driver statistics for a specific season."""
        from ..models.f1_models import Race

        # Get season results
        results = db.query(RaceResult).join(Race).filter(
            RaceResult.driver_id == driver_id,
            Race.season_year == season
        ).all()

        wins = sum(1 for r in results if r.final_position == 1)
        points = sum(float(r.points or 0) for r in results)

        # Calculate championship position (simplified - would need all drivers' points)
        championship_position = self._calculate_championship_position(db, driver_id, season)

        return {
            'wins': wins,
            'points': points,
            'championship_position': championship_position
        }

    def _calculate_championship_position(
        self,
        db: Session,
        driver_id: int,
        season: int
    ) -> Optional[int]:
        """Calculate driver's championship position for the season."""
        from ..models.f1_models import Race
        from sqlalchemy import func

        # Get all drivers' points for the season
        driver_points = db.query(
            RaceResult.driver_id,
            func.sum(RaceResult.points).label('total_points')
        ).join(Race).filter(
            Race.season_year == season
        ).group_by(RaceResult.driver_id).subquery()

        # Rank drivers by points
        ranked_drivers = db.query(
            driver_points.c.driver_id,
            driver_points.c.total_points,
            func.row_number().over(
                order_by=desc(driver_points.c.total_points)
            ).label('position')
        ).subquery()

        # Get position for specific driver
        result = db.query(ranked_drivers.c.position).filter(
            ranked_drivers.c.driver_id == driver_id
        ).first()

        return result.position if result else None

    def _calculate_current_streak(self, results: List[RaceResult]) -> int:
        """Calculate current win/podium streak."""
        if not results:
            return 0

        # Sort by race date (most recent first)
        # Note: This is simplified - would need to join with Race table for proper sorting
        sorted_results = sorted(
            results,
            key=lambda r: r.created_at,
            reverse=True
        )

        streak = 0
        for result in sorted_results:
            if result.final_position and result.final_position <= 3:
                streak += 1
            else:
                break

        return streak